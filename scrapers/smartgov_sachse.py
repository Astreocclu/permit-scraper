#!/usr/bin/env python3
"""
SACHSE SMARTGOV PERMIT SCRAPER (Playwright)
Portal: SmartGov by Granicus
City: Sachse, TX

Usage:
  python3 scrapers/smartgov_sachse.py 100
  python3 scrapers/smartgov_sachse.py 500
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

SMARTGOV_CONFIG = {
    'name': 'Sachse',
    'base_url': 'https://ci-sachse-tx.smartgovcommunity.com',
    'search_url': 'https://ci-sachse-tx.smartgovcommunity.com/ApplicationPublic/ApplicationSearch',
}

# Search terms to find permits
SEARCH_TERMS = ['2025', '2024', '2023', 'residential', 'commercial', 'new', 'remodel']


@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=1, min=1, max=4),
    retry=retry_if_exception_type((PlaywrightTimeout,)),
    reraise=True
)
async def search_permits(page, search_term: str) -> list:
    """Search for permits and extract results."""
    permits = []

    try:
        await page.goto(SMARTGOV_CONFIG['search_url'], timeout=30000)
        await asyncio.sleep(2)

        # Fill search and submit
        await page.fill('#query', search_term)
        await page.click('button:has-text("SEARCH")')
        await asyncio.sleep(3)

        # Extract results from page text
        # Results appear as: permit_id, type, status+date, address
        content = await page.inner_text('body')

        # Parse results - look for permit patterns
        # Format: 8-digit number followed by type, status, date, address
        lines = content.split('\n')

        current_permit = {}
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue

            # Check for permit ID (8 digits starting with 202)
            if re.match(r'^202\d{5}$', line):
                # Save previous permit if exists
                if current_permit.get('permit_id'):
                    permits.append(current_permit)

                current_permit = {
                    'permit_id': line,
                    'permit_type': '',
                    'status': '',
                    'date': '',
                    'address': '',
                    'city': 'Sachse',
                    'source': 'smartgov',
                }

            elif current_permit.get('permit_id'):
                # Try to classify the line
                if any(t in line.lower() for t in ['residential', 'commercial', 'electrical', 'mechanical', 'plumbing', 'new construction', 'remodel', 'addition', 'fence', 'pool', 'roof']):
                    if not current_permit['permit_type']:
                        current_permit['permit_type'] = line

                elif re.search(r'\d{1,2}/\d{1,2}/\d{4}', line):
                    # Status + Date line
                    date_match = re.search(r'(\d{1,2}/\d{1,2}/\d{4})', line)
                    if date_match:
                        current_permit['date'] = date_match.group(1)
                        current_permit['status'] = line.replace(date_match.group(1), '').strip().rstrip(',').strip()

                elif re.match(r'^\d+\s+[A-Z]', line) and not current_permit['address']:
                    # Address line (starts with number)
                    current_permit['address'] = line

                elif line in ['SACHSE, TX', 'SACHSE TX', ',']:
                    # City/state - append to address if needed
                    if current_permit['address'] and 'SACHSE' not in current_permit['address']:
                        current_permit['address'] += f", {line}"

        # Don't forget last permit
        if current_permit.get('permit_id'):
            permits.append(current_permit)

        logger.info(f"Search '{search_term}': found {len(permits)} permits")

    except PlaywrightTimeout:
        logger.warning(f"Timeout searching '{search_term}'")
    except Exception as e:
        logger.error(f"Error searching '{search_term}': {e}")

    return permits


async def scrape_sachse(target_count: int) -> list:
    """Scrape permits from Sachse SmartGov portal."""
    all_permits = []
    seen_ids = set()

    print("=" * 60)
    print("SACHSE SMARTGOV PERMIT SCRAPER")
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

                permits = await search_permits(page, term)

                # Dedupe
                new_count = 0
                for permit in permits:
                    pid = permit.get('permit_id')
                    if pid and pid not in seen_ids:
                        seen_ids.add(pid)
                        all_permits.append(permit)
                        new_count += 1

                if new_count > 0:
                    logger.info(f"  +{new_count} new permits (total: {len(all_permits)})")

                await asyncio.sleep(1)

        finally:
            await browser.close()

    # Save results
    output_file = OUTPUT_DIR / "sachse_raw.json"
    with open(output_file, 'w') as f:
        json.dump(all_permits[:target_count], f, indent=2, default=str)

    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"City: Sachse")
    print(f"Permits found: {len(all_permits)}")
    print(f"Saved to: {output_file}")

    if all_permits:
        print()
        print("SAMPLE:")
        for p in all_permits[:5]:
            print(f"  {p.get('permit_id')} | {p.get('permit_type', 'N/A')[:30]} | {p.get('address', '')[:40]}")

    return all_permits[:target_count]


async def main():
    target = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    await scrape_sachse(target)


if __name__ == '__main__':
    asyncio.run(main())
