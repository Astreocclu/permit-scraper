#!/usr/bin/env python3
"""
TYLER eSUITE PARCEL-BASED PERMIT SCRAPER

Scrapes permits by querying individual parcels from CAD data.
Uses Denton CAD parcel IDs to query Tyler eSuite portal.

Usage:
    python3 scrapers/tyler_esuite_parcel.py --parcel-file data/parcels/lewisville_denton_parcels.json --limit 100
    python3 scrapers/tyler_esuite_parcel.py --parcel R00000123456  # Single parcel
"""

import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

# Output directory
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "raw"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Portal configuration
LEWISVILLE_CONFIG = {
    'name': 'Lewisville',
    'base_url': 'https://etools.cityoflewisville.com/esuite.permits/',
    'county': 'denton',
}


def format_parcel_id(prop_id: Optional[str]) -> str:
    """Format Denton parcel ID for Tyler eSuite (add R prefix)."""
    if not prop_id:
        return ''
    prop_id = str(prop_id).strip()
    if prop_id.upper().startswith('R'):
        return prop_id.upper()
    return f"R{prop_id}"


async def query_parcel_permits(page, parcel_id: str) -> list[dict]:
    """
    Query Tyler eSuite for permits on a specific parcel.

    Returns list of permit dictionaries.

    NOTE: As of 2025-12-20, the Lewisville Tyler eSuite portal does not
    have a publicly accessible search interface. This function contains
    placeholder logic that will need to be updated once we identify
    the correct navigation path or gain API access.
    """
    permits = []

    try:
        # Navigate to home page (resets state)
        await page.goto(LEWISVILLE_CONFIG['base_url'], wait_until='networkidle', timeout=30000)
        await asyncio.sleep(1)

        # PLACEHOLDER: The portal does not currently have visible search inputs
        # This section will need to be updated based on:
        # 1. Finding the correct entry point for public permit search
        # 2. Obtaining API credentials if required
        # 3. Alternative portal access method

        # Original implementation (currently non-functional):
        # - Look for parcel number input field
        # - Fill with parcel_id
        # - Submit search
        # - Extract permit results from table

        # For now, log the attempt
        print(f"      WARNING: Public search not accessible for {parcel_id}")

    except PlaywrightTimeout:
        pass
    except Exception as e:
        print(f"      Error: {e}")

    return permits


async def scrape_parcels(
    parcel_ids: list[str],
    limit: Optional[int] = None,
    delay: float = 2.0
) -> dict:
    """
    Scrape permits for multiple parcels.

    Returns summary dict with all permits found.
    """
    if limit:
        parcel_ids = parcel_ids[:limit]

    total = len(parcel_ids)
    print(f"\n{'='*60}")
    print(f"LEWISVILLE TYLER eSUITE PARCEL SCRAPER")
    print(f"{'='*60}")
    print(f"Parcels to query: {total}")
    print(f"Delay between queries: {delay}s")
    print(f"Time: {datetime.now().isoformat()}\n")

    all_permits = []
    parcels_with_permits = 0
    errors = 0

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 900},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        page = await context.new_page()

        for i, parcel_id in enumerate(parcel_ids, 1):
            print(f"[{i}/{total}] Querying {parcel_id}...", end=' ')

            try:
                permits = await query_parcel_permits(page, parcel_id)

                if permits:
                    parcels_with_permits += 1
                    for permit in permits:
                        permit['parcel_id'] = parcel_id
                        all_permits.append(permit)
                    print(f"Found {len(permits)} permits")
                else:
                    print("No permits")

            except Exception as e:
                print(f"ERROR: {e}")
                errors += 1

            if i < total:
                await asyncio.sleep(delay)

        await browser.close()

    # Save results
    output = {
        'source': 'lewisville_tyler_esuite',
        'scraped_at': datetime.now().isoformat(),
        'parcels_queried': total,
        'parcels_with_permits': parcels_with_permits,
        'total_permits': len(all_permits),
        'errors': errors,
        'permits': all_permits
    }

    output_file = OUTPUT_DIR / 'lewisville_raw.json'
    output_file.write_text(json.dumps(output, indent=2))

    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"Parcels queried: {total}")
    print(f"Parcels with permits: {parcels_with_permits}")
    print(f"Total permits found: {len(all_permits)}")
    print(f"Errors: {errors}")
    print(f"Output: {output_file}")

    return output


def load_parcel_ids(parcel_file: Path) -> list[str]:
    """Load and format parcel IDs from CAD JSON file."""
    data = json.loads(parcel_file.read_text())
    parcels = data.get('parcels', [])

    parcel_ids = []
    for parcel in parcels:
        prop_id = parcel.get('prop_id', '')
        formatted = format_parcel_id(prop_id)
        if formatted:
            parcel_ids.append(formatted)

    return parcel_ids


def main():
    parser = argparse.ArgumentParser(
        description='Scrape Lewisville permits via parcel lookup'
    )
    parser.add_argument('--parcel-file', type=Path,
                        help='Path to CAD parcel JSON file')
    parser.add_argument('--parcel', type=str,
                        help='Single parcel ID to query')
    parser.add_argument('--limit', type=int,
                        help='Limit number of parcels to query')
    parser.add_argument('--delay', type=float, default=2.0,
                        help='Delay between queries (default: 2.0s)')

    args = parser.parse_args()

    if args.parcel:
        parcel_ids = [format_parcel_id(args.parcel)]
    elif args.parcel_file:
        parcel_ids = load_parcel_ids(args.parcel_file)
    else:
        print("ERROR: Specify --parcel-file or --parcel")
        sys.exit(1)

    asyncio.run(scrape_parcels(parcel_ids, args.limit, args.delay))


if __name__ == '__main__':
    main()
