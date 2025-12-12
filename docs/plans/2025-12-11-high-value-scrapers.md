# High-Value Scrapers Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Get scrapers working for Irving (MGO Connect), Southlake, Colleyville (EnerGov), and investigate Westlake (MyGov).

**Architecture:** Fix existing scrapers with verified URLs and improved wait logic. Irving needs dropdown race condition fix. EnerGov cities need correct URLs and relaxed regex. Westlake is greenfield exploration.

**Tech Stack:** Python 3, Playwright, asyncio

---

## Task 1: Add Colleyville to EnerGov Scraper

**Files:**
- Modify: `scrapers/citizen_self_service.py:27-40`

**Step 1: Add Colleyville config with verified URL**

In `CSS_CITIES` dict (line 27), add Colleyville entry:

```python
CSS_CITIES = {
    'mckinney': {
        'name': 'McKinney',
        'base_url': 'https://egov.mckinneytexas.org/EnerGov_Prod/SelfService',
    },
    'southlake': {
        'name': 'Southlake',
        'base_url': 'https://energov.cityofsouthlake.com/EnerGov_Prod/SelfService',
    },
    'colleyville': {
        'name': 'Colleyville',
        'base_url': 'https://selfservice.colleyville.com/energov_prod/selfservice',
    },
    'allen': {
        'name': 'Allen',
        'base_url': 'https://energovweb.cityofallen.org/EnerGov/SelfService',
    },
}
```

**Step 2: Run scraper to verify URL works**

```bash
cd /home/reid/testhome/permit-scraper && python3 scrapers/citizen_self_service.py colleyville 10
```

Expected: Should navigate to search page without SSL errors. May timeout on extraction (we fix that next).

---

## Task 2: Add Explicit Wait for Results Loading

**Files:**
- Modify: `scrapers/citizen_self_service.py:274-276`

**Step 1: Add wait before checking results**

After line 275 (`print('\n[4] Checking for results and applying Permit filter...')`), add:

```python
            # Step 4: Check for results and filter by Permit type
            print('\n[4] Checking for results and applying Permit filter...')

            # Wait for results to appear in DOM before parsing
            try:
                await page.wait_for_selector(
                    'table tbody tr, .search-result, .result-item, [class*="permit-row"], a[href*="permit"]',
                    timeout=20000
                )
                print('    Results detected in DOM')
            except PlaywrightTimeout:
                print('    WARN: Timeout waiting for results selector - continuing anyway')

            # Look for result count or filter sidebar
```

**Step 2: Test Southlake with explicit wait**

```bash
cd /home/reid/testhome/permit-scraper && python3 scrapers/citizen_self_service.py southlake 20
```

Expected: Should show "Results detected in DOM" message. If still failing, check screenshot.

---

## Task 3: Relax Permit ID Regex Pattern

**Files:**
- Modify: `scrapers/citizen_self_service.py:381`

**Step 1: Replace strict regex with flexible pattern**

Change line 381 from:
```python
                    const permitIdPattern = /^\d{6}-\d{4}(-[A-Z0-9]+)?$/;
```

To:
```python
                    // Flexible: 6+ chars, alphanumeric with dashes (handles various city formats)
                    const permitIdPattern = /^[A-Z0-9]{2,}-[A-Z0-9-]{2,}$/i;
```

**Step 2: Test both cities**

```bash
cd /home/reid/testhome/permit-scraper && python3 scrapers/citizen_self_service.py southlake 50
cd /home/reid/testhome/permit-scraper && python3 scrapers/citizen_self_service.py colleyville 50
```

Expected: Should extract permits. Check `southlake_raw.json` and `colleyville_raw.json` for data.

**Step 3: Commit EnerGov fixes**

```bash
cd /home/reid/testhome/permit-scraper && git add scrapers/citizen_self_service.py && git commit -m "feat: add Colleyville, fix EnerGov wait/regex"
```

---

## Task 4: Test Irving in Headed Mode (Diagnostic)

**Files:**
- None (diagnostic only)

**Step 1: Run Irving scraper in headed mode**

Temporarily modify `scrapers/mgo_connect.py` line 322:
```python
        browser = await p.chromium.launch(headless=False, slow_mo=500)
```

Then run:
```bash
cd /home/reid/testhome/permit-scraper && python3 scrapers/mgo_connect.py Irving 10
```

**Step 2: Observe the dropdown behavior**

Watch for:
- Does Texas get selected?
- Does jurisdiction dropdown populate?
- Does Irving appear and get selected?
- What happens after Continue click?

Take notes on what you observe. Revert headless change after.

---

## Task 5: Fix Irving Dropdown Race Condition

**Files:**
- Modify: `scrapers/mgo_connect.py:203-296`

**Step 1: Replace `select_jurisdiction_from_home` function**

Replace the entire function (lines 203-296) with:

```python
async def select_jurisdiction_from_home(page, city_name: str) -> bool:
    """Select jurisdiction from the home page first, then continue to search."""
    print(f'[JURISDICTION] Setting up {city_name} from home page...')

    # Go to home page first
    print('    Navigating to home page...')
    await page.goto('https://www.mgoconnect.org/cp/home', wait_until='networkidle', timeout=60000)
    await asyncio.sleep(3)

    # Select State: Texas
    print('    Selecting State: Texas...')

    # Click state dropdown and wait for it to open
    state_dropdown = page.locator('.p-dropdown').first
    await state_dropdown.click()
    await asyncio.sleep(1)

    # Select Texas
    texas_option = page.locator('.p-dropdown-item:has-text("Texas")')
    await texas_option.click()
    print('    Texas selected')

    # CRITICAL: Wait for jurisdiction dropdown to become enabled (API loads jurisdictions)
    print('    Waiting for jurisdiction dropdown to populate...')
    try:
        await page.wait_for_function('''() => {
            const dropdowns = document.querySelectorAll('.p-dropdown');
            if (dropdowns.length < 2) return false;
            // Check if second dropdown is NOT disabled
            const jurisdictionDropdown = dropdowns[1];
            return !jurisdictionDropdown.classList.contains('p-disabled') &&
                   !jurisdictionDropdown.querySelector('.p-dropdown-label')?.textContent?.includes('Select');
        }''', timeout=15000)
        print('    Jurisdiction dropdown ready')
    except Exception as e:
        print(f'    WARN: Jurisdiction dropdown wait timed out: {e}')
        # Try anyway

    await asyncio.sleep(2)

    # Select Jurisdiction
    print(f'    Selecting Jurisdiction: {city_name}...')

    # Click jurisdiction dropdown
    jurisdiction_dropdown = page.locator('.p-dropdown').nth(1)
    await jurisdiction_dropdown.click()
    await asyncio.sleep(1)

    # Type to filter (faster than scrolling through list)
    await page.keyboard.type(city_name[:4], delay=100)
    await asyncio.sleep(1)

    # Click the matching option
    city_option = page.locator(f'.p-dropdown-item:has-text("{city_name}")')
    option_count = await city_option.count()

    if option_count == 0:
        # List all available options for debugging
        options = await page.evaluate('''() => {
            return Array.from(document.querySelectorAll('.p-dropdown-item'))
                .map(el => el.textContent?.trim())
                .slice(0, 20);
        }''')
        print(f'    ERROR: {city_name} not found. Available: {options}')
        return False

    await city_option.first.click()
    print(f'    Selected: {city_name}')
    await asyncio.sleep(2)

    # Click Continue button
    print('    Clicking Continue...')
    continue_btn = page.locator('button:has-text("Continue")')
    await continue_btn.click()

    await asyncio.sleep(5)
    await page.screenshot(path=f'debug_html/mgo_{city_name.lower()}_after_continue.png')

    print(f'    Current URL: {page.url}')
    return True
```

**Step 2: Test Irving scraper**

```bash
cd /home/reid/testhome/permit-scraper && python3 scrapers/mgo_connect.py Irving 100
```

Expected: Should select Texas, wait for jurisdictions, select Irving, click Continue, then navigate to search.

**Step 3: Commit Irving fix**

```bash
cd /home/reid/testhome/permit-scraper && git add scrapers/mgo_connect.py && git commit -m "fix: Irving dropdown race condition - wait for jurisdiction list"
```

---

## Task 6: Investigate Westlake MyGov Portal

**Files:**
- Create: `scrapers/mygov_westlake.py`

**Step 1: Create exploration script**

```python
#!/usr/bin/env python3
"""
WESTLAKE MYGOV PORTAL INVESTIGATION
Purpose: Determine if Westlake's MyGov portal is scrapeable.

Known facts:
- URL: https://public.mygov.us/westlake_tx
- Same platform as Rowlett/Grapevine (marked "not scrapeable")
- High-value leads per the user

This script will:
1. Load the portal
2. Check for login requirements
3. Try to find permit search
4. Document what we find
"""

import asyncio
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright

async def investigate():
    print('=' * 60)
    print('WESTLAKE MYGOV INVESTIGATION')
    print('=' * 60)
    print(f'Time: {datetime.now().isoformat()}\n')

    findings = {
        'url': 'https://public.mygov.us/westlake_tx',
        'timestamp': datetime.now().isoformat(),
        'accessible': False,
        'requires_login': None,
        'has_permit_search': None,
        'blockers': [],
        'notes': []
    }

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 900},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        page = await context.new_page()

        Path('debug_html').mkdir(exist_ok=True)

        try:
            # Step 1: Load the portal
            print('[1] Loading Westlake MyGov portal...')
            response = await page.goto(findings['url'], timeout=30000)

            findings['status_code'] = response.status if response else None
            findings['final_url'] = page.url
            print(f'    Status: {findings["status_code"]}')
            print(f'    Final URL: {findings["final_url"]}')

            await asyncio.sleep(3)
            await page.screenshot(path='debug_html/westlake_mygov_initial.png')

            # Step 2: Check for login wall
            print('\n[2] Checking for login requirements...')
            page_text = await page.inner_text('body')

            login_indicators = ['sign in', 'log in', 'login', 'username', 'password', 'authenticate']
            has_login = any(ind in page_text.lower() for ind in login_indicators)
            findings['requires_login'] = has_login
            print(f'    Login wall detected: {has_login}')

            if has_login:
                findings['blockers'].append('Login required')

            # Step 3: Look for permit/project links
            print('\n[3] Searching for permit/project links...')
            links = await page.evaluate('''() => {
                return Array.from(document.querySelectorAll('a'))
                    .map(a => ({href: a.href, text: a.textContent?.trim()}))
                    .filter(l => l.text && l.text.length < 50);
            }''')

            permit_links = [l for l in links if any(
                kw in (l.get('text', '') + l.get('href', '')).lower()
                for kw in ['permit', 'project', 'search', 'public']
            )]

            findings['permit_related_links'] = permit_links[:10]
            print(f'    Found {len(permit_links)} permit-related links')
            for link in permit_links[:5]:
                print(f'      - {link.get("text")}: {link.get("href", "")[:60]}')

            # Step 4: Try clicking "Projects" or similar
            if permit_links:
                print('\n[4] Attempting to navigate to projects/permits...')
                for link in permit_links[:3]:
                    if 'project' in link.get('text', '').lower() or 'permit' in link.get('text', '').lower():
                        try:
                            await page.click(f'a:has-text("{link["text"]}")', timeout=5000)
                            await asyncio.sleep(3)
                            await page.screenshot(path='debug_html/westlake_mygov_projects.png')

                            # Check if we got to a search or list
                            new_text = await page.inner_text('body')
                            if 'search' in new_text.lower() or 'results' in new_text.lower():
                                findings['has_permit_search'] = True
                                findings['notes'].append(f'Found search via: {link["text"]}')
                            break
                        except Exception as e:
                            findings['notes'].append(f'Click failed: {link["text"]} - {e}')

            # Step 5: Check for heavy JS/Canvas issues
            print('\n[5] Checking for technical blockers...')
            tech_check = await page.evaluate('''() => {
                return {
                    hasCanvas: document.querySelectorAll('canvas').length > 0,
                    hasIframe: document.querySelectorAll('iframe').length > 0,
                    hasCaptcha: document.body.innerHTML.toLowerCase().includes('captcha'),
                    angularApp: typeof window.angular !== 'undefined',
                    reactApp: typeof window.React !== 'undefined' || document.querySelector('[data-reactroot]') !== null,
                };
            }''')

            findings['technical'] = tech_check
            print(f'    Canvas rendering: {tech_check["hasCanvas"]}')
            print(f'    Iframe detected: {tech_check["hasIframe"]}')
            print(f'    CAPTCHA detected: {tech_check["hasCaptcha"]}')

            if tech_check['hasCanvas']:
                findings['blockers'].append('Canvas rendering (may be difficult to scrape)')
            if tech_check['hasCaptcha']:
                findings['blockers'].append('CAPTCHA detected')

            findings['accessible'] = len(findings['blockers']) == 0

        except Exception as e:
            print(f'\nERROR: {e}')
            findings['error'] = str(e)
            findings['blockers'].append(f'Exception: {e}')
            await page.screenshot(path='debug_html/westlake_mygov_error.png')

        finally:
            await browser.close()

    # Summary
    print('\n' + '=' * 60)
    print('INVESTIGATION SUMMARY')
    print('=' * 60)
    print(f'Portal URL: {findings["url"]}')
    print(f'Accessible: {findings["accessible"]}')
    print(f'Requires Login: {findings["requires_login"]}')
    print(f'Has Permit Search: {findings["has_permit_search"]}')
    print(f'Blockers: {findings["blockers"]}')
    print(f'Notes: {findings["notes"]}')

    # Write findings
    import json
    Path('westlake_investigation.json').write_text(json.dumps(findings, indent=2))
    print(f'\nFindings saved to: westlake_investigation.json')

    # Verdict
    print('\n' + '-' * 60)
    if findings['accessible'] and findings['has_permit_search']:
        print('VERDICT: PROCEED - Portal appears scrapeable')
        print('NEXT: Build proper scraper based on findings')
    elif findings['requires_login']:
        print('VERDICT: BLOCKED - Login required')
        print('NEXT: Check if public access is available, or skip this city')
    else:
        print('VERDICT: INVESTIGATE FURTHER - See debug screenshots')
        print('NEXT: Review westlake_mygov_initial.png for manual analysis')

    return findings


if __name__ == '__main__':
    asyncio.run(investigate())
```

**Step 2: Run investigation**

```bash
cd /home/reid/testhome/permit-scraper && python3 scrapers/mygov_westlake.py
```

Expected: Will determine if Westlake MyGov is scrapeable or has blockers.

**Step 3: Review findings and decide Go/No-Go**

Check:
- `debug_html/westlake_mygov_initial.png`
- `westlake_investigation.json`

If scrapeable: Create full scraper in next task
If blocked: Document in SCRAPER_STATUS.md and skip

---

## Task 7: Update SCRAPER_STATUS.md

**Files:**
- Modify: `SCRAPER_STATUS.md`

**Step 1: Update status based on results**

Add results from testing. Example format:

```markdown
## Session: 2025-12-11

### Southlake (EnerGov CSS)
- Status: [WORKING/BLOCKED]
- Permits scraped: X
- Notes: [what worked/failed]

### Colleyville (EnerGov CSS)
- Status: [WORKING/BLOCKED]
- Permits scraped: X
- Notes: [what worked/failed]

### Irving (MGO Connect)
- Status: [WORKING/BLOCKED]
- Permits scraped: X
- Notes: [what worked/failed]

### Westlake (MyGov)
- Status: [WORKING/BLOCKED/NOT_SCRAPEABLE]
- Notes: [investigation findings]
```

**Step 2: Commit status update**

```bash
cd /home/reid/testhome/permit-scraper && git add SCRAPER_STATUS.md && git commit -m "docs: update scraper status for high-value cities"
```

---

## Execution Order

1. **Task 1**: Add Colleyville config (quick win)
2. **Task 2**: Add explicit wait (fixes Southlake timeout)
3. **Task 3**: Relax regex (gets data extracting)
4. **Task 4**: Diagnostic headed mode for Irving
5. **Task 5**: Fix Irving dropdown race condition
6. **Task 6**: Investigate Westlake (Go/No-Go decision)
7. **Task 7**: Update status documentation

## Success Criteria

- [ ] Southlake: 50+ permits scraped
- [ ] Colleyville: 50+ permits scraped
- [ ] Irving: 100+ permits scraped
- [ ] Westlake: Clear Go/No-Go decision documented
