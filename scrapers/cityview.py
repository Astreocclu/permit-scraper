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

# Output directory for raw JSON
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "raw"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

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


async def do_search(page, search_term: str) -> list:
    """Execute a single search and extract permits."""
    permits = []

    try:
        # Clear and fill search box (id="searchValue")
        search_box = await page.query_selector('#searchValue, input[type="text"]')
        if not search_box:
            return []

        # Clear existing text
        await search_box.click()
        await page.keyboard.press('Control+a')
        await page.keyboard.press('Backspace')
        await asyncio.sleep(0.3)

        # Type search term
        await search_box.type(search_term, delay=50)
        await asyncio.sleep(2)

        # Click Go button (it's an input with id="bsearch")
        go_button = await page.query_selector('#bsearch, input[value="Go!"]')
        if go_button:
            await go_button.click()
        else:
            await search_box.press('Enter')

        # Wait for loading
        try:
            await page.wait_for_selector('text="Please Wait"', timeout=3000)
            await page.wait_for_selector('text="Please Wait"', state='hidden', timeout=30000)
        except:
            pass

        await asyncio.sleep(2)

        # Extract permits
        permits = await extract_permits_from_page(page)

    except Exception as e:
        print(f'      Search error for "{search_term}": {e}')

    return permits


async def scrape(city_key: str, target_count: int = 100):
    """Scrape permits from CityView portal using multiple granular searches."""
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

    all_permits = []
    seen_ids = set()
    errors = []

    # Granular search terms - streets, permit types, years, etc.
    search_terms = [
        # Years (permit numbers often contain year)
        '2025', '2024', '2023', '2022', '2021', '2020',
        # Permit type prefixes
        'PRBD', 'PREL', 'PRPL', 'PRMH', 'PRRO', 'PRFR', 'PRSG', 'PRDE', 'PRPO', 'PRFE',
        'BD', 'EL', 'PL', 'MH', 'RO', 'FR', 'SG', 'DE', 'PO', 'FE',
        # Common street names in Carrollton
        'Main', 'Keller', 'Belt Line', 'Josey', 'Hebron', 'Trinity',
        'Frankford', 'Marsh', 'Rosemeade', 'Valley View', 'Whitlock',
        'Broadway', 'Jackson', 'Peters Colony', 'Crosby', 'Country Club',
        'Luna', 'Denton', 'Park', 'Old Denton', 'Kelly',
        # Street types
        'Dr', 'Ln', 'Ct', 'Cir', 'Way', 'Pl', 'Blvd',
        # Numbers (address starts)
        '1', '2', '3', '4', '5', '6', '7', '8', '9',
        '10', '11', '12', '13', '14', '15', '16', '17', '18', '19',
        '20', '21', '22', '23', '24', '25',
        '100', '200', '300', '400', '500', '600', '700', '800', '900',
        '1000', '1100', '1200', '1300', '1400', '1500', '1600', '1700', '1800', '1900',
        '2000', '2100', '2200', '2300', '2400', '2500', '2600', '2700', '2800', '2900',
        '3000', '3100', '3200', '3300', '3400', '3500',
    ]

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1400, 'height': 900},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        page = await context.new_page()

        try:
            # Load search page
            print('[1] Loading CityView search page...')
            await page.goto(config['search_url'], wait_until='networkidle', timeout=60000)
            await asyncio.sleep(3)
            print(f'    URL: {page.url}')

            Path('debug_html').mkdir(exist_ok=True)

            # Execute multiple searches
            print(f'\n[2] Running {len(search_terms)} granular searches...')

            for i, term in enumerate(search_terms):
                if len(all_permits) >= target_count:
                    print(f'\n    Reached target of {target_count} permits')
                    break

                permits = await do_search(page, term)

                # Add only new permits
                new_count = 0
                for p in permits:
                    pid = p.get('permit_id', '')
                    if pid and pid not in seen_ids:
                        seen_ids.add(pid)
                        all_permits.append(p)
                        new_count += 1

                if new_count > 0:
                    print(f'    [{i+1}/{len(search_terms)}] "{term}": +{new_count} new ({len(all_permits)} total)')

                # Save periodically (every 50 permits)
                if len(all_permits) % 50 < 20 and len(all_permits) > 0:
                    temp_output = {
                        'source': city_key,
                        'portal_type': 'CityView',
                        'scraped_at': datetime.now().isoformat(),
                        'target_count': target_count,
                        'actual_count': len(all_permits),
                        'errors': errors,
                        'permits': all_permits
                    }
                    (OUTPUT_DIR / f'{city_key}_raw.json').write_text(json.dumps(temp_output, indent=2))

                # Brief pause between searches
                await asyncio.sleep(0.5)

            print(f'\n    Total unique permits: {len(all_permits)}')

        except Exception as e:
            print(f'\nERROR: {e}')
            import traceback
            traceback.print_exc()
            errors.append({'step': 'main', 'error': str(e)})
            try:
                await page.screenshot(path=f'debug_html/cityview_{city_key}_error.png', full_page=True)
            except:
                pass
            # Save whatever we have before crash
            if all_permits:
                crash_output = {
                    'source': city_key,
                    'portal_type': 'CityView',
                    'scraped_at': datetime.now().isoformat(),
                    'target_count': target_count,
                    'actual_count': len(all_permits),
                    'errors': errors,
                    'permits': all_permits
                }
                (OUTPUT_DIR / f'{city_key}_raw.json').write_text(json.dumps(crash_output, indent=2))
                print(f'    Saved {len(all_permits)} permits before crash')

        finally:
            await browser.close()

    # Save results
    output = {
        'source': city_key,
        'portal_type': 'CityView',
        'scraped_at': datetime.now().isoformat(),
        'target_count': target_count,
        'actual_count': len(all_permits),
        'errors': errors,
        'permits': all_permits[:target_count]
    }

    output_file = OUTPUT_DIR / f'{city_key}_raw.json'
    output_file.write_text(json.dumps(output, indent=2))

    print('\n' + '=' * 60)
    print('SUMMARY')
    print('=' * 60)
    print(f'City: {config["name"]}')
    print(f'Permits: {output["actual_count"]}')
    print(f'Errors: {len(errors)}')
    print(f'Output: {output_file}')

    if all_permits:
        print('\nSAMPLE:')
        for p in all_permits[:5]:
            print(f'  {p.get("permit_id", "?")} | {p.get("type", "?")} | {p.get("address", "?")[:40]}')

    return output


if __name__ == '__main__':
    city = sys.argv[1] if len(sys.argv) > 1 else 'carrollton'
    count = int(sys.argv[2]) if len(sys.argv) > 2 else 100
    asyncio.run(scrape(city, count))
