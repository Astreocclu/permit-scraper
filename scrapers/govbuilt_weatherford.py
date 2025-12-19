#!/usr/bin/env python3
"""
WEATHERFORD GOVBUILT PERMIT SCRAPER (Playwright)
Portal: GovBuilt
City: Weatherford, TX (Parker County - NO CAD enrichment available)

Usage:
  python3 scrapers/govbuilt_weatherford.py 100
  python3 scrapers/govbuilt_weatherford.py 500

Note: Parker County has no public CAD API, so these permits cannot be enriched with property data.
"""

import asyncio
import json
import logging
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

OUTPUT_DIR = Path(__file__).parent.parent / "data" / "raw"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

GOVBUILT_CONFIG = {
    'name': 'Weatherford',
    'base_url': 'https://permits.weatherfordtx.gov',
    'search_url': 'https://permits.weatherfordtx.gov/ActivitySearchTool',
}


def parse_permit_row(row_text: str) -> dict:
    """Parse a single permit row from the search results."""
    permit = {
        'permit_id': '',
        'permit_type': '',
        'description': '',
        'address': '',
        'city': 'Weatherford',
        'issued_date': '',
        'value': '',
        'contractor_name': '',
        'contractor_phone': '',
        'contractor_email': '',
        'status': '',
        'source': 'govbuilt',
    }

    # This is a placeholder - will need to be adjusted based on actual HTML structure
    # GovBuilt portals typically use DataTables or similar grid structures

    return permit


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((PlaywrightTimeout,)),
    reraise=True
)
async def scrape_weatherford_permits(limit: int = 100) -> list:
    """
    Scrape permits from Weatherford GovBuilt portal.

    Args:
        limit: Maximum number of permits to scrape

    Returns:
        List of permit dictionaries
    """
    permits = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        page = await context.new_page()

        try:
            logger.info(f"Navigating to {GOVBUILT_CONFIG['search_url']}")
            await page.goto(GOVBUILT_CONFIG['search_url'], wait_until='networkidle', timeout=30000)

            # Wait for the page to load
            await page.wait_for_timeout(2000)

            # Look for search form elements
            # GovBuilt typically has a date range filter
            logger.info("Looking for search controls...")

            # Try to find date inputs
            date_inputs = await page.locator('input[type="date"], input[name*="date"], input[id*="date"]').all()
            if date_inputs:
                logger.info(f"Found {len(date_inputs)} date input fields")

                # Set date range to last 90 days
                end_date = datetime.now()
                start_date = end_date - timedelta(days=90)

                # Fill in date fields (format may need adjustment)
                for i, date_input in enumerate(date_inputs):
                    try:
                        if i == 0:  # Assume first is start date
                            await date_input.fill(start_date.strftime('%m/%d/%Y'))
                        elif i == 1:  # Assume second is end date
                            await date_input.fill(end_date.strftime('%m/%d/%Y'))
                    except Exception as e:
                        logger.warning(f"Could not fill date input {i}: {e}")

            # Look for "Days" dropdown or input (common in GovBuilt)
            days_select = page.locator('select[name*="Days"], select[id*="Days"]').first
            if await days_select.count() > 0:
                logger.info("Found Days dropdown")
                await days_select.select_option('90')

            # Look for search/submit button
            search_buttons = await page.locator(
                'button:has-text("Search"), input[type="submit"], button[type="submit"]'
            ).all()

            if search_buttons:
                logger.info("Clicking search button...")
                await search_buttons[0].click()
                await page.wait_for_timeout(3000)

            # Wait for results to load
            # GovBuilt typically uses DataTables or a similar grid
            await page.wait_for_selector('table, .dataTables_wrapper, .search-results', timeout=10000)

            # Try to increase page size (DataTables typically has a "Show X entries" dropdown)
            page_size_select = page.locator('select[name*="length"], select.form-control').first
            if await page_size_select.count() > 0:
                logger.info("Found page size selector, setting to 100")
                try:
                    await page_size_select.select_option('100')
                    await page.wait_for_timeout(2000)
                except Exception as e:
                    logger.warning(f"Could not set page size: {e}")

            logger.info("Extracting permit data from results table...")

            # Try to find the results table
            tables = await page.locator('table').all()
            if not tables:
                logger.warning("No tables found on page")
                # Save screenshot for debugging
                await page.screenshot(path=OUTPUT_DIR / 'weatherford_debug.png')
                # Save HTML for analysis
                html = await page.content()
                (OUTPUT_DIR / 'weatherford_debug.html').write_text(html)
                logger.info(f"Saved debug files to {OUTPUT_DIR}")
                return permits

            logger.info(f"Found {len(tables)} tables")

            # Find the table with permit data (usually the largest one)
            main_table = None
            max_rows = 0

            for table in tables:
                rows = await table.locator('tbody tr').all()
                if len(rows) > max_rows:
                    max_rows = len(rows)
                    main_table = table

            if not main_table:
                logger.warning("Could not identify main data table")
                return permits

            logger.info(f"Processing {max_rows} rows from main table")

            # Extract header columns to understand structure
            headers = []
            header_cells = await main_table.locator('thead th, thead td').all()
            for cell in header_cells:
                text = await cell.inner_text()
                headers.append(text.strip())

            logger.info(f"Table headers: {headers}")

            # Process rows with pagination support
            page_num = 1
            max_pages = 10  # Safety limit

            while len(permits) < limit and page_num <= max_pages:
                # Get current page rows
                rows = await main_table.locator('tbody tr').all()

                logger.info(f"Page {page_num}: Processing {len(rows)} rows (total permits so far: {len(permits)})")

                for i, row in enumerate(rows):
                    if len(permits) >= limit:
                        break

                    if len(permits) % 10 == 0 and len(permits) > 0:
                        logger.info(f"Processed {len(permits)} permits...")

                    try:
                        cells = await row.locator('td').all()
                        cell_texts = []
                        for cell in cells:
                            text = await cell.inner_text()
                            cell_texts.append(text.strip())

                        # Map cells to permit fields based on headers
                        permit = {
                            'city': 'Weatherford',
                            'source': 'govbuilt',
                        }

                        # GovBuilt Weatherford column mappings based on actual structure:
                        # ['#Reference', 'Classification', 'Type', 'Sub-Type', 'Name', 'Address',
                        #  'Phone Number', 'Created Date', 'Last Activity', 'Status', 'Map', 'View', 'Score']
                        for j, header in enumerate(headers):
                            if j >= len(cell_texts):
                                continue

                            header_lower = header.lower()
                            value = cell_texts[j]

                            if not value or value == '—' or value == '-':
                                continue

                            if '#reference' in header_lower or header == '#Reference':
                                permit['permit_id'] = value
                            elif header == 'Type':
                                permit['permit_type'] = value
                            elif header == 'Sub-Type':
                                if 'description' not in permit:
                                    permit['description'] = value
                                else:
                                    permit['description'] += f" - {value}"
                            elif header == 'Classification':
                                # Could be Permit, License, etc.
                                if not permit.get('permit_type'):
                                    permit['permit_type'] = value
                            elif header == 'Name':
                                # This might be applicant/contractor name
                                permit['contractor_name'] = value
                            elif header == 'Address':
                                permit['address'] = value
                            elif header == 'Phone Number':
                                permit['contractor_phone'] = value
                            elif header == 'Created Date':
                                permit['issued_date'] = value
                            elif header == 'Status':
                                permit['status'] = value

                        # Only add if we got at least a permit ID
                        if permit.get('permit_id'):
                            permits.append(permit)
                        else:
                            logger.debug(f"Row {i} missing permit_id, cell_texts: {cell_texts}")

                    except Exception as e:
                        logger.warning(f"Error processing row {i}: {e}")
                        continue

                # Check if we've hit the limit
                if len(permits) >= limit:
                    break

                # Try to go to next page
                next_button = page.locator('button:has-text("Next"), a:has-text("Next"), .paginate_button.next').first
                if await next_button.count() > 0:
                    # Check if Next button is disabled
                    is_disabled = await next_button.get_attribute('disabled')
                    classes = await next_button.get_attribute('class') or ''

                    if is_disabled or 'disabled' in classes:
                        logger.info("Next button is disabled - no more pages")
                        break

                    logger.info(f"Clicking Next to go to page {page_num + 1}")
                    await next_button.click()
                    await page.wait_for_timeout(2000)
                    page_num += 1
                else:
                    logger.info("No Next button found - single page only")
                    break

            logger.info(f"Successfully scraped {len(permits)} permits")

            # Save a screenshot of results for verification
            await page.screenshot(path=OUTPUT_DIR / 'weatherford_results.png')

        except PlaywrightTimeout as e:
            logger.error(f"Timeout error: {e}")
            await page.screenshot(path=OUTPUT_DIR / 'weatherford_timeout.png')
            raise
        except Exception as e:
            logger.error(f"Scraping error: {e}")
            await page.screenshot(path=OUTPUT_DIR / 'weatherford_error.png')
            raise
        finally:
            await browser.close()

    return permits


async def main():
    """Main entry point."""
    limit = 100
    if len(sys.argv) > 1:
        try:
            limit = int(sys.argv[1])
        except ValueError:
            logger.error(f"Invalid limit: {sys.argv[1]}")
            sys.exit(1)

    logger.info(f"Starting Weatherford GovBuilt scraper (limit: {limit})")
    logger.info("Note: Parker County has no public CAD API - no enrichment available")

    permits = await scrape_weatherford_permits(limit)

    if permits:
        output_file = OUTPUT_DIR / 'weatherford_govbuilt.json'
        with open(output_file, 'w') as f:
            json.dump(permits, f, indent=2)

        logger.info(f"Saved {len(permits)} permits to {output_file}")

        # Print sample
        if permits:
            logger.info("\nSample permit:")
            logger.info(json.dumps(permits[0], indent=2))
    else:
        logger.warning("No permits scraped - check debug files in data/raw/")

    return permits


if __name__ == '__main__':
    asyncio.run(main())
