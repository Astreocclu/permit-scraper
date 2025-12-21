# Scraper Expansion Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add Lewisville permit scraper (Tyler eSuite), fix Irving MGO Connect, and test Richardson with proxy.

**Architecture:** Three independent scrapers using existing patterns: (1) New Tyler eSuite scraper following citizen_self_service.py patterns, (2) Fix MGO Connect orchestrator routing for Irving, (3) Add proxy support for Richardson.

**Tech Stack:** Python 3.11+, Playwright, pandas, httpx, openpyxl

---

## Task 1: Explore Lewisville Tyler eSuite Portal Structure

**Files:**
- Create: `scripts/explore_lewisville.py`

**Step 1: Write exploration script**

Create a Playwright script to explore the Tyler eSuite portal and identify the DOM structure, search forms, and export options.

```python
#!/usr/bin/env python3
"""
Explore Lewisville Tyler eSuite permit portal structure.
Output: debug_html/lewisville_exploration.json
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path

from playwright.async_api import async_playwright

OUTPUT_DIR = Path('debug_html')
OUTPUT_DIR.mkdir(exist_ok=True)

async def explore():
    """Explore the Tyler eSuite portal structure."""
    print('=' * 60)
    print('LEWISVILLE TYLER eSUITE EXPLORATION')
    print('=' * 60)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 900},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        page = await context.new_page()

        results = {
            'timestamp': datetime.now().isoformat(),
            'url': 'https://etools.cityoflewisville.com/esuite.permits/',
            'pages_explored': [],
            'forms': [],
            'api_endpoints': [],
        }

        # Capture API calls
        api_calls = []
        def log_request(request):
            if '/api/' in request.url or '.json' in request.url:
                api_calls.append({
                    'url': request.url,
                    'method': request.method
                })
        page.on('request', log_request)

        try:
            # Step 1: Load main portal
            print('\n[1] Loading portal...')
            await page.goto('https://etools.cityoflewisville.com/esuite.permits/',
                          wait_until='networkidle', timeout=60000)
            await asyncio.sleep(3)

            await page.screenshot(path='debug_html/lewisville_home.png', full_page=True)
            print(f'    URL: {page.url}')

            # Step 2: Analyze page structure
            print('\n[2] Analyzing page structure...')
            structure = await page.evaluate('''() => {
                return {
                    title: document.title,
                    forms: Array.from(document.forms).map(f => ({
                        id: f.id,
                        action: f.action,
                        method: f.method,
                        inputs: Array.from(f.querySelectorAll('input, select')).map(i => ({
                            type: i.type || i.tagName.toLowerCase(),
                            name: i.name,
                            id: i.id,
                            placeholder: i.placeholder
                        }))
                    })),
                    links: Array.from(document.querySelectorAll('a')).map(a => ({
                        text: a.textContent.trim().slice(0, 50),
                        href: a.href
                    })).filter(l => l.text && l.href && !l.href.startsWith('javascript')),
                    buttons: Array.from(document.querySelectorAll('button')).map(b => ({
                        text: b.textContent.trim().slice(0, 50),
                        type: b.type,
                        id: b.id
                    })),
                    tables: document.querySelectorAll('table').length,
                    iframes: Array.from(document.querySelectorAll('iframe')).map(i => i.src)
                };
            }''')

            results['pages_explored'].append({
                'url': page.url,
                'structure': structure
            })
            print(f'    Forms: {len(structure["forms"])}')
            print(f'    Links: {len(structure["links"])}')
            print(f'    Buttons: {len(structure["buttons"])}')

            # Step 3: Look for permit search links
            print('\n[3] Looking for permit search...')
            search_links = [l for l in structure['links']
                          if any(kw in l['text'].lower() for kw in ['search', 'permit', 'lookup', 'find'])]
            print(f'    Found {len(search_links)} potential search links:')
            for link in search_links[:5]:
                print(f'      - {link["text"]}: {link["href"][:60]}')

            # Step 4: Try to navigate to permit search
            if search_links:
                print('\n[4] Navigating to first search link...')
                await page.click(f'text={search_links[0]["text"]}')
                await asyncio.sleep(3)
                await page.screenshot(path='debug_html/lewisville_search.png', full_page=True)

                search_structure = await page.evaluate('''() => {
                    return {
                        url: window.location.href,
                        forms: Array.from(document.forms).map(f => ({
                            id: f.id,
                            inputs: Array.from(f.querySelectorAll('input, select')).map(i => ({
                                type: i.type || i.tagName.toLowerCase(),
                                name: i.name,
                                id: i.id,
                                placeholder: i.placeholder
                            }))
                        })),
                        searchInputs: Array.from(document.querySelectorAll('input[type="text"], input[type="search"]'))
                            .map(i => ({name: i.name, id: i.id, placeholder: i.placeholder}))
                    };
                }''')
                results['pages_explored'].append(search_structure)
                print(f'    Search page URL: {search_structure["url"]}')
                print(f'    Search inputs: {len(search_structure["searchInputs"])}')

            results['api_endpoints'] = api_calls
            print(f'\n[5] API endpoints captured: {len(api_calls)}')
            for call in api_calls[:10]:
                print(f'    {call["method"]} {call["url"][:80]}')

        except Exception as e:
            print(f'\nERROR: {e}')
            results['error'] = str(e)

        finally:
            await browser.close()

        # Save results
        output_file = OUTPUT_DIR / 'lewisville_exploration.json'
        output_file.write_text(json.dumps(results, indent=2))
        print(f'\nSaved exploration to: {output_file}')

        return results

if __name__ == '__main__':
    asyncio.run(explore())
```

**Step 2: Run exploration script**

Run: `cd /home/reid/command-center/testhome/permit-scraper && python3 scripts/explore_lewisville.py`
Expected: Screenshots in debug_html/, JSON with portal structure

**Step 3: Commit exploration script**

```bash
git add scripts/explore_lewisville.py
git commit -m "feat: add Lewisville Tyler eSuite exploration script"
```

---

## Task 2: Create Tyler eSuite Scraper Core

**Files:**
- Create: `scrapers/tyler_esuite.py`

**Step 1: Create scraper skeleton**

Based on exploration results, create the scraper following citizen_self_service.py patterns.

```python
#!/usr/bin/env python3
"""
TYLER eSUITE PERMIT SCRAPER (Playwright Python)
Portal: Tyler Technologies eSuite (NewWorld)
Covers: Lewisville TX

Usage:
  python scrapers/tyler_esuite.py lewisville 500
"""

import asyncio
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

# Try to import stealth
try:
    from playwright_stealth import Stealth
    STEALTH = Stealth()
except ImportError:
    STEALTH = None
    print("WARN: playwright-stealth not found. Install: pip install playwright-stealth")

# Output directory for raw JSON
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "raw"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# City configurations for Tyler eSuite portals
ESUITE_CITIES = {
    'lewisville': {
        'name': 'Lewisville',
        'base_url': 'https://etools.cityoflewisville.com/esuite.permits',
        'cad_county': 'Denton',
    },
}


async def scrape(city_key: str, target_count: int = 500):
    """Scrape permits from Tyler eSuite portal.

    Args:
        city_key: City identifier (e.g., 'lewisville')
        target_count: Target number of permits to scrape
    """
    city_key = city_key.lower().replace(' ', '_')

    if city_key not in ESUITE_CITIES:
        print(f'ERROR: Unknown city "{city_key}". Available: {", ".join(ESUITE_CITIES.keys())}')
        sys.exit(1)

    config = ESUITE_CITIES[city_key]
    city_name = config['name']
    base_url = config['base_url']

    print('=' * 60)
    print(f'{city_name.upper()} PERMIT SCRAPER (Tyler eSuite)')
    print('=' * 60)
    print(f'Target: {target_count} permits')
    print(f'Time: {datetime.now().isoformat()}\n')

    permits = []
    errors = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--disable-blink-features=AutomationControlled']
        )
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 900},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        page = await context.new_page()

        if STEALTH:
            await STEALTH.apply_stealth_async(page)

        try:
            # Step 1: Navigate to portal
            print('[1] Navigating to portal...')
            await page.goto(base_url, wait_until='networkidle', timeout=60000)
            await asyncio.sleep(3)
            await page.screenshot(path=f'debug_html/{city_key}_esuite_home.png')
            print(f'    URL: {page.url}')

            # Step 2: Find and click permit search
            print('\n[2] Looking for permit search...')
            # TODO: Implement based on exploration results
            # This will be filled in after running Task 1

            # Step 3: Execute search with date filter
            print('\n[3] Executing search...')
            # TODO: Implement search with date filter

            # Step 4: Extract permits from results
            print('\n[4] Extracting permits...')
            # TODO: Implement DOM extraction or Excel export

        except Exception as e:
            print(f'\nFATAL ERROR: {e}')
            errors.append({'step': 'main', 'error': str(e)})
            await page.screenshot(path=f'debug_html/{city_key}_esuite_error.png')

        finally:
            await browser.close()

    # Save results
    output = {
        'source': city_key,
        'portal_type': 'Tyler_eSuite',
        'scraped_at': datetime.now().isoformat(),
        'target_count': target_count,
        'actual_count': len(permits),
        'errors': errors,
        'permits': permits[:target_count]
    }

    output_file = OUTPUT_DIR / f'{city_key}_raw.json'
    output_file.write_text(json.dumps(output, indent=2))

    print('\n' + '=' * 60)
    print('SUMMARY')
    print('=' * 60)
    print(f'City: {city_name}')
    print(f'Permits scraped: {output["actual_count"]}')
    print(f'Output: {output_file}')

    return output


if __name__ == '__main__':
    city = sys.argv[1] if len(sys.argv) > 1 else 'lewisville'
    count = int(sys.argv[2]) if len(sys.argv) > 2 else 500
    asyncio.run(scrape(city, count))
```

**Step 2: Commit scraper skeleton**

```bash
git add scrapers/tyler_esuite.py
git commit -m "feat: add Tyler eSuite scraper skeleton for Lewisville"
```

---

## Task 3: Implement Tyler eSuite Search and Extraction

**Files:**
- Modify: `scrapers/tyler_esuite.py`

**Step 1: Implement search navigation**

After running exploration (Task 1), update the scraper with actual selectors and navigation logic.

This step depends on Task 1 exploration results. The implementation will include:
1. Navigate to permit search page
2. Fill date range filter (last 365 days)
3. Execute search
4. Handle pagination
5. Extract permits via DOM or Excel export

**Step 2: Test the scraper**

Run: `cd /home/reid/command-center/testhome/permit-scraper && python3 scrapers/tyler_esuite.py lewisville 100`
Expected: At least 50 permits extracted, saved to data/raw/lewisville_raw.json

**Step 3: Commit working scraper**

```bash
git add scrapers/tyler_esuite.py
git commit -m "feat: implement Lewisville Tyler eSuite permit extraction"
```

---

## Task 4: Add Lewisville to SCRAPER_STATUS.md

**Files:**
- Modify: `SCRAPER_STATUS.md`

**Step 1: Update municipality table**

Find the Lewisville row and update:
```markdown
| 14 | **Lewisville** | 110K | Tyler eSuite | `tyler_esuite.py` | Denton | ✅ Working | Public access |
```

**Step 2: Update platform summary**

Update the Tyler eSuite row to show 1 working:
```markdown
| **Tyler eSuite** | 1 | 1 | 0 | Lewisville - NEW scraper implemented |
```

**Step 3: Commit documentation update**

```bash
git add SCRAPER_STATUS.md
git commit -m "docs: update status for Lewisville Tyler eSuite scraper"
```

---

## Task 5: Fix Irving MGO Connect Orchestrator

**Files:**
- Modify: `scrapers/mgo_connect.py:556-593` (scrape_orchestrator function)

**Step 1: Read the current orchestrator**

Understand the current routing logic in `scrape_orchestrator()`.

**Step 2: Modify orchestrator for Irving**

The orchestrator currently only calls `run_scraper_session()`. For Irving, it should call `scrape()` which has the Advanced Reporting path.

Find this code (approximately lines 556-593):
```python
async def scrape_orchestrator(city_name: str, target_count: int = 1000):
    """Orchestrates the phased fallback strategy.
    ...
    """
    # PHASE 1: HEADLESS
    try:
        print("PHASE 1: Attempting Headless extraction...")
        results = await run_scraper_session(city_name, target_count, headless=True)
```

Replace with:
```python
async def scrape_orchestrator(city_name: str, target_count: int = 1000):
    """Orchestrates the phased fallback strategy.

    Phase 1: Headless + stealth (fast, low resources)
    Phase 2: Headed mode (bypasses simple fingerprinting)
    Phase 3: Fail gracefully with diagnostics

    Special: Irving uses Advanced Reporting -> PDF export path (scrape function)
    """
    from pathlib import Path

    # Irving: Use the Advanced Reporting path (scrape function)
    # because the standard search returns 0 results
    if city_name.lower() == 'irving':
        print("IRVING DETECTED: Using Advanced Reporting path...")
        try:
            results = await scrape(city_name, target_count)
            if results and isinstance(results, dict) and results.get('permits'):
                return results
            elif results and isinstance(results, list):
                return save_results(city_name, results)
        except Exception as e:
            print(f"Irving Advanced Reporting failed: {e}")
            print("Falling back to standard session...")

    # PHASE 1: HEADLESS
    try:
        print("PHASE 1: Attempting Headless extraction...")
        results = await run_scraper_session(city_name, target_count, headless=True)
```

**Step 3: Test Irving scraper**

Run: `cd /home/reid/command-center/testhome/permit-scraper && python3 scrapers/mgo_connect.py Irving 100 2>&1 | tee /tmp/irving_test.log`
Expected: Uses Advanced Reporting path, attempts PDF export

**Step 4: Commit the fix**

```bash
git add scrapers/mgo_connect.py
git commit -m "fix: route Irving to Advanced Reporting path in MGO Connect"
```

---

## Task 6: Update Irving Status in Documentation

**Files:**
- Modify: `SCRAPER_STATUS.md`

**Step 1: Update Irving row**

If the fix works, update:
```markdown
| 5 | **Irving** | 240K | MGO Connect | `mgo_connect.py` | Dallas | ⚠️ Partial | Advanced Reporting path, PDF export |
```

If still not working, update notes:
```markdown
| 5 | **Irving** | 240K | MGO Connect | `mgo_connect.py` | Dallas | ⚠️ Partial | Advanced Reporting path attempted, needs PDF parsing |
```

**Step 2: Commit documentation**

```bash
git add SCRAPER_STATUS.md
git commit -m "docs: update Irving MGO Connect status"
```

---

## Task 7: Add Proxy Support Infrastructure

**Files:**
- Modify: `scrapers/utils.py`
- Create: `scrapers/proxy_config.py`

**Step 1: Create proxy configuration module**

```python
#!/usr/bin/env python3
"""
Proxy configuration for scrapers.
Supports datacenter and residential proxies.

Usage:
    from scrapers.proxy_config import get_proxy_config

    # In Playwright context creation:
    context = await browser.new_context(
        proxy=get_proxy_config('residential'),
        ...
    )
"""

import os
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

# Proxy configurations
# Set these in .env:
#   RESIDENTIAL_PROXY_URL=http://user:pass@proxy.example.com:8080
#   DATACENTER_PROXY_URL=http://user:pass@dc-proxy.example.com:8080

PROXY_CONFIGS = {
    'residential': {
        'server': os.getenv('RESIDENTIAL_PROXY_URL'),
    },
    'datacenter': {
        'server': os.getenv('DATACENTER_PROXY_URL'),
    },
}


def get_proxy_config(proxy_type: str = 'residential') -> Optional[dict]:
    """
    Get proxy configuration for Playwright.

    Args:
        proxy_type: 'residential' or 'datacenter'

    Returns:
        Playwright proxy config dict, or None if not configured
    """
    config = PROXY_CONFIGS.get(proxy_type, {})
    server = config.get('server')

    if not server:
        return None

    return {'server': server}


def is_proxy_configured(proxy_type: str = 'residential') -> bool:
    """Check if proxy is configured."""
    config = PROXY_CONFIGS.get(proxy_type, {})
    return bool(config.get('server'))
```

**Step 2: Commit proxy config**

```bash
git add scrapers/proxy_config.py
git commit -m "feat: add proxy configuration module"
```

---

## Task 8: Test Richardson with Residential Proxy

**Files:**
- Create: `scripts/test_richardson_proxy.py`

**Step 1: Create proxy test script**

```python
#!/usr/bin/env python3
"""
Test Richardson permit portal with residential proxy.
Richardson (cor.net) returns 403 from datacenter IPs.
"""

import asyncio
import sys
from datetime import datetime

from playwright.async_api import async_playwright

sys.path.insert(0, str(__file__).rsplit('/', 2)[0])
from scrapers.proxy_config import get_proxy_config, is_proxy_configured


async def test_richardson():
    """Test Richardson portal access with proxy."""
    print('=' * 60)
    print('RICHARDSON PROXY TEST')
    print('=' * 60)
    print(f'Time: {datetime.now().isoformat()}\n')

    # URLs to test
    test_urls = [
        'https://www.cor.net',
        'https://www.citizenserve.com/Portal/PortalController?Action=showSearchPage&ctzPagePrefix=Portal_&installationID=343',
    ]

    # Test without proxy first
    print('[1] Testing without proxy...')
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        for url in test_urls:
            try:
                response = await page.goto(url, timeout=30000)
                print(f'    {url[:50]}... -> {response.status}')
            except Exception as e:
                print(f'    {url[:50]}... -> ERROR: {e}')

        await browser.close()

    # Test with proxy
    if not is_proxy_configured('residential'):
        print('\n[2] Residential proxy not configured.')
        print('    Set RESIDENTIAL_PROXY_URL in .env to test.')
        return

    print('\n[2] Testing with residential proxy...')
    proxy_config = get_proxy_config('residential')

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(proxy=proxy_config)
        page = await context.new_page()

        for url in test_urls:
            try:
                response = await page.goto(url, timeout=30000)
                print(f'    {url[:50]}... -> {response.status}')

                if response.status == 200:
                    await page.screenshot(path=f'debug_html/richardson_proxy_success.png')
                    print(f'    SUCCESS! Screenshot saved.')

            except Exception as e:
                print(f'    {url[:50]}... -> ERROR: {e}')

        await browser.close()


if __name__ == '__main__':
    asyncio.run(test_richardson())
```

**Step 2: Run proxy test**

Run: `cd /home/reid/command-center/testhome/permit-scraper && python3 scripts/test_richardson_proxy.py`
Expected: Shows 403 without proxy, potentially 200 with residential proxy

**Step 3: Commit test script**

```bash
git add scripts/test_richardson_proxy.py
git commit -m "feat: add Richardson proxy test script"
```

---

## Task 9: Update Richardson Status

**Files:**
- Modify: `SCRAPER_STATUS.md`

**Step 1: Update Richardson row based on test results**

If proxy works:
```markdown
| 13 | **Richardson** | 120K | CitizenServe | — | Dallas/Collin | 🔬 Scrapable | Requires residential proxy |
```

If proxy doesn't work:
```markdown
| 13 | **Richardson** | 120K | Unknown | — | Dallas/Collin | ❌ Blocked | 403 even with residential proxy |
```

**Step 2: Commit documentation**

```bash
git add SCRAPER_STATUS.md
git commit -m "docs: update Richardson status after proxy testing"
```

---

## Task 10: Final Integration Test

**Step 1: Run all new scrapers**

```bash
cd /home/reid/command-center/testhome/permit-scraper

# Test Lewisville
python3 scrapers/tyler_esuite.py lewisville 50

# Test Irving
python3 scrapers/mgo_connect.py Irving 50

# Verify outputs exist
ls -la data/raw/lewisville_raw.json
ls -la data/exports/irving_mgo_raw.json
```

**Step 2: Verify permit counts**

```bash
python3 -c "
import json
from pathlib import Path

files = ['data/raw/lewisville_raw.json', 'data/exports/irving_mgo_raw.json']
for f in files:
    p = Path(f)
    if p.exists():
        data = json.loads(p.read_text())
        print(f'{f}: {data.get(\"actual_count\", 0)} permits')
    else:
        print(f'{f}: NOT FOUND')
"
```

Expected: Both files exist with permit counts > 0

**Step 3: Final commit with integration summary**

```bash
git add -A
git commit -m "feat: complete scraper expansion - Lewisville, Irving fix, proxy support

- Add Tyler eSuite scraper for Lewisville (110K pop)
- Fix Irving MGO Connect routing to Advanced Reporting path
- Add proxy configuration infrastructure
- Add Richardson proxy test script"
```

---

## Summary

| Task | Priority | Effort | Outcome |
|------|----------|--------|---------|
| 1-4 | HIGH | 2-3 hours | Lewisville Tyler eSuite scraper working |
| 5-6 | MEDIUM | 1 hour | Irving MGO Connect routed correctly |
| 7-9 | LOW | 1 hour | Proxy infrastructure + Richardson tested |
| 10 | - | 15 min | Integration verification |

**Total estimated effort:** 4-5 hours

**Dependencies:**
- Task 2-3 depend on Task 1 exploration results
- Task 6 depends on Task 5 test results
- Task 9 depends on Task 8 test results

**Risks:**
- Tyler eSuite portal may have anti-bot protections
- Irving Advanced Reporting may require PDF parsing (pypdf already imported)
- Richardson may be blocked even with residential proxy
