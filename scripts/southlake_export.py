#!/usr/bin/env python3
"""
Southlake EnerGov Export Script

Uses Playwright to:
1. Navigate to Southlake EnerGov portal
2. Search for permits in date range
3. Export results to Excel (if available)
4. Or scrape results page by page

Much faster than Browser-Use for bulk extraction.
"""

import asyncio
import json
import os
import re
from datetime import datetime
from pathlib import Path

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

# Output directory
OUTPUT_DIR = Path("data/extracts/southlake_1000")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

DOWNLOAD_DIR = Path("data/downloads")
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)


async def extract_permits_from_page(page) -> list:
    """Extract permit data from current search results page."""
    permits = []

    # Wait for results to load
    await page.wait_for_timeout(2000)

    # Try to extract permit cards/rows
    try:
        # EnerGov uses entityRecord divs for each result
        cards = await page.query_selector_all('.entityRecord, .SearchResult, [class*="result"], tr[class*="permit"]')

        if not cards:
            # Try alternate selectors
            cards = await page.query_selector_all('.ng-scope .searchResultsListItem, .card')

        print(f"  Found {len(cards)} permit cards")

        for card in cards:
            try:
                permit = {}

                # Try various selectors for each field
                # Permit number
                pn_elem = await card.query_selector('[name="label-CaseNumber"] a, .permit-number, .caseNumber, a[href*="permit"]')
                if pn_elem:
                    permit['permit_number'] = (await pn_elem.inner_text()).strip()

                # Issue date
                date_elem = await card.query_selector('[name="label-IssuedDate"], .issued-date, .issuedDate')
                if date_elem:
                    text = await date_elem.inner_text()
                    match = re.search(r'\d{1,2}/\d{1,2}/\d{4}', text)
                    if match:
                        permit['issue_date'] = match.group()

                # Permit type
                type_elem = await card.query_selector('[name="label-CaseType"], .permit-type, .caseType')
                if type_elem:
                    text = await type_elem.inner_text()
                    # Remove label prefix
                    permit['permit_type'] = re.sub(r'^Type:?\s*', '', text).strip()

                # Status
                status_elem = await card.query_selector('[name="label-Status"] span, .status')
                if status_elem:
                    permit['status'] = (await status_elem.inner_text()).strip()

                # Address
                addr_elem = await card.query_selector('[name="label-Address"], .address')
                if addr_elem:
                    text = await addr_elem.inner_text()
                    permit['address'] = re.sub(r'^Address:?\s*', '', text).strip()

                # Description
                desc_elem = await card.query_selector('[name="label-Description"], .description')
                if desc_elem:
                    text = await desc_elem.inner_text()
                    permit['description'] = re.sub(r'^Description:?\s*', '', text).strip()

                if permit.get('permit_number'):
                    permits.append(permit)

            except Exception as e:
                print(f"    Error extracting card: {e}")
                continue

    except Exception as e:
        print(f"  Error finding cards: {e}")

    return permits


async def scrape_southlake(target_count: int = 1000, headless: bool = True):
    """Scrape Southlake permits using Playwright."""

    all_permits = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            accept_downloads=True,
        )
        page = await context.new_page()

        print("Navigating to Southlake EnerGov portal...")
        await page.goto('https://energov.cityofsouthlake.com/EnerGov_Prod/SelfService#/search')
        await page.wait_for_timeout(3000)

        # Select Permit module
        print("Selecting Permit module...")
        module_select = await page.query_selector('select#ModuleId, select[name*="module"], select')
        if module_select:
            await module_select.select_option(label='Permit')
            await page.wait_for_timeout(1000)

        # Click Advanced search
        print("Opening advanced search...")
        advanced_btn = await page.query_selector('button#button-Advanced, button:has-text("Advanced")')
        if advanced_btn:
            await advanced_btn.click()
            await page.wait_for_timeout(1000)

        # Set date range - 2 years of data
        print("Setting date range...")
        # Find Issued Date fields
        date_from = await page.query_selector('input[name*="IssuedDateFrom"], input[placeholder*="From"]')
        date_to = await page.query_selector('input[name*="IssuedDateTo"], input[placeholder*="To"]')

        if date_from:
            await date_from.fill('01/01/2023')
        if date_to:
            await date_to.fill('12/25/2024')

        await page.wait_for_timeout(500)

        # Click Search
        print("Executing search...")
        search_btn = await page.query_selector('button#button-Search, button:has-text("Search")')
        if search_btn:
            await search_btn.click()
            await page.wait_for_timeout(5000)

        # Check for Export button
        print("Looking for Export button...")
        export_btn = await page.query_selector('button:has-text("Export"), a:has-text("Export"), [aria-label*="export"]')

        if export_btn:
            print("Found Export button - downloading Excel...")
            # Set up download listener
            async with page.expect_download() as download_info:
                await export_btn.click()
            download = await download_info.value
            download_path = DOWNLOAD_DIR / f"southlake_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            await download.save_as(download_path)
            print(f"Downloaded: {download_path}")

            # Parse Excel file
            import pandas as pd
            df = pd.read_excel(download_path)
            print(f"Excel contains {len(df)} rows")

            # Convert to permits list
            for _, row in df.iterrows():
                permit = {
                    'permit_number': str(row.get('Case Number', row.get('Permit Number', ''))),
                    'issue_date': str(row.get('Issued Date', '')),
                    'permit_type': str(row.get('Type', row.get('Permit Type', ''))),
                    'status': str(row.get('Status', '')),
                    'address': str(row.get('Address', '')),
                    'description': str(row.get('Description', '')),
                }
                if permit['permit_number']:
                    all_permits.append(permit)

        else:
            print("No Export button found - scraping page by page...")

            # Sort by Issued Date descending
            sort_select = await page.query_selector('select#SortBy, select[name*="sort"]')
            if sort_select:
                await sort_select.select_option(label='Issued Date')
                await page.wait_for_timeout(500)

            order_select = await page.query_selector('select#SortOrder, select[name*="order"]')
            if order_select:
                await order_select.select_option(label='Descending')
                await page.wait_for_timeout(500)

            # Set page size to max
            page_size = await page.query_selector('select#PageSize, select[name*="pageSize"]')
            if page_size:
                # Try to set to largest available option
                options = await page_size.query_selector_all('option')
                if options:
                    last_option = options[-1]
                    value = await last_option.get_attribute('value')
                    await page_size.select_option(value=value)
                    await page.wait_for_timeout(2000)

            # Scrape pages
            page_num = 0
            while len(all_permits) < target_count:
                page_num += 1
                print(f"\nScraping page {page_num}...")

                permits = await extract_permits_from_page(page)
                if not permits:
                    print("  No permits found on page - stopping")
                    break

                all_permits.extend(permits)
                print(f"  Extracted {len(permits)} permits (total: {len(all_permits)})")

                # Save progress every 100 permits
                if len(all_permits) % 100 < len(permits):
                    save_permits(all_permits, f"progress_{len(all_permits)}.json")

                # Check for next page
                next_btn = await page.query_selector('a#link-NextPage, a:has-text(">"), button:has-text("Next")')
                if next_btn:
                    is_disabled = await next_btn.get_attribute('disabled')
                    if is_disabled:
                        print("  No more pages")
                        break
                    await next_btn.click()
                    await page.wait_for_timeout(2000)
                else:
                    print("  No next button found")
                    break

        await browser.close()

    return all_permits


def save_permits(permits: list, filename: str):
    """Save permits to JSON file."""
    output_file = OUTPUT_DIR / filename
    with open(output_file, 'w') as f:
        json.dump(permits, f, indent=2)
    print(f"Saved {len(permits)} permits to {output_file}")


def analyze_verticals(permits: list):
    """Analyze permit types distribution."""
    from collections import defaultdict

    types = defaultdict(int)
    for p in permits:
        t = p.get('permit_type', 'Unknown')
        types[t] += 1

    print("\n" + "=" * 60)
    print("VERTICAL BREAKDOWN")
    print("=" * 60)
    for t, count in sorted(types.items(), key=lambda x: -x[1])[:25]:
        print(f"  {t}: {count}")
    print(f"\nTotal unique types: {len(types)}")


async def main():
    import argparse
    parser = argparse.ArgumentParser(description="Southlake EnerGov Export")
    parser.add_argument("--target", type=int, default=1000, help="Target permit count")
    parser.add_argument("--headless", action="store_true", default=True, help="Run headless")
    parser.add_argument("--visible", action="store_true", help="Show browser window")
    args = parser.parse_args()

    headless = not args.visible

    print(f"\n{'=' * 60}")
    print(f"SOUTHLAKE PERMIT EXPORT")
    print(f"Target: {args.target} permits")
    print(f"Headless: {headless}")
    print(f"{'=' * 60}")

    permits = await scrape_southlake(target_count=args.target, headless=headless)

    # Deduplicate
    seen = set()
    unique = []
    for p in permits:
        pn = p.get('permit_number')
        if pn and pn not in seen:
            seen.add(pn)
            unique.append(p)

    print(f"\n{'=' * 60}")
    print(f"EXTRACTION COMPLETE")
    print(f"  Total permits: {len(unique)}")
    print(f"{'=' * 60}")

    # Save final results
    save_permits(unique, f"southlake_permits_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    save_permits(unique, "southlake_permits_latest.json")

    # Analyze verticals
    analyze_verticals(unique)


if __name__ == "__main__":
    asyncio.run(main())
