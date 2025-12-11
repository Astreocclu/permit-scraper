#!/usr/bin/env python3
"""
Simplified Westlake scraper based on working test.
"""

import asyncio
import json
import re
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type


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


async def scrape_westlake(target_count=100):
    """Scrape Westlake permits."""
    print(f"Westlake Permit Scraper - Target: {target_count} permits\n")

    all_permits = []
    addresses_tested = []

    # Generate address list
    test_addresses = []

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

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            for idx, address in enumerate(test_addresses):
                if len(all_permits) >= target_count:
                    print(f"\nReached target of {target_count} permits!")
                    break

                print(f"[{idx+1}/{len(test_addresses)}] Testing: {address}...", end='', flush=True)

                # Use retry-decorated function to fetch permits
                try:
                    permits = await fetch_address_permits(page, address)

                    if not permits:
                        print(" no results")
                    else:
                        print(f" -> Found {len(permits)} permits!")
                        all_permits.extend(permits)

                    addresses_tested.append(address)

                except Exception as e:
                    print(f" ERROR: {e}")
                    addresses_tested.append(address)

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
