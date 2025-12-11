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
    """Extract permits from CityView search results page."""
    return await page.evaluate('''() => {
        const permits = [];
        const seen = new Set();

        // Find all text nodes that contain permit data
        // Use a tree walker to iterate through all text content
        const allText = document.body.innerText || document.body.textContent;

        // Split by "Application Number:" to get individual permit blocks
        const blocks = allText.split('Application Number:');

        for (let i = 1; i < blocks.length; i++) {  // Skip first split (before first permit)
            const text = 'Application Number:' + blocks[i];

            // Take only the first ~500 chars (one permit's worth of data)
            const permitText = text.substring(0, 600);

            let permit_id = '';
            let address = '';
            let permit_type = '';
            let status = '';

            // Extract Application Number (first line after "Application Number:")
            const appNumMatch = permitText.match(/Application Number:\\s*([^\\n]+)/);
            if (appNumMatch) permit_id = appNumMatch[1].trim();

            // Skip if no permit ID or already seen
            if (!permit_id || seen.has(permit_id)) continue;
            seen.add(permit_id);

            // Extract Permit Type
            const typeMatch = permitText.match(/Permit Type:\\s*([^\\n]+)/);
            if (typeMatch) permit_type = typeMatch[1].trim();

            // Extract Status
            const statusMatch = permitText.match(/Status:\\s*([^\\n]+)/);
            if (statusMatch) status = statusMatch[1].trim();

            // Extract Address or Location
            let addrMatch = permitText.match(/Address:\\s*([^\\n]+)/);
            if (addrMatch) {
                address = addrMatch[1].trim();
            } else {
                addrMatch = permitText.match(/Locations?:\\s*([^\\n]+)/);
                if (addrMatch) address = addrMatch[1].trim();
            }

            permits.push({
                permit_id: permit_id,
                address: address,
                type: permit_type,
                status: status,
                date: '',
                raw_text: permitText.substring(0, 300)
            });
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
                            items = data.get('data', data.get('results', data.get('permits', [])))
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

            # Step 2: Try to search - use address search with autocomplete
            print('\n[2] Attempting search...')

            # Try typing a search term that will return many results
            try:
                # Fill in search box with a year to match permit numbers
                search_box = await page.query_selector('input[type="text"]')
                if search_box:
                    # Try typing "2025" to match recent permit numbers
                    await search_box.type('2025', delay=100)
                    print('    Typed "2025" to search for recent permits')
                    await asyncio.sleep(3)  # Wait for autocomplete

                    # Check if autocomplete list appeared
                    autocomplete_check = await page.evaluate('''() => {
                        const lists = document.querySelectorAll('ul.ui-autocomplete, .autocomplete-results, [role="listbox"]');
                        for (const list of lists) {
                            if (list.children.length > 0) {
                                const firstItem = list.children[0];
                                firstItem.click();
                                return { success: true, clicked: firstItem.textContent };
                            }
                        }
                        return { success: false };
                    }''')
                    print(f'    Autocomplete result: {autocomplete_check}')

                    if autocomplete_check.get('success'):
                        await asyncio.sleep(2)
                    else:
                        # No autocomplete, try clicking Go
                        go_button = await page.query_selector('button:has-text("Go!"), input[value*="Go"]')
                        if go_button:
                            await go_button.click()
                            print('    Clicked Go! button')
                        else:
                            await search_box.press('Enter')
                            print('    Pressed Enter')

                    # Wait for "Please Wait" dialog to appear and disappear
                    print('    Waiting for search to complete...')
                    try:
                        # Wait for loading indicator to disappear (max 60 seconds)
                        await page.wait_for_selector('text="Please Wait"', timeout=5000)
                        print('    Loading dialog appeared')
                        await page.wait_for_selector('text="Please Wait"', state='hidden', timeout=60000)
                        print('    Loading dialog disappeared')
                    except:
                        print('    No loading dialog or already complete')

                    await asyncio.sleep(3)
                else:
                    print('    ERROR: Could not find search input')
            except Exception as e:
                print(f'    Search error: {e}')

            await page.screenshot(path=f'debug_html/cityview_{city_key}_after_search.png', full_page=True)

            # Step 3: Extract results from DOM
            print('\n[3] Extracting permits from page...')

            # Extract from DOM (primary method for CityView)
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
