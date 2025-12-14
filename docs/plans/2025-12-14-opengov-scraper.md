# OpenGov Permit Scraper Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a scraper for OpenGov permit portals to capture Highland Park (ultra-wealthy, 9k pop) and Bedford (48k pop) permits.

**Architecture:** Playwright-based DOM scraper for Ember.js SPA. Use address/street name searches to discover permits (similar to MyGov pattern). Multi-city config dict for reuse.

**Tech Stack:** Python 3, Playwright, asyncio, tenacity for retries

---

## Summary of Changes

| File | Action |
|------|--------|
| `scrapers/opengov.py` | Create - New scraper |
| `tests/test_opengov.py` | Create - Unit tests |
| `docs/research/dfw_municipalities.json` | Modify - Update status |

---

## Task 1: Create OpenGov Scraper Skeleton

**Files:**
- Create: `scrapers/opengov.py`

**Step 1: Write the basic scraper structure**

```python
#!/usr/bin/env python3
"""
OPENGOV PERMIT SCRAPER (Playwright)
Platform: OpenGov Permitting & Licensing Portal
Covers: Highland Park, Bedford (wealthy DFW suburbs)

Usage:
  python3 scrapers/opengov.py highland_park 100
  python3 scrapers/opengov.py bedford 100
  python3 scrapers/opengov.py --list
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

# OpenGov cities with confirmed public access
OPENGOV_CITIES = {
    'highland_park': {
        'name': 'Highland Park',
        'base_url': 'https://highlandparktx.portal.opengov.com',
        'pop': 9000,
        'tier': 'A',  # Ultra-wealthy
    },
    'bedford': {
        'name': 'Bedford',
        'base_url': 'https://bedfordtx.portal.opengov.com',
        'pop': 48000,
        'tier': 'B',
    },
}

# Common street names to search (same as MyGov pattern)
SEARCH_TERMS = [
    'Main', 'Oak', 'Park', 'Hill', 'Lake',
    'Cedar', 'Pine', 'Maple', 'Elm',
    'First', 'Second', 'Third',
    'North', 'South', 'East', 'West',
    'Creek', 'Spring', 'Valley', 'Ridge',
    'Meadow', 'Forest', 'Highland', 'Sunset',
]


async def main():
    if len(sys.argv) < 2 or sys.argv[1] == '--list':
        print("OpenGov Multi-City Scraper")
        print()
        print("Available cities:")
        for key, city in sorted(OPENGOV_CITIES.items(), key=lambda x: -x[1]['pop']):
            print(f"  {key:15} - {city['name']:15} (pop: {city['pop']:,})")
        print()
        print("Usage: python3 opengov.py <city> [count]")
        return

    city_key = sys.argv[1].lower()
    target = int(sys.argv[2]) if len(sys.argv) > 2 else 50

    if city_key not in OPENGOV_CITIES:
        print(f"Unknown city: {city_key}")
        print(f"Available: {', '.join(sorted(OPENGOV_CITIES.keys()))}")
        return

    await scrape_city(city_key, target)


async def scrape_city(city_key: str, target_count: int) -> list:
    """Scrape permits for a city."""
    # Placeholder - implemented in Task 2
    print(f"Scraping {city_key} for {target_count} permits...")
    return []


if __name__ == '__main__':
    asyncio.run(main())
```

**Step 2: Verify file runs**

Run: `cd /home/reid/testhome/permit-scraper && python3 scrapers/opengov.py --list`

Expected output:
```
OpenGov Multi-City Scraper

Available cities:
  bedford         - Bedford         (pop: 48,000)
  highland_park   - Highland Park   (pop: 9,000)

Usage: python3 opengov.py <city> [count]
```

**Step 3: Commit skeleton**

```bash
cd /home/reid/testhome/permit-scraper
git add scrapers/opengov.py
git commit -m "feat: add OpenGov scraper skeleton for Highland Park and Bedford"
```

---

## Task 2: Implement Portal Navigation

**Files:**
- Modify: `scrapers/opengov.py`

**Step 1: Add navigate_to_search function**

Add this function after the SEARCH_TERMS list:

```python
async def navigate_to_search(page, city_config: dict) -> bool:
    """
    Navigate to OpenGov portal and find the search interface.

    OpenGov uses Ember.js SPA - we need to wait for app to bootstrap,
    then find the search functionality.

    Returns True if search is accessible, False otherwise.
    """
    base_url = city_config['base_url']
    city_name = city_config['name']

    try:
        logger.info(f"[{city_name}] Navigating to {base_url}")
        await page.goto(base_url, timeout=30000)

        # Wait for Ember app to load (loading spinner disappears)
        await page.wait_for_selector('#main-content, .ember-application', timeout=20000)
        logger.info(f"[{city_name}] App loaded, looking for search...")

        # Give Angular/Ember extra time to render
        await asyncio.sleep(3)

        # Look for search button/link in header
        # Common patterns: "Search" link, magnifying glass icon, search input
        search_selectors = [
            'a:has-text("Search")',
            'button:has-text("Search")',
            '[data-test="search"]',
            '.search-button',
            'input[type="search"]',
            '[placeholder*="Search"]',
        ]

        for selector in search_selectors:
            element = page.locator(selector).first
            if await element.count() > 0:
                logger.info(f"[{city_name}] Found search element: {selector}")
                return True

        # If no search found, try clicking "Permits" or "Records" link
        nav_links = ['Permits', 'Records', 'Applications', 'Public Records']
        for link_text in nav_links:
            link = page.locator(f'a:has-text("{link_text}")').first
            if await link.count() > 0:
                await link.click()
                await asyncio.sleep(2)
                logger.info(f"[{city_name}] Clicked '{link_text}' navigation")
                return True

        logger.warning(f"[{city_name}] Could not find search interface")
        return False

    except PlaywrightTimeout:
        logger.error(f"[{city_name}] Timeout loading portal")
        return False
    except Exception as e:
        logger.error(f"[{city_name}] Error navigating: {e}")
        return False
```

**Step 2: Test navigation manually**

Run: `cd /home/reid/testhome/permit-scraper && python3 -c "
import asyncio
from playwright.async_api import async_playwright

async def test():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # Show browser
        page = await browser.new_page()
        await page.goto('https://highlandparktx.portal.opengov.com')
        await asyncio.sleep(10)  # Watch what loads
        print(await page.title())
        await browser.close()

asyncio.run(test())
"`

Expected: Browser opens, shows OpenGov portal loading, note the UI structure.

**Step 3: Commit navigation**

```bash
cd /home/reid/testhome/permit-scraper
git add scrapers/opengov.py
git commit -m "feat: add OpenGov portal navigation function"
```

---

## Task 3: Implement Search Function

**Files:**
- Modify: `scrapers/opengov.py`

**Step 1: Add search_permits function**

Add after navigate_to_search:

```python
@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=1, min=1, max=4),
    retry=retry_if_exception_type((PlaywrightTimeout,)),
    reraise=True
)
async def search_permits(page, city_config: dict, search_term: str) -> list:
    """
    Search for permits using a search term and extract results.

    Args:
        page: Playwright page
        city_config: City configuration dict
        search_term: Street name or keyword to search

    Returns:
        List of permit dicts
    """
    permits = []
    city_name = city_config['name']

    try:
        # Find and fill search input
        search_input = page.locator('input[type="search"], input[placeholder*="Search"], #search-input').first
        if await search_input.count() == 0:
            logger.warning(f"[{city_name}] Search input not found")
            return permits

        await search_input.clear()
        await search_input.fill(search_term)
        await asyncio.sleep(0.5)

        # Submit search (Enter key or click search button)
        await search_input.press('Enter')
        await asyncio.sleep(3)  # Wait for results

        # Extract results from page
        # OpenGov typically shows results in a table or card layout
        result_selectors = [
            '.search-result',
            '.permit-card',
            'tr[data-permit]',
            '.record-item',
            '[data-record-id]',
        ]

        for selector in result_selectors:
            results = page.locator(selector)
            count = await results.count()
            if count > 0:
                logger.info(f"[{city_name}] Found {count} results with {selector}")

                for i in range(min(count, 50)):  # Limit per search
                    try:
                        result = results.nth(i)
                        text = await result.inner_text()

                        permit = parse_permit_text(text, city_name)
                        if permit:
                            permits.append(permit)
                    except Exception as e:
                        logger.debug(f"Error parsing result {i}: {e}")
                        continue
                break

        if not permits:
            # Fallback: try to parse entire page body
            body_text = await page.inner_text('body')
            permits = parse_page_content(body_text, city_name)

        logger.info(f"[{city_name}] Search '{search_term}': {len(permits)} permits")
        return permits

    except PlaywrightTimeout:
        logger.warning(f"[{city_name}] Timeout searching '{search_term}'")
        return permits
    except Exception as e:
        logger.debug(f"[{city_name}] Search error: {e}")
        return permits
```

**Step 2: Add parsing helpers**

Add before search_permits:

```python
def parse_permit_text(text: str, city: str) -> dict | None:
    """Parse permit info from result text."""
    if not text or len(text) < 10:
        return None

    lines = [l.strip() for l in text.split('\n') if l.strip()]

    permit = {
        'permit_id': '',
        'permit_type': '',
        'address': '',
        'status': '',
        'date': '',
        'city': city,
        'source': 'opengov',
    }

    for line in lines:
        # Look for permit ID patterns (varies by city)
        # Common: BLD-2025-001234, P25-00123, 2025-BP-0001
        id_match = re.search(r'([A-Z]{2,4}[-]?\d{4}[-]?\d{3,6})', line)
        if id_match and not permit['permit_id']:
            permit['permit_id'] = id_match.group(1)

        # Look for dates
        date_match = re.search(r'(\d{1,2}/\d{1,2}/\d{4})', line)
        if date_match and not permit['date']:
            permit['date'] = date_match.group(1)

        # Look for addresses (number + street)
        addr_match = re.search(r'(\d+\s+[A-Z][A-Za-z\s]+(?:St|Ave|Dr|Rd|Ln|Blvd|Ct|Way|Pl))', line, re.IGNORECASE)
        if addr_match and not permit['address']:
            permit['address'] = addr_match.group(1).strip()

        # Look for permit types
        type_keywords = ['residential', 'commercial', 'electrical', 'mechanical',
                        'plumbing', 'building', 'fence', 'pool', 'roof', 'hvac',
                        'remodel', 'addition', 'new construction']
        for kw in type_keywords:
            if kw in line.lower() and not permit['permit_type']:
                permit['permit_type'] = line[:50]
                break

    # Only return if we have at least permit_id or address
    if permit['permit_id'] or permit['address']:
        return permit
    return None


def parse_page_content(content: str, city: str) -> list:
    """Fallback: parse permits from raw page text."""
    permits = []

    # Split by common separators
    chunks = re.split(r'\n{2,}|<hr>|───', content)

    for chunk in chunks:
        permit = parse_permit_text(chunk, city)
        if permit:
            permits.append(permit)

    return permits
```

**Step 3: Commit search function**

```bash
cd /home/reid/testhome/permit-scraper
git add scrapers/opengov.py
git commit -m "feat: add OpenGov permit search and parsing functions"
```

---

## Task 4: Implement Main Scrape Loop

**Files:**
- Modify: `scrapers/opengov.py`

**Step 1: Replace scrape_city placeholder**

Replace the placeholder `scrape_city` function with:

```python
async def scrape_city(city_key: str, target_count: int) -> list:
    """Scrape permits for a city using street name searches."""
    if city_key not in OPENGOV_CITIES:
        print(f"Unknown city: {city_key}")
        return []

    city = OPENGOV_CITIES[city_key]
    all_permits = []
    seen_ids = set()

    print("=" * 60)
    print(f"{city['name'].upper()} OPENGOV PERMIT SCRAPER")
    print("=" * 60)
    print(f"Target: {target_count} permits")
    print(f"Time: {datetime.now().isoformat()}")
    print()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        page = await context.new_page()

        try:
            # Navigate to portal
            if not await navigate_to_search(page, city):
                logger.error(f"Could not access {city['name']} portal")
                return []

            # Search using street names
            for term in SEARCH_TERMS:
                if len(all_permits) >= target_count:
                    break

                permits = await search_permits(page, city, term)

                # Dedupe
                new_count = 0
                for permit in permits:
                    key = permit.get('permit_id') or permit.get('address', '')
                    if key and key not in seen_ids:
                        seen_ids.add(key)
                        all_permits.append(permit)
                        new_count += 1

                if new_count > 0:
                    logger.info(f"  +{new_count} permits (total: {len(all_permits)})")

                await asyncio.sleep(1)  # Rate limit

        finally:
            await browser.close()

    # Save results
    output_file = OUTPUT_DIR / f"{city_key}_opengov_raw.json"
    output_data = {
        'source': city_key,
        'scraped_at': datetime.now().isoformat(),
        'permits': all_permits[:target_count]
    }
    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)

    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"City: {city['name']}")
    print(f"Permits found: {len(all_permits)}")
    print(f"Saved to: {output_file}")

    if all_permits:
        print()
        print("SAMPLE:")
        for p in all_permits[:3]:
            print(f"  {p.get('permit_id', 'N/A')} | {p.get('address', '')[:50]}")

    return all_permits[:target_count]
```

**Step 2: Test full scraper**

Run: `cd /home/reid/testhome/permit-scraper && python3 scrapers/opengov.py highland_park 10`

Expected: Attempts to scrape, may need debugging based on actual portal structure.

**Step 3: Commit main loop**

```bash
cd /home/reid/testhome/permit-scraper
git add scrapers/opengov.py
git commit -m "feat: implement OpenGov main scrape loop with deduplication"
```

---

## Task 5: Debug and Adapt to Actual Portal Structure

**Files:**
- Modify: `scrapers/opengov.py`

**Step 1: Run with visible browser to inspect portal**

Run: `cd /home/reid/testhome/permit-scraper && python3 -c "
import asyncio
from playwright.async_api import async_playwright

async def debug():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        # Highland Park portal
        await page.goto('https://highlandparktx.portal.opengov.com')
        await asyncio.sleep(5)

        # Take screenshot
        await page.screenshot(path='opengov_debug.png')

        # Print page structure
        content = await page.content()
        with open('opengov_debug.html', 'w') as f:
            f.write(content)

        print('Screenshot: opengov_debug.png')
        print('HTML: opengov_debug.html')

        # Wait for manual inspection
        input('Press Enter to close browser...')
        await browser.close()

asyncio.run(debug())
"`

Expected: Browser opens, you can see actual UI structure, screenshots saved.

**Step 2: Update selectors based on findings**

After inspecting the portal, update the selectors in `navigate_to_search` and `search_permits` to match actual DOM elements.

**Step 3: Commit fixes**

```bash
cd /home/reid/testhome/permit-scraper
git add scrapers/opengov.py opengov_debug.png
git commit -m "fix: update OpenGov selectors based on portal inspection"
```

---

## Task 6: Add Unit Tests

**Files:**
- Create: `tests/test_opengov.py`

**Step 1: Write parsing tests**

```python
#!/usr/bin/env python3
"""Tests for OpenGov scraper parsing functions."""

import pytest
import sys
from pathlib import Path

# Add scrapers to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'scrapers'))

from opengov import parse_permit_text, parse_page_content


class TestParsePermitText:
    """Tests for parse_permit_text function."""

    def test_parses_permit_id(self):
        text = "BLD-2025-001234 New Construction 123 Main St"
        result = parse_permit_text(text, "Highland Park")
        assert result is not None
        assert result['permit_id'] == 'BLD-2025-001234'

    def test_parses_address(self):
        text = "Permit #12345 at 456 Oak Ave Highland Park"
        result = parse_permit_text(text, "Highland Park")
        assert result is not None
        assert '456 Oak Ave' in result['address']

    def test_parses_date(self):
        text = "BLD-2025-001 Issued 12/15/2025"
        result = parse_permit_text(text, "Bedford")
        assert result is not None
        assert result['date'] == '12/15/2025'

    def test_parses_permit_type(self):
        text = "P-2025-001 Residential Remodel 789 Pine Dr"
        result = parse_permit_text(text, "Bedford")
        assert result is not None
        assert 'remodel' in result['permit_type'].lower()

    def test_returns_none_for_empty_text(self):
        result = parse_permit_text("", "Highland Park")
        assert result is None

    def test_returns_none_for_no_identifiers(self):
        result = parse_permit_text("Just some random text", "Highland Park")
        assert result is None

    def test_sets_city_and_source(self):
        text = "BLD-2025-001 123 Main St"
        result = parse_permit_text(text, "Highland Park")
        assert result['city'] == 'Highland Park'
        assert result['source'] == 'opengov'


class TestParsePageContent:
    """Tests for parse_page_content function."""

    def test_parses_multiple_permits(self):
        content = """
        BLD-2025-001 Residential 123 Main St

        BLD-2025-002 Commercial 456 Oak Ave

        BLD-2025-003 Pool 789 Pine Dr
        """
        results = parse_page_content(content, "Bedford")
        assert len(results) >= 3

    def test_handles_empty_content(self):
        results = parse_page_content("", "Bedford")
        assert results == []
```

**Step 2: Run tests**

Run: `cd /home/reid/testhome/permit-scraper && pytest tests/test_opengov.py -v`

Expected: All tests pass.

**Step 3: Commit tests**

```bash
cd /home/reid/testhome/permit-scraper
git add tests/test_opengov.py
git commit -m "test: add unit tests for OpenGov parsing functions"
```

---

## Task 7: Update Documentation

**Files:**
- Modify: `docs/research/dfw_municipalities.json`
- Modify: `CLAUDE.md`

**Step 1: Update municipalities JSON**

Update Highland Park and Bedford entries:

```json
{
  "city": "Highland Park",
  "status": "working",
  "platform": "OpenGov",
  "portal_url": "https://highlandparktx.portal.opengov.com",
  "notes": "ADDED Dec 2024 - Ultra high wealth enclave, covered by opengov.py"
},
{
  "city": "Bedford",
  "status": "working",
  "platform": "OpenGov",
  "portal_url": "https://bedfordtx.portal.opengov.com",
  "notes": "ADDED Dec 2024 - Covered by opengov.py"
}
```

**Step 2: Add OpenGov to CLAUDE.md working portals**

Add under "### Other":
```markdown
### OpenGov
- Highland Park, Bedford - `opengov.py`
```

**Step 3: Commit documentation**

```bash
cd /home/reid/testhome/permit-scraper
git add docs/research/dfw_municipalities.json CLAUDE.md
git commit -m "docs: add OpenGov scraper to working portals documentation"
```

---

## Task 8: Integration Test

**Step 1: Run full scrape on both cities**

```bash
cd /home/reid/testhome/permit-scraper
python3 scrapers/opengov.py highland_park 50
python3 scrapers/opengov.py bedford 50
```

**Step 2: Load to database**

```bash
python3 scripts/load_permits.py --file data/raw/highland_park_opengov_raw.json
python3 scripts/load_permits.py --file data/raw/bedford_opengov_raw.json
```

**Step 3: Verify data quality**

```bash
python3 -c "
import json
for city in ['highland_park', 'bedford']:
    with open(f'data/raw/{city}_opengov_raw.json') as f:
        data = json.load(f)
    permits = data.get('permits', [])
    print(f'{city}: {len(permits)} permits')
    if permits:
        print(f'  Sample: {permits[0]}')
"
```

**Step 4: Final commit**

```bash
git add .
git commit -m "feat: complete OpenGov scraper for Highland Park and Bedford"
```

---

## Risk Summary

| Risk | Mitigation |
|------|------------|
| OpenGov portal requires login | Check for public records section first |
| Ember.js loads slowly | Extended timeouts (20s) |
| Search interface varies by city | Multiple selector fallbacks |
| Rate limiting | 1s delay between searches |
| No permits found | Debug with visible browser, adjust selectors |

---

## Expected Outcome

- **Highland Park**: 50-200 permits (small wealthy city, lower volume but high value)
- **Bedford**: 100-500 permits (larger city, more activity)
- **Combined**: ~57,000 population coverage added

---

## Verification Checklist

- [ ] `python3 scrapers/opengov.py --list` shows both cities
- [ ] `python3 scrapers/opengov.py highland_park 10` returns permits
- [ ] `python3 scrapers/opengov.py bedford 10` returns permits
- [ ] `pytest tests/test_opengov.py -v` passes
- [ ] Data loads to database successfully
