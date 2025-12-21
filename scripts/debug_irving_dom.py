#!/usr/bin/env python3
"""Debug script to capture Irving MGO search page DOM structure."""
import asyncio
import json
import os
from pathlib import Path
from dotenv import load_dotenv
from playwright.async_api import async_playwright

# Load environment variables
load_dotenv()
MGO_EMAIL = os.getenv('MGO_EMAIL')
MGO_PASSWORD = os.getenv('MGO_PASSWORD')

async def capture_dom():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1400, 'height': 900},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        page = await context.new_page()

        # Login
        print('[1] Logging in...')
        await page.goto('https://www.mgoconnect.org/cp/login', wait_until='networkidle', timeout=60000)
        await asyncio.sleep(2)
        await page.fill('input[type="email"]', MGO_EMAIL)
        await page.fill('input[type="password"]', MGO_PASSWORD)

        login_btn = page.locator('button:has-text("Login")').first
        await login_btn.click()
        await asyncio.sleep(5)

        if 'login' in page.url:
            print('[1] Login FAILED - still on login page')
            await page.screenshot(path='debug_html/irving_login_failed.png')
            await browser.close()
            return

        print('[1] Login SUCCESS')

        # Select Irving jurisdiction
        print('[2] Selecting Irving...')
        await page.goto('https://www.mgoconnect.org/cp/home', wait_until='networkidle')
        await asyncio.sleep(2)

        # Click state dropdown and select Texas
        state_dropdown = page.locator('.p-dropdown').first
        await state_dropdown.click()
        await asyncio.sleep(1)
        await page.locator('.p-dropdown-item:has-text("Texas")').click()
        await asyncio.sleep(2)

        # Click jurisdiction dropdown and select Irving
        jurisdiction_dropdown = page.locator('.p-dropdown').nth(1)
        await jurisdiction_dropdown.click()
        await asyncio.sleep(1)
        await page.keyboard.type('irvi', delay=100)
        await asyncio.sleep(1)
        await page.locator('.p-dropdown-item:has-text("irving")').first.click()
        await asyncio.sleep(2)

        # Click Continue
        await page.click('button:has-text("Continue")')
        await asyncio.sleep(3)
        print('[2] Irving selected')

        # Navigate to search
        print('[3] Navigating to search page...')
        await page.goto('https://mgoconnect.org/cp/search', wait_until='networkidle')
        await asyncio.sleep(3)

        # Scroll to top to see full form
        await page.evaluate('window.scrollTo(0, 0)')
        await asyncio.sleep(1)

        # Take full page screenshot
        await page.screenshot(path='debug_html/irving_full_page.png', full_page=True)
        print('[3] Full page screenshot saved')

        # Capture all input fields
        print('[4] Capturing DOM structure...')
        dom_info = await page.evaluate('''() => {
            const result = {
                inputs: [],
                buttons: [],
                dropdowns: [],
                accordions: [],
                sections: []
            };

            // All inputs
            document.querySelectorAll('input').forEach(el => {
                result.inputs.push({
                    name: el.name || '',
                    id: el.id || '',
                    type: el.type || '',
                    placeholder: el.placeholder || '',
                    class: el.className || '',
                    visible: el.offsetParent !== null,
                    value: el.value || ''
                });
            });

            // All buttons
            document.querySelectorAll('button').forEach(el => {
                result.buttons.push({
                    text: el.textContent?.trim() || '',
                    class: el.className || '',
                    disabled: el.disabled
                });
            });

            // PrimeNG dropdowns
            document.querySelectorAll('.p-dropdown').forEach(el => {
                result.dropdowns.push({
                    label: el.querySelector('.p-dropdown-label')?.textContent || '',
                    class: el.className || ''
                });
            });

            // Accordion panels (collapsed sections)
            document.querySelectorAll('.p-accordion-header, .p-panel-header, [class*="collapse"], [class*="accordion"]').forEach(el => {
                result.accordions.push({
                    text: el.textContent?.trim().substring(0, 100) || '',
                    class: el.className || '',
                    expanded: el.getAttribute('aria-expanded') || 'unknown'
                });
            });

            // Form sections
            document.querySelectorAll('form, [class*="form"], [class*="search"]').forEach(el => {
                result.sections.push({
                    tag: el.tagName,
                    class: el.className || '',
                    childCount: el.children.length
                });
            });

            return result;
        }''')

        # Save DOM analysis
        with open('debug_html/irving_dom_analysis.json', 'w') as f:
            json.dump(dom_info, f, indent=2)
        print('[4] DOM analysis saved')

        # Print summary
        print(f'\n=== DOM SUMMARY ===')
        print(f'Inputs: {len(dom_info["inputs"])}')
        print(f'Buttons: {len(dom_info["buttons"])}')
        print(f'Dropdowns: {len(dom_info["dropdowns"])}')
        print(f'Accordions: {len(dom_info["accordions"])}')

        # Find date-related inputs
        print(f'\n=== DATE-RELATED INPUTS ===')
        for inp in dom_info['inputs']:
            if any(kw in (inp['name'] + inp['placeholder'] + inp['id']).lower()
                   for kw in ['date', 'created', 'after', 'before', 'from', 'to']):
                print(f"  {inp}")

        await browser.close()

if __name__ == '__main__':
    asyncio.run(capture_dom())
