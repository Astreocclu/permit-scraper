# Scraper Hardening Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix MGO Connect anti-bot blocking, repair EnerGov McKinney/Allen scrapers, and expand Westlake address automation.

**Architecture:** Phased fallback approach for MGO (headless→headed→fail gracefully), diagnosis-first approach for EnerGov, and recursive A-Z prefix search for Westlake address discovery.

**Tech Stack:** Python 3, Playwright, playwright-stealth, requests, urllib3 Retry

---

## Pre-Implementation Setup

### Task 0: Create Feature Branch

**Files:**
- None (git operation)

**Step 1: Create and checkout branch**

```bash
cd /home/reid/testhome/permit-scraper
git checkout -b fix/scraper-hardening
```

Expected: `Switched to a new branch 'fix/scraper-hardening'`

**Step 2: Verify branch**

```bash
git branch --show-current
```

Expected: `fix/scraper-hardening`

---

## Task 1: MGO Connect Anti-Bot Fix

**Confidence: 85%**

### Task 1.1: Write Failing Test for Phased Fallback

**Files:**
- Create: `tests/test_mgo_connect.py`

**Step 1: Write the failing test**

```python
"""Tests for MGO Connect scraper phased fallback."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


class TestMGOPhasedFallback:
    """Test the phased fallback strategy."""

    @pytest.mark.asyncio
    async def test_scrape_orchestrator_tries_headless_first(self):
        """Orchestrator should try headless mode before headed."""
        from scrapers.mgo_connect import scrape_orchestrator

        with patch('scrapers.mgo_connect.run_scraper_session') as mock_session:
            mock_session.return_value = [{'permit_id': '123'}]

            # Should call with headless=True first
            await scrape_orchestrator('Irving', 5)

            first_call = mock_session.call_args_list[0]
            assert first_call[1].get('headless', first_call[0][2] if len(first_call[0]) > 2 else True) == True

    @pytest.mark.asyncio
    async def test_scrape_orchestrator_falls_back_to_headed(self):
        """If headless fails, should try headed mode."""
        from scrapers.mgo_connect import scrape_orchestrator

        with patch('scrapers.mgo_connect.run_scraper_session') as mock_session:
            # First call (headless) returns None (failure), second returns data
            mock_session.side_effect = [None, [{'permit_id': '123'}]]

            await scrape_orchestrator('Irving', 5)

            assert mock_session.call_count == 2
            # Second call should be headed (headless=False)
            second_call = mock_session.call_args_list[1]
            assert second_call[0][2] == False  # headless parameter


class TestStealthImport:
    """Test that stealth is properly imported and used."""

    def test_stealth_import_graceful_fallback(self):
        """Should not crash if playwright-stealth not installed."""
        # This tests the try/except import pattern
        import scrapers.mgo_connect as mgo
        # Should have stealth_async attribute (either function or None)
        assert hasattr(mgo, 'stealth_async') or 'stealth_async' in dir(mgo)
```

**Step 2: Run test to verify it fails**

```bash
cd /home/reid/testhome/permit-scraper
python3 -m pytest tests/test_mgo_connect.py -v
```

Expected: FAIL - either import error or missing functions

### Task 1.2: Implement Phased Fallback in MGO Connect

**Files:**
- Modify: `scrapers/mgo_connect.py`

**Step 1: Read current file to understand structure**

```bash
head -100 /home/reid/testhome/permit-scraper/scrapers/mgo_connect.py
```

**Step 2: Add stealth import at top of file (after existing imports)**

Find the imports section and add:

```python
# Try to import stealth, fail gracefully if not installed
try:
    from playwright_stealth import stealth_async
except ImportError:
    stealth_async = None
    print("WARN: playwright-stealth not found. Install: pip install playwright-stealth")
```

**Step 3: Add the `run_scraper_session` function**

Add this new function (find appropriate location, likely after `login` function):

```python
async def run_scraper_session(city_name: str, target_count: int, headless: bool):
    """Single scraper attempt with specific browser config.

    Returns:
        List of permits if successful, None if login/detection failed.
    """
    print(f"\n--- Starting Session (Headless: {headless}) ---")
    permits = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=headless,
            slow_mo=50 if not headless else 0
        )
        context = await browser.new_context(
            viewport={'width': 1400, 'height': 900},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
        )
        page = await context.new_page()

        # Apply stealth if available
        if stealth_async:
            print("[INIT] Applying Playwright Stealth...")
            await stealth_async(page)

        try:
            # Login
            if not await login(page):
                print("[SESSION] Login failed - returning None for retry")
                await browser.close()
                return None

            # Setup jurisdiction
            if not await select_jurisdiction_from_home(page, city_name):
                await browser.close()
                raise Exception("Jurisdiction selection failed")

            # Search and extract (reuse existing logic)
            # Navigate to search
            print('[SEARCH] Navigating to search...')
            await page.goto('https://mgoconnect.org/cp/search', wait_until='networkidle', timeout=60000)

            # Set date filter (last 30 days)
            from datetime import datetime, timedelta
            created_after = (datetime.now() - timedelta(days=30)).strftime('%m/%d/%Y')

            date_input = page.locator('input[placeholder*="Created"]').first
            if await date_input.count() > 0:
                await date_input.fill(created_after)

            search_btn = page.locator('button:has-text("Search")').first
            if await search_btn.count() > 0:
                await search_btn.click()
                await asyncio.sleep(5)

            # Extract table data
            print('[EXTRACT] Reading table data...')
            while len(permits) < target_count:
                rows = await page.evaluate('''() => {
                    const results = [];
                    document.querySelectorAll('tbody tr').forEach(row => {
                        const cells = Array.from(row.querySelectorAll('td')).map(td => td.innerText.trim());
                        if(cells.length > 4) results.push(cells);
                    });
                    return results;
                }''')

                for row in rows:
                    if len(row) >= 5:
                        permits.append({
                            'permit_id': row[0],
                            'address': row[1],
                            'type': row[2],
                            'status': row[3],
                            'date': row[4]
                        })

                print(f"   Collected {len(permits)} permits...")

                # Try next page
                next_btn = page.locator('.p-paginator-next:not(.p-disabled)')
                if await next_btn.count() > 0:
                    await next_btn.click()
                    await asyncio.sleep(2)
                else:
                    break

            await browser.close()
            return permits

        except Exception as e:
            print(f"[SESSION] Error: {e}")
            await page.screenshot(path=f'debug_html/mgo_{city_name.lower()}_error.png')
            await browser.close()
            raise
```

**Step 4: Add the orchestrator function**

```python
async def scrape_orchestrator(city_name: str, target_count: int = 1000):
    """Orchestrates the phased fallback strategy.

    Phase 1: Headless + stealth (fast, low resources)
    Phase 2: Headed mode (bypasses simple fingerprinting)
    Phase 3: Fail gracefully with diagnostics
    """
    from pathlib import Path

    # PHASE 1: HEADLESS
    try:
        print("PHASE 1: Attempting Headless extraction...")
        results = await run_scraper_session(city_name, target_count, headless=True)
        if results is not None:
            return save_results(city_name, results)
    except Exception as e:
        print(f"Phase 1 failed: {e}")

    # PHASE 2: HEADED (fallback)
    try:
        print("\nPHASE 2: Attempting Headed extraction...")
        results = await run_scraper_session(city_name, target_count, headless=False)
        if results is not None:
            return save_results(city_name, results)
    except Exception as e:
        print(f"Phase 2 failed: {e}")

    # PHASE 3: FAIL GRACEFULLY
    print("\nCRITICAL: All automated phases failed.")
    print("Next steps: Try residential proxy or manual intervention")
    import sys
    sys.exit(1)


def save_results(city_name: str, permits: list):
    """Save scraped permits to JSON."""
    from pathlib import Path
    from datetime import datetime
    import json

    output_dir = Path(__file__).parent.parent / 'data' / 'exports'
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f'{city_name.lower()}_mgo_raw.json'

    output = {
        'source': city_name,
        'scraped_at': datetime.now().isoformat(),
        'count': len(permits),
        'permits': permits
    }

    output_file.write_text(json.dumps(output, indent=2))
    print(f"\nSUCCESS: Saved {len(permits)} permits to {output_file}")
    return permits
```

**Step 5: Update the `if __name__ == '__main__'` block**

Replace the existing main block to use orchestrator:

```python
if __name__ == '__main__':
    import sys
    city = sys.argv[1] if len(sys.argv) > 1 else 'Irving'
    count = int(sys.argv[2]) if len(sys.argv) > 2 else 1000

    if not MGO_EMAIL or not MGO_PASSWORD:
        print("Error: MGO_EMAIL and MGO_PASSWORD required in .env")
        sys.exit(1)

    asyncio.run(scrape_orchestrator(city, count))
```

**Step 6: Run tests**

```bash
python3 -m pytest tests/test_mgo_connect.py -v
```

Expected: PASS

**Step 7: Commit**

```bash
git add scrapers/mgo_connect.py tests/test_mgo_connect.py
git commit -m "feat(mgo): add phased fallback (headless→headed) with stealth support"
```

---

## Task 2: EnerGov Diagnosis Script

**Confidence: 30% (diagnosis phase - unknowns remain)**

### Task 2.1: Create Diagnosis Script

**Files:**
- Create: `scripts/diagnose_energov.py`

**Step 1: Write the diagnosis script**

```python
#!/usr/bin/env python3
"""
EnerGov Portal Diagnosis Tool

Captures HTML snapshots and screenshots from McKinney and Allen
to diagnose why scrapers are failing.

Run: python scripts/diagnose_energov.py
Output: debug_html/energov_{city}_diag.{png,html}
"""
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

# Target URLs for diagnosis
ENERGOV_URLS = {
    'mckinney': 'https://egov.mckinneytexas.org/EnerGov_Prod/SelfService#/search',
    'allen': 'https://energovweb.cityofallen.org/EnerGov/SelfService#/search',
    # Working cities for comparison
    'southlake': 'https://southlake-egov.tylerhost.net/EnerGov/SelfService#/search',
    'colleyville': 'https://www.colleyville.com/EnerGov/SelfService#/search',
}

OUTPUT_DIR = Path(__file__).parent.parent / 'debug_html'


async def diagnose_portal(page, city: str, url: str):
    """Capture diagnostic data from a single portal."""
    print(f"\n{'='*50}")
    print(f"Diagnosing: {city.upper()}")
    print(f"URL: {url}")
    print('='*50)

    try:
        # Navigate with extended timeout
        print(f"  [1/5] Navigating...")
        response = await page.goto(url, wait_until='networkidle', timeout=60000)
        print(f"  Status: {response.status if response else 'No response'}")

        # Wait for Angular to settle
        print(f"  [2/5] Waiting for Angular...")
        await asyncio.sleep(5)

        # Check for Cloudflare/challenge pages
        content = await page.content()
        if 'challenge' in content.lower() or 'cloudflare' in content.lower():
            print(f"  WARNING: Possible Cloudflare challenge detected!")

        # Capture screenshot
        print(f"  [3/5] Capturing screenshot...")
        screenshot_path = OUTPUT_DIR / f'energov_{city}_diag.png'
        await page.screenshot(path=str(screenshot_path), full_page=True)
        print(f"  Saved: {screenshot_path}")

        # Capture HTML
        print(f"  [4/5] Capturing HTML...")
        html_path = OUTPUT_DIR / f'energov_{city}_diag.html'
        html_path.write_text(content)
        print(f"  Saved: {html_path}")

        # Extract key selectors
        print(f"  [5/5] Analyzing selectors...")
        selectors = await page.evaluate('''() => {
            const info = {
                searchModule: document.querySelector('#SearchModule')?.outerHTML?.slice(0,200),
                contentPlaceholder: document.querySelector('[id*="ContentPlaceHolder"]')?.id,
                dateInputs: Array.from(document.querySelectorAll('input[type="date"], input[id*="Date"]')).map(e => e.id),
                dropdowns: Array.from(document.querySelectorAll('select, .dropdown, [role="listbox"]')).map(e => e.id || e.className).slice(0,5),
                angularApp: !!document.querySelector('[ng-app], [data-ng-app], .ng-scope'),
                forms: Array.from(document.querySelectorAll('form')).map(f => f.id || f.action).slice(0,3),
            };
            return info;
        }''')

        print(f"\n  Selector Analysis:")
        for key, value in selectors.items():
            print(f"    {key}: {value}")

        return {'status': 'success', 'selectors': selectors}

    except Exception as e:
        print(f"  ERROR: {e}")
        # Try to capture error state
        try:
            await page.screenshot(path=str(OUTPUT_DIR / f'energov_{city}_error.png'))
        except:
            pass
        return {'status': 'error', 'error': str(e)}


async def main():
    """Run diagnosis on all EnerGov portals."""
    print("EnerGov Portal Diagnosis Tool")
    print("="*50)

    # Ensure output directory exists
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    results = {}

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1400, 'height': 900},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        page = await context.new_page()

        for city, url in ENERGOV_URLS.items():
            results[city] = await diagnose_portal(page, city, url)

        await browser.close()

    # Summary
    print("\n" + "="*50)
    print("DIAGNOSIS SUMMARY")
    print("="*50)
    for city, result in results.items():
        status = result.get('status', 'unknown')
        print(f"  {city}: {status}")
        if status == 'error':
            print(f"    Error: {result.get('error', 'Unknown')}")

    print(f"\nDiagnostic files saved to: {OUTPUT_DIR}")
    print("\nNext steps:")
    print("  1. Compare McKinney/Allen HTML to Southlake/Colleyville")
    print("  2. Look for selector differences")
    print("  3. Check for anti-bot mechanisms")


if __name__ == '__main__':
    asyncio.run(main())
```

**Step 2: Run the diagnosis**

```bash
cd /home/reid/testhome/permit-scraper
python3 scripts/diagnose_energov.py
```

Expected: Screenshots and HTML files in `debug_html/`

**Step 3: Commit**

```bash
git add scripts/diagnose_energov.py
git commit -m "feat(energov): add diagnosis script for McKinney/Allen debugging"
```

**Step 4: Review diagnosis output**

```bash
ls -la debug_html/energov_*.png debug_html/energov_*.html
```

Expected: 8 files (4 cities x 2 file types)

**Note:** After running diagnosis, a follow-up task will be needed to implement the actual fix based on findings. This is acknowledged as 30% confidence until diagnosis completes.

---

## Task 3: Westlake Recursive Address Harvester

**Confidence: 80%**

### Task 3.1: Write Failing Test for Recursive Search

**Files:**
- Create: `tests/test_westlake_harvester.py`

**Step 1: Write the failing test**

```python
"""Tests for Westlake Address Harvester."""
import pytest
from unittest.mock import patch, MagicMock
import json


class TestRecursiveSearch:
    """Test the recursive A-Z search algorithm."""

    def test_recursive_search_single_letter(self):
        """Single letter search should query API."""
        from scrapers.westlake_harvester import recursive_search

        all_addresses = {}

        with patch('scrapers.westlake_harvester.search_addresses') as mock_search:
            mock_search.return_value = [
                {'address': '100 Apple St', 'location_id': '1'},
                {'address': '200 Acorn Ln', 'location_id': '2'},
            ]

            recursive_search('A', all_addresses, depth=0)

            mock_search.assert_called_once_with('A')
            assert len(all_addresses) == 2
            assert '100 Apple St' in all_addresses

    def test_recursive_search_drills_down_on_limit(self):
        """When results hit limit (50+), should recurse with next character."""
        from scrapers.westlake_harvester import recursive_search

        all_addresses = {}

        with patch('scrapers.westlake_harvester.search_addresses') as mock_search:
            # First call returns 50 results (hit limit)
            first_results = [{'address': f'{i} A St', 'location_id': str(i)} for i in range(50)]
            # Subsequent calls return fewer
            subsequent = [{'address': '1 AA St', 'location_id': '100'}]

            mock_search.side_effect = [first_results] + [subsequent] * 36  # A-Z + 0-9

            recursive_search('A', all_addresses, depth=0)

            # Should have drilled down
            assert mock_search.call_count > 1

    def test_recursive_search_respects_max_depth(self):
        """Should not recurse beyond max depth."""
        from scrapers.westlake_harvester import recursive_search

        all_addresses = {}

        with patch('scrapers.westlake_harvester.search_addresses') as mock_search:
            mock_search.return_value = []

            recursive_search('AAAA', all_addresses, depth=4)

            # Should not call API at depth > 3
            mock_search.assert_not_called()


class TestRetryLogic:
    """Test urllib3 retry/backoff integration."""

    def test_session_has_retry_adapter(self):
        """Session should have retry adapter configured."""
        from scrapers.westlake_harvester import get_session

        session = get_session()

        # Check HTTPS adapter exists
        adapter = session.get_adapter('https://')
        assert adapter is not None
        # Should have retry config
        assert adapter.max_retries.total >= 3


class TestCheckpointing:
    """Test progress saving for resumability."""

    def test_save_addresses_creates_file(self, tmp_path):
        """Should save addresses to JSON file."""
        from scrapers.westlake_harvester import save_addresses

        addresses = {
            '100 Test St': {'address': '100 Test St', 'location_id': '1'}
        }

        with patch('scrapers.westlake_harvester.OUTPUT_FILE', tmp_path / 'addresses.json'):
            save_addresses(addresses)

            saved = json.loads((tmp_path / 'addresses.json').read_text())
            assert len(saved) == 1
            assert saved[0]['address'] == '100 Test St'
```

**Step 2: Run test to verify it fails**

```bash
python3 -m pytest tests/test_westlake_harvester.py -v
```

Expected: FAIL - import errors or missing functions

### Task 3.2: Implement Recursive Harvester

**Files:**
- Modify: `scrapers/westlake_harvester.py`

**Step 1: Rewrite the harvester with recursive search**

Replace the entire file content with:

```python
#!/usr/bin/env python3
"""
Westlake Address Harvester (Recursive A-Z Search)

Discovers ALL addresses in Westlake via recursive prefix search.
Uses MyGov API endpoint with exponential backoff for rate limiting.

Algorithm:
1. Search A, B, C... Z, 0-9
2. If any search hits result limit (50), drill down (AA, AB, AC...)
3. Recurse up to depth 3 to handle dense prefixes
4. Checkpoint progress for resumability

Run: python scrapers/westlake_harvester.py
Output: data/westlake_addresses.json
"""
import json
import time
import string
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Configuration
API_URL = "https://public.mygov.us/westlake_tx/getLookupResults"
OUTPUT_FILE = Path(__file__).parent.parent / "data" / "westlake_addresses.json"
STATE_FILE = Path(__file__).parent.parent / "data" / "westlake_harvest_state.json"

# Search parameters
RESULT_LIMIT = 50  # If we get this many, we need to drill down
MAX_DEPTH = 3  # Don't recurse deeper than this
BASE_SLEEP = 1.0  # Seconds between requests


def get_session():
    """Create requests session with retry/backoff for rate limiting."""
    session = requests.Session()

    retries = Retry(
        total=5,
        backoff_factor=1,  # Wait 1s, 2s, 4s, 8s, 16s on retry
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["POST"]
    )

    adapter = HTTPAdapter(max_retries=retries)
    session.mount('https://', adapter)
    session.mount('http://', adapter)

    return session


# Global session for reuse
_session = None


def get_global_session():
    """Get or create global session."""
    global _session
    if _session is None:
        _session = get_session()
    return _session


def search_addresses(search_term: str) -> list:
    """Search MyGov API for addresses matching term.

    Args:
        search_term: Prefix to search (e.g., "A", "AB", "100")

    Returns:
        List of address dicts with 'address' and 'location_id' keys
    """
    session = get_global_session()

    try:
        response = session.post(
            API_URL,
            data={'address_search': search_term},
            headers={
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'Accept': 'application/json, text/javascript, */*; q=0.01',
                'X-Requested-With': 'XMLHttpRequest',
                'Referer': 'https://public.mygov.us/westlake_tx/lookup',
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
            },
            timeout=30
        )

        response.raise_for_status()
        data = response.json()

        # Parse response - extract address items
        results = []
        for item in data if isinstance(data, list) else []:
            if isinstance(item, dict) and item.get('address'):
                results.append({
                    'address': item.get('address'),
                    'location_id': item.get('location_id')
                })

        return results

    except requests.exceptions.RequestException as e:
        print(f"  ERROR searching '{search_term}': {e}")
        return []
    except json.JSONDecodeError as e:
        print(f"  ERROR parsing response for '{search_term}': {e}")
        return []


def recursive_search(prefix: str, all_addresses: dict, depth: int = 0):
    """Recursively search addresses by prefix.

    Args:
        prefix: Current search prefix (e.g., "A", "AB")
        all_addresses: Dict to accumulate results (address -> item dict)
        depth: Current recursion depth
    """
    # Safety: Don't recurse too deep
    if depth > MAX_DEPTH:
        return

    print(f"{'  ' * depth}Scanning: {prefix}* ...")
    results = search_addresses(prefix)

    # Add new addresses
    new_count = 0
    for item in results:
        addr = item.get('address')
        if addr and addr not in all_addresses:
            all_addresses[addr] = item
            new_count += 1

    print(f"{'  ' * depth}  Found {len(results)} results ({new_count} new)")

    # If we hit the limit, need to drill down
    if len(results) >= RESULT_LIMIT:
        print(f"{'  ' * depth}  HIT LIMIT - drilling down...")
        chars = string.ascii_uppercase + string.digits
        for char in chars:
            recursive_search(prefix + char, all_addresses, depth + 1)
            time.sleep(BASE_SLEEP * 0.5)  # Shorter sleep for drill-down

    # Checkpoint after significant progress
    if new_count > 0 and depth == 0:
        save_addresses(all_addresses)


def save_addresses(addresses: dict):
    """Save addresses to JSON file.

    Args:
        addresses: Dict mapping address string to full item dict
    """
    # Convert dict to list for JSON
    data = list(addresses.values())

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_FILE, 'w') as f:
        json.dump(data, f, indent=2)

    print(f"  Checkpointed {len(data)} addresses to {OUTPUT_FILE}")


def load_existing_addresses() -> dict:
    """Load previously harvested addresses for resumption."""
    if not OUTPUT_FILE.exists():
        return {}

    try:
        data = json.loads(OUTPUT_FILE.read_text())
        return {item['address']: item for item in data if item.get('address')}
    except Exception as e:
        print(f"Could not load existing addresses: {e}")
        return {}


def main():
    """Run the recursive address harvest."""
    print("Westlake Recursive Address Harvester")
    print("=" * 50)

    # Load any existing addresses
    all_addresses = load_existing_addresses()
    print(f"Loaded {len(all_addresses)} existing addresses")

    # Search A-Z, 0-9
    start_chars = string.ascii_uppercase + string.digits

    print(f"\nStarting recursive search for {len(start_chars)} prefixes...")

    for char in start_chars:
        recursive_search(char, all_addresses, depth=0)
        time.sleep(BASE_SLEEP)

    # Final save
    save_addresses(all_addresses)

    print("\n" + "=" * 50)
    print(f"COMPLETE: Harvested {len(all_addresses)} unique addresses")
    print(f"Output: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
```

**Step 3: Run tests**

```bash
python3 -m pytest tests/test_westlake_harvester.py -v
```

Expected: PASS

**Step 4: Test manual run (quick sanity check)**

```bash
# Just test first 2 letters to verify it works
cd /home/reid/testhome/permit-scraper
timeout 30 python3 -c "
from scrapers.westlake_harvester import search_addresses, get_session
results = search_addresses('A')
print(f'Found {len(results)} addresses starting with A')
if results:
    print(f'Sample: {results[0]}')
"
```

Expected: Output showing some addresses found

**Step 5: Commit**

```bash
git add scrapers/westlake_harvester.py tests/test_westlake_harvester.py
git commit -m "feat(westlake): implement recursive A-Z search with retry/backoff"
```

---

## Task 4: Final Verification & Documentation

### Task 4.1: Run All Tests

**Step 1: Run full test suite**

```bash
cd /home/reid/testhome/permit-scraper
python3 -m pytest tests/ -v
```

Expected: All tests PASS

**Step 2: Update SCRAPER_STATUS.md**

Add a note about the changes:

```markdown
## Recent Changes (2025-12-12)

### MGO Connect
- Added phased fallback: headless → headed → fail gracefully
- Integrated playwright-stealth for anti-bot evasion
- Status: Ready for testing

### EnerGov (McKinney/Allen)
- Created diagnosis script: `scripts/diagnose_energov.py`
- Status: Diagnosis pending - run script and analyze output

### Westlake
- Replaced hardcoded street list with recursive A-Z search
- Added urllib3 retry/backoff for rate limiting
- Status: Ready for full harvest
```

**Step 3: Commit documentation**

```bash
git add SCRAPER_STATUS.md
git commit -m "docs: update status with scraper hardening changes"
```

---

## Summary

| Task | Files Modified | Confidence | Status |
|------|---------------|------------|--------|
| MGO Connect | `scrapers/mgo_connect.py`, `tests/test_mgo_connect.py` | 85% | Ready |
| EnerGov Diagnosis | `scripts/diagnose_energov.py` | 30% | Diagnosis needed |
| Westlake Harvest | `scrapers/westlake_harvester.py`, `tests/test_westlake_harvester.py` | 80% | Ready |

**Next Steps After Implementation:**
1. Run `python3 scripts/diagnose_energov.py` and analyze output
2. Test MGO against Irving: `python3 scrapers/mgo_connect.py Irving 10`
3. Run full Westlake harvest: `python3 scrapers/westlake_harvester.py`
4. Based on EnerGov diagnosis, create follow-up plan for McKinney/Allen fix
