#!/usr/bin/env python3
"""
Irving (MGO Connect) PDF Sampler

Goal: Download ONE sample PDF to analyze structure before writing parser.
This is a discovery script, not a production scraper.

Usage:
    python scrapers/irving_pdf_sampler.py

Requires:
    MGO_EMAIL and MGO_PASSWORD in .env
"""
import os
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from playwright.async_api import async_playwright

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Output directory
SAMPLE_DIR = Path(__file__).parent.parent / "data" / "samples"
SAMPLE_DIR.mkdir(parents=True, exist_ok=True)

MGO_EMAIL = os.getenv("MGO_EMAIL")
MGO_PASSWORD = os.getenv("MGO_PASSWORD")

if not MGO_EMAIL or not MGO_PASSWORD:
    raise ValueError("MGO_EMAIL and MGO_PASSWORD must be set in .env")


async def download_irving_pdf_sample():
    """
    Login to Irving MGO Connect and download ONE PDF sample.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # Visible for debugging
        context = await browser.new_context(accept_downloads=True)
        page = await context.new_page()

        try:
            # Navigate to Irving MGO Connect login
            logger.info("Navigating to MGO Connect login...")
            await page.goto("https://www.mgoconnect.org/cp/login", timeout=60000)
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(2)

            # Check if already logged in
            if 'login' not in page.url:
                logger.info("Already logged in")
            else:
                # Login
                logger.info("Logging in...")
                await page.wait_for_selector('input[type="email"]', timeout=10000)
                await page.fill('input[type="email"]', MGO_EMAIL)
                await page.fill('input[type="password"]', MGO_PASSWORD)

                # Click login button
                login_btn = page.locator('button:has-text("Login")').first
                await login_btn.click(timeout=5000)
                await asyncio.sleep(5)

                # Check if login succeeded
                if "login" in page.url.lower():
                    logger.error("Login failed - still on login page")
                    await page.screenshot(path=str(SAMPLE_DIR / "login_failed.png"))
                    return None

                logger.info("Login successful")

            # Navigate to home page to select jurisdiction
            logger.info("Navigating to home page to select Irving...")
            await page.goto('https://www.mgoconnect.org/cp/home', wait_until='networkidle', timeout=60000)
            await asyncio.sleep(3)

            # Select State: Texas
            logger.info("Selecting State: Texas...")
            state_dropdown = page.locator('.p-dropdown').first
            await state_dropdown.click()
            await asyncio.sleep(1)

            texas_option = page.locator('.p-dropdown-item:has-text("Texas")')
            await texas_option.click()
            logger.info("Texas selected")

            # Wait for jurisdiction dropdown to populate
            logger.info("Waiting for jurisdiction dropdown to populate...")
            await page.wait_for_function('''() => {
                const dropdowns = document.querySelectorAll('.p-dropdown');
                if (dropdowns.length < 2) return false;
                const jurisdictionDropdown = dropdowns[1];
                return !jurisdictionDropdown.classList.contains('p-disabled') &&
                       !jurisdictionDropdown.querySelector('.p-dropdown-label')?.textContent?.includes('Select');
            }''', timeout=15000)
            await asyncio.sleep(2)

            # Select Jurisdiction: Irving
            logger.info("Selecting Jurisdiction: Irving...")
            jurisdiction_dropdown = page.locator('.p-dropdown').nth(1)
            await jurisdiction_dropdown.click()
            await asyncio.sleep(1)

            # Type to filter
            await page.keyboard.type("Irvi", delay=100)
            await asyncio.sleep(1)

            # Click Irving option
            city_option = page.locator('.p-dropdown-item:has-text("Irving")')
            if await city_option.count() == 0:
                logger.error("Irving not found in jurisdiction list")
                await page.screenshot(path=str(SAMPLE_DIR / "irving_not_found.png"))
                return None

            await city_option.first.click()
            logger.info("Irving selected")
            await asyncio.sleep(2)

            # Click Continue button
            logger.info("Clicking Continue...")
            continue_btn = page.locator('button:has-text("Continue")')
            await continue_btn.click()
            await asyncio.sleep(5)

            logger.info(f"Current URL after Continue: {page.url}")

            # Look for Advanced Reporting link
            logger.info("Looking for Advanced Reporting link...")
            advanced_link = page.locator('text=Click here for advanced reporting')

            if await advanced_link.count() == 0:
                # Try to find the search permits link instead
                logger.info("Advanced Reporting not visible, trying Search Permits...")
                search_permits_link = page.locator('a:has-text("Search Permits")')

                if await search_permits_link.count() > 0:
                    await search_permits_link.first.click(timeout=10000)
                    await asyncio.sleep(5)
                    logger.info("Navigated to Search Permits")
                else:
                    logger.warning("Could not find navigation links, taking screenshot for analysis")
                    await page.screenshot(path=str(SAMPLE_DIR / "irving_no_nav_links.png"), full_page=True)

                    # Save page content for debugging
                    content = await page.content()
                    with open(SAMPLE_DIR / "irving_page_content.html", "w") as f:
                        f.write(content)

                    return None

            # If we found the advanced reporting link, click it
            if await advanced_link.count() > 0:
                await advanced_link.click(timeout=5000)
                await asyncio.sleep(3)
                logger.info("Advanced Reporting page opened")

                # Look for View Report buttons
                view_btns = page.locator('button:has-text("View Report")')
                btn_count = await view_btns.count()
                logger.info(f"Found {btn_count} View Report buttons")

                if btn_count == 0:
                    logger.warning("No View Report buttons found")
                    await page.screenshot(path=str(SAMPLE_DIR / "irving_no_view_report_btn.png"), full_page=True)
                    return None

                # Click the LAST View Report button (Open Records Data Export)
                logger.info("Clicking last View Report button (Open Records Data Export)...")
                await view_btns.last.click(timeout=10000)
                await asyncio.sleep(5)

                logger.info(f"Export page URL: {page.url}")
                await page.screenshot(path=str(SAMPLE_DIR / "irving_export_page.png"), full_page=True)

                # Check for PDF export button/link
                pdf_btn = page.locator("button:has-text('View Report'), button:has-text('Generate'), button:has-text('Export'), a:has-text('PDF')")

                if await pdf_btn.count() > 0:
                    logger.info("Found PDF export button, attempting download...")

                    try:
                        # Wait for download
                        async with page.expect_download(timeout=60000) as download_info:
                            await pdf_btn.first.click()
                            logger.info("Clicked export button, waiting for download...")

                        download = await download_info.value

                        # Save sample
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        sample_path = SAMPLE_DIR / f"irving_sample_{timestamp}.pdf"
                        await download.save_as(str(sample_path))

                        file_size = os.path.getsize(sample_path)
                        logger.info(f"Downloaded: {sample_path} ({file_size} bytes)")

                        if file_size < 1000:
                            logger.warning("File very small - may be empty or error page")

                        return str(sample_path)

                    except Exception as e:
                        logger.error(f"Download failed: {e}")
                        logger.info("This report may require date inputs or other parameters first")

                        # Take screenshot of current state
                        await page.screenshot(path=str(SAMPLE_DIR / "irving_export_error.png"), full_page=True)

                        # Save page content
                        content = await page.content()
                        with open(SAMPLE_DIR / "irving_export_page_content.html", "w") as f:
                            f.write(content)

                        return None
                else:
                    logger.warning("No PDF export button found on this page")
                    await page.screenshot(path=str(SAMPLE_DIR / "irving_no_pdf_btn.png"), full_page=True)

                    # Save page content
                    content = await page.content()
                    with open(SAMPLE_DIR / "irving_export_page_content.html", "w") as f:
                        f.write(content)

                    return None

        except Exception as e:
            logger.error(f"Error: {e}")
            import traceback
            traceback.print_exc()
            await page.screenshot(path=str(SAMPLE_DIR / "irving_error.png"), full_page=True)
            return None

        finally:
            await browser.close()


if __name__ == "__main__":
    result = asyncio.run(download_irving_pdf_sample())

    if result:
        print(f"\n{'='*50}")
        print(f"SUCCESS: Sample PDF downloaded to {result}")
        print(f"{'='*50}")
        print("\nNext steps:")
        print("1. Open the PDF manually and analyze structure")
        print("2. Check if it's text-based or image-based")
        print("3. Identify table columns and layout")
        print("4. Then implement parser in scrapers/mgo_connect.py")
    else:
        print(f"\n{'='*50}")
        print("FAILED: Could not download PDF sample")
        print(f"{'='*50}")
        print(f"\nCheck {SAMPLE_DIR} for screenshots and debug info")
        print("\nPossible reasons:")
        print("- PDF export requires date range inputs")
        print("- Report page has different layout than expected")
        print("- Irving portal may not support automated PDF downloads")
        print("\nReview screenshots and HTML files in data/samples/")
