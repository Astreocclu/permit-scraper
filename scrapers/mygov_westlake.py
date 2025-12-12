#!/usr/bin/env python3
"""
Simplified Westlake scraper based on working test.
"""

import asyncio
import json
import logging
import re
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Path to harvested addresses file
ADDRESSES_FILE = Path(__file__).parent.parent / "data" / "westlake_addresses.json"


def load_harvested_addresses() -> list[str]:
    """
    Load pre-harvested addresses from JSON file instead of guessing.

    Returns list of address strings in format: "2204 Cedar Elm Terr., Westlake, TX 76262"
    Flattens all streets into a single list for iteration.
    """
    if not ADDRESSES_FILE.exists():
        logger.warning(f"Harvested addresses file not found: {ADDRESSES_FILE}")
        logger.warning("Run scrapers/westlake_harvester.py first to harvest addresses.")
        return []

    try:
        with open(ADDRESSES_FILE) as f:
            data = json.load(f)

        # Flatten all street addresses into single list
        addresses = []
        for street_name, street_addresses in data.items():
            for addr_obj in street_addresses:
                if isinstance(addr_obj, dict) and 'address' in addr_obj:
                    addresses.append(addr_obj['address'])
                elif isinstance(addr_obj, str):
                    addresses.append(addr_obj)

        logger.info(f"Loaded {len(addresses)} harvested addresses from {len(data)} streets")
        return addresses

    except Exception as e:
        logger.error(f"Error loading harvested addresses: {e}")
        return []


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=2, max=8),
    retry=retry_if_exception_type((PlaywrightTimeout, Exception)),
    reraise=True
)
async def fetch_address_permits(page, address: str) -> list:
    """Fetch permits for a single address with retry logic."""
    permits = []

    # Load lookup page
    await page.goto('https://public.mygov.us/westlake_tx/lookup', timeout=20000)
    await asyncio.sleep(1)

    # Search for address
    search_input = await page.query_selector('input[type="text"]')
    if not search_input:
        return permits

    await search_input.fill(address)
    await asyncio.sleep(0.5)
    await search_input.press('Enter')
    await asyncio.sleep(2)

    # Check for accordion items
    accordion_items = await page.query_selector_all('a.accordion-toggle')

    if not accordion_items:
        return permits

    # Process accordion items
    for item_idx, accordion in enumerate(accordion_items[:10]):  # Check first 10 entities
        try:
            await accordion.click()
            await asyncio.sleep(0.8)

            # Look for the parent <li> element which contains the accordion content
            parent_li = await accordion.evaluate_handle('node => node.closest("li")')
            if not parent_li:
                await accordion.click()  # Collapse
                await asyncio.sleep(0.3)
                continue

            # Get text within this specific list item
            li_text = await parent_li.inner_text() if parent_li else ''
            permit_match = re.search(r'Permits?\s*\((\d+)\)', li_text, re.IGNORECASE)

            if permit_match and int(permit_match.group(1)) > 0:
                # Click permits toggle
                permit_toggle = await page.query_selector('a.lookup-toggle-button')
                if permit_toggle:
                    await permit_toggle.click()
                    await asyncio.sleep(0.5)

                    # Extract permits
                    permit_divs = await page.query_selector_all('.lb-right')

                    for pdiv in permit_divs:
                        title_elem = await pdiv.query_selector('h3.lookup-project-title')
                        if not title_elem:
                            continue

                        title_text = await title_elem.inner_text()
                        entity_name = await accordion.inner_text()

                        # Parse project ID
                        project_id = ''
                        if 'Project ' in title_text:
                            pid_match = re.search(r'Project\s+([\d-]+)', title_text)
                            if pid_match:
                                project_id = pid_match.group(1)

                        # Get title (before the bracket)
                        title = title_text.split('[')[0].strip()

                        # Get status
                        status_elem = await pdiv.query_selector('strong.step-status')
                        status = await status_elem.inner_text() if status_elem else ''

                        # Get description
                        desc_elem = await pdiv.query_selector('.lookup-project-description p')
                        description = await desc_elem.inner_text() if desc_elem else ''

                        # Get date
                        date_elem = await pdiv.query_selector('em span')
                        date_info = await date_elem.inner_text() if date_elem else ''

                        permits.append({
                            'permit_id': project_id,
                            'title': title,
                            'address': address,
                            'entity': entity_name.strip(),
                            'status': status.strip(),
                            'description': description.strip(),
                            'date': date_info.strip(),
                            'city': 'Westlake',
                            'state': 'TX',
                            'scraped_at': datetime.now().isoformat()
                        })

            # Collapse before next
            await accordion.click()
            await asyncio.sleep(0.3)

        except Exception as e:
            # Skip this entity if error
            continue

    return permits


async def scan_neighborhood(page, center_address: str, center_num: int, street_name: str, permits_found: list) -> list:
    """
    Expanding Ripple scan: when a permit is found at center_num, scan ±50 addresses.

    Logic:
    - Range: center_num - 50 to center_num + 50
    - Step: 2 (preserve street parity - even/odd)
    - Stop conditions (any):
      1. Reached ±50 boundary
      2. 5 consecutive "No Results"
      3. 15 total failures in this neighborhood
    """
    consecutive_failures = 0
    total_failures = 0
    MAX_CONSECUTIVE = 5
    MAX_TOTAL_FAILURES = 15
    RANGE = 50
    STEP = 2

    start_num = max(1, center_num - RANGE)
    end_num = center_num + RANGE

    # Determine parity from center (even addresses vs odd)
    start_parity = center_num % 2
    if start_num % 2 != start_parity:
        start_num += 1

    logger.info(f"Deep dive: scanning {start_num}-{end_num} on {street_name}")

    neighborhood_permits = []

    for num in range(start_num, end_num + 1, STEP):
        if num == center_num:
            continue  # Already scanned

        if consecutive_failures >= MAX_CONSECUTIVE:
            logger.info(f"Stopping deep dive: {MAX_CONSECUTIVE} consecutive failures")
            break

        if total_failures >= MAX_TOTAL_FAILURES:
            logger.info(f"Stopping deep dive: {MAX_TOTAL_FAILURES} total failures")
            break

        address = f"{num} {street_name}"
        try:
            results = await fetch_address_permits(page, address)
            if results:
                neighborhood_permits.extend(results)
                consecutive_failures = 0
                logger.info(f"Found {len(results)} permits at {address}")
            else:
                consecutive_failures += 1
                total_failures += 1
        except Exception as e:
            logger.warning(f"Error scanning {address}: {e}")
            consecutive_failures += 1
            total_failures += 1

    return neighborhood_permits


async def scrape_westlake(target_count=100):
    """Scrape Westlake permits with adaptive scanning."""
    print(f"Westlake Permit Scraper - Target: {target_count} permits\n")

    all_permits = []
    addresses_tested = []
    global_request_count = 0
    MAX_GLOBAL_REQUESTS = 2000

    # Load harvested addresses from JSON file
    test_addresses = load_harvested_addresses()

    if not test_addresses:
        # Fallback to address guessing if harvested file doesn't exist
        print("WARNING: No harvested addresses found. Falling back to address guessing.")
        print("This is less efficient. Run scrapers/westlake_harvester.py to harvest addresses first.\n")

        # Known streets in Westlake
        streets = [
            'Solana Blvd',
            'Ottinger Rd',
            'Dove Rd',
            'Westlake Pkwy',
            'Trophy Club Dr',
            'Village Cir',
            'Pearson Ln',
            'Carillon Pkwy',
            'State Highway 114',
            'Byron Nelson Blvd',
            'Continental Blvd',
            'Circle Dr',
            'Roanoke Rd',
            'Davis Blvd',
            'Park Dr',
        ]

        # Generate addresses (every 100 from 1000-3500)
        for street in streets:
            for num in range(1000, 3600, 100):
                test_addresses.append(f'{num} {street}')
    else:
        print(f"Using {len(test_addresses)} harvested addresses from data/westlake_addresses.json\n")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            for idx, address in enumerate(test_addresses):
                if len(all_permits) >= target_count:
                    print(f"\nReached target of {target_count} permits!")
                    break

                if global_request_count >= MAX_GLOBAL_REQUESTS:
                    logger.warning(f"Hit global request limit: {MAX_GLOBAL_REQUESTS}")
                    break

                print(f"[{idx+1}/{len(test_addresses)}] Testing: {address}...", end='', flush=True)

                # Use retry-decorated function to fetch permits
                try:
                    permits = await fetch_address_permits(page, address)
                    global_request_count += 1

                    if not permits:
                        print(" no results")
                    else:
                        print(f" -> Found {len(permits)} permits!")
                        all_permits.extend(permits)

                        # ADAPTIVE: Deep dive into this neighborhood
                        # Extract street number and street name
                        parts = address.split(' ', 1)
                        if len(parts) == 2:
                            try:
                                base_num = int(parts[0])
                                street_name = parts[1]

                                logger.info(f"Triggering neighborhood scan for {address}")
                                neighborhood = await scan_neighborhood(
                                    page, address, base_num, street_name, permits
                                )
                                all_permits.extend(neighborhood)
                                # Approximate request count from neighborhood scan
                                global_request_count += len(neighborhood) // 2

                                if neighborhood:
                                    logger.info(f"Neighborhood scan found {len(neighborhood)} additional permits")
                            except ValueError:
                                logger.warning(f"Could not parse address number from: {address}")

                    addresses_tested.append(address)

                except Exception as e:
                    print(f" ERROR: {e}")
                    addresses_tested.append(address)
                    global_request_count += 1

                # Wait between addresses
                await asyncio.sleep(0.5)

        except Exception as e:
            print(f"\nError: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await browser.close()

    # Save results
    print(f"\n{'='*60}")
    print(f"SUMMARY")
    print(f"{'='*60}")
    print(f"Addresses tested: {len(addresses_tested)}")
    print(f"Total permits found: {len(all_permits)}")
    print(f"Global requests made: {global_request_count}")

    output = {
        'city': 'Westlake',
        'state': 'TX',
        'scrape_date': datetime.now().isoformat(),
        'permit_count': len(all_permits),
        'addresses_tested': addresses_tested,
        'permits': all_permits
    }

    Path('westlake_raw.json').write_text(json.dumps(output, indent=2))
    print(f"\nSaved to: {Path('westlake_raw.json').absolute()}")

    return output


if __name__ == '__main__':
    import sys
    target = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    asyncio.run(scrape_westlake(target))
