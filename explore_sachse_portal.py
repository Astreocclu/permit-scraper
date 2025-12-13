#!/usr/bin/env python3
"""
Detailed exploration of Sachse portal sections
"""

import asyncio
import json
from playwright.async_api import async_playwright

async def explore_portal():
    """Explore the My Portal section to see if permits are publicly accessible"""

    url = "https://ci-sachse-tx.smartgovcommunity.com"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        page = await context.new_page()

        # Track network requests
        network_log = []
        def log_request(request):
            network_log.append({
                'url': request.url,
                'method': request.method,
                'type': request.resource_type
            })

        def log_response(response):
            if 'application/json' in response.headers.get('content-type', ''):
                print(f"  JSON Response: {response.url[:80]}")

        page.on('request', log_request)
        page.on('response', log_response)

        try:
            print(f"Navigating to {url}...")
            await page.goto(url, wait_until='networkidle')
            await asyncio.sleep(2)

            # Take screenshot of home
            await page.screenshot(path='/home/reid/testhome/permit-scraper/explore_1_home.png')
            print("Screenshot 1: Home page")

            # Try clicking "My Portal"
            print("\n1. Exploring 'My Portal'...")
            my_portal_button = page.locator('text="My Portal"').first
            if await my_portal_button.count() > 0:
                await my_portal_button.click()
                await asyncio.sleep(3)
                await page.screenshot(path='/home/reid/testhome/permit-scraper/explore_2_my_portal.png')
                print("   Clicked 'My Portal' - screenshot saved")

                # Check if login is required
                current_url = page.url
                print(f"   Current URL: {current_url}")

                if 'login' in current_url.lower():
                    print("   LOGIN REQUIRED for My Portal")
                else:
                    print("   No login detected - may have public access")

                # Go back
                await page.goto(url)
                await asyncio.sleep(2)

            # Try "Public Notices"
            print("\n2. Exploring 'Public Notices'...")
            notices_button = page.locator('text="Public Notices"').first
            if await notices_button.count() > 0:
                await notices_button.click()
                await asyncio.sleep(3)
                await page.screenshot(path='/home/reid/testhome/permit-scraper/explore_3_public_notices.png')
                print("   Clicked 'Public Notices' - screenshot saved")
                await page.goto(url)
                await asyncio.sleep(2)

            # Try "Parcel Search"
            print("\n3. Exploring 'Parcel Search'...")
            parcel_button = page.locator('text="Parcel Search"').first
            if await parcel_button.count() > 0:
                await parcel_button.click()
                await asyncio.sleep(3)
                await page.screenshot(path='/home/reid/testhome/permit-scraper/explore_4_parcel_search.png')
                print("   Clicked 'Parcel Search' - screenshot saved")
                await page.goto(url)
                await asyncio.sleep(2)

            # Check if there's a direct search URL
            print("\n4. Trying direct application search URL...")
            search_urls = [
                f"{url}/ApplicationPublic/ApplicationSearch",
                f"{url}/Public/ApplicationSearch",
                f"{url}/ApplicationPublic/ApplicationSearchAdvanced",
            ]

            for search_url in search_urls:
                print(f"   Trying: {search_url}")
                try:
                    response = await page.goto(search_url, wait_until='domcontentloaded', timeout=10000)
                    if response.status == 200:
                        print(f"   SUCCESS! Found search at: {search_url}")
                        await asyncio.sleep(3)
                        screenshot_name = search_url.split('/')[-1] + '.png'
                        await page.screenshot(path=f'/home/reid/testhome/permit-scraper/{screenshot_name}')
                        print(f"   Screenshot: {screenshot_name}")

                        # Check page content
                        html = await page.content()
                        if 'search' in html.lower():
                            print("   Page contains search functionality!")

                        # Look for search fields
                        inputs = await page.locator('input').all()
                        print(f"   Found {len(inputs)} input fields")

                        for inp in inputs[:10]:
                            try:
                                name = await inp.get_attribute('name')
                                placeholder = await inp.get_attribute('placeholder')
                                input_type = await inp.get_attribute('type')
                                print(f"     - {input_type}: {name} ({placeholder})")
                            except:
                                pass

                        break
                except Exception as e:
                    print(f"   Failed: {e}")

            # Keep browser open for manual inspection
            print("\n" + "="*80)
            print("Browser will stay open for 30 seconds for manual exploration...")
            print("="*80)
            await asyncio.sleep(30)

        except Exception as e:
            print(f"Error: {e}")

        finally:
            await browser.close()

        # Save network log for API analysis
        api_calls = [req for req in network_log if any(
            keyword in req['url'].lower()
            for keyword in ['api', 'service', 'data', 'application', 'permit', 'parcel']
        )]

        with open('/home/reid/testhome/permit-scraper/network_log.json', 'w') as f:
            json.dump({
                'all_requests': len(network_log),
                'api_calls': api_calls
            }, f, indent=2)

        print(f"\n\nNetwork log saved. Total requests: {len(network_log)}, API-like: {len(api_calls)}")

if __name__ == "__main__":
    asyncio.run(explore_portal())
