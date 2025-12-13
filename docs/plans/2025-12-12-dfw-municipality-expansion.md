# DFW Municipality Expansion Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add 13 new DFW municipalities to the permit scraper system using existing patterns (MyGov, eTRAKiT, EnerGov CSS) plus one new platform (SmartGov).

**Architecture:** Leverage existing scraper patterns - most cities just need config additions. MyGov cities use the `mygov_westlake.py` pattern with address iteration. eTRAKiT and EnerGov CSS cities just need config entries in existing scrapers.

**Tech Stack:** Python 3, Playwright (async), existing scraper modules

---

## Research Summary

### MyGov Cities - PUBLIC ACCESS CONFIRMED (9 cities)

| Priority | City | Pop | MyGov URL | CAD County |
|----------|------|-----|-----------|------------|
| 1 | **Mansfield** | 75K | `public.mygov.us/mansfield_tx/lookup` | Tarrant |
| 2 | **Rowlett** | 67K | `public.mygov.us/rowlett_tx/lookup` | Dallas/Rockwall |
| 3 | **Burleson** | 50K | `public.mygov.us/burleson_tx/lookup` | Johnson |
| 4 | **Little Elm** | 50K | `public.mygov.us/little_elm_tx/lookup` | Denton |
| 5 | **Lancaster** | 40K | `public.mygov.us/lancaster_tx/lookup` | Dallas |
| 6 | **Midlothian** | 35K | `public.mygov.us/midlothian_tx/lookup` | Ellis |
| 7 | **Celina** | 20K | `public.mygov.us/celina_tx/lookup` | Collin/Denton |
| 8 | **Fate** | 20K | `public.mygov.us/fate_tx/lookup` | Rockwall |
| 9 | **Venus** | 5K | `public.mygov.us/venus_tx/lookup` | Johnson |

### eTRAKiT Cities (1 city)

| Priority | City | Pop | eTRAKiT URL | CAD County |
|----------|------|-----|-------------|------------|
| 1 | **Keller** | 48K | `trakitweb.cityofkeller.com` | Tarrant |

### EnerGov CSS Cities (2 cities)

| Priority | City | Pop | CSS URL | CAD County |
|----------|------|-----|---------|------------|
| 1 | **DeSoto** | 55K | `cityofdesototx-energovweb.tylerhost.net/apps/selfservice` | Dallas |
| 2 | **Cedar Hill** | 50K | `cedarhilltx-energovpub.tylerhost.net/Apps/SelfService` | Dallas |

### SmartGov Cities (1 city - needs new scraper)

| Priority | City | Pop | Portal URL | CAD County |
|----------|------|-----|------------|------------|
| 1 | **Sachse** | 30K | `ci-sachse-tx.smartgovcommunity.com` | Dallas/Collin |

---

## Phase 1: Quick Wins - Config-Only Additions

### Task 1: Add Keller to eTRAKiT Scraper

**Files:**
- Modify: `scrapers/etrakit_fast.py`

**Step 1: Add Keller configuration**

Add to `ETRAKIT_CITIES` dict (around line 70, after denton):

```python
    'keller': {
        'name': 'Keller',
        'base_url': 'https://trakitweb.cityofkeller.com',
        'search_path': '/etrakit/Search/permit.aspx',
        'prefixes': ['B25', 'B24', 'B23', 'B22', 'B21', 'B20'],
        'permit_regex': r'^[A-Z]\d{2}-\d{4,5}$',
    },
```

**Step 2: Test scraper**

Run: `cd /home/reid/testhome/permit-scraper && python3 scrapers/etrakit_fast.py keller 10`

Expected: 10+ permits extracted

**Step 3: Commit**

```bash
git add scrapers/etrakit_fast.py
git commit -m "feat: add Keller to eTRAKiT scraper"
```

---

### Task 2: Add Cedar Hill to EnerGov CSS Scraper

**Files:**
- Modify: `scrapers/citizen_self_service.py`

**Step 1: Add Cedar Hill configuration**

Add to `CSS_CITIES` dict (after waxahachie config, around line 77):

```python
    'cedar_hill': {
        'name': 'Cedar Hill',
        'base_url': 'https://cedarhilltx-energovpub.tylerhost.net/Apps/SelfService',
    },
```

**Step 2: Test scraper**

Run: `cd /home/reid/testhome/permit-scraper && python3 scrapers/citizen_self_service.py cedar_hill 10`

Expected: 10+ permits extracted via Excel export

**Step 3: Commit**

```bash
git add scrapers/citizen_self_service.py
git commit -m "feat: add Cedar Hill to EnerGov CSS scraper"
```

---

### Task 3: Add DeSoto to EnerGov CSS Scraper

**Files:**
- Modify: `scrapers/citizen_self_service.py`

**Step 1: Add DeSoto configuration**

Add to `CSS_CITIES` dict:

```python
    'desoto': {
        'name': 'DeSoto',
        'base_url': 'https://cityofdesototx-energovweb.tylerhost.net/apps/selfservice',
    },
```

**Step 2: Test scraper**

Run: `cd /home/reid/testhome/permit-scraper && python3 scrapers/citizen_self_service.py desoto 10`

Expected: 10+ permits extracted

**Step 3: Commit**

```bash
git add scrapers/citizen_self_service.py
git commit -m "feat: add DeSoto to EnerGov CSS scraper"
```

---

## Phase 2: MyGov Multi-City Scraper

The existing `mygov_westlake.py` scraper requires pre-harvested addresses. For multiple cities, we need a more generic approach.

### Task 4: Create Generic MyGov Scraper

**Files:**
- Create: `scrapers/mygov_multi.py`

**Step 1: Create multi-city MyGov scraper**

```python
#!/usr/bin/env python3
"""
MYGOV MULTI-CITY PERMIT SCRAPER (Playwright)
Platform: MyGov Public Portal (public.mygov.us)

Supports multiple DFW cities with public MyGov access.
Uses keyword search approach (not address-based like Westlake).

Usage:
  python3 scrapers/mygov_multi.py mansfield 100
  python3 scrapers/mygov_multi.py rowlett 100
  python3 scrapers/mygov_multi.py burleson 100
"""

import asyncio
import json
import logging
import re
import sys
from datetime import datetime
from pathlib import Path

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

OUTPUT_DIR = Path(__file__).parent.parent / "data" / "raw"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# MyGov cities with public access
MYGOV_CITIES = {
    'mansfield': {
        'name': 'Mansfield',
        'slug': 'mansfield_tx',
        'county': 'tarrant',
    },
    'rowlett': {
        'name': 'Rowlett',
        'slug': 'rowlett_tx',
        'county': 'dallas',
    },
    'burleson': {
        'name': 'Burleson',
        'slug': 'burleson_tx',
        'county': 'johnson',
    },
    'little_elm': {
        'name': 'Little Elm',
        'slug': 'little_elm_tx',
        'county': 'denton',
    },
    'lancaster': {
        'name': 'Lancaster',
        'slug': 'lancaster_tx',
        'county': 'dallas',
    },
    'midlothian': {
        'name': 'Midlothian',
        'slug': 'midlothian_tx',
        'county': 'ellis',
    },
    'celina': {
        'name': 'Celina',
        'slug': 'celina_tx',
        'county': 'collin',
    },
    'fate': {
        'name': 'Fate',
        'slug': 'fate_tx',
        'county': 'rockwall',
    },
    'venus': {
        'name': 'Venus',
        'slug': 'venus_tx',
        'county': 'johnson',
    },
}


def get_lookup_url(slug: str) -> str:
    """Get the public lookup URL for a MyGov city."""
    return f'https://public.mygov.us/{slug}/lookup'


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=2, max=8),
    retry=retry_if_exception_type((PlaywrightTimeout, Exception)),
    reraise=True
)
async def search_permits(page, city_config: dict, search_term: str) -> list:
    """Search for permits using a search term."""
    permits = []
    url = get_lookup_url(city_config['slug'])

    await page.goto(url, timeout=30000)
    await asyncio.sleep(1)

    # Find search input
    search_input = await page.query_selector('input[type="text"]')
    if not search_input:
        logger.warning("Search input not found")
        return permits

    await search_input.fill(search_term)
    await asyncio.sleep(0.5)
    await search_input.press('Enter')
    await asyncio.sleep(2)

    # Check for results
    results = await page.query_selector_all('.search-result, .lookup-result, tr[class*="row"]')
    logger.info(f"Found {len(results)} results for '{search_term}'")

    # Extract permit data from results
    for result in results[:50]:  # Limit per search
        try:
            text = await result.inner_text()

            # Look for permit patterns
            permit_match = re.search(r'(BP?[-\s]?\d{2,4}[-\s]?\d{3,6}|P\d{6,})', text, re.IGNORECASE)
            if permit_match:
                permit_id = permit_match.group(1)

                # Extract address if present
                addr_match = re.search(r'(\d+\s+[A-Z][a-zA-Z\s]+(?:St|Ave|Rd|Dr|Ln|Blvd|Ct|Way|Cir|Pl))', text)
                address = addr_match.group(1) if addr_match else ''

                permits.append({
                    'permit_id': permit_id,
                    'address': address,
                    'raw_text': text[:500],
                    'city': city_config['name'],
                    'source': 'mygov',
                })
        except Exception as e:
            logger.debug(f"Error extracting result: {e}")

    return permits


async def scrape_city(city_key: str, target_count: int) -> list:
    """Scrape permits for a single city."""
    if city_key not in MYGOV_CITIES:
        logger.error(f"Unknown city: {city_key}")
        logger.info(f"Available: {', '.join(MYGOV_CITIES.keys())}")
        return []

    city_config = MYGOV_CITIES[city_key]
    all_permits = []

    print("=" * 60)
    print(f"{city_config['name'].upper()} MYGOV PERMIT SCRAPER")
    print("=" * 60)
    print(f"Target: {target_count} permits")
    print(f"Time: {datetime.now().isoformat()}")
    print()

    # Common search terms for permit lookup
    search_terms = [
        '2025',  # Year-based search
        '2024',
        'permit',
        'building',
        'residential',
        'new construction',
        'remodel',
        'pool',
        'fence',
        'roof',
        'electrical',
        'plumbing',
        'mechanical',
    ]

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        page = await context.new_page()

        try:
            seen_ids = set()

            for term in search_terms:
                if len(all_permits) >= target_count:
                    break

                logger.info(f"Searching: '{term}'...")
                permits = await search_permits(page, city_config, term)

                # Dedupe
                for permit in permits:
                    pid = permit.get('permit_id', '')
                    if pid and pid not in seen_ids:
                        seen_ids.add(pid)
                        all_permits.append(permit)

                logger.info(f"Total unique permits: {len(all_permits)}")
                await asyncio.sleep(1)  # Rate limiting

        finally:
            await browser.close()

    # Save results
    output_file = OUTPUT_DIR / f"{city_key}_raw.json"
    with open(output_file, 'w') as f:
        json.dump(all_permits[:target_count], f, indent=2, default=str)

    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total permits: {len(all_permits)}")
    print(f"Saved to: {output_file}")

    return all_permits[:target_count]


async def main():
    if len(sys.argv) < 2:
        print("Usage: python3 mygov_multi.py <city> [count]")
        print(f"Available cities: {', '.join(MYGOV_CITIES.keys())}")
        sys.exit(1)

    city_key = sys.argv[1].lower()
    target_count = int(sys.argv[2]) if len(sys.argv) > 2 else 100

    await scrape_city(city_key, target_count)


if __name__ == '__main__':
    asyncio.run(main())
```

**Step 2: Test with one city**

Run: `cd /home/reid/testhome/permit-scraper && python3 scrapers/mygov_multi.py mansfield 10`

Expected: Some permits found (may need DOM selector refinement)

**Step 3: Commit skeleton**

```bash
git add scrapers/mygov_multi.py
git commit -m "feat: add multi-city MyGov scraper for DFW"
```

---

### Task 5: Refine MyGov Scraper Based on Actual DOM

**Step 1: Take debug screenshots**

Add screenshot capability to understand actual DOM structure.

**Step 2: Inspect MyGov page structure**

Navigate to `https://public.mygov.us/mansfield_tx/lookup` manually and inspect.

**Step 3: Update selectors based on actual structure**

MyGov portals typically have:
- Search input for address/permit lookup
- Accordion-style results
- Permit details in collapsible sections

**Step 4: Test and commit refinements**

```bash
git add scrapers/mygov_multi.py
git commit -m "fix: refine MyGov DOM selectors"
```

---

## Phase 3: Sachse SmartGov Scraper

### Task 6: Create Sachse SmartGov Scraper

See separate plan: `docs/plans/2025-12-12-sachse-smartgov-scraper.md`

This task is already documented in detail in the Sachse-specific plan.

---

## Phase 4: Update Documentation

### Task 7: Update CLAUDE.md

**Files:**
- Modify: `/home/reid/testhome/permit-scraper/CLAUDE.md`

**Step 1: Add new cities to Working Portals section**

```markdown
## Working Portals (All Fast DOM Extraction)

### eTRAKiT
- Dallas (Accela) - `accela_fast.py`
- ...existing...
- Keller (eTRAKiT) - `etrakit_fast.py`

### EnerGov CSS
- Southlake, Colleyville, McKinney, Allen, Trophy Club, Waxahachie - `citizen_self_service.py`
- Cedar Hill, DeSoto - `citizen_self_service.py` (NEW)

### MyGov
- Westlake - `mygov_westlake.py`
- Mansfield, Rowlett, Burleson, Little Elm, Lancaster, Midlothian, Celina, Fate, Venus - `mygov_multi.py` (NEW)

### SmartGov
- Sachse - `smartgov_sachse.py` (NEW)
```

**Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: add new municipalities to CLAUDE.md"
```

---

### Task 8: Update TODO.md

**Files:**
- Modify: `/home/reid/testhome/permit-scraper/TODO.md`

Remove completed items and add any new follow-up tasks discovered during implementation.

---

## Verification Checklist

After completing all tasks:

### eTRAKiT
- [ ] `python3 scrapers/etrakit_fast.py keller 10` returns 10+ permits

### EnerGov CSS
- [ ] `python3 scrapers/citizen_self_service.py cedar_hill 10` returns 10+ permits
- [ ] `python3 scrapers/citizen_self_service.py desoto 10` returns 10+ permits

### MyGov
- [ ] `python3 scrapers/mygov_multi.py mansfield 10` returns permits
- [ ] `python3 scrapers/mygov_multi.py rowlett 10` returns permits
- [ ] `python3 scrapers/mygov_multi.py burleson 10` returns permits
- [ ] Additional cities tested

### SmartGov
- [ ] `python3 scrapers/smartgov_sachse.py 10` returns permits

### Documentation
- [ ] CLAUDE.md updated
- [ ] All commits pushed

---

## Risk Register

| Risk | Mitigation |
|------|------------|
| eTRAKiT permit prefix varies by city | Test first, adjust regex pattern |
| EnerGov CSS URL format may differ | Tyler-hosted URLs follow pattern |
| MyGov DOM structure varies | Take screenshots, iterate on selectors |
| SmartGov Angular SPA complexity | Use Playwright with network idle waits |
| Some cities may block scrapers | Use stealth mode, realistic delays |
| CAD enrichment for new counties | Johnson, Rockwall counties need research |

---

## CAD County Coverage

| County | Status | Cities Affected |
|--------|--------|-----------------|
| Tarrant | ✅ Existing | Mansfield, Keller |
| Dallas | ✅ Existing | Rowlett, Lancaster, Cedar Hill, DeSoto, Sachse |
| Denton | ✅ Existing | Little Elm |
| Collin | ✅ Existing | Celina, Sachse |
| Rockwall | ⚠️ Need research | Rowlett, Fate |
| Johnson | ⚠️ Need research | Burleson, Venus |
| Ellis | ❌ No API | Midlothian |

**Note:** Cities in Ellis County (Midlothian) can be scraped but won't have CAD enrichment until an API is found or alternative data source added.

---

## Summary of Changes

| File | Change Type | Cities Added |
|------|-------------|--------------|
| `scrapers/etrakit_fast.py` | Config addition | Keller |
| `scrapers/citizen_self_service.py` | Config additions | Cedar Hill, DeSoto |
| `scrapers/mygov_multi.py` | New file | 9 MyGov cities |
| `scrapers/smartgov_sachse.py` | New file | Sachse |
| `CLAUDE.md` | Documentation | All 13 cities |

---

## Estimated Impact

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| Cities covered | ~11 | ~24 | +13 cities |
| Population coverage | ~500K | ~1M+ | +100% |
| Scrapers | 7 | 9 | +2 new |
