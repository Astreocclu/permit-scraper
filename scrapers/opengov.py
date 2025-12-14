#!/usr/bin/env python3
"""
OPENGOV PERMIT SCRAPER (Playwright)
Platform: OpenGov Permitting & Licensing Portal

Tested working: Bedford
Not working: Highland Park (no public search inputs)

Usage:
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

# OpenGov cities - only Bedford has working public search
OPENGOV_CITIES = {
    'bedford': {
        'name': 'Bedford',
        'base_url': 'https://bedfordtx.portal.opengov.com',
        'pop': 48000,
        'tier': 'B',
        'has_public_search': True,
    },
    # Highland Park has no public search inputs - application-only portal
    # Use TPIA email request: Building.Permits@hptx.org
}

# Permit type prefixes to search (Bedford's record numbering)
PERMIT_PREFIXES = [
    'BLDG',   # New Construction/Additions
    'RBLG',   # Remodel Building Permit
    'ROOF',   # Residential Roofing
    'MECH',   # Mechanical
    'PLUM',   # Plumbing
    'ELEC',   # Electrical
    'SWM',    # Swimming Pool
    'FENC',   # Fence/Retaining Wall
    'ACC',    # Accessory Structure
    'MISC',   # Miscellaneous (Demolition, etc.)
    'SIGN',   # Sign Permit
]


async def navigate_to_record_search(page, city_config: dict) -> bool:
    """
    Navigate to OpenGov portal's /search page and activate the Records tab.

    Returns True if record search input is accessible, False otherwise.
    """
    base_url = city_config['base_url']
    city_name = city_config['name']

    try:
        logger.info(f"[{city_name}] Navigating to {base_url}/search")
        await page.goto(f"{base_url}/search", wait_until='domcontentloaded', timeout=60000)
        await asyncio.sleep(4)  # Wait for Ember app to render

        # Check if the Records tab exists and click it
        records_tab = page.locator('li:has-text("Records")').first
        if await records_tab.count() > 0:
            await records_tab.click()
            await asyncio.sleep(2)

            # Verify record search input is visible
            record_input = page.locator('#recordSearchKey')
            if await record_input.is_visible():
                logger.info(f"[{city_name}] Record search input is visible")
                return True
            else:
                logger.warning(f"[{city_name}] Record search input not visible after clicking Records")
                return False
        else:
            logger.warning(f"[{city_name}] Records tab not found")
            return False

    except PlaywrightTimeout:
        logger.error(f"[{city_name}] Timeout loading portal")
        return False
    except Exception as e:
        logger.error(f"[{city_name}] Error navigating: {e}")
        return False


async def get_record_ids_from_search(page, city_config: dict, prefix: str) -> list:
    """
    Search for records by prefix and return list of record IDs found.

    Args:
        page: Playwright page
        city_config: City configuration dict
        prefix: Permit prefix to search (e.g., 'BLDG', 'ROOF')

    Returns:
        List of record IDs (e.g., ['BLDG-23-87', 'BLDG-23-68'])
    """
    city_name = city_config['name']
    record_ids = []

    try:
        record_input = page.locator('#recordSearchKey')
        await record_input.clear()
        await record_input.fill(prefix)
        await asyncio.sleep(2)  # Wait for autocomplete

        # Get page text and extract record IDs
        body_text = await page.locator('body').inner_text()
        lines = body_text.split('\n')

        for line in lines:
            line = line.strip()
            # Match patterns like "Record BLDG-23-87 New Construction/Additions"
            match = re.match(r'Record\s+([A-Z]+-\d+-\d+)', line)
            if match:
                record_ids.append(match.group(1))

        logger.info(f"[{city_name}] Search '{prefix}': found {len(record_ids)} record IDs")
        return record_ids

    except Exception as e:
        logger.debug(f"[{city_name}] Error searching '{prefix}': {e}")
        return record_ids


async def get_permit_details(page, city_config: dict, record_id: str) -> dict | None:
    """
    Navigate to a record detail page and extract permit information.

    Args:
        page: Playwright page
        city_config: City configuration dict
        record_id: Record ID (e.g., 'BLDG-23-87')

    Returns:
        Permit dict or None
    """
    base_url = city_config['base_url']
    city_name = city_config['name']

    try:
        # Search for the record and click on it
        record_input = page.locator('#recordSearchKey')

        # First check if input is visible, if not re-navigate
        if not await record_input.is_visible():
            await navigate_to_record_search(page, city_config)

        await record_input.clear()
        await record_input.fill(record_id)
        await asyncio.sleep(1.5)

        # Click on the result
        result = page.locator(f'text=Record {record_id}').first
        if await result.count() > 0:
            await result.click()

            # Wait for detail page to load - look for Applicant section
            try:
                await page.wait_for_selector('text=Applicant', timeout=10000)
            except:
                await asyncio.sleep(3)  # Fallback wait

            # Extract details from page
            body_text = await page.locator('body').inner_text()
            lines = [l.strip() for l in body_text.split('\n') if l.strip()]

            permit = {
                'permit_id': record_id,
                'permit_type': '',
                'address': '',
                'city': city_name,
                'status': '',
                'issued_date': '',
                'created_date': '',
                'expires': '',
                'applicant': '',
                'description': '',
                'valuation': '',
                'sq_ft': '',
                'source': 'opengov',
            }

            # Parse the page content
            # Format is: Label on one line, value on next line
            for i, line in enumerate(lines):
                next_line = lines[i + 1] if i + 1 < len(lines) else ''
                next_next = lines[i + 2] if i + 2 < len(lines) else ''

                # Permit type is usually at the top after navigation
                if any(kw in line for kw in ['Construction', 'Permit', 'Roofing', 'Mechanical', 'Plumbing']):
                    if not permit['permit_type'] and len(line) < 100 and 'toggle' not in line.lower():
                        permit['permit_type'] = line

                # Location/Address - value is on next line
                if line == 'Location' and next_line:
                    addr_match = re.match(r'(\d+\s+[A-Z][A-Z0-9\s]+)', next_line)
                    if addr_match:
                        permit['address'] = addr_match.group(1).strip()

                # Created date - value is on next line
                if line == 'Created' and next_line:
                    date_match = re.match(r'([A-Z][a-z]{2}\s+\d{1,2},?\s+\d{4})', next_line)
                    if date_match:
                        permit['created_date'] = date_match.group(1)

                # Expires date - value is on next line
                if line == 'Expires' and next_line:
                    date_match = re.match(r'([A-Z][a-z]{2}\s+\d{1,2},?\s+\d{4})', next_line)
                    if date_match:
                        permit['expires'] = date_match.group(1)

                # Issued date - in Documents section "Issued Aug 1, 2023"
                if 'Issued' in line:
                    date_match = re.search(r'Issued\s+([A-Z][a-z]{2}\s+\d{1,2},?\s+\d{4})', line)
                    if date_match:
                        permit['issued_date'] = date_match.group(1)

                # Status - value is on next line after "Status"
                if line == 'Status' and next_line in ['Complete', 'Active', 'Pending', 'Issued', 'Approved', 'Expired']:
                    permit['status'] = next_line

                # Applicant - value is on next line
                if line == 'Applicant' and next_line:
                    permit['applicant'] = next_line

                # Valuation - "Total Value of Work: $ *" then value on next line
                if 'Value of Work' in line and next_line:
                    val_match = re.match(r'([\d,]+)', next_line)
                    if val_match:
                        permit['valuation'] = val_match.group(1).replace(',', '')

                # Square footage - "Total Sq. Ft. *" then value on next line
                if 'Sq. Ft' in line and next_line:
                    sqft_match = re.match(r'([\d,]+)', next_line)
                    if sqft_match:
                        permit['sq_ft'] = sqft_match.group(1).replace(',', '')

                # Description - "Description *" then "toggle tooltip" then actual description
                if line == 'Description *' and next_next and 'toggle' not in next_next.lower():
                    permit['description'] = next_next[:200]
                elif line == 'Description *' and next_line and 'toggle' in next_line.lower() and i + 2 < len(lines):
                    permit['description'] = lines[i + 2][:200]

            # Go back to search
            await page.goto(f"{base_url}/search", wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(2)
            records_tab = page.locator('li:has-text("Records")').first
            if await records_tab.count() > 0:
                await records_tab.click()
                await asyncio.sleep(1)

            if permit['permit_id'] and (permit['address'] or permit['permit_type']):
                return permit

        return None

    except Exception as e:
        logger.debug(f"[{city_name}] Error getting details for {record_id}: {e}")
        return None


async def main():
    if len(sys.argv) < 2 or sys.argv[1] == '--list':
        print("OpenGov Permit Scraper")
        print()
        print("Available cities:")
        for key, city in sorted(OPENGOV_CITIES.items(), key=lambda x: -x[1]['pop']):
            status = "✓ working" if city.get('has_public_search') else "✗ no public search"
            print(f"  {key:15} - {city['name']:15} (pop: {city['pop']:,}) {status}")
        print()
        print("Usage: python3 opengov.py <city> [count]")
        print()
        print("Note: Highland Park has no public search - use TPIA email: Building.Permits@hptx.org")
        return

    city_key = sys.argv[1].lower()
    target = int(sys.argv[2]) if len(sys.argv) > 2 else 50

    if city_key not in OPENGOV_CITIES:
        print(f"Unknown city: {city_key}")
        print(f"Available: {', '.join(sorted(OPENGOV_CITIES.keys()))}")
        return

    city = OPENGOV_CITIES[city_key]
    if not city.get('has_public_search'):
        print(f"Error: {city['name']} does not have public permit search.")
        print("Use TPIA email request instead.")
        return

    await scrape_city(city_key, target)


async def scrape_city(city_key: str, target_count: int) -> list:
    """
    Scrape permits for a city using record prefix searches.

    Strategy:
    1. Navigate to /search page and activate Records tab
    2. Search each permit prefix (BLDG, ROOF, etc.) to get record IDs
    3. Click each record to get full details
    4. Deduplicate and save
    """
    if city_key not in OPENGOV_CITIES:
        print(f"Unknown city: {city_key}")
        return []

    city = OPENGOV_CITIES[city_key]
    all_permits = []
    seen_ids = set()
    all_record_ids = []

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
            # Navigate to record search
            if not await navigate_to_record_search(page, city):
                logger.error(f"Could not access {city['name']} record search")
                return []

            # Phase 1: Collect all record IDs by searching prefixes
            print("Phase 1: Collecting record IDs...")
            for prefix in PERMIT_PREFIXES:
                record_ids = await get_record_ids_from_search(page, city, prefix)
                for rid in record_ids:
                    if rid not in seen_ids:
                        seen_ids.add(rid)
                        all_record_ids.append(rid)

                if len(all_record_ids) >= target_count * 2:  # Get extra in case some fail
                    break

                await asyncio.sleep(0.5)

            print(f"Found {len(all_record_ids)} unique record IDs")
            print()

            # Phase 2: Get details for each record
            print("Phase 2: Fetching permit details...")
            for i, record_id in enumerate(all_record_ids[:target_count * 2]):
                if len(all_permits) >= target_count:
                    break

                permit = await get_permit_details(page, city, record_id)
                if permit:
                    all_permits.append(permit)
                    if len(all_permits) % 10 == 0:
                        print(f"  Progress: {len(all_permits)}/{target_count}")

                await asyncio.sleep(0.5)  # Rate limit

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
    print(f"Record IDs found: {len(all_record_ids)}")
    print(f"Permits scraped: {len(all_permits)}")
    print(f"Saved to: {output_file}")

    if all_permits:
        print()
        print("SAMPLE:")
        for p in all_permits[:3]:
            print(f"  {p.get('permit_id', 'N/A')} | {p.get('address', '')[:40]} | ${p.get('valuation', 'N/A')}")

    return all_permits[:target_count]


if __name__ == '__main__':
    asyncio.run(main())
