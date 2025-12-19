#!/usr/bin/env python3
"""
MYGOV MULTI-CITY PERMIT SCRAPER (Playwright)
Platform: MyGov Public Portal (public.mygov.us)

Uses street name searches to discover permits across multiple DFW cities.

Usage:
  python3 scrapers/mygov_multi.py mansfield 100
  python3 scrapers/mygov_multi.py rowlett 100
  python3 scrapers/mygov_multi.py --list  # Show available cities
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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

OUTPUT_DIR = Path(__file__).parent.parent / "data" / "raw"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# MyGov cities with confirmed public access
MYGOV_CITIES = {
    'mansfield': {'name': 'Mansfield', 'slug': 'mansfield_tx', 'pop': 75000},
    'rowlett': {'name': 'Rowlett', 'slug': 'rowlett_tx', 'pop': 67000},
    'grapevine': {'name': 'Grapevine', 'slug': 'tx_grapevine', 'pop': 50000},
    'burleson': {'name': 'Burleson', 'slug': 'burleson_tx', 'pop': 50000},
    'little_elm': {'name': 'Little Elm', 'slug': 'little_elm_tx', 'pop': 50000},
    'lancaster': {'name': 'Lancaster', 'slug': 'lancaster_tx', 'pop': 40000},
    'midlothian': {'name': 'Midlothian', 'slug': 'midlothian_tx', 'pop': 35000},
    'celina': {'name': 'Celina', 'slug': 'celina_tx', 'pop': 20000},
    'fate': {'name': 'Fate', 'slug': 'fate_tx', 'pop': 20000},
    'venus': {'name': 'Venus', 'slug': 'venus_tx', 'pop': 5000},
    'university_park': {'name': 'University Park', 'slug': 'university_park_tx', 'pop': 25000},
    'forney': {'name': 'Forney', 'slug': 'forney_tx', 'pop': 25000},
    'royse_city': {'name': 'Royse City', 'slug': 'roysecity_tx', 'pop': 13000},
    'crowley': {'name': 'Crowley', 'slug': 'crowley_tx', 'pop': 18000},
}

# Common street names/patterns to search
SEARCH_TERMS = [
    'Main', 'Oak', 'Elm', 'Cedar', 'Pine', 'Maple',
    'First', 'Second', 'Third', 'Fourth', 'Fifth',
    'Park', 'Lake', 'Creek', 'Spring', 'Hill',
    'North', 'South', 'East', 'West',
    'Church', 'School', 'College', 'University',
    'Meadow', 'Forest', 'Valley', 'Ridge',
    'Sunset', 'Sunrise', 'Highland', 'Woodland',
]


def get_lookup_url(slug: str) -> str:
    return f'https://public.mygov.us/{slug}/lookup'


@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=1, min=1, max=4),
    retry=retry_if_exception_type((PlaywrightTimeout,)),
    reraise=True
)
async def search_address(page, city_slug: str, search_term: str) -> list:
    """Search for addresses and extract any permits found."""
    permits = []
    url = get_lookup_url(city_slug)

    try:
        await page.goto(url, timeout=20000)
        await asyncio.sleep(1)

        # Find and fill search
        search_input = await page.query_selector('input[type="text"]')
        if not search_input:
            return permits

        await search_input.fill(search_term)
        await asyncio.sleep(0.5)
        await search_input.press('Enter')
        await asyncio.sleep(2)

        # Look for address results (accordion items)
        accordions = await page.query_selector_all('a.accordion-toggle, .address-result, .search-result')

        for accordion in accordions[:20]:  # Limit per search (increased from 10)
            try:
                # Scroll into view and click to expand
                await accordion.scroll_into_view_if_needed()
                await accordion.click()
                await asyncio.sleep(0.8)

                # Get parent container (as ElementHandle)
                parent_handle = await accordion.evaluate_handle('node => node.closest("li") || node.parentElement')
                if not parent_handle:
                    continue
                parent = parent_handle.as_element()
                if not parent:
                    continue

                text = await parent.inner_text()

                # Look for permit indicators
                permit_match = re.search(r'Permits?\s*\((\d+)\)', text, re.IGNORECASE)
                if permit_match and int(permit_match.group(1)) > 0:
                    # Try to click permits section - search within parent, not entire page
                    permit_toggle = await parent.query_selector('a.lookup-toggle-button, [data-type="permit"]')
                    if permit_toggle:
                        # Scroll into view and click
                        await permit_toggle.scroll_into_view_if_needed()
                        await permit_toggle.click()
                        await asyncio.sleep(0.5)

                        # Extract permit details from within parent container
                        permit_divs = await parent.query_selector_all('.lb-right, .permit-item')
                        for pdiv in permit_divs:
                            title_elem = await pdiv.query_selector('h3, .permit-title, .project-title')
                            if title_elem:
                                title = await title_elem.inner_text()

                                # Extract address from accordion
                                addr_text = await accordion.inner_text()

                                # Parse permit ID
                                pid_match = re.search(r'Project\s+([\d-]+)|#([\d-]+)|(P\d+)', title)
                                permit_id = pid_match.group(1) or pid_match.group(2) or pid_match.group(3) if pid_match else ''

                                permits.append({
                                    'permit_id': permit_id,
                                    'title': title.strip()[:100],
                                    'address': addr_text.strip()[:100],
                                    'raw_text': text[:300],
                                    'source': 'mygov',
                                })

                # Collapse accordion
                await accordion.click()
                await asyncio.sleep(0.3)

            except Exception as e:
                logger.debug(f"Error processing accordion: {e}")
                continue

    except PlaywrightTimeout:
        logger.warning(f"Timeout searching '{search_term}'")
    except Exception as e:
        logger.debug(f"Search error: {e}")

    return permits


async def scrape_city(city_key: str, target_count: int) -> list:
    """Scrape permits for a city using street name searches."""
    if city_key not in MYGOV_CITIES:
        print(f"Unknown city: {city_key}")
        print(f"Available: {', '.join(sorted(MYGOV_CITIES.keys()))}")
        return []

    city = MYGOV_CITIES[city_key]
    all_permits = []
    seen_ids = set()

    print("=" * 60)
    print(f"{city['name'].upper()} MYGOV PERMIT SCRAPER")
    print("=" * 60)
    print(f"Target: {target_count} permits")
    print(f"Time: {datetime.now().isoformat()}")
    print()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        page = await context.new_page()

        try:
            for term in SEARCH_TERMS:
                if len(all_permits) >= target_count:
                    break

                logger.info(f"Searching '{term}'...")
                permits = await search_address(page, city['slug'], term)

                # Dedupe
                new_count = 0
                for permit in permits:
                    key = permit.get('permit_id') or permit.get('address', '')
                    if key and key not in seen_ids:
                        seen_ids.add(key)
                        all_permits.append(permit)
                        new_count += 1

                if new_count > 0:
                    logger.info(f"  +{new_count} permits (total: {len(all_permits)})")

                await asyncio.sleep(0.5)  # Rate limit

        finally:
            await browser.close()

    # Save results
    output_file = OUTPUT_DIR / f"{city_key}_mygov_raw.json"
    with open(output_file, 'w') as f:
        json.dump(all_permits[:target_count], f, indent=2, default=str)

    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"City: {city['name']}")
    print(f"Permits found: {len(all_permits)}")
    print(f"Saved to: {output_file}")

    if all_permits:
        print()
        print("SAMPLE:")
        for p in all_permits[:3]:
            print(f"  {p.get('permit_id', 'N/A')} | {p.get('address', '')[:50]}")

    return all_permits[:target_count]


async def main():
    if len(sys.argv) < 2 or sys.argv[1] == '--list':
        print("MyGov Multi-City Scraper")
        print()
        print("Available cities:")
        for key, city in sorted(MYGOV_CITIES.items(), key=lambda x: -x[1]['pop']):
            print(f"  {key:15} - {city['name']:15} (pop: {city['pop']:,})")
        print()
        print("Usage: python3 mygov_multi.py <city> [count]")
        return

    city_key = sys.argv[1].lower()
    target = int(sys.argv[2]) if len(sys.argv) > 2 else 50

    await scrape_city(city_key, target)


if __name__ == '__main__':
    asyncio.run(main())
