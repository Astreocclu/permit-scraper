# Sachse SmartGov Scraper Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create a Playwright-based scraper for Sachse, TX permits using the SmartGov (Granicus) platform.

**Architecture:** Browser automation via Playwright to interact with Angular SPA. Navigate to application search, perform wildcard searches, extract permit data from results. Similar pattern to existing `mygov_westlake.py` but adapted for SmartGov's different DOM structure.

**Tech Stack:** Python 3, Playwright (async), tenacity (retry logic), JSON output

---

## Research Summary (Completed)

| Item | Value |
|------|-------|
| Portal URL | `https://ci-sachse-tx.smartgovcommunity.com` |
| Search URL | `https://ci-sachse-tx.smartgovcommunity.com/ApplicationPublic/ApplicationSearch` |
| Framework | Angular SPA (JavaScript rendering required) |
| Login Required | No (public access) |
| Platform | SmartGov by Granicus (version 2025.20) |
| Scrapability | Easy-Medium |

---

## Task 1: Create SmartGov Scraper Skeleton

**Files:**
- Create: `scrapers/smartgov_sachse.py`

**Step 1: Write the basic scraper structure**

```python
#!/usr/bin/env python3
"""
SACHSE SMARTGOV PERMIT SCRAPER (Playwright)
Portal: SmartGov by Granicus (Angular SPA)
City: Sachse, TX

Usage:
  python3 scrapers/smartgov_sachse.py 100
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

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Output path
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "raw"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# SmartGov configuration
SMARTGOV_CONFIG = {
    'base_url': 'https://ci-sachse-tx.smartgovcommunity.com',
    'search_url': 'https://ci-sachse-tx.smartgovcommunity.com/ApplicationPublic/ApplicationSearch',
    'city': 'Sachse',
}


async def main(target_count: int = 100):
    """Main scraper entry point."""
    print("=" * 60)
    print(f"SACHSE SMARTGOV PERMIT SCRAPER")
    print("=" * 60)
    print(f"Target: {target_count} permits")
    print(f"Time: {datetime.now().isoformat()}")
    print()

    permits = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        page = await context.new_page()

        try:
            permits = await scrape_permits(page, target_count)
        finally:
            await browser.close()

    # Save results
    output_file = OUTPUT_DIR / "sachse_raw.json"
    with open(output_file, 'w') as f:
        json.dump(permits, f, indent=2, default=str)

    print()
    print("=" * 60)
    print(f"SUMMARY")
    print("=" * 60)
    print(f"Total permits: {len(permits)}")
    print(f"Saved to: {output_file}")

    return permits


async def scrape_permits(page, target_count: int) -> list:
    """Scrape permits from SmartGov search interface."""
    permits = []

    # TODO: Implement search and extraction
    logger.info("Scraper not yet implemented")

    return permits


if __name__ == '__main__':
    target = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    asyncio.run(main(target))
```

**Step 2: Verify skeleton runs**

Run: `cd /home/reid/testhome/permit-scraper && python3 scrapers/smartgov_sachse.py 5`

Expected output:
```
============================================================
SACHSE SMARTGOV PERMIT SCRAPER
============================================================
Target: 5 permits
Time: 2025-12-12T...

============================================================
SUMMARY
============================================================
Total permits: 0
Saved to: data/raw/sachse_raw.json
```

**Step 3: Commit skeleton**

```bash
git add scrapers/smartgov_sachse.py
git commit -m "feat: add Sachse SmartGov scraper skeleton"
```

---

## Task 2: Implement Search Navigation

**Files:**
- Modify: `scrapers/smartgov_sachse.py`

**Step 1: Add navigation to search page**

Add this function before `scrape_permits`:

```python
async def navigate_to_search(page) -> bool:
    """Navigate to the SmartGov application search page."""
    logger.info(f"[1] Navigating to search page...")

    try:
        await page.goto(
            SMARTGOV_CONFIG['search_url'],
            wait_until='networkidle',
            timeout=30000
        )

        # Wait for Angular to load
        await page.wait_for_function(
            'typeof window.angular !== "undefined" || document.querySelector("input[type=text]") !== null',
            timeout=10000
        )

        # Check for search input
        search_input = await page.query_selector('input[type="text"], input[type="search"]')
        if search_input:
            logger.info(f"    Search input found")
            return True

        logger.warning(f"    Search input not found")
        return False

    except PlaywrightTimeout:
        logger.error(f"    Timeout navigating to search page")
        return False
```

**Step 2: Update scrape_permits to use navigation**

Replace the `scrape_permits` function:

```python
async def scrape_permits(page, target_count: int) -> list:
    """Scrape permits from SmartGov search interface."""
    permits = []

    # Navigate to search
    if not await navigate_to_search(page):
        logger.error("Failed to navigate to search page")
        return permits

    # Take debug screenshot
    await page.screenshot(path='debug_html/sachse_search.png')
    logger.info(f"[2] Screenshot saved to debug_html/sachse_search.png")

    return permits
```

**Step 3: Test navigation works**

Run: `cd /home/reid/testhome/permit-scraper && python3 scrapers/smartgov_sachse.py 5`

Expected: Screenshot saved showing search page.

**Step 4: Commit**

```bash
git add scrapers/smartgov_sachse.py
git commit -m "feat: add SmartGov search navigation"
```

---

## Task 3: Implement Search Execution

**Files:**
- Modify: `scrapers/smartgov_sachse.py`

**Step 1: Add search execution function**

Add after `navigate_to_search`:

```python
async def execute_search(page, query: str = "*") -> int:
    """Execute a search query and return result count."""
    logger.info(f"[3] Executing search with query: {query}")

    try:
        # Find and fill search input
        search_input = await page.query_selector('input[type="text"], input[type="search"]')
        if not search_input:
            logger.error("    Search input not found")
            return 0

        await search_input.fill(query)
        await asyncio.sleep(0.5)

        # Try to find and click search button
        search_btn = await page.query_selector('button:has-text("Search"), input[type="submit"]')
        if search_btn:
            await search_btn.click()
        else:
            # Fallback: press Enter
            await search_input.press('Enter')

        # Wait for results
        await asyncio.sleep(2)
        await page.wait_for_load_state('networkidle', timeout=15000)

        # Check for results
        result_count = await page.evaluate('''() => {
            // Try to find result count indicator
            const countEl = document.querySelector('.result-count, .total-count, [class*="count"]');
            if (countEl) return parseInt(countEl.textContent) || 0;

            // Count result rows
            const rows = document.querySelectorAll('tr[class*="row"], .search-result, [class*="result-item"]');
            return rows.length;
        }''')

        logger.info(f"    Results found: {result_count}")
        return result_count

    except PlaywrightTimeout:
        logger.error("    Timeout executing search")
        return 0
```

**Step 2: Update scrape_permits to execute search**

```python
async def scrape_permits(page, target_count: int) -> list:
    """Scrape permits from SmartGov search interface."""
    permits = []

    # Navigate to search
    if not await navigate_to_search(page):
        logger.error("Failed to navigate to search page")
        return permits

    # Execute search
    result_count = await execute_search(page, "*")

    # Take debug screenshot
    await page.screenshot(path='debug_html/sachse_results.png')
    logger.info(f"[4] Screenshot saved to debug_html/sachse_results.png")

    return permits
```

**Step 3: Test search execution**

Run: `cd /home/reid/testhome/permit-scraper && python3 scrapers/smartgov_sachse.py 5`

Check: `debug_html/sachse_results.png` should show search results.

**Step 4: Commit**

```bash
git add scrapers/smartgov_sachse.py
git commit -m "feat: add SmartGov search execution"
```

---

## Task 4: Implement Result Extraction

**Files:**
- Modify: `scrapers/smartgov_sachse.py`

**Step 1: Add result extraction function**

Add after `execute_search`:

```python
async def extract_permits_from_page(page) -> list:
    """Extract permit data from current results page."""
    logger.info(f"[5] Extracting permits from page...")

    permits = await page.evaluate('''() => {
        const results = [];

        // SmartGov typically uses table rows or card-style results
        const rows = document.querySelectorAll(
            'table tbody tr, .search-result, .result-card, [class*="application-row"]'
        );

        rows.forEach(row => {
            // Try to extract common permit fields
            const cells = row.querySelectorAll('td');
            const getText = (el) => el ? el.textContent.trim() : '';

            // Adapt selectors based on actual page structure
            const permit = {
                permit_id: '',
                permit_type: '',
                address: '',
                status: '',
                description: '',
                issued_date: '',
                raw_text: getText(row)
            };

            // Try table cells
            if (cells.length >= 2) {
                permit.permit_id = getText(cells[0]);
                permit.permit_type = cells.length > 1 ? getText(cells[1]) : '';
                permit.address = cells.length > 2 ? getText(cells[2]) : '';
                permit.status = cells.length > 3 ? getText(cells[3]) : '';
            }

            // Try card-style with labeled fields
            const idEl = row.querySelector('[class*="id"], [class*="number"], a[href*="Application"]');
            if (idEl) permit.permit_id = getText(idEl);

            const addrEl = row.querySelector('[class*="address"], [class*="location"]');
            if (addrEl) permit.address = getText(addrEl);

            const typeEl = row.querySelector('[class*="type"], [class*="category"]');
            if (typeEl) permit.permit_type = getText(typeEl);

            const statusEl = row.querySelector('[class*="status"]');
            if (statusEl) permit.status = getText(statusEl);

            if (permit.permit_id || permit.address) {
                results.push(permit);
            }
        });

        return results;
    }''')

    logger.info(f"    Extracted {len(permits)} permits")
    return permits
```

**Step 2: Update scrape_permits to extract results**

```python
async def scrape_permits(page, target_count: int) -> list:
    """Scrape permits from SmartGov search interface."""
    all_permits = []

    # Navigate to search
    if not await navigate_to_search(page):
        logger.error("Failed to navigate to search page")
        return all_permits

    # Execute search
    result_count = await execute_search(page, "*")

    # Extract permits
    permits = await extract_permits_from_page(page)
    all_permits.extend(permits)

    # Take debug screenshot
    await page.screenshot(path='debug_html/sachse_results.png')

    logger.info(f"[6] Total permits extracted: {len(all_permits)}")
    return all_permits
```

**Step 3: Test extraction**

Run: `cd /home/reid/testhome/permit-scraper && python3 scrapers/smartgov_sachse.py 5`

Expected: Some permits extracted (may need DOM selector refinement based on actual page).

**Step 4: Commit**

```bash
git add scrapers/smartgov_sachse.py
git commit -m "feat: add SmartGov permit extraction"
```

---

## Task 5: Refine Extraction Based on Actual DOM

**Files:**
- Modify: `scrapers/smartgov_sachse.py`

**Step 1: Run scraper with debug output**

Run: `cd /home/reid/testhome/permit-scraper && python3 scrapers/smartgov_sachse.py 5`

**Step 2: Inspect debug screenshot**

Check `debug_html/sachse_results.png` to see actual page structure.

**Step 3: Update selectors based on actual DOM**

This step requires manual inspection. Common SmartGov patterns:

```python
# If results are in a table:
'table.search-results tbody tr'

# If results are card-style:
'.application-card, .result-item'

# If Angular uses ng-repeat:
'[ng-repeat*="application"], [ng-repeat*="result"]'
```

**Step 4: Test refined extraction**

Run: `python3 scrapers/smartgov_sachse.py 10`

Expected: More accurate permit data extracted.

**Step 5: Commit**

```bash
git add scrapers/smartgov_sachse.py
git commit -m "fix: refine SmartGov DOM selectors"
```

---

## Task 6: Add Pagination Support

**Files:**
- Modify: `scrapers/smartgov_sachse.py`

**Step 1: Add pagination function**

Add after `extract_permits_from_page`:

```python
async def get_next_page(page) -> bool:
    """Navigate to next page of results. Returns False if no more pages."""
    try:
        # SmartGov pagination patterns
        next_btn = await page.query_selector(
            'a:has-text("Next"), button:has-text("Next"), '
            '.pagination-next, [aria-label="Next"], .next-page'
        )

        if next_btn:
            is_disabled = await next_btn.get_attribute('disabled')
            has_disabled_class = await next_btn.evaluate('el => el.classList.contains("disabled")')

            if is_disabled or has_disabled_class:
                return False

            await next_btn.click()
            await asyncio.sleep(1)
            await page.wait_for_load_state('networkidle', timeout=10000)
            return True

        return False

    except Exception as e:
        logger.warning(f"Pagination error: {e}")
        return False
```

**Step 2: Update scrape_permits with pagination loop**

```python
async def scrape_permits(page, target_count: int) -> list:
    """Scrape permits from SmartGov search interface."""
    all_permits = []

    # Navigate to search
    if not await navigate_to_search(page):
        logger.error("Failed to navigate to search page")
        return all_permits

    # Execute search
    result_count = await execute_search(page, "*")

    # Pagination loop
    page_num = 1
    while len(all_permits) < target_count:
        logger.info(f"[Page {page_num}] Extracting...")

        permits = await extract_permits_from_page(page)
        if not permits:
            logger.info("    No permits found on page")
            break

        all_permits.extend(permits)
        logger.info(f"    Total so far: {len(all_permits)}")

        if len(all_permits) >= target_count:
            break

        # Try next page
        if not await get_next_page(page):
            logger.info("    No more pages")
            break

        page_num += 1

    return all_permits[:target_count]
```

**Step 3: Test pagination**

Run: `python3 scrapers/smartgov_sachse.py 50`

Expected: Multiple pages scraped if results exceed one page.

**Step 4: Commit**

```bash
git add scrapers/smartgov_sachse.py
git commit -m "feat: add SmartGov pagination support"
```

---

## Task 7: Add Retry Logic and Error Handling

**Files:**
- Modify: `scrapers/smartgov_sachse.py`

**Step 1: Add retry decorator to navigation**

Update `navigate_to_search`:

```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=2, max=8),
    retry=retry_if_exception_type((PlaywrightTimeout, Exception)),
    reraise=True
)
async def navigate_to_search(page) -> bool:
    # ... existing code ...
```

**Step 2: Add retry to search execution**

Update `execute_search`:

```python
@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=1, min=1, max=4),
    retry=retry_if_exception_type((PlaywrightTimeout,)),
    reraise=True
)
async def execute_search(page, query: str = "*") -> int:
    # ... existing code ...
```

**Step 3: Test error recovery**

Run with short timeout to trigger retries, then normal run.

**Step 4: Commit**

```bash
git add scrapers/smartgov_sachse.py
git commit -m "feat: add retry logic to SmartGov scraper"
```

---

## Task 8: Update CLAUDE.md and Documentation

**Files:**
- Modify: `/home/reid/testhome/permit-scraper/CLAUDE.md`

**Step 1: Add Sachse to working portals list**

In the "Working Portals" section, add:

```markdown
- Sachse (SmartGov) - `smartgov_sachse.py`
```

**Step 2: Add common command**

In the "Common Commands" section under "Other platforms", add:

```bash
python3 scrapers/smartgov_sachse.py 500             # Sachse (SmartGov)
```

**Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: add Sachse SmartGov scraper to documentation"
```

---

## Task 9: Integration Test

**Step 1: Run full scrape**

Run: `cd /home/reid/testhome/permit-scraper && python3 scrapers/smartgov_sachse.py 100`

**Step 2: Verify output**

Check `data/raw/sachse_raw.json`:
- Contains permit IDs
- Contains addresses
- Data is properly formatted

**Step 3: Load to database (if applicable)**

Run: `python3 scripts/load_permits.py`

Verify permits appear in `leads_permit` table.

---

## Risk Register

| Risk | Mitigation |
|------|------------|
| Angular SPA may require additional waits | Use `wait_for_load_state('networkidle')` and explicit sleeps |
| Search requires minimum 2 characters | Use wildcard search "*" or common prefixes |
| DOM structure may differ from expected | Take debug screenshots, iterate on selectors |
| No CAD enrichment for Sachse | Sachse is in Dallas/Collin county - existing CAD should work |
| Rate limiting or bot detection | Add delays between requests, use realistic user agent |

---

## Summary of Changes

| File | Change Type |
|------|-------------|
| `scrapers/smartgov_sachse.py` | New file |
| `CLAUDE.md` | Add Sachse to docs |
| `data/raw/sachse_raw.json` | Output (not committed) |

---

## Notes

- Sachse is in Dallas/Collin county overlap - existing CAD enrichment should work
- SmartGov platform version 2025.20 (as of research date)
- Public access confirmed - no login required
- Contact: devservices@cityofsachse.com if issues arise
