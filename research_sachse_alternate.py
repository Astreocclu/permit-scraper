#!/usr/bin/env python3
"""
Alternative research script - try different URL variations
"""

import asyncio
import json
from playwright.async_api import async_playwright

async def test_url_variations():
    """Test different URL variations to find the correct endpoint"""

    base_urls = [
        "https://pl-sachse-tx.smartgovcommunity.com",
        "https://pl-sachse-tx.smartgovcommunity.com/Public",
        "https://pl-sachse-tx.smartgovcommunity.com/Public/Home",
        "https://pl-sachse-tx.smartgovcommunity.com/public",
        "https://sachse-tx.smartgovcommunity.com",
        "https://www.sachse-tx.smartgovcommunity.com",
        "https://sachse.smartgovcommunity.com",
    ]

    results = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        page = await context.new_page()

        for url in base_urls:
            print(f"\nTrying: {url}")
            try:
                response = await page.goto(url, wait_until='domcontentloaded', timeout=15000)
                status = response.status
                title = await page.title()

                result = {
                    'url': url,
                    'status': status,
                    'title': title,
                    'accessible': status < 400
                }

                print(f"  Status: {status}")
                print(f"  Title: {title}")

                if status < 400 and title:
                    # Take screenshot of successful page
                    screenshot_name = url.replace('https://', '').replace('/', '_') + '.png'
                    await page.screenshot(path=f'/home/reid/testhome/permit-scraper/{screenshot_name}')
                    print(f"  Screenshot saved: {screenshot_name}")

                    # Get some page content info
                    html = await page.content()
                    result['has_permit_text'] = 'permit' in html.lower()
                    result['has_search'] = 'search' in html.lower()
                    result['html_length'] = len(html)

                    print(f"  Has 'permit': {result['has_permit_text']}")
                    print(f"  Has 'search': {result['has_search']}")
                    print(f"  HTML length: {result['html_length']} chars")

                    # Wait a bit to see the page
                    await asyncio.sleep(3)

                results.append(result)

            except Exception as e:
                print(f"  Error: {e}")
                results.append({
                    'url': url,
                    'status': 'error',
                    'error': str(e)
                })

            await asyncio.sleep(1)

        print("\n\nKeeping browser open for 20 seconds for manual inspection...")
        await asyncio.sleep(20)

        await browser.close()

    # Save results
    with open('/home/reid/testhome/permit-scraper/url_variations_test.json', 'w') as f:
        json.dump(results, f, indent=2)

    print("\n" + "="*80)
    print("ACCESSIBLE URLs:")
    print("="*80)
    for result in results:
        if result.get('accessible'):
            print(f"✓ {result['url']} (Status: {result['status']})")
            print(f"  Title: {result.get('title', 'N/A')}")

    print("\n" + "="*80)
    print("FAILED URLs:")
    print("="*80)
    for result in results:
        if not result.get('accessible'):
            print(f"✗ {result['url']} (Status: {result.get('status', 'error')})")

    return results

if __name__ == "__main__":
    print("Testing URL variations for Sachse SmartGov...")
    asyncio.run(test_url_variations())
