# scrapers/westlake_spike.py
"""
Spike: Verify Westlake MyGov address search.
This portal uses a search (not autocomplete) - type address, press Enter, get results list.
"""
import asyncio
from playwright.async_api import async_playwright

WESTLAKE_URL = "https://public.mygov.us/westlake_tx/lookup"

async def spike_search():
    """Type a street name, press Enter, and capture search results."""

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # Visible for debugging
        page = await browser.new_page()

        # Capture ALL network responses to find the API
        api_responses = []

        async def handle_response(response):
            url = response.url.lower()
            # Look for any API that might return address data
            if any(kw in url for kw in ['lookup', 'search', 'address', 'api', 'query']):
                try:
                    if response.status == 200:
                        data = await response.json()
                        print(f"API FOUND: {response.url}")
                        print(f"  Status: {response.status}")
                        print(f"  Data preview: {str(data)[:200]}...")
                        api_responses.append({'url': response.url, 'data': data})
                except:
                    pass  # Not JSON, skip

        page.on("response", handle_response)

        await page.goto(WESTLAKE_URL)
        await page.wait_for_timeout(2000)

        # Find input - it's a simple text input
        address_input = page.locator('input[type="text"]').first

        print("Typing 'Vaquero' and pressing Enter...")
        await address_input.fill("Vaquero")
        await address_input.press("Enter")

        # Wait for loading spinner to disappear and results to appear
        print("Waiting for results to load...")
        await page.wait_for_timeout(5000)  # Give it more time

        # Look for ANY list-like elements that appeared
        print("\n--- Searching for result elements ---")

        # Try various selectors for result lists
        selectors_to_try = [
            'li',                    # List items
            '.result',               # Result class
            '.address',              # Address class
            '[class*="result"]',     # Any class containing "result"
            '[class*="address"]',    # Any class containing "address"
            '.accordion',            # Accordion items
            '.card',                 # Card components
            'a[href*="lookup"]',     # Links to lookup pages
        ]

        for selector in selectors_to_try:
            elements = page.locator(selector)
            count = await elements.count()
            if count > 0:
                print(f"\n{selector}: Found {count} elements")
                for i in range(min(count, 5)):
                    text = await elements.nth(i).text_content()
                    if text and text.strip():
                        print(f"  [{i}]: {text.strip()[:100]}")

        # Also dump the page HTML structure for debugging
        print("\n--- Page structure (main content) ---")
        main_content = page.locator('main, .content, #content, body > div').first
        if await main_content.count() > 0:
            inner_html = await main_content.inner_html()
            print(inner_html[:1500])

        await page.wait_for_timeout(3000)  # Keep browser open to inspect
        await browser.close()

        return api_responses

if __name__ == "__main__":
    results = asyncio.run(spike_search())
    print(f"\nSPIKE COMPLETE: Found {len(results)} API responses")
