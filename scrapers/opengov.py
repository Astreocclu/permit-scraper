#!/usr/bin/env python3
"""
OPENGOV PERMIT SCRAPER (Playwright)
Platform: OpenGov Permitting & Licensing Portal
Covers: Highland Park, Bedford (wealthy DFW suburbs)

Usage:
  python3 scrapers/opengov.py highland_park 100
  python3 scrapers/opengov.py bedford 100
  python3 scrapers/opengov.py --list
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

# OpenGov cities with confirmed public access
OPENGOV_CITIES = {
    'highland_park': {
        'name': 'Highland Park',
        'base_url': 'https://highlandparktx.portal.opengov.com',
        'pop': 9000,
        'tier': 'A',  # Ultra-wealthy
    },
    'bedford': {
        'name': 'Bedford',
        'base_url': 'https://bedfordtx.portal.opengov.com',
        'pop': 48000,
        'tier': 'B',
    },
}

# Common street names to search (same as MyGov pattern)
SEARCH_TERMS = [
    'Main', 'Oak', 'Park', 'Hill', 'Lake',
    'Cedar', 'Pine', 'Maple', 'Elm',
    'First', 'Second', 'Third',
    'North', 'South', 'East', 'West',
    'Creek', 'Spring', 'Valley', 'Ridge',
    'Meadow', 'Forest', 'Highland', 'Sunset',
]


def parse_permit_text(text: str, city: str) -> dict | None:
    """Parse permit info from result text."""
    if not text or len(text) < 10:
        return None

    lines = [l.strip() for l in text.split('\n') if l.strip()]

    permit = {
        'permit_id': '',
        'permit_type': '',
        'address': '',
        'status': '',
        'date': '',
        'city': city,
        'source': 'opengov',
    }

    for line in lines:
        # Look for permit ID patterns (varies by city)
        # Common: BLD-2025-001234, P25-00123, 2025-BP-0001
        id_match = re.search(r'([A-Z]{2,4}[-]?\d{4}[-]?\d{3,6})', line)
        if id_match and not permit['permit_id']:
            permit['permit_id'] = id_match.group(1)

        # Look for dates
        date_match = re.search(r'(\d{1,2}/\d{1,2}/\d{4})', line)
        if date_match and not permit['date']:
            permit['date'] = date_match.group(1)

        # Look for addresses (number + street)
        addr_match = re.search(r'(\d+\s+[A-Z][A-Za-z\s]+(?:St|Ave|Dr|Rd|Ln|Blvd|Ct|Way|Pl))', line, re.IGNORECASE)
        if addr_match and not permit['address']:
            permit['address'] = addr_match.group(1).strip()

        # Look for permit types
        type_keywords = ['residential', 'commercial', 'electrical', 'mechanical',
                        'plumbing', 'building', 'fence', 'pool', 'roof', 'hvac',
                        'remodel', 'addition', 'new construction']
        for kw in type_keywords:
            if kw in line.lower() and not permit['permit_type']:
                permit['permit_type'] = line[:50]
                break

    # Only return if we have at least permit_id or address
    if permit['permit_id'] or permit['address']:
        return permit
    return None


def parse_page_content(content: str, city: str) -> list:
    """Fallback: parse permits from raw page text."""
    permits = []

    # Split by common separators
    chunks = re.split(r'\n{2,}|<hr>|───', content)

    for chunk in chunks:
        permit = parse_permit_text(chunk, city)
        if permit:
            permits.append(permit)

    return permits


async def navigate_to_search(page, city_config: dict) -> bool:
    """
    Navigate to OpenGov portal and find the search interface.

    OpenGov uses Ember.js SPA - we need to wait for app to bootstrap,
    then find the search functionality.

    Returns True if search is accessible, False otherwise.
    """
    base_url = city_config['base_url']
    city_name = city_config['name']

    try:
        logger.info(f"[{city_name}] Navigating to {base_url}")
        await page.goto(base_url, timeout=30000)

        # Wait for Ember app to load (loading spinner disappears)
        await page.wait_for_selector('#main-content, .ember-application', timeout=20000)
        logger.info(f"[{city_name}] App loaded, looking for search...")

        # Give Angular/Ember extra time to render
        await asyncio.sleep(3)

        # Look for search button/link in header
        # Common patterns: "Search" link, magnifying glass icon, search input
        search_selectors = [
            'a:has-text("Search")',
            'button:has-text("Search")',
            '[data-test="search"]',
            '.search-button',
            'input[type="search"]',
            '[placeholder*="Search"]',
        ]

        for selector in search_selectors:
            element = page.locator(selector).first
            if await element.count() > 0:
                logger.info(f"[{city_name}] Found search element: {selector}")
                return True

        # If no search found, try clicking "Permits" or "Records" link
        nav_links = ['Permits', 'Records', 'Applications', 'Public Records']
        for link_text in nav_links:
            link = page.locator(f'a:has-text("{link_text}")').first
            if await link.count() > 0:
                await link.click()
                await asyncio.sleep(2)
                logger.info(f"[{city_name}] Clicked '{link_text}' navigation")
                return True

        logger.warning(f"[{city_name}] Could not find search interface")
        return False

    except PlaywrightTimeout:
        logger.error(f"[{city_name}] Timeout loading portal")
        return False
    except Exception as e:
        logger.error(f"[{city_name}] Error navigating: {e}")
        return False


@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=1, min=1, max=4),
    retry=retry_if_exception_type((PlaywrightTimeout,)),
    reraise=True
)
async def search_permits(page, city_config: dict, search_term: str) -> list:
    """
    Search for permits using a search term and extract results.

    Args:
        page: Playwright page
        city_config: City configuration dict
        search_term: Street name or keyword to search

    Returns:
        List of permit dicts
    """
    permits = []
    city_name = city_config['name']

    try:
        # Find and fill search input
        search_input = page.locator('input[type="search"], input[placeholder*="Search"], #search-input').first
        if await search_input.count() == 0:
            logger.warning(f"[{city_name}] Search input not found")
            return permits

        await search_input.clear()
        await search_input.fill(search_term)
        await asyncio.sleep(0.5)

        # Submit search (Enter key or click search button)
        await search_input.press('Enter')
        await asyncio.sleep(3)  # Wait for results

        # Extract results from page
        # OpenGov typically shows results in a table or card layout
        result_selectors = [
            '.search-result',
            '.permit-card',
            'tr[data-permit]',
            '.record-item',
            '[data-record-id]',
        ]

        for selector in result_selectors:
            results = page.locator(selector)
            count = await results.count()
            if count > 0:
                logger.info(f"[{city_name}] Found {count} results with {selector}")

                for i in range(min(count, 50)):  # Limit per search
                    try:
                        result = results.nth(i)
                        text = await result.inner_text()

                        permit = parse_permit_text(text, city_name)
                        if permit:
                            permits.append(permit)
                    except Exception as e:
                        logger.debug(f"Error parsing result {i}: {e}")
                        continue
                break

        if not permits:
            # Fallback: try to parse entire page body
            body_text = await page.inner_text('body')
            permits = parse_page_content(body_text, city_name)

        logger.info(f"[{city_name}] Search '{search_term}': {len(permits)} permits")
        return permits

    except PlaywrightTimeout:
        logger.warning(f"[{city_name}] Timeout searching '{search_term}'")
        return permits
    except Exception as e:
        logger.debug(f"[{city_name}] Search error: {e}")
        return permits


async def main():
    if len(sys.argv) < 2 or sys.argv[1] == '--list':
        print("OpenGov Multi-City Scraper")
        print()
        print("Available cities:")
        for key, city in sorted(OPENGOV_CITIES.items(), key=lambda x: -x[1]['pop']):
            print(f"  {key:15} - {city['name']:15} (pop: {city['pop']:,})")
        print()
        print("Usage: python3 opengov.py <city> [count]")
        return

    city_key = sys.argv[1].lower()
    target = int(sys.argv[2]) if len(sys.argv) > 2 else 50

    if city_key not in OPENGOV_CITIES:
        print(f"Unknown city: {city_key}")
        print(f"Available: {', '.join(sorted(OPENGOV_CITIES.keys()))}")
        return

    await scrape_city(city_key, target)


async def scrape_city(city_key: str, target_count: int) -> list:
    """Scrape permits for a city using street name searches."""
    if city_key not in OPENGOV_CITIES:
        print(f"Unknown city: {city_key}")
        return []

    city = OPENGOV_CITIES[city_key]
    all_permits = []
    seen_ids = set()

    print("=" * 60)
    print(f"{city['name'].upper()} OPENGOV PERMIT SCRAPER")
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
            # Navigate to portal
            if not await navigate_to_search(page, city):
                logger.error(f"Could not access {city['name']} portal")
                return []

            # Search using street names
            for term in SEARCH_TERMS:
                if len(all_permits) >= target_count:
                    break

                permits = await search_permits(page, city, term)

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

                await asyncio.sleep(1)  # Rate limit

        finally:
            await browser.close()

    # Save results
    output_file = OUTPUT_DIR / f"{city_key}_opengov_raw.json"
    output_data = {
        'source': city_key,
        'scraped_at': datetime.now().isoformat(),
        'permits': all_permits[:target_count]
    }
    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)

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


if __name__ == '__main__':
    asyncio.run(main())
