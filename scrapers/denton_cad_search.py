#!/usr/bin/env python3
"""
DENTON CAD PROPERTY SEARCH SCRAPER
Searches Denton Central Appraisal District for property addresses.

Used to enrich The Colony permits (which only have street names) with full addresses.

Usage:
    python3 scrapers/denton_cad_search.py --street "BAKER DR" --city "THE COLONY"
    python3 scrapers/denton_cad_search.py --enrich-permits
"""

import argparse
import asyncio
import json
import re
from datetime import datetime
from pathlib import Path

from playwright.async_api import async_playwright

OUTPUT_DIR = Path(__file__).parent.parent / "data" / "raw"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


async def search_by_address(street_name: str, city: str = None, year: int = 2025, limit: int = 100) -> list:
    """
    Search DCAD for properties matching a street name.

    Args:
        street_name: Street to search (e.g., "BAKER DR")
        city: Optional city filter (e.g., "THE COLONY")
        year: Tax year to search
        limit: Max results to return

    Returns:
        List of property records with full addresses
    """
    results = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            print(f'Loading DCAD property search...')
            await page.goto('https://denton.prodigycad.com/property-search',
                          wait_until='networkidle', timeout=60000)
            await asyncio.sleep(3)

            # Change search type to Address
            # Click on the search type dropdown (default is "Compound Text Search" or "Name")
            dropdown_trigger = await page.query_selector('[class*="select"] >> text=/Name|Compound|Address/')
            if dropdown_trigger:
                await dropdown_trigger.click()
                await asyncio.sleep(1)
                # Look for Address option
                addr_option = await page.query_selector('text=/^Address$/')
                if addr_option:
                    await addr_option.click()
                    await asyncio.sleep(1)

            # Enter search term
            search_input = await page.query_selector('input[placeholder*="Search"]')
            if search_input:
                await search_input.fill(street_name)
                await asyncio.sleep(0.5)

                # Click search button or press Enter
                search_btn = await page.query_selector('button[type="submit"], [class*="search"] button')
                if search_btn:
                    await search_btn.click()
                else:
                    await search_input.press('Enter')

                await asyncio.sleep(5)

                # Extract results from table
                rows = await page.query_selector_all('tbody tr')
                print(f'Found {len(rows)} rows')

                for row in rows[:limit]:
                    cells = await row.query_selector_all('td')
                    if len(cells) >= 8:
                        prop_id = await cells[2].inner_text()  # PropID
                        owner = await cells[6].inner_text()    # Owner Name
                        address = await cells[10].inner_text() if len(cells) > 10 else ''  # Property Address
                        result_city = await cells[11].inner_text() if len(cells) > 11 else ''  # City

                        # Filter by city if specified
                        if city and city.upper() not in result_city.upper():
                            continue

                        results.append({
                            'prop_id': prop_id.strip(),
                            'owner_name': owner.strip(),
                            'address': address.strip(),
                            'city': result_city.strip(),
                            'source': 'DCAD',
                        })

        except Exception as e:
            print(f'Error: {e}')
            await page.screenshot(path='data/debug_dcad_error.png')

        finally:
            await browser.close()

    return results


async def enrich_colony_permits():
    """
    Enrich The Colony permits with full addresses from DCAD.

    Reads the_colony_raw.json, extracts unique street names,
    searches DCAD for each, and updates permits with full addresses.
    """
    raw_file = OUTPUT_DIR / 'the_colony_raw.json'
    if not raw_file.exists():
        print(f'No raw permits file found: {raw_file}')
        return

    with open(raw_file) as f:
        data = json.load(f)

    permits = data.get('permits', data) if isinstance(data, dict) else data
    print(f'Loaded {len(permits)} permits from The Colony')

    # Extract unique street names from raw_cells
    street_names = set()
    for p in permits:
        raw = p.get('raw_cells', [])
        if len(raw) >= 2:
            street = raw[1]  # Second cell is usually street name
            if street and not street.startswith(('DKB', 'JJ_')):  # Skip contractor codes
                street_names.add(street.strip().upper())

    print(f'Found {len(street_names)} unique street names to lookup')

    # Build address lookup table
    address_lookup = {}
    for street in sorted(street_names)[:20]:  # Limit for testing
        print(f'\nSearching DCAD for: {street}')
        results = await search_by_address(street, city='THE COLONY')
        for r in results:
            # Key by street name (without number) for fuzzy matching
            full_addr = r['address']
            if full_addr:
                address_lookup[street] = full_addr
                print(f'  Found: {full_addr}')
                break

    # Update permits with full addresses
    enriched = 0
    for p in permits:
        if not p.get('address'):
            raw = p.get('raw_cells', [])
            if len(raw) >= 2:
                street = raw[1].strip().upper()
                if street in address_lookup:
                    p['address'] = address_lookup[street]
                    p['address_source'] = 'DCAD'
                    enriched += 1

    print(f'\nEnriched {enriched}/{len(permits)} permits with addresses')

    # Save enriched data
    output_file = OUTPUT_DIR / 'the_colony_enriched.json'
    with open(output_file, 'w') as f:
        json.dump({
            'source': 'the_colony',
            'enriched_at': datetime.now().isoformat(),
            'permits': permits,
        }, f, indent=2)

    print(f'Saved to: {output_file}')


def main():
    parser = argparse.ArgumentParser(description='Search DCAD for property addresses')
    parser.add_argument('--street', help='Street name to search')
    parser.add_argument('--city', help='City filter')
    parser.add_argument('--enrich-permits', action='store_true', help='Enrich The Colony permits')

    args = parser.parse_args()

    if args.enrich_permits:
        asyncio.run(enrich_colony_permits())
    elif args.street:
        results = asyncio.run(search_by_address(args.street, args.city))
        print(f'\nFound {len(results)} properties:')
        for r in results[:10]:
            print(f'  {r["address"]} - {r["owner_name"]}')
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
