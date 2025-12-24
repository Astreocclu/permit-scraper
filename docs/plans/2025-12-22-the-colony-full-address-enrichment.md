# The Colony Full Address Enrichment Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Enrich The Colony permit addresses (currently street names only) with full street addresses (number + name) via Denton CAD.

**Architecture:** The Colony's eTRAKiT portal only provides street names in search results (e.g., "BAKER DR" without house numbers). We'll use the existing Denton CAD ArcGIS API in `enrich_cad.py` to reverse-lookup properties by street name and match them to permits.

**Tech Stack:** Python, Playwright, ArcGIS REST API, PostgreSQL

---

## Background

### Current State
- **The Colony raw permits:** 10 permits with street names only (e.g., `raw_cells: ["0701-4211", "BAKER DR", "DKB_00558883"]`)
- **load_permits.py:** Already modified to accept partial addresses from The Colony
- **denton_cad_search.py:** Playwright scraper exists but needs debugging (React UI is complex)
- **enrich_cad.py:** Has working Denton CAD ArcGIS API support via `query_county_cad()`

### Available Data Sources
1. **Denton CAD ArcGIS API** (preferred) - `https://gis.dentoncounty.gov/arcgis/rest/services/CAD/MapServer/0/query`
   - Fast, reliable, already integrated
   - Query by `situs_street LIKE '%BAKER%'` + filter by city
2. **Denton CAD Web Portal** - `https://denton.prodigycad.com/property-search`
   - Complex React UI, fragile
   - Only needed if ArcGIS doesn't work

### Enrichment Strategy
Since The Colony permits only have street names, we'll:
1. Query Denton CAD for ALL properties on that street in The Colony
2. Store the address lookup table
3. Load permits with partial addresses
4. Cross-reference during CAD enrichment

---

## Task 1: Add Street-Based Denton CAD Query

**Files:**
- Modify: `scripts/enrich_cad.py:666-677` (add new query type)
- Create: `scripts/enrich_colony_addresses.py`
- Test: `tests/test_enrich_colony.py`

**Step 1: Write the failing test**

Create `tests/test_enrich_colony.py`:

```python
"""Test The Colony address enrichment via Denton CAD."""
import pytest


def test_query_denton_by_street_name():
    """Can query Denton CAD by street name only."""
    from scripts.enrich_cad import query_denton_by_street

    results = query_denton_by_street("BAKER", city_filter="THE COLONY", limit=10)

    assert isinstance(results, list)
    # Should return property records with full addresses
    for r in results:
        assert 'situs_addr' in r or 'address' in r


def test_query_returns_full_addresses():
    """Results should have full addresses (number + street)."""
    from scripts.enrich_cad import query_denton_by_street

    results = query_denton_by_street("BAKER", city_filter="THE COLONY", limit=5)

    # At least some results should have house numbers
    addresses_with_numbers = [
        r for r in results
        if r.get('situs_addr', '').strip() and
           r['situs_addr'][0].isdigit()
    ]
    assert len(addresses_with_numbers) > 0, "No full addresses found"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_enrich_colony.py::test_query_denton_by_street_name -v`
Expected: FAIL with "cannot import name 'query_denton_by_street'"

**Step 3: Add query_denton_by_street function**

Add to `scripts/enrich_cad.py` after line 744 (after `query_county_cad`):

```python
def query_denton_by_street(street_name: str, city_filter: str = None, limit: int = 100) -> list:
    """
    Query Denton CAD for all properties on a street.
    Used for The Colony permits which only have street names.

    Args:
        street_name: Street name without number (e.g., "BAKER" or "BAKER DR")
        city_filter: Optional city name to filter (e.g., "THE COLONY")
        limit: Max results to return

    Returns:
        List of property records with full addresses
    """
    config = COUNTY_CONFIGS['denton']

    # Strip any trailing suffix for broader match
    street_core = re.sub(
        r'\s+(DR|DRIVE|ST|STREET|AVE|AVENUE|BLVD|LN|LANE|CT|COURT|CIR|RD|ROAD|WAY|PL)\.?$',
        '', street_name.upper(), flags=re.I
    ).strip()

    # Build query - search by street name only
    where_clause = f"situs_street LIKE '%{street_core}%'"
    if city_filter:
        where_clause += f" AND situs_city LIKE '%{city_filter.upper()}%'"

    params = {
        "where": where_clause,
        "outFields": ",".join(config['fields']),
        "f": "json",
        "resultRecordCount": limit
    }

    try:
        response = requests.get(config['url'], params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        features = data.get("features", [])

        results = []
        fm = config['field_map']

        for feature in features:
            raw = feature.get("attributes", {})

            # Build full situs address
            situs_num = str(raw.get(fm.get('situs_num', ''), '') or '').strip()
            situs_street = str(raw.get(fm.get('situs_street', ''), '') or '').strip()
            situs_suffix = str(raw.get(fm.get('situs_suffix', ''), '') or '').strip()
            situs_city = str(raw.get(fm.get('situs_city', ''), '') or '').strip()

            full_addr = f"{situs_num} {situs_street} {situs_suffix}".strip()

            results.append({
                'situs_addr': full_addr,
                'situs_city': situs_city,
                'owner_name': raw.get(fm.get('owner_name', ''), ''),
                'market_value': raw.get(fm.get('market_value', '')),
                'year_built': raw.get(fm.get('year_built', '')),
                'account_num': raw.get(fm.get('account_num', '')),
            })

        return results

    except requests.RequestException as e:
        logger.warning(f"Denton CAD query failed: {e}")
        return []
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_enrich_colony.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add scripts/enrich_cad.py tests/test_enrich_colony.py
git commit -m "feat: add street-based Denton CAD query for The Colony enrichment"
```

---

## Task 2: Create Colony Address Enrichment Script

**Files:**
- Create: `scripts/enrich_colony_addresses.py`
- Test: `tests/test_enrich_colony.py` (extend)

**Step 1: Write the failing test**

Add to `tests/test_enrich_colony.py`:

```python
def test_enrich_colony_permit():
    """Can enrich a Colony permit with partial address."""
    from scripts.enrich_colony_addresses import enrich_permit

    permit = {
        'permit_id': '0701-4211',
        'address': '',
        'raw_cells': ['0701-4211', 'BAKER DR', 'DKB_00558883']
    }

    enriched = enrich_permit(permit)

    # Should have found a full address
    assert enriched['address'], "Address should be enriched"
    assert enriched['address'][0].isdigit(), "Should start with house number"
    assert 'BAKER' in enriched['address'].upper()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_enrich_colony.py::test_enrich_colony_permit -v`
Expected: FAIL with "No module named 'scripts.enrich_colony_addresses'"

**Step 3: Create enrich_colony_addresses.py**

Create `scripts/enrich_colony_addresses.py`:

```python
#!/usr/bin/env python3
"""
THE COLONY ADDRESS ENRICHMENT
Enriches The Colony permits with full addresses from Denton CAD.

The Colony's eTRAKiT portal only provides street names (e.g., "BAKER DR").
This script queries Denton CAD to find matching properties and assigns
the best-matching full address.

Usage:
    python3 scripts/enrich_colony_addresses.py                # Process raw JSON
    python3 scripts/enrich_colony_addresses.py --dry-run      # Preview only
    python3 scripts/enrich_colony_addresses.py --reload       # Reload to DB after
"""

import argparse
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
load_dotenv()

# Add parent to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.enrich_cad import query_denton_by_street

DATA_DIR = Path(__file__).parent.parent / "data" / "raw"


def extract_street_from_permit(permit: dict) -> Optional[str]:
    """Extract street name from permit raw_cells."""
    raw = permit.get('raw_cells', [])
    if len(raw) >= 2:
        street = raw[1]
        # Skip contractor codes
        if street and not street.startswith(('DKB', 'JJ_', 'KB_')):
            return street.strip().upper()
    return None


def build_address_lookup(street_names: set) -> dict:
    """
    Query Denton CAD for all unique street names.
    Returns {street_name: [list of full addresses]}
    """
    lookup = {}

    for street in sorted(street_names):
        print(f"  Querying Denton CAD for: {street}")
        results = query_denton_by_street(street, city_filter="THE COLONY", limit=50)

        addresses = []
        for r in results:
            addr = r.get('situs_addr', '').strip()
            if addr and addr[0].isdigit():
                addresses.append(addr)

        if addresses:
            lookup[street] = addresses
            print(f"    Found {len(addresses)} addresses")
        else:
            print(f"    No addresses found")

    return lookup


def enrich_permit(permit: dict, lookup: dict = None) -> dict:
    """
    Enrich a single permit with full address from CAD.

    Args:
        permit: Permit dict with raw_cells
        lookup: Pre-built address lookup (optional, will query if not provided)

    Returns:
        Permit dict with address filled in
    """
    # Already has address
    if permit.get('address'):
        return permit

    street = extract_street_from_permit(permit)
    if not street:
        return permit

    # Build lookup if not provided
    if lookup is None:
        results = query_denton_by_street(street, city_filter="THE COLONY", limit=10)
        addresses = [r.get('situs_addr', '').strip() for r in results
                    if r.get('situs_addr', '').strip() and r['situs_addr'][0].isdigit()]
        lookup = {street: addresses} if addresses else {}

    # Find matching addresses
    # Strip suffix for matching
    street_core = street.replace(' DR', '').replace(' ST', '').replace(' LN', '').strip()

    for lookup_street, addresses in lookup.items():
        if street_core in lookup_street.upper():
            if addresses:
                # Use first matching address
                permit['address'] = addresses[0]
                permit['address_source'] = 'DENTON_CAD'
                permit['address_candidates'] = len(addresses)
                break

    return permit


def enrich_colony_permits(dry_run: bool = False) -> dict:
    """
    Enrich all The Colony permits from raw JSON.

    Returns:
        Summary stats
    """
    raw_file = DATA_DIR / 'the_colony_raw.json'
    if not raw_file.exists():
        print(f"ERROR: {raw_file} not found")
        return {'error': 'file not found'}

    with open(raw_file) as f:
        data = json.load(f)

    permits = data.get('permits', data) if isinstance(data, dict) else data
    print(f"Loaded {len(permits)} permits from The Colony")

    # Extract unique street names
    street_names = set()
    for p in permits:
        street = extract_street_from_permit(p)
        if street:
            street_names.add(street)

    print(f"Found {len(street_names)} unique streets to lookup")

    # Build address lookup
    print("\n[1/3] Querying Denton CAD...")
    lookup = build_address_lookup(street_names)

    print(f"\n[2/3] Enriching {len(permits)} permits...")
    enriched_count = 0
    for permit in permits:
        original_addr = permit.get('address')
        permit = enrich_permit(permit, lookup)
        if permit.get('address') and not original_addr:
            enriched_count += 1
            print(f"  {permit['permit_id']}: {permit['address']}")

    # Save enriched data
    output_file = DATA_DIR / 'the_colony_enriched.json'

    if not dry_run:
        print(f"\n[3/3] Saving to {output_file}...")
        output = {
            'source': 'the_colony',
            'enriched_at': datetime.now().isoformat(),
            'enrichment_method': 'DENTON_CAD',
            'permits': permits,
        }
        with open(output_file, 'w') as f:
            json.dump(output, f, indent=2)
    else:
        print(f"\n[3/3] DRY RUN - not saving")

    return {
        'total': len(permits),
        'enriched': enriched_count,
        'streets_found': len([s for s in street_names if s in lookup]),
        'streets_missing': len([s for s in street_names if s not in lookup]),
    }


def main():
    parser = argparse.ArgumentParser(description='Enrich The Colony permits with Denton CAD addresses')
    parser.add_argument('--dry-run', action='store_true', help='Preview without saving')
    parser.add_argument('--reload', action='store_true', help='Reload enriched data to DB after')
    args = parser.parse_args()

    print("=" * 60)
    print("THE COLONY ADDRESS ENRICHMENT")
    print("=" * 60)
    print()

    result = enrich_colony_permits(dry_run=args.dry_run)

    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total permits: {result.get('total', 0)}")
    print(f"Enriched: {result.get('enriched', 0)}")
    print(f"Streets found in CAD: {result.get('streets_found', 0)}")
    print(f"Streets not found: {result.get('streets_missing', 0)}")

    if args.reload and not args.dry_run:
        print("\nReloading to database...")
        import subprocess
        subprocess.run(['python3', 'scripts/load_permits.py', '--file', 'data/raw/the_colony_enriched.json'])


if __name__ == '__main__':
    main()
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_enrich_colony.py -v`
Expected: PASS (may need network access for CAD query)

**Step 5: Commit**

```bash
git add scripts/enrich_colony_addresses.py tests/test_enrich_colony.py
git commit -m "feat: add The Colony address enrichment script"
```

---

## Task 3: Integration Test - Run Enrichment

**Files:**
- None (testing existing code)

**Step 1: Run the enrichment script in dry-run mode**

```bash
cd /home/reid/testhome/permit-scraper
python3 scripts/enrich_colony_addresses.py --dry-run
```

Expected output:
```
============================================================
THE COLONY ADDRESS ENRICHMENT
============================================================

Loaded 10 permits from The Colony
Found 1 unique streets to lookup

[1/3] Querying Denton CAD...
  Querying Denton CAD for: BAKER DR
    Found X addresses

[2/3] Enriching 10 permits...
  0701-4211: 123 BAKER DR
  ...

[3/3] DRY RUN - not saving
```

**Step 2: If addresses found, run without dry-run**

```bash
python3 scripts/enrich_colony_addresses.py
```

**Step 3: Verify enriched file**

```bash
python3 -c "
import json
with open('data/raw/the_colony_enriched.json') as f:
    data = json.load(f)
for p in data['permits'][:5]:
    print(f\"{p['permit_id']}: {p.get('address', 'NO ADDRESS')}\")
"
```

**Step 4: Reload to database**

```bash
python3 scripts/load_permits.py --file data/raw/the_colony_enriched.json
```

**Step 5: Verify in database**

```bash
python3 -c "
import os, psycopg2
from dotenv import load_dotenv
load_dotenv()
conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()
cur.execute(\"\"\"
    SELECT permit_id, property_address
    FROM leads_permit
    WHERE LOWER(city) LIKE '%colony%'
    LIMIT 10
\"\"\")
for row in cur.fetchall():
    print(f'{row[0]}: {row[1]}')
"
```

**Step 6: Commit**

```bash
git add -A
git commit -m "test: verify The Colony address enrichment pipeline"
```

---

## Task 4: Handle Edge Cases - Multiple Street Matches

**Files:**
- Modify: `scripts/enrich_colony_addresses.py`
- Test: `tests/test_enrich_colony.py` (extend)

**Step 1: Write the failing test**

Add to `tests/test_enrich_colony.py`:

```python
def test_handles_multiple_addresses_on_street():
    """When multiple addresses on street, picks best match."""
    from scripts.enrich_colony_addresses import select_best_address

    # Permit contractor code might hint at property
    permit = {
        'permit_id': '0701-4211',
        'raw_cells': ['0701-4211', 'BAKER DR', 'DKB_00558883']
    }

    candidates = [
        '100 BAKER DR',
        '200 BAKER DR',
        '300 BAKER DR',
    ]

    # Should select one (implementation can refine logic)
    selected = select_best_address(permit, candidates)
    assert selected in candidates
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_enrich_colony.py::test_handles_multiple_addresses_on_street -v`
Expected: FAIL with "cannot import name 'select_best_address'"

**Step 3: Add select_best_address function**

Add to `scripts/enrich_colony_addresses.py`:

```python
def select_best_address(permit: dict, candidates: list) -> Optional[str]:
    """
    Select best address from multiple candidates.

    Heuristics:
    1. If only one candidate, use it
    2. If contractor code contains numbers, try to match
    3. Otherwise use first (most recent in CAD)
    """
    if not candidates:
        return None

    if len(candidates) == 1:
        return candidates[0]

    # Try to extract numbers from contractor code
    raw = permit.get('raw_cells', [])
    if len(raw) >= 3:
        contractor = raw[2]
        # Extract any number sequence
        import re
        numbers = re.findall(r'\d+', contractor)
        for num in numbers:
            for addr in candidates:
                if addr.startswith(num + ' '):
                    return addr

    # Default to first (CAD usually returns newest first)
    return candidates[0]
```

Update `enrich_permit()` to use `select_best_address()`:

```python
# In enrich_permit(), replace:
#   permit['address'] = addresses[0]
# With:
    permit['address'] = select_best_address(permit, addresses)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_enrich_colony.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add scripts/enrich_colony_addresses.py tests/test_enrich_colony.py
git commit -m "feat: add best-address selection for multi-match streets"
```

---

## Task 5: Run Full CAD Enrichment Pipeline

**Files:**
- None (running existing pipeline)

**Step 1: Run The Colony enrichment**

```bash
python3 scripts/enrich_colony_addresses.py --reload
```

**Step 2: Run standard CAD enrichment**

```bash
python3 scripts/enrich_cad.py --limit 20 --fresh
```

**Step 3: Verify The Colony permits are enriched**

```bash
python3 -c "
import os, psycopg2
from dotenv import load_dotenv
load_dotenv()
conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()
cur.execute(\"\"\"
    SELECT p.permit_id, p.property_address, prop.owner_name, prop.market_value
    FROM leads_permit p
    LEFT JOIN leads_property prop ON p.property_address = prop.property_address
    WHERE LOWER(p.city) LIKE '%colony%'
    LIMIT 10
\"\"\")
for row in cur.fetchall():
    print(f'{row[0]}: {row[1]} | {row[2]} | \${row[3]:,.0f}' if row[3] else f'{row[0]}: {row[1]} | {row[2]} | N/A')
"
```

**Step 4: Commit**

```bash
git add -A
git commit -m "chore: complete The Colony enrichment pipeline"
```

---

## Task 6: Update Documentation

**Files:**
- Modify: `CLAUDE.md`
- Modify: `docs/the-colony-fix-options.md`

**Step 1: Update CLAUDE.md**

Add to the "Working Portals" section under eTRAKiT:

```markdown
- The Colony - `etrakit.py` + `enrich_colony_addresses.py` (partial addresses, CAD enriched)
```

**Step 2: Update docs/the-colony-fix-options.md**

Add "Solution Implemented" section:

```markdown
## Solution Implemented (December 2025)

The Colony address enrichment uses a multi-stage pipeline:

1. **Scrape** - `etrakit.py the_colony 100` extracts permits with street names only
2. **Enrich** - `enrich_colony_addresses.py` queries Denton CAD for full addresses
3. **Load** - `load_permits.py` loads enriched permits to database
4. **CAD Enrich** - `enrich_cad.py` adds owner/value data

### Commands

\`\`\`bash
# Full pipeline
python3 scrapers/etrakit.py the_colony 100
python3 scripts/enrich_colony_addresses.py --reload
python3 scripts/enrich_cad.py --fresh

# Quick re-enrichment
python3 scripts/enrich_colony_addresses.py
\`\`\`
```

**Step 3: Commit**

```bash
git add CLAUDE.md docs/the-colony-fix-options.md
git commit -m "docs: document The Colony enrichment solution"
```

---

## Summary

| Task | Description | Files Changed |
|------|-------------|---------------|
| 1 | Add street-based Denton CAD query | `enrich_cad.py`, `tests/test_enrich_colony.py` |
| 2 | Create Colony enrichment script | `enrich_colony_addresses.py` |
| 3 | Integration test | (testing only) |
| 4 | Handle multiple address matches | `enrich_colony_addresses.py` |
| 5 | Run full pipeline | (testing only) |
| 6 | Update documentation | `CLAUDE.md`, `docs/the-colony-fix-options.md` |

### Expected Result
- The Colony permits will have full addresses (e.g., "123 BAKER DR" instead of just "BAKER DR")
- CAD enrichment will work normally for these permits
- Documentation will reflect the solution
