# scrapers/westlake_spike.py
"""
Spike: Verify Westlake MyGov autocomplete endpoint.
Run this to confirm we can harvest addresses from autocomplete.
"""
import asyncio
from playwright.async_api import async_playwright

WESTLAKE_URL = "https://public.mygov.us/westlake_tx/lookup"

async def spike_autocomplete():
    """Type a street name and capture autocomplete responses."""

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # Visible for debugging
        page = await browser.new_page()

        # Capture network requests
        addresses_found = []

        async def handle_response(response):
            if 'autocomplete' in response.url.lower() or 'search' in response.url.lower():
                try:
                    data = await response.json()
                    print(f"FOUND API: {response.url}")
                    print(f"DATA: {data}")
                    addresses_found.append(data)
                except:
                    pass

        page.on("response", handle_response)

        await page.goto(WESTLAKE_URL)
        await page.wait_for_timeout(2000)

        # Look for address input field
        address_input = page.locator('input[placeholder*="address" i], input[name*="address" i], input#address')

        if await address_input.count() > 0:
            print("Found address input field")
            await address_input.first.fill("Vaquero")
            await page.wait_for_timeout(3000)  # Wait for autocomplete

            # Try to find dropdown options
            options = page.locator('.autocomplete-item, .ui-menu-item, [role="option"], .dropdown-item')
            count = await options.count()
            print(f"Found {count} autocomplete options in DOM")

            for i in range(min(count, 10)):
                text = await options.nth(i).text_content()
                print(f"  Option {i}: {text}")
        else:
            print("Could not find address input field")
            # List all inputs for debugging
            inputs = page.locator('input')
            for i in range(await inputs.count()):
                inp = inputs.nth(i)
                placeholder = await inp.get_attribute('placeholder') or ''
                name = await inp.get_attribute('name') or ''
                print(f"  Input {i}: placeholder='{placeholder}' name='{name}'")

        await browser.close()

        return addresses_found

if __name__ == "__main__":
    results = asyncio.run(spike_autocomplete())
    print(f"\nSPIKE COMPLETE: Found {len(results)} API responses")
