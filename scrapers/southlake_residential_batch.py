#!/usr/bin/env python3
"""
Batch scraper for Southlake residential permits.
Downloads up to 1000 permits for each residential permit type.
"""
import asyncio
import os
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright

DOWNLOAD_DIR = Path(__file__).parent.parent / "data" / "downloads"
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

# High-value residential permit types
RESIDENTIAL_TYPES = [
    "Residential New Building (Single Family Home)",
    "Residential New Building (Duplex)",
    "Residential New Building (Townhome)",
    "Residential Remodel",
    "Residential Addition Conditioned Space",
    "Residential Addition Conditioned & Uncond",
    "Pool & Spa (Residential)",
    "Pool (Residential)",
    "Electrical Permit (Residential)",
    "Mechanical Permit (Residential)",
    "Plumbing Permit (Residential)",
    "Residential Reroof",
    "Fence (Residential)",
    "Solar Panel - Residential",
]

async def scrape_permit_type(page, permit_type: str) -> dict:
    """Scrape permits for a single permit type."""
    result = {"type": permit_type, "count": 0, "file": None, "error": None}

    try:
        # Go to search page (fresh load each time)
        await page.goto("https://energov.cityofsouthlake.com/EnerGov_Prod/SelfService#/search", wait_until="networkidle")
        await page.wait_for_timeout(3000)

        # Select Permit module
        await page.select_option('#SearchModule', label='Permit')
        await page.wait_for_timeout(2000)

        # Click Advanced and wait for form to load
        await page.click('button:has-text("Advanced")')
        await page.wait_for_timeout(3000)

        # Select permit type - find dropdown by option text (wait for it)
        permit_select = page.locator('select:has(option:text("--Select Permit Type--"))')
        try:
            await permit_select.wait_for(state="attached", timeout=5000)
        except:
            pass  # Continue anyway, will check count below
        if await permit_select.count() > 0:
            await permit_select.select_option(label=permit_type)
            print(f"    Selected: {permit_type}")
        else:
            result["error"] = "Could not find permit type dropdown"
            return result

        await page.wait_for_timeout(1000)

        # Search
        await page.click('button:has-text("Search")')
        await page.wait_for_timeout(10000)  # Longer wait for results

        # Click Export - wait for it to become visible
        export_btn = page.locator('button#button-Export, button:has-text("Export")')
        try:
            await export_btn.first.wait_for(state="visible", timeout=15000)
            print(f"    Export button visible")
        except:
            # Check if there's a "no records" specific message
            no_records = page.locator('text="No records found", text="No results"')
            if await no_records.count() > 0:
                result["error"] = "No results found for this permit type"
            else:
                result["error"] = "Export button not visible after search"
            return result

        await export_btn.first.click()
        await page.wait_for_timeout(2000)

        # Select "Export Current View" (gets all filtered results)
        current_view = page.locator('text="Export Current View"')
        if await current_view.count() > 0:
            await current_view.click()
            await page.wait_for_timeout(500)

        # Fill filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_type = permit_type.replace(' ', '_').replace('(', '').replace(')', '').lower()
        filename = f"southlake_{safe_type}"

        modal_input = page.locator('#FilenameModal input[type="text"]')
        if await modal_input.count() > 0:
            await modal_input.fill(filename)
            await page.wait_for_timeout(500)

        # Download
        filepath = DOWNLOAD_DIR / f"{filename}.xlsx"
        async with page.expect_download(timeout=60000) as download_info:
            await page.click('#FilenameModal button:has-text("Ok")')

        download = await download_info.value
        await download.save_as(str(filepath))

        # Count lines
        with open(filepath, 'r', errors='ignore') as f:
            lines = len(f.readlines()) - 1  # Subtract header

        result["count"] = lines
        result["file"] = str(filepath)

    except Exception as e:
        result["error"] = str(e)

    return result

async def batch_scrape():
    """Scrape all residential permit types."""
    print("=" * 60)
    print("SOUTHLAKE RESIDENTIAL BATCH SCRAPER")
    print("=" * 60)
    print(f"Types to scrape: {len(RESIDENTIAL_TYPES)}")
    print(f"Time: {datetime.now().isoformat()}\n")

    results = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # Visible for reliability
        context = await browser.new_context(accept_downloads=True)
        page = await context.new_page()

        for i, permit_type in enumerate(RESIDENTIAL_TYPES, 1):
            print(f"\n[{i}/{len(RESIDENTIAL_TYPES)}] {permit_type}")
            print("-" * 50)

            try:
                result = await scrape_permit_type(page, permit_type)
                results.append(result)

                if result["error"]:
                    print(f"    ERROR: {result['error']}")
                else:
                    print(f"    SUCCESS: {result['count']} permits -> {result['file']}")
            except Exception as e:
                print(f"    EXCEPTION: {e}")
                results.append({"type": permit_type, "count": 0, "file": None, "error": str(e)})
                # Try to recover by creating new page
                try:
                    await page.close()
                except:
                    pass
                page = await context.new_page()

            # Brief pause between types
            try:
                await page.wait_for_timeout(2000)
            except:
                page = await context.new_page()

        await browser.close()

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    total = 0
    for r in results:
        status = f"{r['count']} permits" if not r['error'] else f"ERROR: {r['error'][:50]}"
        print(f"  {r['type'][:45]:45} | {status}")
        total += r['count']

    print(f"\nTOTAL: {total} permits across {len(RESIDENTIAL_TYPES)} types")

    return results

if __name__ == "__main__":
    asyncio.run(batch_scrape())
