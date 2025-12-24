# CAD Enrichment Backfill Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix address matching so 80-91% of high-value leads (pools, roofs, foundation, outdoor living) get CAD enrichment data (market_value, owner_name) for scoring.

**Architecture:** New backfill script builds full addresses from permit data (`{street}, {city}, TX`), queries free CAD APIs, and UPSERTs `leads_property` using the original permit address as key (so JOINs work). Reuses existing CAD query logic from `enrich_cad.py`.

**Tech Stack:** Python 3, psycopg2, requests, existing CAD API configs

**Problem Context:**
- Permits have short addresses: `14108 SANTA ANN ST`
- Properties have full addresses: `16975 RED BUD DR FRISCO TX 75071`
- The JOIN in `score_leads.py` requires exact match on `property_address`
- Currently losing 80-91% of high-value leads due to this mismatch

---

## Task 1: Create Address Builder Function

**Files:**
- Create: `scripts/backfill_cad_enrichment.py`
- Test: `tests/test_backfill_cad.py`

**Step 1: Write the failing test**

Create `tests/test_backfill_cad.py`:

```python
"""Tests for CAD enrichment backfill."""
import pytest


class TestBuildFullAddress:
    """Test address construction from permit data."""

    def test_basic_address(self):
        from scripts.backfill_cad_enrichment import build_full_address

        result = build_full_address("14108 SANTA ANN ST", "frisco")
        assert result == "14108 SANTA ANN ST, Frisco, TX"

    def test_uppercase_city(self):
        from scripts.backfill_cad_enrichment import build_full_address

        result = build_full_address("123 MAIN DR", "MCKINNEY")
        assert result == "123 MAIN DR, Mckinney, TX"

    def test_lowercase_city(self):
        from scripts.backfill_cad_enrichment import build_full_address

        result = build_full_address("456 OAK LN", "allen")
        assert result == "456 OAK LN, Allen, TX"

    def test_multi_word_city(self):
        from scripts.backfill_cad_enrichment import build_full_address

        result = build_full_address("789 ELM ST", "fort worth")
        assert result == "789 ELM ST, Fort Worth, TX"

    def test_empty_address_returns_none(self):
        from scripts.backfill_cad_enrichment import build_full_address

        assert build_full_address("", "frisco") is None
        assert build_full_address(None, "frisco") is None

    def test_empty_city_returns_none(self):
        from scripts.backfill_cad_enrichment import build_full_address

        assert build_full_address("123 MAIN ST", "") is None
        assert build_full_address("123 MAIN ST", None) is None

    def test_strips_whitespace(self):
        from scripts.backfill_cad_enrichment import build_full_address

        result = build_full_address("  123 MAIN ST  ", "  frisco  ")
        assert result == "123 MAIN ST, Frisco, TX"
```

**Step 2: Run test to verify it fails**

```bash
cd /home/reid/testhome/permit-scraper && pytest tests/test_backfill_cad.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.backfill_cad_enrichment'`

**Step 3: Write minimal implementation**

Create `scripts/backfill_cad_enrichment.py`:

```python
#!/usr/bin/env python3
"""
CAD Enrichment Backfill Script.

Fixes address matching by building full addresses from permit data,
querying CAD APIs, and populating leads_property for scoring.

Problem: Permits have "14108 SANTA ANN ST", properties have "14108 SANTA ANN ST, Frisco TX 75071"
Solution: Build full address using permit's city column, query CAD, store with original address as key.

Usage:
    python3 scripts/backfill_cad_enrichment.py --limit 10      # Test run
    python3 scripts/backfill_cad_enrichment.py                  # Full backfill
    python3 scripts/backfill_cad_enrichment.py --city frisco    # Single city
    python3 scripts/backfill_cad_enrichment.py --dry-run        # Preview without DB writes
"""

from typing import Optional


def build_full_address(street_address: Optional[str], city: Optional[str]) -> Optional[str]:
    """
    Build a full queryable address from permit data.

    Args:
        street_address: Street address from permit (e.g., "14108 SANTA ANN ST")
        city: City from permit (e.g., "frisco")

    Returns:
        Full address like "14108 SANTA ANN ST, Frisco, TX" or None if invalid
    """
    if not street_address or not city:
        return None

    street = street_address.strip()
    city_clean = city.strip().title()

    if not street or not city_clean:
        return None

    return f"{street}, {city_clean}, TX"
```

**Step 4: Run test to verify it passes**

```bash
cd /home/reid/testhome/permit-scraper && pytest tests/test_backfill_cad.py -v
```

Expected: All 7 tests PASS

**Step 5: Commit**

```bash
git add scripts/backfill_cad_enrichment.py tests/test_backfill_cad.py
git commit -m "feat: add build_full_address for CAD backfill"
```

---

## Task 2: Add City-to-County Lookup

**Files:**
- Modify: `scripts/backfill_cad_enrichment.py`
- Modify: `tests/test_backfill_cad.py`

**Step 1: Write the failing test**

Add to `tests/test_backfill_cad.py`:

```python
class TestGetCountyForCity:
    """Test city to county mapping."""

    def test_collin_cities(self):
        from scripts.backfill_cad_enrichment import get_county_for_city

        assert get_county_for_city("frisco") == "collin"
        assert get_county_for_city("mckinney") == "collin"
        assert get_county_for_city("allen") == "collin"
        assert get_county_for_city("plano") == "collin"
        assert get_county_for_city("prosper") == "collin"

    def test_tarrant_cities(self):
        from scripts.backfill_cad_enrichment import get_county_for_city

        assert get_county_for_city("fort worth") == "tarrant"
        assert get_county_for_city("arlington") == "tarrant"
        assert get_county_for_city("southlake") == "tarrant"
        assert get_county_for_city("keller") == "tarrant"

    def test_dallas_cities(self):
        from scripts.backfill_cad_enrichment import get_county_for_city

        assert get_county_for_city("dallas") == "dallas"
        assert get_county_for_city("irving") == "dallas"
        assert get_county_for_city("grand prairie") == "dallas"
        assert get_county_for_city("mesquite") == "dallas"

    def test_denton_cities(self):
        from scripts.backfill_cad_enrichment import get_county_for_city

        assert get_county_for_city("denton") == "denton"
        assert get_county_for_city("flower mound") == "denton"
        assert get_county_for_city("lewisville") == "denton"

    def test_case_insensitive(self):
        from scripts.backfill_cad_enrichment import get_county_for_city

        assert get_county_for_city("FRISCO") == "collin"
        assert get_county_for_city("Frisco") == "collin"
        assert get_county_for_city("FrIsCo") == "collin"

    def test_unknown_city_returns_none(self):
        from scripts.backfill_cad_enrichment import get_county_for_city

        assert get_county_for_city("unknown_city") is None
        assert get_county_for_city("") is None
        assert get_county_for_city(None) is None
```

**Step 2: Run test to verify it fails**

```bash
cd /home/reid/testhome/permit-scraper && pytest tests/test_backfill_cad.py::TestGetCountyForCity -v
```

Expected: FAIL with `ImportError: cannot import name 'get_county_for_city'`

**Step 3: Write minimal implementation**

Add to `scripts/backfill_cad_enrichment.py` after the imports:

```python
# City to county mapping for DFW area
# Only includes cities in counties with FREE CAD APIs
CITY_TO_COUNTY = {
    # Collin County (free API)
    'frisco': 'collin',
    'mckinney': 'collin',
    'allen': 'collin',
    'plano': 'collin',
    'prosper': 'collin',
    'celina': 'collin',
    'anna': 'collin',
    'princeton': 'collin',
    'melissa': 'collin',
    'fairview': 'collin',
    'lucas': 'collin',
    'murphy': 'collin',
    'wylie': 'collin',
    'sachse': 'collin',

    # Tarrant County (free API)
    'fort worth': 'tarrant',
    'arlington': 'tarrant',
    'north richland hills': 'tarrant',
    'hurst': 'tarrant',
    'bedford': 'tarrant',
    'euless': 'tarrant',
    'grapevine': 'tarrant',
    'colleyville': 'tarrant',
    'southlake': 'tarrant',
    'keller': 'tarrant',
    'watauga': 'tarrant',
    'haltom city': 'tarrant',
    'richland hills': 'tarrant',
    'mansfield': 'tarrant',

    # Dallas County (free API)
    'dallas': 'dallas',
    'irving': 'dallas',
    'grand prairie': 'dallas',
    'mesquite': 'dallas',
    'garland': 'dallas',
    'richardson': 'dallas',
    'carrollton': 'dallas',
    'farmers branch': 'dallas',
    'coppell': 'dallas',
    'desoto': 'dallas',
    'duncanville': 'dallas',
    'cedar hill': 'dallas',
    'lancaster': 'dallas',
    'rowlett': 'dallas',

    # Denton County (free API)
    'denton': 'denton',
    'lewisville': 'denton',
    'flower mound': 'denton',
    'highland village': 'denton',
    'the colony': 'denton',
    'little elm': 'denton',
    'corinth': 'denton',
    'aubrey': 'denton',
    'pilot point': 'denton',
    'sanger': 'denton',
    'argyle': 'denton',
    'bartonville': 'denton',
    'trophy club': 'denton',

    # Kaufman County (free API)
    'forney': 'kaufman',
    'terrell': 'kaufman',
    'kaufman': 'kaufman',

    # Rockwall County (free API)
    'rockwall': 'rockwall',
    'royse city': 'rockwall',
    'heath': 'rockwall',
    'fate': 'rockwall',
}


def get_county_for_city(city: Optional[str]) -> Optional[str]:
    """
    Get the county for a city.

    Args:
        city: City name (case-insensitive)

    Returns:
        County name (lowercase) or None if not found
    """
    if not city:
        return None
    return CITY_TO_COUNTY.get(city.lower().strip())
```

**Step 4: Run test to verify it passes**

```bash
cd /home/reid/testhome/permit-scraper && pytest tests/test_backfill_cad.py::TestGetCountyForCity -v
```

Expected: All 6 tests PASS

**Step 5: Commit**

```bash
git add scripts/backfill_cad_enrichment.py tests/test_backfill_cad.py
git commit -m "feat: add city-to-county mapping for CAD lookup"
```

---

## Task 3: Add Database Fetch for Unenriched Permits

**Files:**
- Modify: `scripts/backfill_cad_enrichment.py`
- Modify: `tests/test_backfill_cad.py`

**Step 1: Write the failing test**

Add to `tests/test_backfill_cad.py`:

```python
class TestFetchUnenrichedPermits:
    """Test fetching permits that need enrichment."""

    def test_query_structure(self):
        """Verify the SQL query selects correct columns and filters."""
        from scripts.backfill_cad_enrichment import build_unenriched_permits_query

        query = build_unenriched_permits_query()

        # Must select these columns
        assert "p.id" in query
        assert "p.property_address" in query
        assert "p.city" in query

        # Must filter for unenriched (no successful leads_property match)
        assert "LEFT JOIN leads_property" in query
        assert "enrichment_status" in query

        # Must only get active permits
        assert "processing_bin = 'active'" in query

    def test_query_with_city_filter(self):
        from scripts.backfill_cad_enrichment import build_unenriched_permits_query

        query = build_unenriched_permits_query(city="frisco")
        assert "LOWER(p.city) = LOWER" in query

    def test_query_with_limit(self):
        from scripts.backfill_cad_enrichment import build_unenriched_permits_query

        query = build_unenriched_permits_query(limit=100)
        assert "LIMIT 100" in query
```

**Step 2: Run test to verify it fails**

```bash
cd /home/reid/testhome/permit-scraper && pytest tests/test_backfill_cad.py::TestFetchUnenrichedPermits -v
```

Expected: FAIL with `ImportError: cannot import name 'build_unenriched_permits_query'`

**Step 3: Write minimal implementation**

Add to `scripts/backfill_cad_enrichment.py`:

```python
def build_unenriched_permits_query(city: Optional[str] = None, limit: Optional[int] = None) -> str:
    """
    Build SQL query to fetch permits needing CAD enrichment.

    A permit needs enrichment if:
    - No matching leads_property record exists, OR
    - The leads_property record has enrichment_status != 'success'

    Args:
        city: Optional city filter (case-insensitive)
        limit: Optional limit on results

    Returns:
        SQL query string
    """
    query = """
        SELECT DISTINCT
            p.id,
            p.property_address,
            p.city
        FROM leads_permit p
        LEFT JOIN leads_property prop ON p.property_address = prop.property_address
        WHERE p.property_address IS NOT NULL
          AND p.city IS NOT NULL
          AND p.processing_bin = 'active'
          AND (prop.property_address IS NULL OR prop.enrichment_status != 'success')
    """

    if city:
        query += f"\n          AND LOWER(p.city) = LOWER('{city}')"

    query += "\n        ORDER BY p.id"

    if limit:
        query += f"\n        LIMIT {limit}"

    return query
```

**Step 4: Run test to verify it passes**

```bash
cd /home/reid/testhome/permit-scraper && pytest tests/test_backfill_cad.py::TestFetchUnenrichedPermits -v
```

Expected: All 3 tests PASS

**Step 5: Commit**

```bash
git add scripts/backfill_cad_enrichment.py tests/test_backfill_cad.py
git commit -m "feat: add query builder for unenriched permits"
```

---

## Task 4: Add CAD Query Integration

**Files:**
- Modify: `scripts/backfill_cad_enrichment.py`

**Step 1: Add imports and CAD query wrapper**

This task integrates with the existing `enrich_cad.py` CAD query functions. Add to the top of `scripts/backfill_cad_enrichment.py`:

```python
#!/usr/bin/env python3
"""
CAD Enrichment Backfill Script.
[... existing docstring ...]
"""

import argparse
import logging
import os
import sys
import time
from datetime import datetime
from typing import Optional, Tuple

from dotenv import load_dotenv
load_dotenv()

import psycopg2

# Import CAD query functions from existing enrich_cad.py
# These handle the actual API calls to county CAD systems
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from enrich_cad import (
    query_cad_with_retry,
    parse_float,
    parse_int,
    is_absentee_owner,
    COUNTY_CONFIGS,
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)
```

**Step 2: Add database connection function**

Add after imports:

```python
def get_db_connection():
    """Get PostgreSQL connection from DATABASE_URL."""
    url = os.environ.get('DATABASE_URL')
    if not url:
        raise ValueError("DATABASE_URL environment variable not set")
    return psycopg2.connect(url)
```

**Step 3: Verify imports work**

```bash
cd /home/reid/testhome/permit-scraper && python3 -c "from scripts.backfill_cad_enrichment import query_cad_with_retry, COUNTY_CONFIGS; print('OK')"
```

Expected: `OK`

**Step 4: Commit**

```bash
git add scripts/backfill_cad_enrichment.py
git commit -m "feat: integrate CAD query functions from enrich_cad"
```

---

## Task 5: Add Database Upsert Function

**Files:**
- Modify: `scripts/backfill_cad_enrichment.py`
- Modify: `tests/test_backfill_cad.py`

**Step 1: Write the failing test**

Add to `tests/test_backfill_cad.py`:

```python
class TestUpsertLeadsProperty:
    """Test the leads_property upsert SQL generation."""

    def test_upsert_sql_structure(self):
        from scripts.backfill_cad_enrichment import build_upsert_property_sql

        sql = build_upsert_property_sql()

        # Must be an upsert (INSERT ... ON CONFLICT)
        assert "INSERT INTO leads_property" in sql
        assert "ON CONFLICT (property_address)" in sql
        assert "DO UPDATE SET" in sql

        # Must include key CAD fields
        assert "market_value" in sql
        assert "owner_name" in sql
        assert "year_built" in sql
        assert "enrichment_status" in sql
```

**Step 2: Run test to verify it fails**

```bash
cd /home/reid/testhome/permit-scraper && pytest tests/test_backfill_cad.py::TestUpsertLeadsProperty -v
```

Expected: FAIL with `ImportError: cannot import name 'build_upsert_property_sql'`

**Step 3: Write minimal implementation**

Add to `scripts/backfill_cad_enrichment.py`:

```python
def build_upsert_property_sql() -> str:
    """
    Build SQL for upserting CAD data into leads_property.

    Uses the ORIGINAL permit address as the key (not CAD canonical address)
    so that JOINs in score_leads.py work correctly.

    Returns:
        SQL query with placeholders for psycopg2
    """
    return """
        INSERT INTO leads_property (
            property_address,
            property_address_normalized,
            cad_account_id,
            county,
            owner_name,
            mailing_address,
            market_value,
            land_value,
            improvement_value,
            year_built,
            square_feet,
            lot_size,
            is_absentee,
            homestead_exempt,
            enrichment_status,
            enriched_at
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, false, 'success', %s
        )
        ON CONFLICT (property_address) DO UPDATE SET
            property_address_normalized = EXCLUDED.property_address_normalized,
            cad_account_id = EXCLUDED.cad_account_id,
            county = EXCLUDED.county,
            owner_name = EXCLUDED.owner_name,
            mailing_address = EXCLUDED.mailing_address,
            market_value = EXCLUDED.market_value,
            land_value = EXCLUDED.land_value,
            improvement_value = EXCLUDED.improvement_value,
            year_built = EXCLUDED.year_built,
            square_feet = EXCLUDED.square_feet,
            lot_size = EXCLUDED.lot_size,
            is_absentee = EXCLUDED.is_absentee,
            enrichment_status = 'success',
            enriched_at = EXCLUDED.enriched_at
    """
```

**Step 4: Run test to verify it passes**

```bash
cd /home/reid/testhome/permit-scraper && pytest tests/test_backfill_cad.py::TestUpsertLeadsProperty -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add scripts/backfill_cad_enrichment.py tests/test_backfill_cad.py
git commit -m "feat: add upsert SQL for leads_property"
```

---

## Task 6: Add Single Permit Processing Function

**Files:**
- Modify: `scripts/backfill_cad_enrichment.py`

**Step 1: Add the process_permit function**

Add to `scripts/backfill_cad_enrichment.py`:

```python
def process_permit(
    permit_id: int,
    property_address: str,
    city: str,
    conn,
    dry_run: bool = False
) -> Tuple[str, Optional[str]]:
    """
    Process a single permit for CAD enrichment.

    Args:
        permit_id: Database ID of the permit
        property_address: Original permit address (will be used as key)
        city: City from permit
        conn: Database connection
        dry_run: If True, don't write to database

    Returns:
        Tuple of (status, detail) where status is 'success', 'not_found', 'skip', or 'error'
    """
    # Get county for this city
    county = get_county_for_city(city)
    if not county:
        return ('skip', f'No CAD API for city: {city}')

    if county not in COUNTY_CONFIGS:
        return ('skip', f'No CAD config for county: {county}')

    # Build full address for CAD query
    full_address = build_full_address(property_address, city)
    if not full_address:
        return ('skip', 'Could not build full address')

    # Query CAD API
    try:
        cad_data, county_name, variant_used = query_cad_with_retry(full_address, county, timeout=30)
    except Exception as e:
        return ('error', str(e))

    if not cad_data:
        return ('not_found', f'No CAD match for: {full_address}')

    if dry_run:
        market_value = parse_float(cad_data.get('market_value'))
        return ('success', f'DRY RUN: Would save ${market_value:,.0f}' if market_value else 'DRY RUN: Would save (no value)')

    # Extract CAD data
    owner_name = (cad_data.get('owner_name') or '').strip()
    market_value = parse_float(cad_data.get('market_value'))
    land_value = parse_float(cad_data.get('land_value'))
    improvement_value = parse_float(cad_data.get('improvement_value'))
    year_built = parse_int(cad_data.get('year_built'))
    square_feet = parse_int(cad_data.get('square_feet'))
    lot_size = parse_float(cad_data.get('lot_size'))
    situs_addr = cad_data.get('situs_addr', '')
    account_num = cad_data.get('account_num')

    # Build mailing address
    owner_addr = (cad_data.get('owner_addr') or '').strip()
    owner_city = (cad_data.get('owner_city') or '').strip()
    owner_zip = (cad_data.get('owner_zip') or '').strip()
    mailing_address = f"{owner_addr}, {owner_city} {owner_zip}".strip(", ")

    # Detect absentee owner
    absentee = is_absentee_owner(situs_addr, mailing_address) if owner_addr else None

    # Upsert into leads_property using ORIGINAL permit address as key
    sql = build_upsert_property_sql()
    with conn.cursor() as cur:
        cur.execute(sql, (
            property_address,           # Original permit address (KEY)
            situs_addr,                 # CAD canonical address (for reference)
            account_num,
            county_name.lower() if county_name else county,
            owner_name,
            mailing_address if mailing_address else None,
            market_value,
            land_value,
            improvement_value,
            year_built,
            square_feet,
            lot_size,
            absentee,
            datetime.now()
        ))
    conn.commit()

    value_str = f'${market_value:,.0f}' if market_value else 'N/A'
    return ('success', f'{owner_name[:30]} | {value_str}')
```

**Step 2: Test the function compiles**

```bash
cd /home/reid/testhome/permit-scraper && python3 -c "from scripts.backfill_cad_enrichment import process_permit; print('OK')"
```

Expected: `OK`

**Step 3: Commit**

```bash
git add scripts/backfill_cad_enrichment.py
git commit -m "feat: add process_permit function for CAD enrichment"
```

---

## Task 7: Add Main Function and CLI

**Files:**
- Modify: `scripts/backfill_cad_enrichment.py`

**Step 1: Add main function**

Add to the end of `scripts/backfill_cad_enrichment.py`:

```python
def main():
    parser = argparse.ArgumentParser(
        description='Backfill CAD enrichment for permits with missing property data',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python3 scripts/backfill_cad_enrichment.py --limit 10      # Test with 10 permits
    python3 scripts/backfill_cad_enrichment.py --dry-run       # Preview without DB writes
    python3 scripts/backfill_cad_enrichment.py --city frisco   # Single city
    python3 scripts/backfill_cad_enrichment.py                 # Full backfill (~9 hours)
        """
    )
    parser.add_argument('--limit', type=int, help='Limit number of permits to process')
    parser.add_argument('--city', type=str, help='Filter to specific city')
    parser.add_argument('--dry-run', action='store_true', help='Preview without writing to database')
    parser.add_argument('--delay', type=float, default=1.0, help='Delay between API calls (default: 1.0s)')
    args = parser.parse_args()

    print("=" * 60)
    print("CAD ENRICHMENT BACKFILL")
    print("=" * 60)
    print(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")
    print(f"Rate limit: {args.delay}s between requests")
    if args.city:
        print(f"City filter: {args.city}")
    if args.limit:
        print(f"Limit: {args.limit} permits")
    print()

    # Connect to database
    try:
        conn = get_db_connection()
    except ValueError as e:
        print(f"ERROR: {e}")
        return 1

    # Fetch permits needing enrichment
    query = build_unenriched_permits_query(city=args.city, limit=args.limit)
    with conn.cursor() as cur:
        cur.execute(query)
        permits = cur.fetchall()

    total = len(permits)
    print(f"Found {total} permits needing enrichment")

    if total == 0:
        print("Nothing to do!")
        conn.close()
        return 0

    # Process permits
    success = 0
    not_found = 0
    skipped = 0
    errors = 0

    for i, (permit_id, property_address, city) in enumerate(permits, 1):
        county = get_county_for_city(city) or '???'

        status, detail = process_permit(
            permit_id, property_address, city, conn, dry_run=args.dry_run
        )

        # Log result
        prefix = f"[{i}/{total}] [{county.upper()[:6]:6}]"
        addr_short = property_address[:40] if property_address else 'N/A'

        if status == 'success':
            print(f"{prefix} {addr_short}... -> {detail}")
            success += 1
        elif status == 'not_found':
            print(f"{prefix} {addr_short}... -> NOT FOUND")
            not_found += 1
        elif status == 'skip':
            print(f"{prefix} {addr_short}... -> SKIP: {detail}")
            skipped += 1
        else:
            print(f"{prefix} {addr_short}... -> ERROR: {detail}")
            errors += 1

        # Rate limiting
        time.sleep(args.delay)

    # Summary
    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Success:   {success:,}")
    print(f"Not found: {not_found:,}")
    print(f"Skipped:   {skipped:,}")
    print(f"Errors:    {errors:,}")
    print(f"Total:     {total:,}")

    if success > 0 and not args.dry_run:
        print()
        print("Next step: Run scoring to update lead scores:")
        print("  python3 scripts/score_leads.py --rescore")

    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

**Step 2: Test CLI help**

```bash
cd /home/reid/testhome/permit-scraper && python3 scripts/backfill_cad_enrichment.py --help
```

Expected: Help text with all options

**Step 3: Commit**

```bash
git add scripts/backfill_cad_enrichment.py
git commit -m "feat: add CLI for CAD enrichment backfill"
```

---

## Task 8: Integration Test with Dry Run

**Files:**
- None (testing only)

**Step 1: Run dry-run test on 5 permits**

```bash
cd /home/reid/testhome/permit-scraper && python3 scripts/backfill_cad_enrichment.py --dry-run --limit 5 --city frisco
```

Expected output pattern:
```
============================================================
CAD ENRICHMENT BACKFILL
============================================================
Mode: DRY RUN
Rate limit: 1.0s between requests
City filter: frisco
Limit: 5 permits

Found X permits needing enrichment
[1/X] [COLLIN] 123 MAIN ST...                    -> DRY RUN: Would save $XXX,XXX
...
```

**Step 2: Verify no database changes**

```bash
cd /home/reid/testhome/permit-scraper && PGPASSWORD=localdev123 psql -h localhost -U contractors_user -d contractors_dev -c "
SELECT COUNT(*) as enriched_today
FROM leads_property
WHERE enriched_at > NOW() - INTERVAL '5 minutes';"
```

Expected: `enriched_today = 0` (dry run made no changes)

**Step 3: Commit test results**

```bash
git add -A && git commit -m "test: verify dry-run mode works correctly"
```

---

## Task 9: Live Test on Small Batch

**Files:**
- None (testing only)

**Step 1: Run live enrichment on 10 Frisco permits**

```bash
cd /home/reid/testhome/permit-scraper && python3 scripts/backfill_cad_enrichment.py --limit 10 --city frisco
```

Expected: Mix of success/not_found results

**Step 2: Verify database was updated**

```bash
cd /home/reid/testhome/permit-scraper && PGPASSWORD=localdev123 psql -h localhost -U contractors_user -d contractors_dev -c "
SELECT
    property_address,
    county,
    market_value,
    owner_name,
    enrichment_status
FROM leads_property
WHERE enriched_at > NOW() - INTERVAL '5 minutes'
LIMIT 5;"
```

Expected: Records with market_value and owner_name populated

**Step 3: Verify scoring can now see these permits**

```bash
cd /home/reid/testhome/permit-scraper && PGPASSWORD=localdev123 psql -h localhost -U contractors_user -d contractors_dev -c "
-- Count permits that can now be scored (have successful enrichment)
SELECT COUNT(*) as scorable
FROM leads_permit p
JOIN leads_property prop ON p.property_address = prop.property_address
WHERE p.city = 'frisco'
  AND prop.enrichment_status = 'success';"
```

Expected: Higher count than before backfill

**Step 4: Commit**

```bash
git add -A && git commit -m "test: verify live enrichment works on small batch"
```

---

## Task 10: Full Backfill Execution

**Files:**
- None (execution only)

**Step 1: Check total permits needing enrichment**

```bash
cd /home/reid/testhome/permit-scraper && PGPASSWORD=localdev123 psql -h localhost -U contractors_user -d contractors_dev -c "
SELECT COUNT(*) as unenriched
FROM leads_permit p
LEFT JOIN leads_property prop ON p.property_address = prop.property_address
WHERE p.property_address IS NOT NULL
  AND p.city IS NOT NULL
  AND p.processing_bin = 'active'
  AND (prop.property_address IS NULL OR prop.enrichment_status != 'success');"
```

Note the count for estimation.

**Step 2: Run full backfill in background**

```bash
cd /home/reid/testhome/permit-scraper && nohup python3 scripts/backfill_cad_enrichment.py > logs/backfill_$(date +%Y%m%d_%H%M%S).log 2>&1 &
echo $! > logs/backfill.pid
echo "Backfill started. PID: $(cat logs/backfill.pid)"
echo "Monitor with: tail -f logs/backfill_*.log"
```

**Step 3: Monitor progress**

```bash
# Check progress
tail -20 /home/reid/testhome/permit-scraper/logs/backfill_*.log

# Check database enrichment count
PGPASSWORD=localdev123 psql -h localhost -U contractors_user -d contractors_dev -c "
SELECT
    DATE(enriched_at) as date,
    COUNT(*) as enriched
FROM leads_property
WHERE enriched_at > NOW() - INTERVAL '1 day'
GROUP BY DATE(enriched_at);"
```

**Step 4: After completion, run scoring**

```bash
cd /home/reid/testhome/permit-scraper && python3 scripts/score_leads.py --rescore
```

---

## Task 11: Verify Results

**Files:**
- None (verification only)

**Step 1: Check enrichment improvement by category**

```bash
cd /home/reid/testhome/permit-scraper && PGPASSWORD=localdev123 psql -h localhost -U contractors_user -d contractors_dev -c "
SELECT
    CASE
        WHEN p.permit_type ILIKE '%pool%' OR p.description ILIKE '%pool%' THEN 'Pool'
        WHEN p.permit_type ILIKE '%roof%' OR p.description ILIKE '%roof%' THEN 'Roof'
        WHEN p.permit_type ILIKE '%foundation%' OR p.description ILIKE '%foundation%' THEN 'Foundation'
        WHEN p.permit_type ILIKE '%patio%' OR p.permit_type ILIKE '%outdoor%' THEN 'Outdoor'
    END as category,
    COUNT(*) as total,
    COUNT(prop.market_value) as enriched,
    ROUND(100.0 * COUNT(prop.market_value) / COUNT(*)) as pct
FROM leads_permit p
LEFT JOIN leads_property prop ON p.property_address = prop.property_address
WHERE p.city IN ('frisco', 'mckinney', 'allen', 'plano', 'prosper', 'celina')
  AND (p.permit_type ILIKE '%pool%' OR p.description ILIKE '%pool%'
       OR p.permit_type ILIKE '%roof%' OR p.description ILIKE '%roof%'
       OR p.permit_type ILIKE '%foundation%' OR p.description ILIKE '%foundation%'
       OR p.permit_type ILIKE '%patio%' OR p.permit_type ILIKE '%outdoor%')
GROUP BY 1
HAVING COUNT(*) > 10
ORDER BY total DESC;"
```

Expected: Enrichment percentages significantly higher than before (was 9-20%, target 60%+)

**Step 2: Check premium lead count improvement**

```bash
cd /home/reid/testhome/permit-scraper && PGPASSWORD=localdev123 psql -h localhost -U contractors_user -d contractors_dev -c "
SELECT
    tier,
    COUNT(*) as count
FROM clients_scoredlead sl
JOIN leads_permit p ON sl.permit_id = p.id
WHERE p.city IN ('frisco', 'mckinney', 'allen', 'plano', 'prosper', 'celina')
GROUP BY tier
ORDER BY tier;"
```

Expected: Higher Tier A and B counts than before

**Step 3: Document results**

Update `LEADS_INVENTORY.md` with new counts if significant improvement.

---

## Summary

| Task | Description | Estimated Time |
|------|-------------|----------------|
| 1 | Create address builder function | 5 min |
| 2 | Add city-to-county lookup | 5 min |
| 3 | Add database fetch query | 5 min |
| 4 | Add CAD query integration | 5 min |
| 5 | Add database upsert function | 5 min |
| 6 | Add single permit processor | 10 min |
| 7 | Add main function and CLI | 10 min |
| 8 | Integration test (dry run) | 5 min |
| 9 | Live test on small batch | 10 min |
| 10 | Full backfill execution | ~9 hours (background) |
| 11 | Verify results | 10 min |

**Total implementation time:** ~70 minutes + ~9 hours background processing
