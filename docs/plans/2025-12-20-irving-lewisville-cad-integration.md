# Irving Fix + Lewisville CAD Integration + Sequential Parcel Fetching

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix Irving MGO Connect scraper, implement Lewisville permit scraping via Denton CAD parcel integration, and build reusable infrastructure for sequential parcel fetching across DFW counties.

**Architecture:** Three-phase approach: (1) Test existing Irving fix, (2) Build CAD parcel fetcher for Denton County with pagination support, (3) Create Tyler eSuite parcel-based permit scraper for Lewisville that queries each parcel.

**Tech Stack:** Python 3.11+, Playwright, httpx, PostgreSQL, ArcGIS REST API

---

## Phase 1: Irving MGO Connect Fix

### Task 1: Test Irving Advanced Reporting Path

**Files:**
- Test: `scrapers/mgo_connect.py` (already has Irving routing at lines 567-579)

**Context:** The orchestrator already routes Irving to the `scrape()` function which has Advanced Reporting logic. We need to verify it works.

**Step 1: Run Irving scraper with timeout**

```bash
cd /home/reid/command-center/testhome/permit-scraper
timeout 180 python3 scrapers/mgo_connect.py Irving 50 2>&1 | tee /tmp/irving_test.log
```

Expected output should show:
- "IRVING DETECTED: Using Advanced Reporting path..."
- Navigation to Advanced Reporting page
- PDF export attempt or permit extraction

**Step 2: Check results**

```bash
# Check if any permits were saved
cat data/exports/irving_mgo_raw.json | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'Permits: {d[\"count\"]}')"

# Check log for errors
grep -i "error\|fail\|exception" /tmp/irving_test.log
```

**Step 3: Document findings**

If Irving works: Update `SCRAPER_STATUS.md` to mark Irving as ✅ Working
If Irving fails: Document the specific failure point for further investigation

---

## Phase 2: Denton CAD Sequential Parcel Fetcher

### Task 2: Create CAD Parcel Fetcher Module

**Files:**
- Create: `scrapers/cad_parcel_fetcher.py`

**Context:** Denton CAD has 24,755 Lewisville parcels. API supports pagination (1000 records max per request). We need ~25 API calls to fetch all parcels.

**Step 1: Create the parcel fetcher**

```python
#!/usr/bin/env python3
"""
CAD Parcel Fetcher - Bulk download parcels from County CAD APIs.

Supports:
- Denton County (gis.dentoncounty.gov)
- Tarrant County (tad.newedgeservices.com)
- Dallas County (maps.dcad.org)
- Collin County (gismaps.cityofallen.org)

Usage:
    python3 scrapers/cad_parcel_fetcher.py denton --city lewisville
    python3 scrapers/cad_parcel_fetcher.py denton --city "flower mound"
    python3 scrapers/cad_parcel_fetcher.py tarrant --city southlake
"""

import argparse
import asyncio
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Generator, Optional

import httpx

# Output directory for parcel data
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "parcels"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# CAD API configurations
CAD_CONFIGS = {
    'denton': {
        'name': 'Denton County',
        'base_url': 'https://gis.dentoncounty.gov/arcgis/rest/services/CAD/MapServer/0/query',
        'city_field': 'situs_city',
        'parcel_id_field': 'prop_id',
        'fields': [
            'prop_id', 'situs_num', 'situs_street', 'situs_street_sufix',
            'situs_city', 'situs_zip', 'owner_name', 'addr_line1',
            'addr_city', 'addr_zip', 'cert_mkt_val', 'yr_blt', 'living_area'
        ],
        'max_records': 1000,
    },
    'tarrant': {
        'name': 'Tarrant County',
        'base_url': 'https://tad.newedgeservices.com/arcgis/rest/services/TAD/ParcelView/MapServer/1/query',
        'city_field': 'City',  # Need to verify
        'parcel_id_field': 'Account_Nu',
        'fields': [
            'Account_Nu', 'Situs_Addr', 'Owner_Name', 'Owner_Addr',
            'Owner_City', 'Owner_Zip', 'Total_Valu', 'Year_Built', 'Living_Are'
        ],
        'max_records': 1000,
    },
    'dallas': {
        'name': 'Dallas County',
        'base_url': 'https://maps.dcad.org/prdwa/rest/services/Property/ParcelQuery/MapServer/4/query',
        'city_field': 'SITUSCITY',  # Need to verify
        'parcel_id_field': 'PARCELID',
        'fields': [
            'PARCELID', 'SITEADDRESS', 'OWNERNME1', 'PSTLADDRESS',
            'PSTLCITY', 'PSTLZIP5', 'CNTASSDVAL', 'RESYRBLT', 'BLDGAREA'
        ],
        'max_records': 1000,
    },
}


async def fetch_parcel_count(county: str, city: str) -> int:
    """Get total count of parcels for a city."""
    config = CAD_CONFIGS[county]

    params = {
        'where': f"{config['city_field']}='{city.upper()}'",
        'returnCountOnly': 'true',
        'f': 'json',
    }

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(config['base_url'], params=params)
        response.raise_for_status()
        data = response.json()
        return data.get('count', 0)


async def fetch_parcels_page(
    county: str,
    city: str,
    offset: int = 0,
    limit: int = 1000
) -> list[dict]:
    """Fetch a single page of parcels."""
    config = CAD_CONFIGS[county]

    params = {
        'where': f"{config['city_field']}='{city.upper()}'",
        'outFields': ','.join(config['fields']),
        'resultOffset': offset,
        'resultRecordCount': limit,
        'f': 'json',
    }

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(config['base_url'], params=params)
        response.raise_for_status()
        data = response.json()

        features = data.get('features', [])
        return [f['attributes'] for f in features]


async def fetch_all_parcels(
    county: str,
    city: str,
    delay: float = 0.5,
    progress_callback: Optional[callable] = None
) -> Generator[dict, None, None]:
    """
    Fetch all parcels for a city with pagination.

    Args:
        county: County key (denton, tarrant, dallas)
        city: City name (e.g., 'lewisville')
        delay: Delay between API calls (rate limiting)
        progress_callback: Optional callback(fetched, total)

    Yields:
        Parcel dictionaries
    """
    config = CAD_CONFIGS[county]
    max_records = config['max_records']

    # Get total count
    total = await fetch_parcel_count(county, city)
    print(f"Total parcels for {city} in {config['name']}: {total:,}")

    if total == 0:
        return

    fetched = 0
    offset = 0

    while fetched < total:
        parcels = await fetch_parcels_page(county, city, offset, max_records)

        if not parcels:
            break

        for parcel in parcels:
            yield parcel
            fetched += 1

        if progress_callback:
            progress_callback(fetched, total)
        else:
            print(f"  Fetched {fetched:,} / {total:,} ({100*fetched/total:.1f}%)")

        offset += max_records

        if offset < total:
            await asyncio.sleep(delay)


async def save_parcels_to_file(county: str, city: str, delay: float = 0.5) -> Path:
    """
    Fetch all parcels and save to JSON file.

    Returns:
        Path to saved file
    """
    city_slug = city.lower().replace(' ', '_')
    output_file = OUTPUT_DIR / f"{city_slug}_{county}_parcels.json"

    print(f"\n{'='*60}")
    print(f"FETCHING PARCELS: {city.title()} ({county.title()} County)")
    print(f"{'='*60}")

    parcels = []
    async for parcel in fetch_all_parcels(county, city, delay):
        parcels.append(parcel)

    output = {
        'county': county,
        'city': city,
        'fetched_at': datetime.now().isoformat(),
        'count': len(parcels),
        'parcels': parcels
    }

    output_file.write_text(json.dumps(output, indent=2))
    print(f"\nSaved {len(parcels):,} parcels to {output_file}")

    return output_file


def main():
    parser = argparse.ArgumentParser(
        description='Fetch parcels from County CAD APIs',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('county', choices=list(CAD_CONFIGS.keys()),
                        help='County to fetch from')
    parser.add_argument('--city', required=True,
                        help='City name (e.g., lewisville, "flower mound")')
    parser.add_argument('--delay', type=float, default=0.5,
                        help='Delay between API calls (default: 0.5s)')
    parser.add_argument('--count-only', action='store_true',
                        help='Only show count, do not fetch')

    args = parser.parse_args()

    if args.count_only:
        count = asyncio.run(fetch_parcel_count(args.county, args.city))
        print(f"Parcels for {args.city} in {args.county}: {count:,}")
    else:
        asyncio.run(save_parcels_to_file(args.county, args.city, args.delay))


if __name__ == '__main__':
    main()
```

**Step 2: Test parcel count for Lewisville**

```bash
cd /home/reid/command-center/testhome/permit-scraper
python3 scrapers/cad_parcel_fetcher.py denton --city lewisville --count-only
```

Expected: `Parcels for lewisville in denton: 24,755`

**Step 3: Fetch all Lewisville parcels**

```bash
python3 scrapers/cad_parcel_fetcher.py denton --city lewisville --delay 0.3
```

Expected: ~25 API calls, ~24,755 parcels saved to `data/parcels/lewisville_denton_parcels.json`

**Step 4: Commit**

```bash
git add scrapers/cad_parcel_fetcher.py data/parcels/
git commit -m "feat: add CAD parcel fetcher with Denton/Tarrant/Dallas support"
```

---

### Task 3: Create Parcel ID Extractor Utility

**Files:**
- Create: `scripts/extract_parcel_ids.py`

**Context:** Tyler eSuite requires parcel IDs in a specific format (Denton uses "R" prefix for residential). We need to extract and format parcel IDs from the fetched data.

**Step 1: Create extractor script**

```python
#!/usr/bin/env python3
"""
Extract and format parcel IDs from CAD parcel data.

For Denton County / Tyler eSuite:
- Prefix residential parcels with "R" (e.g., R00000123456)

Usage:
    python3 scripts/extract_parcel_ids.py data/parcels/lewisville_denton_parcels.json
"""

import argparse
import json
from pathlib import Path


def format_denton_parcel_id(prop_id: str) -> str:
    """
    Format Denton County parcel ID for Tyler eSuite.
    Residential parcels need "R" prefix.
    """
    if not prop_id:
        return ''

    prop_id = str(prop_id).strip()

    # If already has R prefix, return as-is
    if prop_id.upper().startswith('R'):
        return prop_id.upper()

    # Add R prefix for residential
    return f"R{prop_id}"


def extract_parcel_ids(input_file: Path, county: str = 'denton') -> list[str]:
    """Extract formatted parcel IDs from parcel JSON file."""
    data = json.loads(input_file.read_text())
    parcels = data.get('parcels', [])

    parcel_ids = []
    for parcel in parcels:
        if county == 'denton':
            prop_id = parcel.get('prop_id', '')
            formatted = format_denton_parcel_id(prop_id)
            if formatted:
                parcel_ids.append(formatted)

    return parcel_ids


def main():
    parser = argparse.ArgumentParser(description='Extract parcel IDs from CAD data')
    parser.add_argument('input_file', type=Path, help='Input parcel JSON file')
    parser.add_argument('--output', '-o', type=Path, help='Output file (default: stdout)')
    parser.add_argument('--limit', type=int, help='Limit number of IDs')

    args = parser.parse_args()

    parcel_ids = extract_parcel_ids(args.input_file)

    if args.limit:
        parcel_ids = parcel_ids[:args.limit]

    print(f"Extracted {len(parcel_ids)} parcel IDs")

    if args.output:
        args.output.write_text('\n'.join(parcel_ids))
        print(f"Saved to {args.output}")
    else:
        for pid in parcel_ids[:10]:
            print(f"  {pid}")
        if len(parcel_ids) > 10:
            print(f"  ... and {len(parcel_ids) - 10} more")


if __name__ == '__main__':
    main()
```

**Step 2: Test extraction**

```bash
python3 scripts/extract_parcel_ids.py data/parcels/lewisville_denton_parcels.json --limit 20
```

Expected: 20 formatted parcel IDs like `R00000123456`

**Step 3: Commit**

```bash
git add scripts/extract_parcel_ids.py
git commit -m "feat: add parcel ID extractor for Tyler eSuite format"
```

---

## Phase 3: Lewisville Tyler eSuite Parcel-Based Scraper

### Task 4: Create Tyler eSuite Parcel Scraper

**Files:**
- Create: `scrapers/tyler_esuite_parcel.py`

**Context:** Tyler eSuite (Lewisville) requires a parcel number to search for permits. We'll iterate through Denton CAD parcels and query each one.

**Step 1: Create the parcel-based scraper**

```python
#!/usr/bin/env python3
"""
TYLER eSUITE PARCEL-BASED PERMIT SCRAPER

Scrapes permits by querying individual parcels from CAD data.
Uses Denton CAD parcel IDs to query Tyler eSuite portal.

Usage:
    python3 scrapers/tyler_esuite_parcel.py --parcel-file data/parcels/lewisville_denton_parcels.json --limit 100
    python3 scrapers/tyler_esuite_parcel.py --parcel R00000123456  # Single parcel
"""

import argparse
import asyncio
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

# Output directory
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "raw"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Portal configuration
LEWISVILLE_CONFIG = {
    'name': 'Lewisville',
    'base_url': 'https://etools.cityoflewisville.com/esuite.permits/',
    'county': 'denton',
}


def format_parcel_id(prop_id: str) -> str:
    """Format Denton parcel ID for Tyler eSuite (add R prefix)."""
    if not prop_id:
        return ''
    prop_id = str(prop_id).strip()
    if prop_id.upper().startswith('R'):
        return prop_id.upper()
    return f"R{prop_id}"


async def query_parcel_permits(page, parcel_id: str) -> list[dict]:
    """
    Query Tyler eSuite for permits on a specific parcel.

    Returns list of permit dictionaries.
    """
    permits = []

    try:
        # Navigate to home page (resets state)
        await page.goto(LEWISVILLE_CONFIG['base_url'], wait_until='networkidle', timeout=30000)
        await asyncio.sleep(1)

        # Find and fill the parcel number input
        # Based on exploration: there's a hidden search div that may need activation
        parcel_input = page.locator('input[id*="ParcelNumber"], input[name*="parcel"]').first

        if await parcel_input.count() == 0:
            # Try to find any text input
            parcel_input = page.locator('input[type="text"]').first

        if await parcel_input.count() > 0:
            await parcel_input.fill(parcel_id)
            await asyncio.sleep(0.5)

            # Click search/submit button
            submit_btn = page.locator('input[type="submit"], button[type="submit"]').first
            if await submit_btn.count() > 0:
                await submit_btn.click()
                await asyncio.sleep(2)

            # Extract permits from results table
            permits = await page.evaluate('''() => {
                const results = [];
                const rows = document.querySelectorAll('table tr, .permit-row, [class*="permit"]');
                rows.forEach(row => {
                    const text = row.textContent || '';
                    // Look for permit number patterns
                    const permitMatch = text.match(/(BP|BLD|BLDG|P|RES|COM)-?\d{4,}/i);
                    if (permitMatch) {
                        results.push({
                            permit_id: permitMatch[0],
                            raw_text: text.slice(0, 200)
                        });
                    }
                });
                return results;
            }''')

    except PlaywrightTimeout:
        pass
    except Exception as e:
        print(f"      Error: {e}")

    return permits


async def scrape_parcels(
    parcel_ids: list[str],
    limit: Optional[int] = None,
    delay: float = 2.0
) -> dict:
    """
    Scrape permits for multiple parcels.

    Returns summary dict with all permits found.
    """
    if limit:
        parcel_ids = parcel_ids[:limit]

    total = len(parcel_ids)
    print(f"\n{'='*60}")
    print(f"LEWISVILLE TYLER eSUITE PARCEL SCRAPER")
    print(f"{'='*60}")
    print(f"Parcels to query: {total}")
    print(f"Delay between queries: {delay}s")
    print(f"Time: {datetime.now().isoformat()}\n")

    all_permits = []
    parcels_with_permits = 0
    errors = 0

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 900},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        page = await context.new_page()

        for i, parcel_id in enumerate(parcel_ids, 1):
            print(f"[{i}/{total}] Querying {parcel_id}...", end=' ')

            try:
                permits = await query_parcel_permits(page, parcel_id)

                if permits:
                    parcels_with_permits += 1
                    for permit in permits:
                        permit['parcel_id'] = parcel_id
                        all_permits.append(permit)
                    print(f"Found {len(permits)} permits")
                else:
                    print("No permits")

            except Exception as e:
                print(f"ERROR: {e}")
                errors += 1

            if i < total:
                await asyncio.sleep(delay)

        await browser.close()

    # Save results
    output = {
        'source': 'lewisville_tyler_esuite',
        'scraped_at': datetime.now().isoformat(),
        'parcels_queried': total,
        'parcels_with_permits': parcels_with_permits,
        'total_permits': len(all_permits),
        'errors': errors,
        'permits': all_permits
    }

    output_file = OUTPUT_DIR / 'lewisville_raw.json'
    output_file.write_text(json.dumps(output, indent=2))

    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"Parcels queried: {total}")
    print(f"Parcels with permits: {parcels_with_permits}")
    print(f"Total permits found: {len(all_permits)}")
    print(f"Errors: {errors}")
    print(f"Output: {output_file}")

    return output


def load_parcel_ids(parcel_file: Path) -> list[str]:
    """Load and format parcel IDs from CAD JSON file."""
    data = json.loads(parcel_file.read_text())
    parcels = data.get('parcels', [])

    parcel_ids = []
    for parcel in parcels:
        prop_id = parcel.get('prop_id', '')
        formatted = format_parcel_id(prop_id)
        if formatted:
            parcel_ids.append(formatted)

    return parcel_ids


def main():
    parser = argparse.ArgumentParser(
        description='Scrape Lewisville permits via parcel lookup'
    )
    parser.add_argument('--parcel-file', type=Path,
                        help='Path to CAD parcel JSON file')
    parser.add_argument('--parcel', type=str,
                        help='Single parcel ID to query')
    parser.add_argument('--limit', type=int,
                        help='Limit number of parcels to query')
    parser.add_argument('--delay', type=float, default=2.0,
                        help='Delay between queries (default: 2.0s)')

    args = parser.parse_args()

    if args.parcel:
        parcel_ids = [format_parcel_id(args.parcel)]
    elif args.parcel_file:
        parcel_ids = load_parcel_ids(args.parcel_file)
    else:
        print("ERROR: Specify --parcel-file or --parcel")
        sys.exit(1)

    asyncio.run(scrape_parcels(parcel_ids, args.limit, args.delay))


if __name__ == '__main__':
    main()
```

**Step 2: Test with single parcel**

First, get a sample parcel ID:
```bash
python3 -c "
import json
data = json.loads(open('data/parcels/lewisville_denton_parcels.json').read())
parcel = data['parcels'][0]
print(f\"Parcel ID: R{parcel['prop_id']}\")
print(f\"Address: {parcel.get('situs_num', '')} {parcel.get('situs_street', '')}\")
"
```

Then test:
```bash
python3 scrapers/tyler_esuite_parcel.py --parcel R00000123456 --delay 1
```

**Step 3: Test with small batch**

```bash
python3 scrapers/tyler_esuite_parcel.py --parcel-file data/parcels/lewisville_denton_parcels.json --limit 20 --delay 2
```

**Step 4: Commit**

```bash
git add scrapers/tyler_esuite_parcel.py
git commit -m "feat: add Tyler eSuite parcel-based scraper for Lewisville"
```

---

### Task 5: Optimize Tyler eSuite Scraper Based on Testing

**Files:**
- Modify: `scrapers/tyler_esuite_parcel.py`

**Context:** After testing, we'll need to adjust selectors and logic based on actual portal behavior.

**Step 1: Run exploration with Playwright to capture actual DOM**

```bash
python3 -c "
import asyncio
from playwright.async_api import async_playwright

async def explore():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # Headed for observation
        page = await browser.new_page()
        await page.goto('https://etools.cityoflewisville.com/esuite.permits/')
        await asyncio.sleep(30)  # Time to observe
        await browser.close()

asyncio.run(explore())
"
```

**Step 2: Update selectors based on observations**

Modify `query_parcel_permits()` function with correct selectors.

**Step 3: Re-test and iterate**

```bash
python3 scrapers/tyler_esuite_parcel.py --parcel-file data/parcels/lewisville_denton_parcels.json --limit 50 --delay 2
```

**Step 4: Commit optimizations**

```bash
git add scrapers/tyler_esuite_parcel.py
git commit -m "fix: optimize Tyler eSuite selectors for Lewisville portal"
```

---

### Task 6: Update Documentation

**Files:**
- Modify: `SCRAPER_STATUS.md`
- Modify: `CLAUDE.md`

**Step 1: Update SCRAPER_STATUS.md**

Add/update entries:
```markdown
| 5 | **Irving** | 240K | MGO Connect | `mgo_connect.py` | Dallas | ⚠️/✅ | Advanced Reporting path |
| 14 | **Lewisville** | 110K | Tyler eSuite | `tyler_esuite_parcel.py` | Denton | ✅ Working | CAD parcel-based scraping |
```

Update Platform Summary:
```markdown
| **Tyler eSuite** | 1 | 1 | 0 | Lewisville - CAD parcel integration |
```

**Step 2: Add CAD parcel infrastructure to CLAUDE.md**

```markdown
### CAD Parcel Integration
```bash
# Fetch all parcels for a city
python3 scrapers/cad_parcel_fetcher.py denton --city lewisville

# Scrape permits using parcel data
python3 scrapers/tyler_esuite_parcel.py --parcel-file data/parcels/lewisville_denton_parcels.json
```
```

**Step 3: Commit documentation**

```bash
git add SCRAPER_STATUS.md CLAUDE.md
git commit -m "docs: update status for Irving and Lewisville, add CAD parcel docs"
```

---

## Phase 4: Future CAD Expansion Infrastructure

### Task 7: Add Support for Additional Denton County Cities

**Files:**
- Modify: `scrapers/tyler_esuite_parcel.py`

**Context:** Other Denton County cities that may use Tyler eSuite or similar parcel-based portals.

**Step 1: List Denton County cities with parcel counts**

```bash
for city in "flower mound" "highland village" "the colony" "little elm" "corinth" "aubrey" "argyle"; do
    echo -n "$city: "
    curl -s "https://gis.dentoncounty.gov/arcgis/rest/services/CAD/MapServer/0/query?where=situs_city='${city^^}'&returnCountOnly=true&f=json" | python3 -c "import json,sys; print(json.load(sys.stdin).get('count', 0))"
done
```

**Step 2: Create city configuration**

Add to `tyler_esuite_parcel.py`:
```python
DENTON_CITIES = {
    'lewisville': {'portal_url': 'https://etools.cityoflewisville.com/esuite.permits/'},
    'flower_mound': {'portal_url': None},  # Research needed
    'highland_village': {'portal_url': None},
    # Add more as researched
}
```

**Step 3: Document in SCRAPER_STATUS.md**

Add "Denton County CAD Integration" section listing which cities can be scraped via this method.

**Step 4: Commit**

```bash
git add scrapers/tyler_esuite_parcel.py SCRAPER_STATUS.md
git commit -m "feat: add Denton County city configurations for CAD parcel scraping"
```

---

## Summary

| Task | Phase | Effort | Outcome |
|------|-------|--------|---------|
| 1 | Irving Fix | 15 min | Test existing Irving Advanced Reporting routing |
| 2 | CAD Infrastructure | 1 hour | Denton CAD parcel fetcher with pagination |
| 3 | Parcel Utilities | 30 min | Parcel ID extractor for Tyler eSuite format |
| 4 | Lewisville Scraper | 2 hours | Tyler eSuite parcel-based permit scraper |
| 5 | Optimization | 1 hour | Selector tuning based on testing |
| 6 | Documentation | 30 min | Update status docs |
| 7 | Future Expansion | 1 hour | Multi-city Denton County support |

**Total estimated effort:** 6-7 hours

**Key Metrics:**
- Denton CAD: 24,755 Lewisville parcels (1000/request, ~25 API calls)
- Rate limiting: 0.3-0.5s between CAD calls, 2s between portal queries
- Expected yield: Permits for ~5-10% of parcels (residential with active permits)

**Dependencies:**
- Task 2-4 require Task 1 verification
- Task 5 requires Task 4 testing results
- Task 7 can run in parallel after Task 2

**Risks:**
- Tyler eSuite may block after many queries (mitigate with delays, residential proxy)
- ASP.NET ViewState may expire (mitigate with session refresh)
- Some parcels may return errors (track and retry)
