# Fix New City Scrapers Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix 4 newly added city scrapers (Mesquite, Prosper, Keller, Grapevine) to return 1000+ residential building permits from the last 2 months.

**Architecture:** Each city uses a different permit portal platform. Fixes involve adjusting search filters, DOM extraction patterns, and portal configurations. Test each fix by running the scraper and verifying permit types and dates.

**Tech Stack:** Python 3, Playwright (async), BeautifulSoup, pytest

---

## Task 1: Fix Mesquite EnerGov CSS - Filter for Building Permits

**Problem:** Scraper returns 1000 permits but wrong types (events, temp structures, pools). Need residential building permits (remodel, electrical, plumbing, mechanical, roofing).

**Files:**
- Modify: `/home/reid/testhome/permit-scraper/scrapers/citizen_self_service.py:85-89`
- Test: Manual scraper run

**Step 1: Update Mesquite config to specify permit type filter**

The scraper already supports a `permit_type` parameter. We need to add a default filter for Mesquite.

Edit `/home/reid/testhome/permit-scraper/scrapers/citizen_self_service.py` line 85-89:

```python
    'mesquite': {
        'name': 'Mesquite',
        'base_url': 'https://energov.cityofmesquite.com/EnerGov_Prod/SelfService',
        'default_permit_types': ['Residential Remodel', 'Residential Addition', 'Residential New Construction'],
    },
```

**Step 2: Modify scrape function to use city-specific permit type defaults**

Edit `/home/reid/testhome/permit-scraper/scrapers/citizen_self_service.py` around line 238, after `permit_type` parameter check:

```python
    # Use city-specific default permit types if none specified
    if not permit_type and city_config.get('default_permit_types'):
        permit_type = city_config['default_permit_types'][0]  # Use first as primary filter
```

**Step 3: Test Mesquite scraper with building permit filter**

Run:
```bash
cd /home/reid/testhome/permit-scraper && python3 scrapers/citizen_self_service.py mesquite 100
```

Expected: Output shows "Residential Remodel" or similar building permit types, not "Other Special Event" or "Temporary Storage Vault"

**Step 4: Verify permit types in output**

Run:
```bash
cd /home/reid/testhome/permit-scraper && python3 -c "
import json
with open('mesquite_raw.json') as f:
    data = json.load(f)
permits = data.get('permits', data)
types = {}
for p in permits[:20]:
    t = p.get('type', 'Unknown')
    types[t] = types.get(t, 0) + 1
print('Top permit types:', dict(sorted(types.items(), key=lambda x: -x[1])[:10]))
"
```

Expected: Types include "Residential Remodel", "Electrical", "Plumbing", "Mechanical", "Roofing" - NOT "Special Event" or "Temporary"

**Step 5: Commit changes**

```bash
cd /home/reid/testhome/permit-scraper
git add scrapers/citizen_self_service.py
git commit -m "fix(mesquite): add default building permit type filter

Mesquite was returning events/temp structures instead of building permits.
Added default_permit_types config to filter for residential permits."
```

---

## Task 2: Fix Prosper eTRAKiT - Improve DOM Data Extraction

**Problem:** Scraper returns 420 permits but type and date fields are empty. The DOM extraction regex isn't matching Prosper's table structure.

**Files:**
- Modify: `/home/reid/testhome/permit-scraper/scrapers/etrakit.py:90-157`
- Test: Manual scraper run

**Step 1: Debug Prosper's actual DOM structure**

Run this debug script to see what data is in the table:

```bash
cd /home/reid/testhome/permit-scraper && python3 -c "
import asyncio
from playwright.async_api import async_playwright

async def debug():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto('http://etrakit.prospertx.gov/eTRAKIT/Search/permit.aspx', timeout=60000)
        await asyncio.sleep(2)
        await page.fill('#cplMain_txtSearchString', 'RE')
        await page.click('input[id*=\"btnSearch\"]')
        await asyncio.sleep(4)

        # Get table headers and first few rows
        result = await page.evaluate('''() => {
            const headers = Array.from(document.querySelectorAll('th')).map(th => th.innerText.trim());
            const rows = document.querySelectorAll('tr.rgRow, tr.rgAltRow');
            const samples = [];
            for (let i = 0; i < Math.min(5, rows.length); i++) {
                const cells = rows[i].querySelectorAll('td');
                samples.push(Array.from(cells).map(c => c.innerText.trim()));
            }
            return {headers, samples, rowCount: rows.length};
        }''')
        print('Headers:', result['headers'])
        print('Row count:', result['rowCount'])
        for i, row in enumerate(result['samples']):
            print(f'Row {i}: {row}')
        await browser.close()

asyncio.run(debug())
"
```

Expected: See actual column headers and sample data to understand the table structure

**Step 2: Update extract_permits_from_page to match Prosper's structure**

Based on typical eTRAKiT layouts, the columns are usually: [Permit#, Address, Type, Status, Applied, Issued]

Edit `/home/reid/testhome/permit-scraper/scrapers/etrakit.py` line 131-142, improve field extraction:

```python
            // Extract other fields from cells by position (eTRAKiT standard layout)
            // Typical columns: [Permit#, Address, Type, Status, AppliedDate, IssuedDate]
            if (cellTexts.length >= 4) {
                // If permit_id was from link, cells are offset
                const offset = link ? 0 : 0;
                address = address || cellTexts[1 + offset] || '';
                permit_type = permit_type || cellTexts[2 + offset] || '';
                status = status || cellTexts[3 + offset] || '';
                // Date might be in position 4 or 5
                if (cellTexts.length > 4) {
                    date = date || cellTexts[4 + offset] || cellTexts[5 + offset] || '';
                }
            }

            // Fallback: pattern matching for fields not found by position
            for (const text of cellTexts) {
```

**Step 3: Test Prosper scraper with improved extraction**

Run:
```bash
cd /home/reid/testhome/permit-scraper && python3 scrapers/etrakit.py prosper 100 2>&1 | head -50
```

Expected: Sample permits show type and date values, not empty strings

**Step 4: Verify extracted data has type and date**

Run:
```bash
cd /home/reid/testhome/permit-scraper && python3 -c "
import json
with open('prosper_raw.json') as f:
    permits = json.load(f)
has_type = sum(1 for p in permits if p.get('type'))
has_date = sum(1 for p in permits if p.get('date'))
print(f'Total: {len(permits)}, With type: {has_type}, With date: {has_date}')
print('Samples:')
for p in permits[:5]:
    print(f\"  {p.get('permit_id')} | {p.get('type', 'NO TYPE')} | {p.get('date', 'NO DATE')}\")
"
```

Expected: >80% of permits have type and date values

**Step 5: Commit changes**

```bash
cd /home/reid/testhome/permit-scraper
git add scrapers/etrakit.py
git commit -m "fix(prosper): improve DOM extraction for type/date fields

eTRAKiT extraction now uses positional column mapping in addition to
pattern matching, capturing type and date from Prosper's table layout."
```

---

## Task 3: Fix Keller eTRAKiT - Research Public Portal

**Problem:** Keller's eTRAKiT portal at `trakitweb.cityofkeller.com` is contractor-login focused, returning 0 public results.

**Files:**
- Modify: `/home/reid/testhome/permit-scraper/scrapers/etrakit.py:71-78`
- Modify: `/home/reid/testhome/permit-scraper/docs/research/dfw_municipalities.json`

**Step 1: Search for Keller's actual public permit portal**

Run web search to find if Keller has an alternate public portal:

```bash
# Manual step: Search "Keller Texas building permits public search portal citizen"
# Look for: EnerGov CSS, MyGov, or other public-facing permit lookup
```

**Step 2a: If public portal found - update config**

If a public portal is found (e.g., EnerGov CSS), add Keller to the appropriate scraper config.

**Step 2b: If no public portal - mark as unavailable**

Edit `/home/reid/testhome/permit-scraper/scrapers/etrakit.py` line 71-78, remove or comment out Keller:

```python
    # 'keller': {
    #     'name': 'Keller',
    #     'base_url': 'https://trakitweb.cityofkeller.com',
    #     'search_path': '/etrakit/Search/permit.aspx',
    #     # NOTE: This portal requires contractor login - no public search available
    #     'prefixes': ['B25-', 'B24-'],
    #     'permit_regex': r'^[A-Z]\d{2}-\d{4,5}$',
    #     'status': 'blocked',  # Contractor-only portal
    # },
```

**Step 3: Update research documentation**

Edit `/home/reid/testhome/permit-scraper/docs/research/dfw_municipalities.json`, update Keller entry:

```json
{
    "city": "Keller",
    "tier": "B",
    "population": 45000,
    "status": "blocked",
    "platform": "eTRAKiT (contractor-only)",
    "portal_url": "https://trakitweb.cityofkeller.com/etrakit/",
    "notes": "BLOCKED - Portal requires contractor login. No public permit search available."
}
```

**Step 4: Commit changes**

```bash
cd /home/reid/testhome/permit-scraper
git add scrapers/etrakit.py docs/research/dfw_municipalities.json
git commit -m "fix(keller): mark as blocked - contractor-only portal

Keller's eTRAKiT portal requires contractor login for permit searches.
No public-facing permit lookup is available. Marked as blocked in config."
```

---

## Task 4: Fix Grapevine MyGov - Debug Search Interaction

**Problem:** Grapevine MyGov portal loads but search returns 0 permits. Slug was fixed to `tx_grapevine` but search still not working.

**Files:**
- Modify: `/home/reid/testhome/permit-scraper/scrapers/mygov_multi.py:67-146`
- Test: Manual debug and scraper run

**Step 1: Debug Grapevine's MyGov search interface**

Run this to understand Grapevine's specific MyGov implementation:

```bash
cd /home/reid/testhome/permit-scraper && python3 -c "
import asyncio
from playwright.async_api import async_playwright

async def debug():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto('https://public.mygov.us/tx_grapevine/lookup', timeout=30000)
        await asyncio.sleep(3)

        # Find all input elements
        result = await page.evaluate('''() => {
            const inputs = document.querySelectorAll('input');
            const inputInfo = Array.from(inputs).map(i => ({
                type: i.type, id: i.id, name: i.name,
                placeholder: i.placeholder, class: i.className
            }));

            // Check for search form structure
            const forms = document.querySelectorAll('form');
            const formInfo = Array.from(forms).map(f => ({
                id: f.id, action: f.action, method: f.method
            }));

            return {inputs: inputInfo, forms: formInfo, bodyText: document.body.innerText.substring(0, 500)};
        }''')

        print('Inputs:', result['inputs'])
        print('Forms:', result['forms'])
        print('Body text:', result['bodyText'][:300])

        # Try searching
        search_input = await page.query_selector('input[type=\"text\"], input[type=\"search\"]')
        if search_input:
            await search_input.fill('Main')
            await asyncio.sleep(1)
            await search_input.press('Enter')
            await asyncio.sleep(3)

            # Check for results
            result2 = await page.evaluate('''() => {
                const results = document.querySelectorAll('.accordion-toggle, .search-result, .address-result, li');
                return {
                    resultCount: results.length,
                    bodyText: document.body.innerText.substring(0, 500)
                };
            }''')
            print('After search:', result2)

        await browser.close()

asyncio.run(debug())
"
```

Expected: See what elements exist and if search returns any results

**Step 2: Update search_address function for Grapevine's interface**

If Grapevine uses a different input selector or search mechanism, update `/home/reid/testhome/permit-scraper/scrapers/mygov_multi.py` line 76-84:

```python
        # Find and fill search - try multiple selectors
        search_input = await page.query_selector(
            'input[type="text"], input[type="search"], '
            'input[placeholder*="search" i], input[placeholder*="address" i], '
            '#search, .search-input'
        )
        if not search_input:
            logger.warning(f"No search input found for {city_slug}")
            return permits

        await search_input.click()
        await search_input.fill(search_term)
        await asyncio.sleep(1)

        # Try multiple ways to submit search
        await search_input.press('Enter')
        await asyncio.sleep(2)

        # Some MyGov portals need a button click instead of Enter
        search_btn = await page.query_selector('button[type="submit"], button:has-text("Search"), .search-button')
        if search_btn:
            await search_btn.click()
            await asyncio.sleep(2)
```

**Step 3: Test Grapevine scraper**

Run:
```bash
cd /home/reid/testhome/permit-scraper && python3 scrapers/mygov_multi.py grapevine 100 2>&1 | head -50
```

Expected: Some permits found (even 10-20 is progress)

**Step 4: If still failing, check if Grapevine has different permit structure**

Some MyGov implementations don't show permits on the lookup page. Check if permits are under a different tab:

```bash
cd /home/reid/testhome/permit-scraper && python3 -c "
import asyncio
from playwright.async_api import async_playwright

async def check_tabs():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto('https://public.mygov.us/tx_grapevine/lookup', timeout=30000)
        await asyncio.sleep(3)

        # Look for navigation tabs
        result = await page.evaluate('''() => {
            const navItems = document.querySelectorAll('nav a, .nav a, [role=\"tab\"], .tab');
            return Array.from(navItems).map(n => ({text: n.innerText, href: n.href}));
        }''')
        print('Navigation items:', result)
        await browser.close()

asyncio.run(check_tabs())
"
```

**Step 5: Update Grapevine status based on findings**

If Grapevine's MyGov doesn't support public permit lookup, update the config:

Edit `/home/reid/testhome/permit-scraper/scrapers/mygov_multi.py` line 35:

```python
    # 'grapevine': {'name': 'Grapevine', 'slug': 'tx_grapevine', 'pop': 50000, 'status': 'research_needed'},
```

**Step 6: Commit changes**

```bash
cd /home/reid/testhome/permit-scraper
git add scrapers/mygov_multi.py
git commit -m "fix(grapevine): improve MyGov search interaction

Updated search selectors and submission logic for Grapevine's MyGov portal.
Added fallback button click for portals that don't respond to Enter key."
```

---

## Task 5: Final Validation - Run All Fixed Scrapers

**Files:**
- Test: All 4 scrapers

**Step 1: Run Mesquite and verify building permits**

```bash
cd /home/reid/testhome/permit-scraper && python3 scrapers/citizen_self_service.py mesquite 500
```

Expected: 500 permits with types like "Residential Remodel", "Electrical", "Plumbing"

**Step 2: Run Prosper and verify type/date extraction**

```bash
cd /home/reid/testhome/permit-scraper && python3 scrapers/etrakit.py prosper 500
```

Expected: 400+ permits with populated type and date fields

**Step 3: Verify Keller marked as blocked**

```bash
cd /home/reid/testhome/permit-scraper && python3 scrapers/etrakit.py keller 10 2>&1 | head -5
```

Expected: Error message or config indicating Keller is blocked

**Step 4: Run Grapevine and check results**

```bash
cd /home/reid/testhome/permit-scraper && python3 scrapers/mygov_multi.py grapevine 100 2>&1 | tail -20
```

Expected: Some permits found OR clear documentation that portal doesn't support public lookup

**Step 5: Generate summary report**

```bash
cd /home/reid/testhome/permit-scraper && python3 -c "
import json
from pathlib import Path

cities = ['mesquite', 'prosper']
for city in cities:
    path = Path(f'{city}_raw.json')
    if not path.exists():
        print(f'{city}: NO FILE')
        continue
    with open(path) as f:
        data = json.load(f)
    permits = data.get('permits', data) if isinstance(data, dict) else data

    has_type = sum(1 for p in permits if p.get('type'))
    has_date = sum(1 for p in permits if p.get('date'))

    print(f'{city.upper()}: {len(permits)} permits, {has_type} with type, {has_date} with date')
"
```

Expected: Both cities show high percentage of permits with type and date data

**Step 6: Final commit**

```bash
cd /home/reid/testhome/permit-scraper
git add -A
git commit -m "feat: complete new city scraper fixes

- Mesquite: Now filtering for residential building permits
- Prosper: DOM extraction captures type/date fields
- Keller: Marked as blocked (contractor-only portal)
- Grapevine: Search interaction improved (or marked for research)"
```

---

## Summary

| Task | City | Issue | Fix |
|------|------|-------|-----|
| 1 | Mesquite | Wrong permit types | Add default_permit_types filter |
| 2 | Prosper | Missing type/date | Improve DOM extraction by position |
| 3 | Keller | Contractor-only | Mark as blocked, update docs |
| 4 | Grapevine | Search not working | Debug and fix search interaction |
| 5 | All | Validation | Run all scrapers, verify output |

**Estimated tasks:** 5 major tasks, ~15 steps total
