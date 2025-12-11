# Expand Scraper Coverage Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add 2 new working scrapers (Flower Mound, Carrollton), update status documentation, and close out unsolvable portals (MyGov, Garland).

**Architecture:** Flower Mound uses existing eTRAKiT platform (reuse `etrakit_fast.py`). Carrollton uses CityView which requires a new scraper with DOM extraction. MyGov and Garland are marked as not scrapeable.

**Tech Stack:** Python 3, Playwright, asyncio, existing scraper patterns

---

## Task 1: Test Flower Mound eTRAKiT (Already Configured)

**Files:**
- Existing: `scrapers/etrakit_fast.py` (already has Flower Mound config at lines 27-34)
- Output: `flower_mound_raw.json`

**Step 1: Verify the existing config**

The config already exists in `etrakit_fast.py`:

```python
'flower_mound': {
    'name': 'Flower Mound',
    'base_url': 'https://etrakit.flower-mound.com',
    'search_path': '/etrakit/Search/permit.aspx',
    'prefixes': ['BP25', 'BP24', 'BP23', '25-', '24-', '23-', '22-', '21-'],
    'permit_regex': r'^(BP)?\d{2}-\d{5}$',
},
```

**Step 2: Run the scraper with small target**

Run:
```bash
cd /home/reid/testhome/permit-scraper && python3 scrapers/etrakit_fast.py flower_mound 50
```

Expected:
- Output shows "FLOWER MOUND FAST PERMIT SCRAPER"
- Permit data extracted with IDs like `BP25-00001` or `25-00001`
- `flower_mound_raw.json` created with permits array

**Step 3: Verify output structure**

Run:
```bash
cd /home/reid/testhome/permit-scraper && python3 -c "import json; d=json.load(open('flower_mound_raw.json')); print(f'Count: {d[\"actual_count\"]}'); print(f'Sample: {d[\"permits\"][0] if d[\"permits\"] else \"none\"}')"
```

Expected: Count > 0, Sample shows permit_id, address, type fields

**Step 4: Run full scrape if test passes**

Run:
```bash
cd /home/reid/testhome/permit-scraper && python3 scrapers/etrakit_fast.py flower_mound 1000
```

Expected: ~1000 permits collected

**Step 5: Commit**

```bash
cd /home/reid/testhome/permit-scraper && git add flower_mound_raw.json && git commit -m "data: add Flower Mound permit data (eTRAKiT)"
```

---

## Task 2: Create CityView Scraper for Carrollton

**Files:**
- Create: `scrapers/cityview.py`
- Test output: `carrollton_raw.json`
- Debug: `debug_html/cityview_*.png`

**Step 1: Create the scraper skeleton**

Create `scrapers/cityview.py`:

```python
#!/usr/bin/env python3
"""
CITYVIEW PERMIT SCRAPER (Playwright Python)
Portal: CityView (cityserve.cityofcarrollton.com)
Covers: Carrollton TX

Usage:
  python scrapers/cityview.py carrollton 100
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

CITYVIEW_CITIES = {
    'carrollton': {
        'name': 'Carrollton',
        'base_url': 'https://cityserve.cityofcarrollton.com',
        'search_url': 'https://cityserve.cityofcarrollton.com/CityViewPortal/Permit/Locator',
    },
}


async def extract_permits_from_page(page) -> list:
    """Extract permits from CityView search results."""
    return await page.evaluate('''() => {
        const permits = [];

        // CityView typically renders results in a list or table
        // Look for permit cards/rows
        const rows = document.querySelectorAll(
            '.search-result, .permit-row, tr[data-permit], .list-item, ' +
            '[class*="result"], [class*="permit"], .card'
        );

        for (const row of rows) {
            const text = row.innerText || '';

            // Skip if no meaningful content
            if (text.length < 10) continue;

            // Try to extract permit number (various formats)
            let permit_id = null;
            let address = null;
            let permit_type = null;
            let status = null;
            let date = null;

            // Look for permit number patterns
            const permitMatch = text.match(/([A-Z]{2,3}-?\d{4,}-?\d{0,5}|\d{4,}-[A-Z]{2,})/);
            if (permitMatch) permit_id = permitMatch[1];

            // Look for address pattern (number + street)
            const addrMatch = text.match(/(\d+\s+[A-Z][A-Za-z\s]+(?:St|Ave|Rd|Dr|Blvd|Ln|Way|Ct|Cir|Pl)[^,]*)/i);
            if (addrMatch) address = addrMatch[1].trim();

            // Look for date pattern
            const dateMatch = text.match(/(\d{1,2}\/\d{1,2}\/\d{4})/);
            if (dateMatch) date = dateMatch[1];

            // Look for common permit types
            const typeMatch = text.match(/(Building|Electrical|Plumbing|Mechanical|Roofing|HVAC|Residential|Commercial|New Construction|Remodel|Addition)/i);
            if (typeMatch) permit_type = typeMatch[1];

            // Look for status
            const statusMatch = text.match(/(Issued|Active|Final|Closed|Pending|Approved|Expired|In Review)/i);
            if (statusMatch) status = statusMatch[1];

            if (permit_id || address) {
                permits.push({
                    permit_id: permit_id || '',
                    address: address || '',
                    type: permit_type || '',
                    status: status || '',
                    date: date || '',
                    raw_text: text.substring(0, 200)
                });
            }
        }

        return permits;
    }''')


async def scrape(city_key: str, target_count: int = 100):
    """Scrape permits from CityView portal."""
    city_key = city_key.lower()
    if city_key not in CITYVIEW_CITIES:
        print(f'ERROR: Unknown city. Available: {list(CITYVIEW_CITIES.keys())}')
        sys.exit(1)

    config = CITYVIEW_CITIES[city_key]

    print('=' * 60)
    print(f'{config["name"].upper()} PERMIT SCRAPER (CityView)')
    print('=' * 60)
    print(f'Target: {target_count} permits')
    print(f'Time: {datetime.now().isoformat()}\n')

    permits = []
    api_permits = []
    errors = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1400, 'height': 900},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        page = await context.new_page()

        # Capture API responses
        async def handle_response(response):
            url = response.url
            if response.status == 200 and 'permit' in url.lower():
                try:
                    content_type = response.headers.get('content-type', '')
                    if 'json' in content_type:
                        data = await response.json()
                        if isinstance(data, list):
                            api_permits.extend(data)
                            print(f'    [API] Captured {len(data)} permits')
                        elif isinstance(data, dict):
                            items = data.get('data', data.get('results', data.get('permits', []))
                            if items:
                                api_permits.extend(items)
                                print(f'    [API] Captured {len(items)} permits')
                except Exception:
                    pass

        page.on('response', handle_response)

        try:
            # Step 1: Load search page
            print('[1] Loading CityView search page...')
            await page.goto(config['search_url'], wait_until='networkidle', timeout=60000)
            await asyncio.sleep(3)

            Path('debug_html').mkdir(exist_ok=True)
            await page.screenshot(path=f'debug_html/cityview_{city_key}_initial.png', full_page=True)
            print(f'    URL: {page.url}')

            # Step 2: Try to search with wildcard or recent permits
            print('\n[2] Attempting search...')

            # Look for search input and try wildcard search
            search_result = await page.evaluate('''async () => {
                const wait = (ms) => new Promise(r => setTimeout(r, ms));

                // Find search input
                const inputs = document.querySelectorAll(
                    'input[type="text"], input[type="search"], ' +
                    'input[placeholder*="search"], input[placeholder*="address"], ' +
                    'input[id*="search"], input[name*="search"]'
                );

                let searchInput = null;
                for (const input of inputs) {
                    if (input.offsetParent !== null) {  // visible
                        searchInput = input;
                        break;
                    }
                }

                if (!searchInput) {
                    return { error: 'No search input found', inputCount: inputs.length };
                }

                // Enter wildcard search (try * or just a common street)
                searchInput.value = '*';
                searchInput.dispatchEvent(new Event('input', { bubbles: true }));
                searchInput.dispatchEvent(new Event('change', { bubbles: true }));
                await wait(500);

                // Try to click search button
                const buttons = document.querySelectorAll('button, input[type="submit"], a.btn');
                for (const btn of buttons) {
                    const text = (btn.textContent || btn.value || '').toLowerCase();
                    if (text.includes('search') || text.includes('find') || text.includes('go')) {
                        btn.click();
                        return { success: true, clicked: text };
                    }
                }

                // Try pressing Enter
                searchInput.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', keyCode: 13 }));
                return { success: true, clicked: 'enter key' };
            }''')

            print(f'    Search result: {search_result}')
            await asyncio.sleep(5)

            await page.screenshot(path=f'debug_html/cityview_{city_key}_after_search.png', full_page=True)

            # Step 3: Extract results
            print('\n[3] Extracting permits...')

            # Check if we got API data
            if api_permits:
                print(f'    Using {len(api_permits)} permits from API')
                for item in api_permits[:target_count]:
                    permit = {
                        'permit_id': item.get('permitNumber', item.get('referenceNumber', item.get('id', ''))),
                        'address': item.get('address', item.get('siteAddress', item.get('propertyAddress', ''))),
                        'type': item.get('permitType', item.get('type', item.get('workType', ''))),
                        'status': item.get('status', ''),
                        'date': item.get('issuedDate', item.get('applicationDate', item.get('date', ''))),
                        'description': item.get('description', item.get('workDescription', ''))
                    }
                    if permit['permit_id'] or permit['address']:
                        permits.append(permit)
            else:
                # Fall back to DOM extraction
                dom_permits = await extract_permits_from_page(page)
                print(f'    DOM extraction: {len(dom_permits)} permits')
                permits.extend(dom_permits[:target_count])

            # Step 4: Try pagination if needed
            print(f'\n[4] Checking pagination (have {len(permits)} permits)...')
            page_num = 1
            max_pages = 20

            while len(permits) < target_count and page_num < max_pages:
                has_next = await page.evaluate('''() => {
                    const nextBtns = document.querySelectorAll(
                        'a.next, .pagination .next, [rel="next"], ' +
                        'button[aria-label*="next"], a[aria-label*="next"], ' +
                        '.page-link:not(.disabled)'
                    );
                    for (const btn of nextBtns) {
                        const text = (btn.textContent || '').toLowerCase();
                        if ((text.includes('next') || text === '>') && !btn.disabled) {
                            btn.click();
                            return true;
                        }
                    }
                    return false;
                }''')

                if not has_next:
                    print('    No more pages')
                    break

                page_num += 1
                await asyncio.sleep(3)

                more_permits = await extract_permits_from_page(page)
                new_count = len([p for p in more_permits if p.get('permit_id') not in [x.get('permit_id') for x in permits]])
                permits.extend([p for p in more_permits if p.get('permit_id') not in [x.get('permit_id') for x in permits]])
                print(f'    Page {page_num}: +{new_count} permits ({len(permits)} total)')

            print(f'\n    Total permits: {len(permits)}')

        except Exception as e:
            print(f'\nERROR: {e}')
            import traceback
            traceback.print_exc()
            errors.append({'step': 'main', 'error': str(e)})
            await page.screenshot(path=f'debug_html/cityview_{city_key}_error.png', full_page=True)

        finally:
            await browser.close()

    # Save results
    output = {
        'source': city_key,
        'portal_type': 'CityView',
        'scraped_at': datetime.now().isoformat(),
        'target_count': target_count,
        'actual_count': len(permits),
        'errors': errors,
        'permits': permits[:target_count]
    }

    output_file = f'{city_key}_raw.json'
    Path(output_file).write_text(json.dumps(output, indent=2))

    print('\n' + '=' * 60)
    print('SUMMARY')
    print('=' * 60)
    print(f'City: {config["name"]}')
    print(f'Permits: {output["actual_count"]}')
    print(f'Errors: {len(errors)}')
    print(f'Output: {output_file}')

    if permits:
        print('\nSAMPLE:')
        for p in permits[:5]:
            print(f'  {p.get("permit_id", "?")} | {p.get("type", "?")} | {p.get("address", "?")[:40]}')

    return output


if __name__ == '__main__':
    city = sys.argv[1] if len(sys.argv) > 1 else 'carrollton'
    count = int(sys.argv[2]) if len(sys.argv) > 2 else 100
    asyncio.run(scrape(city, count))
```

**Step 2: Run initial test**

Run:
```bash
cd /home/reid/testhome/permit-scraper && python3 scrapers/cityview.py carrollton 20
```

Expected: Either API capture or DOM extraction yields some permits. Check `debug_html/cityview_carrollton_*.png` for debugging.

**Step 3: Iterate on extraction if needed**

If permits are 0, examine screenshots and:
1. Check `debug_html/cityview_carrollton_after_search.png` for actual page structure
2. Update selectors in `extract_permits_from_page()` to match actual DOM
3. Re-run test

**Step 4: Full scrape once working**

Run:
```bash
cd /home/reid/testhome/permit-scraper && python3 scrapers/cityview.py carrollton 500
```

**Step 5: Commit**

```bash
cd /home/reid/testhome/permit-scraper && git add scrapers/cityview.py carrollton_raw.json && git commit -m "feat: add CityView scraper for Carrollton"
```

---

## Task 3: Update SCRAPER_STATUS.md

**Files:**
- Modify: `SCRAPER_STATUS.md`

**Step 1: Update working scrapers table**

Add Flower Mound to working scrapers section (after Plano row):

```markdown
| **Flower Mound** | `etrakit_fast.py` | `python3 scrapers/etrakit_fast.py flower_mound 1000` | ⚡ Fast DOM extraction (eTRAKiT) |
```

Add Carrollton (if CityView scraper works):

```markdown
| **Carrollton** | `cityview.py` | `python3 scrapers/cityview.py carrollton 500` | CityView portal |
```

**Step 2: Update DFW Metro table**

Change these rows:

```markdown
| 12 | **Carrollton** | 140K | CityView | `cityview.py` | ✅ Working |
| 15 | **Flower Mound** | 80K | eTRAKiT | `etrakit_fast.py` | ✅ Working |
| 9 | **Garland** | 240K | None | — | ❌ No online portal |
| 19 | **Rowlett** | 68K | MyGov | — | ❌ Requires contractor login |
| 20 | **Grapevine** | 55K | MyGov (.exe) | — | ❌ Requires desktop client |
```

**Step 3: Update platform summary**

```markdown
| Platform | Working | Blocked | Not Scrapeable |
|----------|---------|---------|----------------|
| Accela | 4 | 0 | 0 |
| eTRAKiT | 3 | 0 | 0 |
| CityView | 1 | 0 | 0 |
| Socrata API | 1 | 0 | 0 |
| MGO Connect | 0 | 5 | 0 |
| EnerGov CSS | 0 | 4 | 0 |
| MyGov | 0 | 0 | 2 |
| None | 0 | 0 | 1 |
```

**Step 4: Update scraper file inventory**

Add new entries:

```markdown
| `scrapers/cityview.py` | Production | CityView portal scraper (Carrollton) |
```

**Step 5: Update next steps**

```markdown
## Next Steps

1. ~~**Research unknown cities**~~ ✅ DONE - Flower Mound (eTRAKiT), Carrollton (CityView), Garland (no portal)
2. **MGO Decision** - Irving/Lewisville/Denton blocked by anti-automation (consider playwright-stealth + proxies)
3. ~~**Grapevine/Rowlett**~~ ❌ CLOSED - MyGov requires login/desktop client, not scrapeable
```

**Step 6: Commit**

```bash
cd /home/reid/testhome/permit-scraper && git add SCRAPER_STATUS.md && git commit -m "docs: update scraper status with new coverage"
```

---

## Task 4: Remove/Archive Broken MyGov Scraper

**Files:**
- Move: `scrapers/mygov.py` → `_archive/2025-12-11/mygov.py`

**Step 1: Archive the file**

```bash
cd /home/reid/testhome/permit-scraper && mkdir -p _archive/2025-12-11 && mv scrapers/mygov.py _archive/2025-12-11/
```

**Step 2: Commit**

```bash
cd /home/reid/testhome/permit-scraper && git add -A && git commit -m "chore: archive mygov.py (requires login, not scrapeable)"
```

---

## Task 5: Verify All Working Scrapers

**Files:**
- Verify outputs exist and have data

**Step 1: Run quick verification of all working scrapers**

```bash
cd /home/reid/testhome/permit-scraper && for city in dallas fort_worth frisco flower_mound; do
  echo "=== $city ==="
  if [ -f "${city}_raw.json" ]; then
    python3 -c "import json; d=json.load(open('${city}_raw.json')); print(f'  Count: {d.get(\"actual_count\", 0)}')"
  else
    echo "  No data file"
  fi
done
```

**Step 2: Verify Carrollton if CityView worked**

```bash
cd /home/reid/testhome/permit-scraper && python3 -c "import json; d=json.load(open('carrollton_raw.json')); print(f'Carrollton: {d.get(\"actual_count\", 0)} permits')"
```

---

## Summary

After completing all tasks:

| City | Population | Status | Scraper |
|------|-----------|--------|---------|
| Dallas | 1.3M | ✅ Working | accela_fast.py |
| Fort Worth | 950K | ✅ Working | accela_fast.py |
| Arlington | 400K | ✅ Working | dfw_big4_socrata.py |
| Plano | 290K | ✅ Working | etrakit.py |
| Garland | 240K | ❌ No portal | — |
| Frisco | 220K | ✅ Working | etrakit_fast.py |
| Grand Prairie | 200K | ✅ Working | accela_fast.py |
| Carrollton | 140K | ✅ NEW | cityview.py |
| Flower Mound | 80K | ✅ NEW | etrakit_fast.py |
| Irving | 250K | ❌ Blocked | (MGO anti-bot) |
| Rowlett | 68K | ❌ Login required | — |
| Grapevine | 55K | ❌ Desktop client | — |

**Total: 9 working scrapers (was 7) covering ~3.8M population**
