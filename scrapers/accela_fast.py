#!/usr/bin/env python3
"""
FAST ACCELA PERMIT SCRAPER - DOM extraction (no LLM)
Extracts directly from page structure, much faster than LLM approach.
Covers: Fort Worth, Dallas

Usage:
  python scrapers/accela_fast.py fort_worth 1000
"""

import asyncio
import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

# City configurations (Same as accela.py)
ACCELA_CITIES = {
    'fort_worth': {
        'name': 'Fort Worth',
        'base_url': 'https://aca-prod.accela.com/CFW',
        'search_path': '/Cap/CapHome.aspx?module=Development&TabName=Development',
    },
    'dallas': {
        'name': 'Dallas',
        'base_url': 'https://aca-prod.accela.com/DALLASTX',
        'search_path': '/Cap/CapHome.aspx?module=Building&TabName=Home',
    },
    'grand_prairie': {
        'name': 'Grand Prairie',
        'base_url': 'https://aca-prod.accela.com/GPTX',
        'search_path': '/Cap/CapHome.aspx?module=Building&TabName=Building',
    },
    # BLOCKED: Duncanville Accela portal URL not publicly accessible
    # City has "Citizen Access Portal" mentioned on duncanvilletx.gov but no working Accela URL found
    # Tested patterns: aca-prod.accela.com/DVILLE, /DUNCANVILLE, /DUNCANVILLETX - all 404
    # May require login, use different platform, or self-hosted instance
    # Research date: 2025-12-13
    # 'duncanville': {
    #     'name': 'Duncanville',
    #     'base_url': 'https://aca-prod.accela.com/DUNCANVILLE',
    #     'search_path': '/Cap/CapHome.aspx?module=Building&TabName=Building',
    # },
}

async def extract_permits_from_page(page) -> list:
    """Extract permits directly from DOM tables - no LLM needed."""
    return await page.evaluate('''() => {
        const permits = [];
        // Look for the specific Accela data grid
        const tables = document.querySelectorAll('table[id*="gdvPermitList"], table[id*="gdvAppList"], table.aca_grid');
        
        for (const table of tables) {
            const rows = table.querySelectorAll('tr.ACA_TabRow_Odd, tr.ACA_TabRow_Even, tr[class*="TabRow"]');
            
            for (const row of rows) {
                let permit_id = null;
                let address = null;
                let permit_type = null;
                let status = null;
                let date = null;
                let description = null;

                // Priority: Try to find specific span IDs which are standard in Accela
                const idSpan = row.querySelector('span[id*="lblPermitNumber"], span[id*="lblAltId"]');
                if (idSpan) permit_id = idSpan.innerText.trim();

                const dateSpan = row.querySelector('span[id*="lblUpdatedTime"], span[id*="lblDate"], span[id*="lblFileDate"]');
                if (dateSpan) date = dateSpan.innerText.trim();

                const typeSpan = row.querySelector('span[id*="lblType"], span[id*="lblAppType"]');
                if (typeSpan) permit_type = typeSpan.innerText.trim();

                const statusSpan = row.querySelector('span[id*="lblStatus"]');
                if (statusSpan) status = statusSpan.innerText.trim();
                
                const addressSpan = row.querySelector('span[id*="lblAddress"], span[id*="lblPermitAddress"]');
                if (addressSpan) address = addressSpan.innerText.trim();
                
                const descSpan = row.querySelector('span[id*="lblShortNote"], span[id*="lblDescription"]');
                if (descSpan) description = descSpan.innerText.trim();

                // Fallback: If no IDs, try column position or regex (backup for different portal versions)
                if (!permit_id) {
                     const cells = row.querySelectorAll('td');
                     const cellTexts = Array.from(cells).map(c => c.innerText.trim());
                     for (const text of cellTexts) {
                        // Broader regex: Alphanumeric with dash, starting with digit or letter
                        if (!permit_id && /^[A-Z0-9]{2,}-[A-Z0-9]+/.test(text) && text.length < 25) {
                            permit_id = text;
                        }
                     }
                }

                if (permit_id) {
                    permits.push({
                        permit_id: permit_id,
                        address: address || '',
                        type: permit_type || '',
                        status: status || '',
                        date: date || '',
                        description: description || ''
                    });
                }
            }
        }
        return permits;
    }''')


async def scrape_fast(city_key: str, target_count: int = 1000):
    """Fast scrape using DOM extraction."""
    city_key = city_key.lower()
    if city_key not in ACCELA_CITIES:
        print(f'ERROR: Unknown city. Available: {list(ACCELA_CITIES.keys())}')
        sys.exit(1)

    config = ACCELA_CITIES[city_key]
    base_url = config['base_url']
    search_path = config['search_path']

    print('=' * 60)
    print(f'{config["name"].upper()} FAST PERMIT SCRAPER (Accela)')
    print('=' * 60)
    print(f'Target: {target_count} permits')
    print(f'Time: {datetime.now().isoformat()}\n')

    all_permits = []
    errors = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1280, 'height': 900})
        page = await context.new_page()

        try:
            print(f'[1] Loading search page...')
            # Use domcontentloaded + longer wait (like accela.py) - networkidle completes too early
            await page.goto(f'{base_url}{search_path}', wait_until='domcontentloaded', timeout=120000)
            await asyncio.sleep(8)  # Dallas needs longer wait for JS to render

            # Handle welcome page redirection if needed (Accela)
            if '/Default.aspx' in page.url:
                 # Logic to click "Search" or similar
                 print('    Redirected to Welcome page, trying to navigate to search...')
                 await page.evaluate('''() => {
                     const links = document.querySelectorAll('a');
                     for (const link of links) {
                         const href = (link.href || '').toLowerCase();
                         if (href.includes('caphome') || href.includes('module=development') || href.includes('module=building')) {
                             link.click();
                             return;
                         }
                     }
                 }''')
                 await asyncio.sleep(4)

            # Set date filter (Last 3 months to be safe)
            print('[2] Setting date filter (last 90 days)...')
            start_date = (datetime.now() - timedelta(days=90)).strftime('%m/%d/%Y')
            end_date = datetime.now().strftime('%m/%d/%Y')

            await page.evaluate(f'''() => {{
                // Try generalized date field finding
                const inputs = document.querySelectorAll('input[type="text"]');
                let foundStart = false;
                for (const input of inputs) {{
                    const id = input.id.toLowerCase();
                    if (id.includes('startdate') || id.includes('fromdate')) {{
                        input.value = '{start_date}';
                        input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        foundStart = true;
                    }} else if (id.includes('enddate') || id.includes('todate')) {{
                        input.value = '{end_date}';
                        input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    }}
                }}
                if (!foundStart) console.log("WARN: Could not find date fields");
            }}''')
            await asyncio.sleep(1)

            # Click Search - use native Playwright click to properly trigger ASP.NET postback
            print('[3] Clicking Search...')
            search_clicked = None

            # Try specific Accela search button selectors (native click triggers __doPostBack properly)
            search_selectors = [
                '#ctl00_PlaceHolderMain_btnNewSearch',
                'a[id*="btnNewSearch"]',
                'a[id*="btnSearch"]:not(.ButtonDisabled)',
                'a.ACA_LgButton[title*="Search"]',
            ]

            for selector in search_selectors:
                try:
                    btn = await page.query_selector(selector)
                    if btn:
                        await btn.click()
                        search_clicked = selector
                        break
                except:
                    continue

            # Fallback: Find by text content
            if not search_clicked:
                btns = await page.query_selector_all('a.ACA_LgButton, input[type="submit"], button')
                for btn in btns:
                    text = await btn.inner_text() or ''
                    if 'search' in text.lower() and 'clear' not in text.lower():
                        await btn.click()
                        search_clicked = f'text:{text}'
                        break

            print(f'    Clicked: {search_clicked}')

            # Wait for network activity to settle after search click
            await page.wait_for_load_state('networkidle', timeout=30000)

            # Wait for search results - try multiple strategies
            try:
                # Wait for results table to appear (preferred)
                await page.wait_for_selector('table[id*="gdvPermitList"], table[id*="gdvAppList"], tr.ACA_TabRow_Odd', timeout=30000)
                print('    Results table found!')
            except PlaywrightTimeout:
                print('    WARN: Results table not found within 30s, trying longer wait...')
                await asyncio.sleep(15)  # Fallback longer wait

            print(f'[4] Extracting results...')
            page_num = 1
            
            while len(all_permits) < target_count:
                # Extract permits
                print('    Extracting results...')
                # Wait for the table to appear definitely
                try:
                    await page.wait_for_selector('table[id*="gdvPermitList"], table[id*="gdvAppList"], table.aca_grid', timeout=10000)
                except PlaywrightTimeout:
                    print("    WARN: Table not found after waiting.")
                
                permits = await extract_permits_from_page(page)
                if not permits:
                    print('    No permits found on this page.')
                    # Check if searching/loading
                    if await page.query_selector('.aca_loading'):
                        print('    Still loading...')
                        await asyncio.sleep(2)
                        continue
                    break
                
                # Check for duplicates to avoid infinite loops if pagination fails
                new_permits = [p for p in permits if p['permit_id'] not in [ap['permit_id'] for ap in all_permits]]
                all_permits.extend(new_permits)
                print(f'    Page {page_num}: +{len(new_permits)} new permits ({len(all_permits)} total)')

                if len(all_permits) >= target_count:
                    break

                # Before clicking, capture first permit ID to detect stale DOM
                first_permit_before = await page.evaluate('''() => {
                    const firstRow = document.querySelector('tr.ACA_TabRow_Odd, tr.ACA_TabRow_Even');
                    if (firstRow) {
                        const idSpan = firstRow.querySelector('span[id*="lblPermitNumber"], span[id*="lblAltId"]');
                        return idSpan ? idSpan.innerText.trim() : null;
                    }
                    return null;
                }''')

                # Next page - robust selector for Accela pagination
                has_next = await page.evaluate('''() => {
                    // Find Next link in pagination
                    const nextLinks = document.querySelectorAll('td.aca_pagination_PrevNext a, a[href*="Page$Next"]');
                    for (const link of nextLinks) {
                         const text = link.innerText || link.textContent;
                         if (text.includes('Next') || text.includes('>')) {
                             link.click();
                             return true;
                         }
                    }
                    return false;
                }''')

                if not has_next:
                    print('    No more pages.')
                    break

                # Wait for network response
                try:
                    await page.wait_for_response(
                        lambda r: 'CapHome.aspx' in r.url and r.status == 200,
                        timeout=15000
                    )
                except:
                    pass  # Response might complete before we start waiting

                # Wait for loading spinner to disappear (if present)
                try:
                    await page.wait_for_selector('.aca_loading', state='hidden', timeout=10000)
                except:
                    pass

                # Wait for content to actually change (critical!)
                content_changed = False
                for _ in range(10):  # Max 10 attempts, 1s each
                    await asyncio.sleep(1)
                    first_permit_after = await page.evaluate('''() => {
                        const firstRow = document.querySelector('tr.ACA_TabRow_Odd, tr.ACA_TabRow_Even');
                        if (firstRow) {
                            const idSpan = firstRow.querySelector('span[id*="lblPermitNumber"], span[id*="lblAltId"]');
                            return idSpan ? idSpan.innerText.trim() : null;
                        }
                        return null;
                    }''')
                    if first_permit_after != first_permit_before:
                        content_changed = True
                        break

                if not content_changed:
                    print('    WARN: Page content did not change after clicking Next')
                    break

                page_num += 1

        except Exception as e:
            print(f'\nERROR: {e}')
            errors.append(str(e))
            await page.screenshot(path='debug_html/accela_fast_error.png')

        finally:
            await browser.close()

    # Save
    output = {
        'source': city_key,
        'portal_type': 'Accela',
        'scraped_at': datetime.now().isoformat(),
        'target_count': target_count,
        'actual_count': len(all_permits),
        'permits': all_permits[:target_count]
    }
    
    output_file = f'{city_key}_raw.json'
    Path(output_file).write_text(json.dumps(output, indent=2))
    print(f'\nSaved {len(all_permits)} permits to {output_file}')

if __name__ == '__main__':
    city = sys.argv[1] if len(sys.argv) > 1 else 'fort_worth'
    count = int(sys.argv[2]) if len(sys.argv) > 2 else 1000
    asyncio.run(scrape_fast(city, count))
