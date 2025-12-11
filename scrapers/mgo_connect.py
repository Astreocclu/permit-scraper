#!/usr/bin/env python3
"""
MGO CONNECT PERMIT SCRAPER (Playwright Python)
Portal: My Government Online (MGO Connect)
Covers: Irving, Lewisville, Denton, Cedar Hill, and more DFW cities

Requires login - credentials from .env:
  MGO_EMAIL, MGO_PASSWORD

Usage:
  python scrapers/mgo_connect.py Irving 1000
  python scrapers/mgo_connect.py Lewisville 1000
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import httpx
from dotenv import load_dotenv
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

# Load environment variables
load_dotenv()

# City JID mappings (jurisdiction IDs)
# To find JID: Go to mgoconnect.org, select state/city, check URL parameter
MGO_CITIES = {
    # DFW Metro - Verified
    'Irving': 245,
    'Lewisville': 325,
    'Denton': 285,
    'Cedar Hill': 305,
    'CedarHill': 305,
    'Duncanville': 253,
    # DFW Metro - Need verification
    'Lancaster': 0,  # TODO: Find JID
    'Balch Springs': 0,  # TODO: Find JID
    'BalchSprings': 0,
    'Sachse': 0,  # TODO: Find JID
    # Central Texas
    'Georgetown': 0,  # TODO: Find JID
    'Temple': 0,
    'Killeen': 0,
    'San Marcos': 0,
    'SanMarcos': 0,
    # North Texas
    'Celina': 0,
    'Lucas': 0,
    'Pilot Point': 0,
    'PilotPoint': 0,
    'Van Alstyne': 0,
    'VanAlstyne': 0,
    # West Texas
    'Amarillo': 0,
    'Wichita Falls': 0,
    'WichitaFalls': 0,
}

DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
MGO_EMAIL = os.getenv('MGO_EMAIL')
MGO_PASSWORD = os.getenv('MGO_PASSWORD')

# Permit types to EXCLUDE (garbage)
EXCLUDED_PERMIT_TYPES = {
    'garage sale', 'code enforcement', 'complaint', 'rental', 'license',
    'pre-development', 'conference', 'sign', 'billboard', 'commercial',
    'environmental', 'health', 'zoning', 'variance', 'planning', 'subdivision',
    'right-of-way', 'row', 'encroachment', 'special event', 'food', 'alcohol',
}


def is_valid_permit_type(permit_type: str) -> bool:
    """Check if permit type is one we want (not garbage)."""
    if not permit_type:
        return True

    permit_type_lower = permit_type.lower()

    for excluded in EXCLUDED_PERMIT_TYPES:
        if excluded in permit_type_lower:
            return False

    return True


def filter_permits(permits: list) -> tuple[list, dict]:
    """Filter out garbage permit types."""
    valid = []
    stats = {'bad_type': 0, 'empty': 0, 'total_rejected': 0}

    for p in permits:
        permit_type = p.get('type', '')
        permit_id = p.get('permit_id', '')

        if not permit_id and not p.get('address'):
            stats['empty'] += 1
            stats['total_rejected'] += 1
        elif not is_valid_permit_type(permit_type):
            stats['bad_type'] += 1
            stats['total_rejected'] += 1
        else:
            valid.append(p)

    return valid, stats


async def call_deepseek(prompt: str) -> str:
    """Call DeepSeek API for extraction."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            'https://api.deepseek.com/v1/chat/completions',
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {DEEPSEEK_API_KEY}'
            },
            json={
                'model': 'deepseek-chat',
                'messages': [{'role': 'user', 'content': prompt}],
                'temperature': 0.1,
                'max_tokens': 4000
            },
            timeout=60.0
        )
        data = response.json()
        return data.get('choices', [{}])[0].get('message', {}).get('content', '')


def parse_json(text: str) -> dict | None:
    """Parse JSON from text, handling markdown code blocks."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    import re
    match = re.search(r'```(?:json)?\s*([\s\S]*?)```', text) or re.search(r'(\{[\s\S]*\})', text)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    return None


async def login(page) -> bool:
    """Login to MGO Connect."""
    print('[LOGIN] Navigating to login page...')
    await page.goto('https://www.mgoconnect.org/cp/login', wait_until='networkidle', timeout=60000)
    await asyncio.sleep(2)

    # Check if already logged in
    if 'login' not in page.url:
        print('[LOGIN] Already logged in')
        return True

    print('[LOGIN] Entering credentials...')

    # Fill email
    try:
        await page.wait_for_selector('input[type="email"]', timeout=10000)
        await page.fill('input[type="email"]', MGO_EMAIL)
        print('[LOGIN] Email entered')
    except PlaywrightTimeout:
        print('[LOGIN] Could not find email field')
        return False

    # Fill password
    try:
        await page.fill('input[type="password"]', MGO_PASSWORD)
        print('[LOGIN] Password entered')
    except PlaywrightTimeout:
        print('[LOGIN] Could not find password field')
        return False

    # Click login button using locator
    print('[LOGIN] Clicking login button...')
    try:
        login_btn = page.locator('button:has-text("Login")').first
        await login_btn.click(timeout=5000)
    except Exception:
        # Fallback to JS click
        await page.evaluate('''() => {
            const buttons = document.querySelectorAll('button');
            for (const btn of buttons) {
                if (btn.textContent?.toLowerCase().includes('login')) {
                    btn.click();
                    return;
                }
            }
        }''')

    await asyncio.sleep(5)

    if 'login' in page.url:
        print('[LOGIN] FAILED - still on login page')
        await page.screenshot(path='debug_html/mgo_login_failed.png', full_page=True)
        return False

    print('[LOGIN] SUCCESS')
    return True


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


async def scrape(city_name: str, target_count: int = 1000):
    """Scrape permits from MGO Connect for a given city."""
    print('=' * 60)
    print(f'MGO CONNECT SCRAPER - {city_name.upper()}')
    print('=' * 60)
    print(f'Target: {target_count} permits')
    print(f'Time: {datetime.now().isoformat()}\n')

    # Validate inputs
    if not MGO_EMAIL or not MGO_PASSWORD:
        print('ERROR: MGO_EMAIL and MGO_PASSWORD must be set in .env')
        sys.exit(1)

    jid = MGO_CITIES.get(city_name)
    if jid is None:
        print(f'ERROR: Unknown city "{city_name}". Available: {", ".join(MGO_CITIES.keys())}')
        sys.exit(1)

    permits = []
    errors = []
    api_data = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1400, 'height': 900},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        page = await context.new_page()

        # Set up API response capture from the start - capture ALL API calls for debugging
        async def handle_response(response):
            url = response.url
            # Capture any API call
            if '/api/' in url and response.status == 200:
                # Skip static assets and charts
                if '.js' not in url and '.css' not in url and 'chart' not in url.lower():
                    try:
                        data = await response.json()
                        # Look for project/permit data
                        if isinstance(data, dict):
                            # Check for common response formats
                            items = data.get('data', data.get('results', data.get('items', data.get('projects', []))))
                            if isinstance(items, list) and len(items) > 0:
                                # Only add if items have permit-like fields
                                sample = items[0] if items else {}
                                if any(k in str(sample).lower() for k in ['project', 'permit', 'address', 'worktype']):
                                    api_data.extend(items)
                        elif isinstance(data, list) and len(data) > 0:
                            sample = data[0] if data else {}
                            if any(k in str(sample).lower() for k in ['project', 'permit', 'address', 'worktype']):
                                api_data.extend(data)
                    except Exception as e:
                        pass  # Not JSON or parsing error

        page.on('response', handle_response)

        try:
            # Step 1: Login
            print('[1] Logging in...')
            if not await login(page):
                raise Exception('Login failed')

            # Step 2: Select jurisdiction from home page (this sets the session)
            print('\n[2] Setting up jurisdiction...')
            if not await select_jurisdiction_from_home(page, city_name):
                raise Exception('Failed to select jurisdiction from home')

            # Step 3: Navigate to Search Permits page and click Search
            print('\n[3] Navigating to Search Permits page...')

            # Click "Search Permits" link on the portal home
            search_permits_link = page.locator('a:has-text("Search Permits")')
            link_count = await search_permits_link.count()
            print(f'    Found {link_count} "Search Permits" links')

            if link_count > 0:
                await search_permits_link.first.click(timeout=10000)
                await asyncio.sleep(5)
            else:
                # Try direct navigation
                await page.goto('https://mgoconnect.org/cp/search', wait_until='networkidle', timeout=60000)
                await asyncio.sleep(5)

            print(f'    Current URL: {page.url}')
            await page.screenshot(path=f'debug_html/mgo_{city_name.lower()}_search_page.png', full_page=True)

            # Step 4: Execute search with date filter and export to Excel
            print('\n[4] Executing search with date filter and Excel export...')

            # Wait for page to stabilize
            await asyncio.sleep(2)

            # Fill in "Created After" date (30 days ago) to limit search
            created_after_date = datetime.now() - timedelta(days=30)
            created_after_str = created_after_date.strftime('%m/%d/%Y')
            print(f'    Setting Created After date: {created_after_str}')

            # Find the "Created After" date input
            created_after_input = page.locator('input[placeholder="Created After"], input[name*="createdAfter"]').first
            if await created_after_input.count() > 0:
                await created_after_input.fill(created_after_str)
                print(f'    Filled Created After: {created_after_str}')
                await asyncio.sleep(1)

            # Check the EXCEL checkbox for export
            excel_checkbox = page.locator('input[type="checkbox"][id*="excel"], input[type="checkbox"] + label:has-text("EXCEL")').first
            if await excel_checkbox.count() > 0:
                print('    Checking EXCEL checkbox...')
                await excel_checkbox.check()
                await asyncio.sleep(0.5)

            # Click the Export button (not Search)
            export_btn = page.locator('button:has-text("Export")').first
            if await export_btn.count() > 0:
                print('    Clicking Export button...')
                await export_btn.click(timeout=10000)
                await asyncio.sleep(5)  # Wait for export to process
            else:
                # If no Export button, click Search
                search_btn = page.locator('button:has-text("Search")').first
                print('    Clicking Search button...')
                await search_btn.click(timeout=10000)
                await asyncio.sleep(10)

            await page.screenshot(path=f'debug_html/mgo_{city_name.lower()}_after_search_click.png', full_page=True)
            print(f'    NOTE: MGO Connect search may require manual interaction or downloads may go to browser downloads folder.')
            print(f'    Current URL: {page.url}')

            # Clear the api_data before searching
            api_data.clear()

            # Check if any new API calls were made
            print(f'    API data captured after stat click: {len(api_data)} items')

            # Check the pagination again
            results_info = await page.evaluate('''() => {
                const bodyText = document.body.innerText;
                const match = bodyText.match(/Showing (\d+) to (\d+) of (\d+)/);
                const rows = document.querySelectorAll('tbody tr');
                return {
                    pagination: match ? { from: match[1], to: match[2], total: match[3] } : null,
                    rowCount: rows.length
                };
            }''')
            print(f'    After stat click: pagination={results_info.get("pagination")}, rows={results_info.get("rowCount")}')

            # If still no data, try searching directly with a broad search
            if len(api_data) == 0 and results_info.get('pagination', {}).get('total', '0') == '0':
                print('    No data from stat click, trying direct search...')

                # Look for search inputs on the current search page
                search_input = page.locator('input[placeholder*="search"], input[type="search"], input[name*="search"]').first
                if await search_input.count() > 0:
                    print('    Found search input, searching for all permits...')
                    # Clear any existing search and hit Enter to show all
                    await search_input.clear()
                    await search_input.press('Enter')
                    await asyncio.sleep(5)

                    # Check if this loaded data
                    new_results = await page.evaluate('''() => {
                        const rows = document.querySelectorAll('.p-datatable-tbody tr, table tbody tr');
                        return rows.length;
                    }''')
                    print(f'    After search: {new_results} rows visible')
                else:
                    # Try the advanced reporting approach
                    print('    Trying Advanced Reporting -> Open Records Data Export...')

                    advanced_link = page.locator('text=Click here for advanced reporting')
                    if await advanced_link.count() > 0:
                        await advanced_link.click(timeout=5000)
                        await asyncio.sleep(3)

                        # Look for different report options - try the LAST button (Open Records Data Export)
                        view_btns = page.locator('button:has-text("View Report")')
                        btn_count = await view_btns.count()
                        print(f'    Found {btn_count} View Report buttons, trying the last one...')

                        if btn_count > 0:
                            # Click the LAST one (Open Records Data Export by Address) - more likely to have tabular data
                            await view_btns.last.click(timeout=10000)
                            await asyncio.sleep(5)

                            await page.screenshot(path=f'debug_html/mgo_{city_name.lower()}_export_page.png', full_page=True)
                            print(f'    Export page URL: {page.url}')

                            # This is a PDF export page - fill dates and get the PDF
                            # Calculate dates: 30 days ago to today
                            end_date = datetime.now()
                            start_date = end_date - timedelta(days=30)
                            print(f'    Filling dates: {start_date.strftime("%m/%d/%Y")} to {end_date.strftime("%m/%d/%Y")}')

                            # Fill date inputs
                            date_inputs = await page.locator('.p-calendar input').count()
                            if date_inputs >= 2:
                                # Start date
                                await page.locator('.p-calendar input').first.click()
                                await asyncio.sleep(0.5)
                                if start_date.month != end_date.month:
                                    await page.locator('.p-datepicker-prev').first.click()
                                    await asyncio.sleep(0.3)
                                await page.locator(f'.p-datepicker-calendar td span:has-text("{start_date.day}")').first.click()
                                await asyncio.sleep(0.5)

                                # End date
                                await page.locator('.p-calendar input').nth(1).click()
                                await asyncio.sleep(0.5)
                                await page.locator(f'.p-datepicker-calendar td span:has-text("{end_date.day}")').first.click()
                                await asyncio.sleep(1)

                                print('    NOTE: This report exports to PDF. Irving MGO Connect does not provide CSV/Excel export.')
                                print('    Skipping PDF export - no permit data can be extracted from this portal.')

            # Step 5: Extract data from the results table
            print('\n[5] Extracting permit data from table...')

            # Try to extract from the visible table
            table_data = await page.evaluate('''() => {
                const results = [];

                // Try PrimeNG datatable
                const rows = document.querySelectorAll('.p-datatable-tbody tr, table tbody tr');

                for (const row of rows) {
                    const cells = row.querySelectorAll('td');
                    if (cells.length >= 2) {
                        // Get all cell values
                        const rowData = Array.from(cells).map(c => c.textContent?.trim());
                        results.push(rowData);
                    }
                }

                return results;
            }''')

            print(f'    Extracted {len(table_data)} rows from table')

            if table_data and len(table_data) > 0:
                print(f'    Sample row: {table_data[0] if table_data else "none"}')

                # Parse table rows into permits
                for row in table_data:
                    if len(row) >= 2:
                        # Try to identify columns - typically: Project#, Address, Type, Status, Date
                        permit = {
                            'permit_id': row[0] if row else '',
                            'address': row[1] if len(row) > 1 else '',
                            'type': row[2] if len(row) > 2 else '',
                            'status': row[3] if len(row) > 3 else '',
                            'date': row[4] if len(row) > 4 else '',
                            'description': row[5] if len(row) > 5 else '',
                        }
                        if permit['permit_id'] or permit['address']:
                            api_data.append(permit)

            # Step 6: Paginate to get more results
            print(f'\n[6] Collecting more permits (target: {target_count})...')
            page_num = 1
            max_pages = (target_count // 10) + 5  # Estimate pages needed (10 per page typical)

            while len(api_data) < target_count and page_num < max_pages:
                print(f'    Page {page_num}: {len(api_data)} permits collected')

                # Look for next page button
                next_btn = page.locator('.p-paginator-next:not(.p-disabled), button[aria-label="Next Page"]:not([disabled])')
                next_count = await next_btn.count()

                if next_count == 0:
                    print('    No more pages available')
                    break

                # Check if next button is disabled
                is_disabled = await page.evaluate('''() => {
                    const nextBtn = document.querySelector('.p-paginator-next, button[aria-label="Next Page"]');
                    return nextBtn ? (nextBtn.disabled || nextBtn.classList.contains('p-disabled')) : true;
                }''')

                if is_disabled:
                    print('    Next button is disabled')
                    break

                # Click next
                await next_btn.first.click(timeout=5000)
                await asyncio.sleep(3)

                # Extract data from new page
                new_rows = await page.evaluate('''() => {
                    const results = [];
                    const rows = document.querySelectorAll('.p-datatable-tbody tr, table tbody tr');
                    for (const row of rows) {
                        const cells = row.querySelectorAll('td');
                        if (cells.length >= 2) {
                            results.push(Array.from(cells).map(c => c.textContent?.trim()));
                        }
                    }
                    return results;
                }''')

                for row in new_rows:
                    if len(row) >= 2:
                        permit = {
                            'permit_id': row[0] if row else '',
                            'address': row[1] if len(row) > 1 else '',
                            'type': row[2] if len(row) > 2 else '',
                            'status': row[3] if len(row) > 3 else '',
                            'date': row[4] if len(row) > 4 else '',
                        }
                        if permit['permit_id'] or permit['address']:
                            api_data.append(permit)

                page_num += 1

            print(f'    Total permits collected: {len(api_data)}')

            # Step 8: Process permits
            print('\n[8] Processing permits...')
            print(f'    Total API data items to process: {len(api_data)}')
            if len(api_data) > 0:
                print(f'    Sample item keys: {list(api_data[0].keys()) if isinstance(api_data[0], dict) else "not a dict"}')
                print(f'    Sample item: {api_data[0]}')

            raw_permits = []
            seen_ids = set()

            for item in api_data:
                # Handle both API response format and table extraction format
                permit_id = (item.get('projectNumber') or item.get('projectID') or
                           item.get('permit_id', '')) if isinstance(item, dict) else ''

                if permit_id and permit_id not in seen_ids:
                    seen_ids.add(permit_id)
                    raw_permits.append({
                        'permit_id': permit_id,
                        'address': item.get('projectAddress') or item.get('address', ''),
                        'type': item.get('workType') or item.get('type', ''),
                        'designation': item.get('designation', ''),
                        'status': item.get('projectStatus') or item.get('status', ''),
                        'date': item.get('dateCreated') or item.get('date', ''),
                        'description': (item.get('projectDescription') or item.get('projectName') or
                                      item.get('description', '')),
                        'contractor': item.get('contractorName') or item.get('contractor', '')
                    })
                elif not permit_id and item.get('address'):
                    # If no permit_id but has address, still include it with address as identifier
                    addr = item.get('address') or item.get('projectAddress', '')
                    if addr and addr not in seen_ids:
                        seen_ids.add(addr)
                        raw_permits.append({
                            'permit_id': '',
                            'address': addr,
                            'type': item.get('workType') or item.get('type', ''),
                            'designation': item.get('designation', ''),
                            'status': item.get('projectStatus') or item.get('status', ''),
                            'date': item.get('dateCreated') or item.get('date', ''),
                            'description': (item.get('projectDescription') or item.get('projectName') or
                                          item.get('description', '')),
                            'contractor': item.get('contractorName') or item.get('contractor', '')
                        })

            print(f'    Unique permits: {len(raw_permits)}')

            # Filter out garbage permit types
            valid_permits, filter_stats = filter_permits(raw_permits)

            if filter_stats['total_rejected'] > 0:
                print(f'    Filtered out {filter_stats["total_rejected"]}: '
                      f'{filter_stats["bad_type"]} bad type, '
                      f'{filter_stats["empty"]} empty')

            permits = valid_permits[:target_count]
            print(f'    Final count: {len(permits)} valid permits')

        except Exception as e:
            print(f'\nFATAL ERROR: {e}')
            import traceback
            traceback.print_exc()
            errors.append({'step': 'main', 'error': str(e)})
            await page.screenshot(path=f'debug_html/mgo_{city_name.lower()}_error.png', full_page=True)

        finally:
            await browser.close()

    # Save results
    output = {
        'source': city_name.lower(),
        'portal_type': 'MGO_Connect',
        'jid': MGO_CITIES.get(city_name),
        'scraped_at': datetime.now().isoformat(),
        'target_count': target_count,
        'actual_count': len(permits),
        'with_contractor': len([p for p in permits if p.get('contractor')]),
        'errors': errors,
        'permits': permits[:target_count]
    }

    # Save to data/exports directory
    output_dir = Path(__file__).parent.parent / 'data' / 'exports'
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f'{city_name.lower()}_mgo_raw.json'
    output_file.write_text(json.dumps(output, indent=2))

    print('\n' + '=' * 50)
    print('SUMMARY')
    print('=' * 50)
    print(f'City: {city_name}')
    print(f'Permits scraped: {output["actual_count"]}')
    print(f'With contractor: {output["with_contractor"]}')
    print(f'Errors: {len(errors)}')
    print(f'Output: {output_file}')

    if errors:
        print('\nERRORS:')
        for e in errors:
            print(f'  - {e["step"]}: {e["error"]}')

    if permits:
        print('\nSAMPLE PERMITS:')
        for p in permits[:5]:
            print(f'  {p["permit_id"]} | {p.get("type", "unknown")} | {p.get("address", "no address")}')

    return output


if __name__ == '__main__':
    city_arg = sys.argv[1] if len(sys.argv) > 1 else 'Irving'
    count_arg = int(sys.argv[2]) if len(sys.argv) > 2 else 1000
    asyncio.run(scrape(city_arg, count_arg))
