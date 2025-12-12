#!/usr/bin/env python3
"""
EnerGov Portal Diagnosis Tool

Captures HTML snapshots and screenshots from McKinney and Allen
to diagnose why scrapers are failing.

Run: python scripts/diagnose_energov.py
Output: debug_html/energov_{city}_diag.{png,html}
"""
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

# Target URLs for diagnosis
ENERGOV_URLS = {
    'mckinney': 'https://egov.mckinneytexas.org/EnerGov_Prod/SelfService#/search',
    'allen': 'https://energovweb.cityofallen.org/EnerGov/SelfService#/search',
    # Working cities for comparison
    'southlake': 'https://southlake-egov.tylerhost.net/EnerGov/SelfService#/search',
    'colleyville': 'https://www.colleyville.com/EnerGov/SelfService#/search',
}

OUTPUT_DIR = Path(__file__).parent.parent / 'debug_html'


async def diagnose_portal(page, city: str, url: str):
    """Capture diagnostic data from a single portal."""
    print(f"\n{'='*50}")
    print(f"Diagnosing: {city.upper()}")
    print(f"URL: {url}")
    print('='*50)

    try:
        # Navigate with extended timeout
        print(f"  [1/5] Navigating...")
        response = await page.goto(url, wait_until='networkidle', timeout=60000)
        print(f"  Status: {response.status if response else 'No response'}")

        # Wait for Angular to settle
        print(f"  [2/5] Waiting for Angular...")
        await asyncio.sleep(5)

        # Check for Cloudflare/challenge pages
        content = await page.content()
        if 'challenge' in content.lower() or 'cloudflare' in content.lower():
            print(f"  WARNING: Possible Cloudflare challenge detected!")

        # Capture screenshot
        print(f"  [3/5] Capturing screenshot...")
        screenshot_path = OUTPUT_DIR / f'energov_{city}_diag.png'
        await page.screenshot(path=str(screenshot_path), full_page=True)
        print(f"  Saved: {screenshot_path}")

        # Capture HTML
        print(f"  [4/5] Capturing HTML...")
        html_path = OUTPUT_DIR / f'energov_{city}_diag.html'
        html_path.write_text(content)
        print(f"  Saved: {html_path}")

        # Extract key selectors
        print(f"  [5/5] Analyzing selectors...")
        selectors = await page.evaluate('''() => {
            const info = {
                searchModule: document.querySelector('#SearchModule')?.outerHTML?.slice(0,200),
                contentPlaceholder: document.querySelector('[id*="ContentPlaceHolder"]')?.id,
                dateInputs: Array.from(document.querySelectorAll('input[type="date"], input[id*="Date"]')).map(e => e.id),
                dropdowns: Array.from(document.querySelectorAll('select, .dropdown, [role="listbox"]')).map(e => e.id || e.className).slice(0,5),
                angularApp: !!document.querySelector('[ng-app], [data-ng-app], .ng-scope'),
                forms: Array.from(document.querySelectorAll('form')).map(f => f.id || f.action).slice(0,3),
            };
            return info;
        }''')

        print(f"\n  Selector Analysis:")
        for key, value in selectors.items():
            print(f"    {key}: {value}")

        return {'status': 'success', 'selectors': selectors}

    except Exception as e:
        print(f"  ERROR: {e}")
        # Try to capture error state
        try:
            await page.screenshot(path=str(OUTPUT_DIR / f'energov_{city}_error.png'))
        except:
            pass
        return {'status': 'error', 'error': str(e)}


async def main():
    """Run diagnosis on all EnerGov portals."""
    print("EnerGov Portal Diagnosis Tool")
    print("="*50)

    # Ensure output directory exists
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    results = {}

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1400, 'height': 900},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        page = await context.new_page()

        for city, url in ENERGOV_URLS.items():
            results[city] = await diagnose_portal(page, city, url)

        await browser.close()

    # Summary
    print("\n" + "="*50)
    print("DIAGNOSIS SUMMARY")
    print("="*50)
    for city, result in results.items():
        status = result.get('status', 'unknown')
        print(f"  {city}: {status}")
        if status == 'error':
            print(f"    Error: {result.get('error', 'Unknown')}")

    print(f"\nDiagnostic files saved to: {OUTPUT_DIR}")
    print("\nNext steps:")
    print("  1. Compare McKinney/Allen HTML to Southlake/Colleyville")
    print("  2. Look for selector differences")
    print("  3. Check for anti-bot mechanisms")


if __name__ == '__main__':
    asyncio.run(main())
