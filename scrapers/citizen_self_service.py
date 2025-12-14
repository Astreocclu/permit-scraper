#!/usr/bin/env python3
"""
CITIZEN SELF SERVICE PERMIT SCRAPER (Playwright Python)
Portal: EnerGov Citizen Self Service (keyword search interface)
Covers: McKinney, Southlake, and similar cities using this interface

This is DIFFERENT from the standard EnerGov Angular SPA.
It uses a simpler keyword search with filter sidebar.

Usage:
  python scrapers/citizen_self_service.py mckinney 100
  python scrapers/citizen_self_service.py southlake 100
  python scrapers/citizen_self_service.py waxahachie 100
"""

import asyncio
import json
import os
import re
import shutil
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
import httpx

load_dotenv()
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

# Stealth mode to bypass bot detection (Cloudflare, etc.)
try:
    from playwright_stealth import Stealth
    STEALTH = Stealth()
except ImportError:
    STEALTH = None
    print("WARN: playwright-stealth not found. Install: pip install playwright-stealth")

try:
    from scrapers.utils import parse_excel_permits
    from scrapers.filters import filter_residential_permits
except ImportError:
    from utils import parse_excel_permits
    from filters import filter_residential_permits

# Download directory
DOWNLOAD_DIR = Path(__file__).parent.parent / "data" / "downloads"
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

# City configurations for Citizen Self Service portals
CSS_CITIES = {
    'mckinney': {
        'name': 'McKinney',
        'base_url': 'https://egov.mckinneytexas.org/EnerGov_Prod/SelfService',
    },
    'southlake': {
        'name': 'Southlake',
        'base_url': 'https://energov.cityofsouthlake.com/EnerGov_Prod/SelfService',
    },
    'colleyville': {
        'name': 'Colleyville',
        'base_url': 'https://selfservice.colleyville.com/energov_prod/selfservice',
    },
    'allen': {
        'name': 'Allen',
        'base_url': 'https://energovweb.cityofallen.org/EnerGov/SelfService',
    },
    'trophy_club': {
        'name': 'Trophy Club',
        'base_url': 'https://energovweb.trophyclub.org/energovprod/selfservice',
    },
    'waxahachie': {
        'name': 'Waxahachie',
        'base_url': 'https://waxahachietx-energovpub.tylerhost.net/Apps/SelfService',
    },
    'cedar_hill': {
        'name': 'Cedar Hill',
        'base_url': 'https://cedarhilltx-energovpub.tylerhost.net/Apps/SelfService',
    },
    'desoto': {
        'name': 'DeSoto',
        'base_url': 'https://cityofdesototx-energovweb.tylerhost.net/apps/selfservice',
    },
    'mesquite': {
        'name': 'Mesquite',
        'base_url': 'https://energov.cityofmesquite.com/EnerGov_Prod/SelfService',
        'default_permit_types': ['Building-Residential Addition/Remodel', 'Building-New Residential Building', 'Building-Residential Accessory Structure'],
        'skip_permit_type_filter': True,  # Angular dropdown bug - filter in Python instead
    },
    'hurst': {
        'name': 'Hurst',
        'base_url': 'https://energov.hursttx.gov/EnerGov_Prod/SelfService',
    },
    'farmers_branch': {
        'name': 'Farmers Branch',
        'base_url': 'https://egselfservice.farmersbranchtx.gov/EnerGov_Prod/SelfService',
    },
    'coppell': {
        'name': 'Coppell',
        'base_url': 'https://muniselfservice.coppelltx.gov/css',
        # Coppell uses newer Tyler Civic Access - may need skip_permit_type_filter
        'skip_permit_type_filter': True,
    },
    'north_richland_hills': {
        'name': 'North Richland Hills',
        'base_url': 'https://selfservice.nrhtx.com/energov_prod/selfservice',
    },
}

DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')


async def call_deepseek(prompt: str) -> str:
    """Call DeepSeek API for extraction."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            'https://api.deepseek.com/v1/chat/completions',
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {DEEPSEEK_API_KEY}'
            },
            json={
                'model': 'deepseek-chat',
                'messages': [{'role': 'user', 'content': prompt}],
                'temperature': 0.1,
                'max_tokens': 4000
            },
            timeout=60.0
        )
        data = response.json()
        return data.get('choices', [{}])[0].get('message', {}).get('content', '')


def parse_json(text: str) -> dict | None:
    """Parse JSON from text, handling markdown code blocks."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    match = re.search(r'```(?:json)?\s*([\s\S]*?)```', text) or re.search(r'(\{[\s\S]*\})', text)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    return None


def clean_html(html: str) -> str:
    """Remove scripts, styles, and normalize whitespace."""
    html = re.sub(r'<style[^>]*>[\s\S]*?</style>', '', html, flags=re.IGNORECASE)
    html = re.sub(r'<script[^>]*>[\s\S]*?</script>', '', html, flags=re.IGNORECASE)
    html = re.sub(r'<!--[\s\S]*?-->', '', html)
    html = re.sub(r'<svg[^>]*>[\s\S]*?</svg>', '', html, flags=re.IGNORECASE)
    html = re.sub(r'\s+', ' ', html)
    return html


async def download_excel_export(page, city: str, timeout_ms: int = 60000, export_current_view: bool = False, permit_type: str = None) -> Optional[str]:
    """
    Click Export button, handle the export modal, and wait for download.

    Args:
        page: Playwright page
        city: City name for filename
        timeout_ms: Max wait time for download (default 60s)
        export_current_view: If True, export filtered results; if False, export first 500/1000
        permit_type: Optional permit type for filename

    Returns:
        Path to downloaded file, or None if failed
    """
    try:
        # Find and click the Export button - use JavaScript to find visible one
        clicked = await page.evaluate('''() => {
            // Find all Export buttons/links
            const buttons = document.querySelectorAll('button, a');
            for (const btn of buttons) {
                const text = btn.textContent || '';
                if (text.includes('Export') && !btn.classList.contains('ng-hide')) {
                    // Check if actually visible
                    const style = window.getComputedStyle(btn);
                    if (style.display !== 'none' && style.visibility !== 'hidden') {
                        btn.click();
                        return true;
                    }
                }
            }
            return false;
        }''')

        if not clicked:
            print(f"[{city}] Export button not found or not visible")
            return None
        print(f"[{city}] Clicked Export, checking for modal...")
        await asyncio.sleep(1)

        # Check for Export Options modal and fill it
        # Try specific modal ID first, then fall back to generic selectors
        modal_input = page.locator('#FilenameModal input[type="text"], .modal input[type="text"], [role="dialog"] input[type="text"]')
        if await modal_input.count() > 0:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            # Include permit type in filename if specified
            if permit_type:
                safe_type = permit_type.replace(' ', '_').replace('(', '').replace(')', '').lower()
                filename_base = f"{city.lower()}_{timestamp}_{safe_type}"
            else:
                filename_base = f"{city.lower()}_{timestamp}"
            await modal_input.first.fill(filename_base)
            print(f"[{city}] Filled filename in export modal")

            # Select export option based on filter
            if export_current_view:
                # Click "Export Current View" radio button (last radio = current view)
                # Try multiple selectors for different EnerGov versions
                current_view_clicked = False

                # Try clicking the label text first
                label = page.locator('label:has-text("Export Current View"), label:has-text("Current View")')
                if await label.count() > 0:
                    await label.first.click()
                    current_view_clicked = True
                    print(f"[{city}] Clicked 'Export Current View' label")
                else:
                    # Try the last radio button (usually current view)
                    radios = page.locator('input[type="radio"]')
                    radio_count = await radios.count()
                    if radio_count > 1:
                        await radios.last.check()
                        current_view_clicked = True
                        print(f"[{city}] Checked last radio button (Current View)")

                if not current_view_clicked:
                    print(f"[{city}] WARNING: Could not find Export Current View option")

                await asyncio.sleep(0.5)
            else:
                # Ensure "Export first 500/1000 Results" is selected (should be default)
                export_default_radio = page.locator('input[type="radio"]').first
                if await export_default_radio.count() > 0:
                    await export_default_radio.check()

            # Wait for download after clicking Ok
            ok_btn = page.locator('button:has-text("Ok"), button:has-text("OK")')
            if await ok_btn.count() > 0:
                async with page.expect_download(timeout=timeout_ms) as download_info:
                    await ok_btn.first.click()
                    print(f"[{city}] Clicked Ok, waiting for download...")

                download = await download_info.value

                # Save to our download directory (use filename_base which includes permit type if set)
                filename = f"{filename_base}.xlsx"
                dest_path = DOWNLOAD_DIR / filename

                await download.save_as(str(dest_path))

                print(f"[{city}] Downloaded: {dest_path}")
                return str(dest_path)
        else:
            # No modal - try direct download (older portal version)
            print(f"[{city}] No modal detected, trying direct download...")
            async with page.expect_download(timeout=timeout_ms) as download_info:
                # Already clicked, just wait
                pass

            download = await download_info.value
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{city.lower()}_{timestamp}.xlsx"
            dest_path = DOWNLOAD_DIR / filename
            await download.save_as(str(dest_path))
            print(f"[{city}] Downloaded: {dest_path}")
            return str(dest_path)

    except Exception as e:
        print(f"[{city}] Download failed: {e}")
        return None


async def scrape(city_key: str, target_count: int = 100, permit_type: str = None):
    """Scrape permits from Citizen Self Service portal.

    Args:
        city_key: City identifier (e.g., 'southlake', 'mckinney')
        target_count: Target number of permits to scrape
        permit_type: Optional permit type filter (e.g., 'Residential Remodel')
    """
    city_key = city_key.lower().replace(' ', '_')

    if city_key not in CSS_CITIES:
        print(f'ERROR: Unknown city "{city_key}". Available: {", ".join(CSS_CITIES.keys())}')
        sys.exit(1)

    city_config = CSS_CITIES[city_key]
    city_name = city_config['name']
    base_url = city_config['base_url']

    # Use city-specific default permit types if none specified
    if not permit_type and city_config.get('default_permit_types'):
        permit_type = city_config['default_permit_types'][0]  # Use first as primary filter

    print('=' * 60)
    print(f'{city_name.upper()} PERMIT SCRAPER (Citizen Self Service)')
    print('=' * 60)
    print(f'Target: {target_count} permits')
    if permit_type:
        print(f'Filter: {permit_type}')
    print(f'Time: {datetime.now().isoformat()}\n')

    if not DEEPSEEK_API_KEY:
        print('ERROR: DEEPSEEK_API_KEY not set')
        sys.exit(1)

    permits = []
    errors = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-first-run',
                '--disable-dev-shm-usage',
            ]
        )
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 900},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        )
        page = await context.new_page()

        # Apply stealth to bypass bot detection
        if STEALTH:
            await STEALTH.apply_stealth_async(page)
            print('[STEALTH] Applied playwright-stealth for anti-bot bypass')

        try:
            Path('debug_html').mkdir(exist_ok=True)

            # Step 1: Navigate directly to search via Angular hash route
            print('[1] Navigating directly to search (Angular hash route)...')
            search_url = f'{base_url}#/search'
            await page.goto(search_url, wait_until='domcontentloaded', timeout=60000)
            # Wait for Angular app to hydrate - Tyler Portico Identity creates
            # background traffic that prevents networkidle from ever completing
            try:
                await page.wait_for_selector('#SearchModule', timeout=15000)
            except Exception:
                # Fallback for legacy WebForms portals
                await page.wait_for_selector('input[type="text"]', timeout=15000)
            await asyncio.sleep(5)  # Wait for Angular hydration

            await page.screenshot(path=f'debug_html/{city_key}_css_step1.png')
            print(f'    Current URL: {page.url}')

            # Check if Angular loaded
            angular_ready = await page.evaluate('''() => {
                return typeof window.angular !== 'undefined';
            }''')
            print(f'    Angular detected: {angular_ready}')

            # Step 2: Select "Permit" module in search dropdown using Playwright
            print('\n[2] Selecting Permit module...')

            # Use Playwright's native select_option with the correct value format
            module_selected = {'found': False}
            try:
                # Try the known ID first (SearchModule)
                search_module = page.locator('#SearchModule')
                if await search_module.count() > 0:
                    await search_module.select_option(value='number:2')  # 'number:2' = Permit
                    module_selected = {'found': True, 'value': 'Permit', 'selector': '#SearchModule'}
                else:
                    # Fallback: try any select with Module in ID
                    module_select = page.locator('select[id*="Module"]')
                    if await module_select.count() > 0:
                        await module_select.first.select_option(label='Permit')
                        module_selected = {'found': True, 'value': 'Permit', 'selector': 'select[id*=Module]'}
            except Exception as e:
                print(f'    Module selection error: {e}')
                module_selected = {'found': False, 'error': str(e)}

            print(f'    Module selection: {module_selected}')
            await asyncio.sleep(2)

            # Step 3: Use Advanced search to filter by recent date range
            print('\n[3] Using Advanced search for recent permits...')

            # Click Advanced button to expand date filters
            advanced_clicked = await page.evaluate('''() => {
                // Look for Advanced button
                const btns = document.querySelectorAll('button, a');
                for (const btn of btns) {
                    if (btn.textContent?.toLowerCase().includes('advanced')) {
                        btn.click();
                        return {clicked: true, text: btn.textContent};
                    }
                }
                return {clicked: false};
            }''')
            print(f'    Advanced button: {advanced_clicked}')
            await asyncio.sleep(2)

            # Step 3b: Select permit type if specified (skip if city uses post-filter)
            if permit_type and not city_config.get('skip_permit_type_filter'):
                print(f'\n[3b] Selecting permit type: {permit_type}...')
                try:
                    # Wait for Advanced form to fully load
                    await asyncio.sleep(2)

                    # Find the permit type dropdown by looking for one with "Select Permit Type" option
                    selects = page.locator('select')
                    select_count = await selects.count()
                    print(f'    Found {select_count} select elements')

                    permit_type_selected = False
                    for i in range(select_count):
                        sel = selects.nth(i)
                        try:
                            first_opt = await sel.locator('option').first.text_content(timeout=2000)
                            if first_opt and 'Permit Type' in first_opt:
                                await sel.select_option(label=permit_type)
                                permit_type_selected = True
                                print(f'    Selected: {permit_type}')
                                break
                        except:
                            continue

                    if not permit_type_selected:
                        print(f'    WARNING: Could not find permit type dropdown')
                        # Try alternative method - look for select by ng-model
                        permit_select = page.locator('select[ng-model*="PermitType"], select[data-ng-model*="PermitType"]')
                        if await permit_select.count() > 0:
                            await permit_select.select_option(label=permit_type)
                            print(f'    Selected via ng-model: {permit_type}')
                            permit_type_selected = True
                except Exception as e:
                    print(f'    Error selecting permit type: {e}')
                await asyncio.sleep(1)

            # Fill in date range (last 60 days for more results) using Playwright
            start_date = (datetime.now() - timedelta(days=60)).strftime('%m/%d/%Y')
            end_date = datetime.now().strftime('%m/%d/%Y')

            # Use the known input IDs from the EnerGov CSS form
            date_filled = {'start': False, 'end': False, 'type': None}

            try:
                # Try Issued Date first (more reliable for recent permits)
                from_input = page.locator('#IssueDateFrom')
                to_input = page.locator('#IssueDateTo')

                if await from_input.count() > 0 and await to_input.count() > 0:
                    date_filled['type'] = 'Issued'
                else:
                    # Fallback to Applied Date
                    from_input = page.locator('#ApplyDateFrom')
                    to_input = page.locator('#ApplyDateTo')
                    if await from_input.count() > 0:
                        date_filled['type'] = 'Applied'

                if await from_input.count() > 0:
                    await from_input.click()
                    await from_input.fill(start_date)
                    await from_input.press('Tab')  # Trigger Angular change event
                    date_filled['start'] = start_date
                    print(f'    Filled {date_filled["type"]} start date: {start_date}')

                if await to_input.count() > 0:
                    await to_input.click()
                    await to_input.fill(end_date)
                    await to_input.press('Tab')  # Trigger Angular change event
                    date_filled['end'] = end_date
                    print(f'    Filled {date_filled["type"]} end date: {end_date}')

            except Exception as e:
                print(f'    Error filling dates: {e}')

            print(f'    Date range filled: {date_filled}')
            await asyncio.sleep(1)

            # Take screenshot after filling dates
            await page.screenshot(path=f'debug_html/{city_key}_css_dates_filled.png')

            # Now execute search
            print('    Executing search with date filter...')

            # Try multiple approaches to trigger search
            search_executed = await page.evaluate('''() => {
                const results = [];

                // Approach 1: Click search button with Angular trigger
                const searchBtns = document.querySelectorAll(
                    'button[ng-click*="search"], ' +
                    'button[ng-click*="Search"], ' +
                    'a[ng-click*="search"], ' +
                    'button.search-btn, ' +
                    'button[type="submit"], ' +
                    'md-button[ng-click*="search"]'
                );

                for (const btn of searchBtns) {
                    const text = (btn.textContent || '').toLowerCase();
                    if (text.includes('search') && !text.includes('reset') && !text.includes('clear')) {
                        btn.click();
                        results.push({method: 'button_click', text: btn.textContent?.trim()});

                        // Also trigger via Angular if available
                        if (window.angular) {
                            try {
                                angular.element(btn).triggerHandler('click');
                                results.push({method: 'angular_trigger'});
                            } catch(e) {}
                        }
                        break;
                    }
                }

                // Approach 2: Submit form
                const forms = document.querySelectorAll('form[ng-submit], form');
                for (const form of forms) {
                    if (form.querySelector('input[type="text"], input[type="search"]')) {
                        if (window.angular) {
                            try {
                                angular.element(form).triggerHandler('submit');
                                results.push({method: 'form_angular_submit'});
                            } catch(e) {}
                        }
                        break;
                    }
                }

                // Approach 3: Press Enter in search input
                const searchInput = document.querySelector(
                    'input[ng-model*="search"], ' +
                    'input[type="search"], ' +
                    'input[placeholder*="Search"], ' +
                    'input.search-input'
                );
                if (searchInput) {
                    searchInput.focus();
                    searchInput.dispatchEvent(new KeyboardEvent('keydown', {key: 'Enter', keyCode: 13, bubbles: true}));
                    searchInput.dispatchEvent(new KeyboardEvent('keypress', {key: 'Enter', keyCode: 13, bubbles: true}));
                    searchInput.dispatchEvent(new KeyboardEvent('keyup', {key: 'Enter', keyCode: 13, bubbles: true}));
                    results.push({method: 'enter_key'});
                }

                return results;
            }''')

            print(f'    Search methods tried: {search_executed}')

            # Wait for results to load
            await asyncio.sleep(5)
            await page.screenshot(path=f'debug_html/{city_key}_css_step3.png')

            # Step 4: Check for results and filter by Permit type
            print('\n[4] Checking for results and applying Permit filter...')

            # Wait for results to appear in DOM before parsing
            try:
                await page.wait_for_selector(
                    'table tbody tr, .search-result, .result-item, [class*="permit-row"], a[href*="permit"]',
                    timeout=20000
                )
                print('    Results detected in DOM')
            except PlaywrightTimeout:
                print('    WARN: Timeout waiting for results selector - continuing anyway')

            # Look for result count or filter sidebar
            page_state = await page.evaluate('''() => {
                const state = {
                    hasResults: false,
                    resultCount: null,
                    filters: [],
                    url: window.location.href
                };

                // Check for result indicators
                const countEl = document.querySelector(
                    '[class*="result-count"], ' +
                    '[class*="total"], ' +
                    '.showing-results, ' +
                    '[ng-bind*="count"], ' +
                    '[ng-bind*="total"]'
                );
                if (countEl) {
                    const match = countEl.textContent.match(/(\d[\d,]*)/);
                    if (match) {
                        state.resultCount = match[1];
                        state.hasResults = true;
                    }
                }

                // Check for filter links (Permit, Plan, License, etc.)
                const links = document.querySelectorAll('a');
                for (const link of links) {
                    const text = link.textContent?.trim() || '';
                    if (/^(Permit|Plan|License|Code)\s*\d*/i.test(text)) {
                        state.filters.push(text);
                    }
                }

                // Check for any table/list of results
                const resultElements = document.querySelectorAll(
                    'table tbody tr, ' +
                    '.search-result, ' +
                    '.result-item, ' +
                    '[class*="permit-row"], ' +
                    '[class*="result-card"]'
                );
                if (resultElements.length > 0) {
                    state.hasResults = true;
                    state.resultCount = state.resultCount || resultElements.length.toString();
                }

                return state;
            }''')

            print(f'    Page state: {page_state}')

            # Click Permit filter if available and has results (skip if count is 0)
            if page_state.get('filters'):
                permit_filter_clicked = await page.evaluate('''() => {
                    const links = document.querySelectorAll('a');
                    for (const link of links) {
                        const text = link.textContent || '';
                        // Match "Permit X" where X > 0
                        const match = text.trim().match(/^Permit\s*(\d+)/i);
                        if (match) {
                            const count = parseInt(match[1], 10);
                            if (count > 0) {
                                link.click();
                                return text.trim();
                            } else {
                                // Skip filters with 0 count
                                return 'skipped_zero';
                            }
                        }
                    }
                    return false;
                }''')

                if permit_filter_clicked == 'skipped_zero':
                    print('    Skipped Permit filter (0 results) - keeping all results')
                elif permit_filter_clicked:
                    print(f'    Clicked filter: {permit_filter_clicked}')
                    await asyncio.sleep(3)

            await page.screenshot(path=f'debug_html/{city_key}_css_filtered.png')

            # Step 4b: Change sort to "Issued Date" Descending (newest first)
            # MUST happen BEFORE export so export gets sorted results
            print('\n[4b] Changing sort to Issued Date Descending...')

            sort_changed = await page.evaluate('''() => {
                const result = {field: false, order: false, debug: []};
                const selects = document.querySelectorAll('select');

                // Find and set the sort FIELD dropdown (first one with date options)
                for (const select of selects) {
                    const options = Array.from(select.options);
                    const optTexts = options.map(o => o.textContent.toLowerCase());

                    // This is likely the sort field dropdown if it has "permit number" and date options
                    if (optTexts.some(t => t.includes('permit number') || t.includes('case number'))) {
                        result.debug.push('Found sort field dropdown');

                        // Find "Issued Date" or "Date Issued" option
                        for (const opt of options) {
                            const text = opt.textContent.toLowerCase();
                            if (text.includes('issued') && text.includes('date')) {
                                select.value = opt.value;
                                select.dispatchEvent(new Event('change', {bubbles: true}));
                                result.field = opt.textContent.trim();
                                result.debug.push('Selected: ' + opt.textContent.trim());
                                break;
                            }
                        }
                        break;
                    }
                }

                // Find and set the sort ORDER dropdown (has Ascending/Descending)
                for (const select of selects) {
                    const options = Array.from(select.options);
                    const optTexts = options.map(o => o.textContent.toLowerCase());

                    if (optTexts.some(t => t.includes('ascending')) && optTexts.some(t => t.includes('descending'))) {
                        result.debug.push('Found sort order dropdown');

                        for (const opt of options) {
                            if (opt.textContent.toLowerCase().includes('descending')) {
                                select.value = opt.value;
                                select.dispatchEvent(new Event('change', {bubbles: true}));
                                result.order = opt.textContent.trim();
                                result.debug.push('Selected: ' + opt.textContent.trim());

                                // Trigger Angular digest
                                if (window.angular) {
                                    try {
                                        const scope = angular.element(select).scope();
                                        if (scope && scope.$apply) scope.$apply();
                                    } catch(e) {}
                                }
                                break;
                            }
                        }
                        break;
                    }
                }

                return result;
            }''')

            print(f'    Sort result: field={sort_changed.get("field")}, order={sort_changed.get("order")}')
            if sort_changed.get('debug'):
                for d in sort_changed.get('debug', []):
                    print(f'      {d}')

            await asyncio.sleep(3)  # Wait for sort to apply (Angular apps auto-resort)

            await page.screenshot(path=f'debug_html/{city_key}_css_sorted.png')

            # Step 4c: Maximize page size before export (show all results on one page)
            print('\n[4c] Maximizing results per page...')
            try:
                # Look for a "Show X entries" or page size dropdown
                # IMPORTANT: Avoid the search module dropdown which has "All/Permit/Plan" options
                page_size_changed = await page.evaluate('''() => {
                    // Find dropdowns that control page size (not the module dropdown)
                    const selects = document.querySelectorAll('select');
                    for (const select of selects) {
                        const options = Array.from(select.options);
                        const optTexts = options.map(o => o.textContent.trim().toLowerCase());

                        // Skip the search module dropdown (has Permit/Plan/License options)
                        if (optTexts.some(t => t === 'permit' || t === 'plan' || t === 'license')) {
                            continue;
                        }

                        // Look for page size dropdown (has numeric options like 10, 25, 50, 100)
                        const hasNumericOptions = options.filter(o => /^\\d+$/.test(o.value.trim())).length >= 2;
                        if (hasNumericOptions) {
                            // Try to select largest option (All, 500, 1000, or -1)
                            for (const opt of options) {
                                const val = opt.value.trim();
                                const text = opt.textContent.trim().toLowerCase();
                                if (text === 'all' || val === '-1' || val === '500' || val === '1000') {
                                    select.value = opt.value;
                                    select.dispatchEvent(new Event('change', {bubbles: true}));
                                    return opt.textContent.trim();
                                }
                            }
                            // Fall back to last option (usually largest)
                            const lastOpt = options[options.length - 1];
                            select.value = lastOpt.value;
                            select.dispatchEvent(new Event('change', {bubbles: true}));
                            return lastOpt.textContent.trim();
                        }
                    }
                    return null;
                }''')
                if page_size_changed:
                    print(f'    Set page size to: {page_size_changed}')
                    await asyncio.sleep(5)  # Wait for results to reload
                else:
                    print('    No page size dropdown found')
            except Exception as e:
                print(f'    Could not change page size: {e}')

            # Wait briefly for Export button to become visible
            await asyncio.sleep(2)

            # Debug: take screenshot and scroll to results
            await page.screenshot(path=f'debug_html/{city_key}_css_before_export.png', full_page=True)

            # Try to scroll to results section
            await page.evaluate('''() => {
                const results = document.querySelector('.search-results, [class*="result"], table, .grid');
                if (results) results.scrollIntoView();
            }''')
            await asyncio.sleep(1)

            # Step 4d: Try Excel export (more reliable than DOM scraping)
            print('\n[4d] Attempting Excel export download...')

            # Always try "Export Current View" first to respect date filters
            # Falls back to regular export if current view option not available
            excel_path = await download_excel_export(
                page, city_name,
                export_current_view=True,  # Try filtered export first
                permit_type=permit_type
            )

            if excel_path:
                # Parse the downloaded Excel file
                excel_permits = parse_excel_permits(excel_path, city_name)
                if excel_permits:
                    # Apply residential filter for cities that skip UI permit type filtering
                    if city_config.get('skip_permit_type_filter'):
                        original_count = len(excel_permits)
                        excel_permits = filter_residential_permits(excel_permits)
                        print(f'    Filtered to {len(excel_permits)} residential permits (from {original_count})')

                    # Filter out utility/maintenance permits (water meters, irrigation, etc.)
                    # These aren't valuable leads for contractors
                    UTILITY_TYPES = {'water meter', 'irrigation meter', 'gas meter'}
                    original_count = len(excel_permits)
                    excel_permits = [
                        p for p in excel_permits
                        if not any(util in p.get('type', '').lower() for util in UTILITY_TYPES)
                    ]
                    if len(excel_permits) < original_count:
                        print(f'    Filtered out {original_count - len(excel_permits)} utility permits')

                    print(f'    SUCCESS: Got {len(excel_permits)} permits from Excel export')
                    permits.extend(excel_permits)

                    # If we got enough permits, we can skip DOM scraping entirely
                    if len(permits) >= target_count:
                        print(f'    Target reached via Excel export - skipping DOM scraping')
                    else:
                        print(f'    Excel gave {len(permits)} permits, will supplement with DOM scraping if needed')
                else:
                    print(f'    WARN: Excel export downloaded but parsing failed - will use DOM scraping')
            else:
                print(f'    Export download failed or not available - will use DOM scraping')

            # Dismiss any modal dialogs that may have been opened by export attempt
            await page.evaluate('''() => {
                // Close any bootstrap modals
                const modals = document.querySelectorAll('.modal.in, .modal.show, [role="dialog"]');
                for (const modal of modals) {
                    // Try clicking close/cancel buttons
                    const closeBtn = modal.querySelector('[data-dismiss="modal"], .close, .btn-close');
                    if (closeBtn) closeBtn.click();
                    // Try to find Cancel button by text
                    const buttons = modal.querySelectorAll('button');
                    for (const btn of buttons) {
                        if (btn.textContent.toLowerCase().includes('cancel') ||
                            btn.textContent.toLowerCase().includes('close')) {
                            btn.click();
                            break;
                        }
                    }
                    // Also try to hide the modal directly
                    modal.classList.remove('in', 'show');
                    modal.style.display = 'none';
                }
                // Remove any modal backdrops
                const backdrops = document.querySelectorAll('.modal-backdrop');
                for (const backdrop of backdrops) {
                    backdrop.remove();
                }
                // Reset body class
                document.body.classList.remove('modal-open');
            }''')
            await asyncio.sleep(1)

            # Step 5: Extract permits from results using direct DOM parsing (faster than LLM)
            print('\n[5] Extracting permits via DOM...')
            page_num = 1
            consecutive_failures = 0

            while len(permits) < target_count and consecutive_failures < 3:
                print(f'\n    Page {page_num}...')

                # Extract directly from DOM - no LLM needed
                page_data = await page.evaluate(r'''() => {
                    const results = {permits: [], total: null, hasNext: false, debug: {}};

                    // Get total count from "Found X results"
                    const bodyText = document.body.textContent;
                    const totalMatch = bodyText.match(/Found\s+([\d,]+)\s+results/i);
                    if (totalMatch) {
                        results.total = parseInt(totalMatch[1].replace(/,/g, ''));
                    }

                    // Check for Next link
                    const links = document.querySelectorAll('a');
                    for (const link of links) {
                        if (link.textContent.trim() === 'Next') {
                            results.hasNext = true;
                            break;
                        }
                    }

                    // METHOD 1: Try to find permit links directly (most reliable)
                    // The permit number is a clickable link in format "000001-2024"
                    const permitLinks = document.querySelectorAll('a');
                    // Flexible: 6+ chars, alphanumeric with dashes (handles various city formats)
                    const permitIdPattern = /^[A-Z0-9]{2,}-[A-Z0-9-]{2,}$/i;
                    const seenIds = new Set();

                    for (const link of permitLinks) {
                        const linkText = link.textContent.trim();
                        if (permitIdPattern.test(linkText) && !seenIds.has(linkText)) {
                            seenIds.add(linkText);

                            // Found a permit ID link, now get surrounding card data
                            // Walk up to find the card/container element
                            let container = link.closest('div, section, article, tr');
                            // If too small, go up more
                            for (let i = 0; i < 5 && container && container.innerText.length < 100; i++) {
                                container = container.parentElement;
                            }

                            if (container) {
                                const cardText = container.innerText;
                                const permit = {permit_id: linkText};

                                // Extract fields from card - handle both inline and multiline
                                const typeMatch = cardText.match(/Type\s*[:\n]?\s*([A-Za-z][^\n]*?)(?=\s*(?:Project|Issued|Status|$))/i);
                                if (typeMatch) permit.type = typeMatch[1].trim();

                                const statusMatch = cardText.match(/Status\s*[:\n]?\s*(\w+)/i);
                                if (statusMatch) permit.status = statusMatch[1].trim();

                                const addrMatch = cardText.match(/Address\s*[:\n]?\s*(\d+[^\n]*?(?:TX|Texas)\s*\d{5})/i);
                                if (addrMatch) permit.address = addrMatch[1].trim();

                                const appliedMatch = cardText.match(/Applied Date\s*[:\n]?\s*(\d{2}\/\d{2}\/\d{4})/i);
                                if (appliedMatch) permit.applied_date = appliedMatch[1];

                                const parcelMatch = cardText.match(/Main Parcel\s*[:\n]?\s*([A-Z0-9-]+)/i);
                                if (parcelMatch) permit.parcel = parcelMatch[1].trim();

                                const descMatch = cardText.match(/Description\s*[:\n]?\s*([^\n]+)/i);
                                if (descMatch && descMatch[1].trim() && !descMatch[1].includes('Previous')) {
                                    permit.description = descMatch[1].trim();
                                }

                                results.permits.push(permit);
                            }
                        }
                    }

                    results.debug.method1_count = results.permits.length;

                    // METHOD 2: Fallback - parse innerText if method 1 failed
                    if (results.permits.length === 0) {
                        const text = document.body.innerText;
                        results.debug.innerTextSample = text.slice(0, 500);

                        // Look for permit IDs anywhere in text with flexible patterns
                        // Handles: "Permit Number\n000001-2024" or "Permit Number 000001-2024-CMISC"
                        const idMatches = text.matchAll(/(?:Permit Number|Permit #|Permit:?)\s*[\n\r]?\s*(\d{6}-\d{4}(?:-[A-Z0-9]+)?)/gi);

                        for (const match of idMatches) {
                            const permit_id = match[1];
                            if (!seenIds.has(permit_id)) {
                                seenIds.add(permit_id);

                                // Find the block for this permit
                                const idx = match.index;
                                const blockEnd = text.indexOf('Permit Number', idx + 10);
                                const block = blockEnd > 0 ? text.slice(idx, blockEnd) : text.slice(idx, idx + 1000);

                                const permit = {permit_id: permit_id};

                                // More flexible field extraction
                                const typeMatch = block.match(/Type\s*[\n:]?\s*([A-Za-z][^\n]*?)(?=\s*(?:Project|Applied|Issued|Status|\n\n|$))/i);
                                if (typeMatch) permit.type = typeMatch[1].trim().slice(0, 100);

                                const statusMatch = block.match(/Status\s*[\n:]?\s*(\w+)/i);
                                if (statusMatch) permit.status = statusMatch[1].trim();

                                const addrMatch = block.match(/Address\s*[\n:]?\s*(\d+[^\n]*?\d{5})/i);
                                if (addrMatch) permit.address = addrMatch[1].trim();

                                const appliedMatch = block.match(/Applied Date\s*[\n:]?\s*(\d{1,2}\/\d{1,2}\/\d{4})/i);
                                if (appliedMatch) permit.applied_date = appliedMatch[1];

                                results.permits.push(permit);
                            }
                        }
                        results.debug.method2_count = results.permits.length;
                    }

                    return results;
                }''')

                if page_data and page_data.get('permits'):
                    new_permits = page_data['permits']

                    # Deduplicate
                    existing_ids = {p['permit_id'] for p in permits}
                    unique_new = [p for p in new_permits if p['permit_id'] not in existing_ids]

                    permits.extend(unique_new)
                    total_str = f" (of {page_data.get('total', '?')} total)" if page_data.get('total') else ""
                    debug = page_data.get('debug', {})
                    method_info = f" [method1:{debug.get('method1_count', '?')}, method2:{debug.get('method2_count', 'n/a')}]"
                    print(f'    Extracted {len(unique_new)} permits{total_str} ({len(permits)} collected){method_info}')
                    consecutive_failures = 0
                else:
                    debug = page_data.get('debug', {}) if page_data else {}
                    print(f'    WARN - No permits extracted from DOM')
                    print(f'    Debug: method1={debug.get("method1_count", 0)}, method2={debug.get("method2_count", 0)}')
                    if debug.get('innerTextSample'):
                        print(f'    Sample: {debug["innerTextSample"][:200]}...')
                    consecutive_failures += 1
                    errors.append({'step': f'extract_page_{page_num}', 'error': 'No permits in DOM', 'debug': debug})

                if len(permits) >= target_count:
                    break

                # Navigate to next page
                if not page_data.get('hasNext'):
                    print('    No Next link found - end of results')
                    break

                print(f'    Clicking Next...')

                # Get the first permit ID before clicking (to detect page change)
                first_permit_before = None
                if page_data and page_data.get('permits'):
                    first_permit_before = page_data['permits'][0]['permit_id'] if page_data['permits'] else None

                # Use Playwright's native click - more reliable for Angular apps
                try:
                    next_link = page.locator('a:text-is("Next")')
                    if await next_link.count() > 0:
                        await next_link.first.click()
                        clicked = True
                    else:
                        # Fallback: try partial text match
                        next_link = page.locator('a:has-text("Next")')
                        if await next_link.count() > 0:
                            await next_link.first.click()
                            clicked = True
                        else:
                            clicked = False
                except Exception as e:
                    print(f'    Click error: {e}')
                    clicked = False

                if not clicked:
                    print('    Failed to click Next')
                    break

                # Wait for Angular to update - check for content change, not URL
                # Angular SPAs often don't change URL on pagination
                try:
                    # Wait for network to settle
                    await page.wait_for_load_state('networkidle', timeout=10000)
                except:
                    pass  # May timeout, that's ok

                # Give Angular time to render
                await asyncio.sleep(3)

                # Verify page actually changed by checking if first permit is different
                if first_permit_before:
                    check_data = await page.evaluate(r'''() => {
                        const permitLinks = document.querySelectorAll('a');
                        const permitIdPattern = /^[A-Z0-9]{2,}-[A-Z0-9-]{2,}$/i;
                        for (const link of permitLinks) {
                            const linkText = link.textContent.trim();
                            if (permitIdPattern.test(linkText)) {
                                return linkText;
                            }
                        }
                        return null;
                    }''')
                    if check_data == first_permit_before:
                        consecutive_failures += 1
                        print(f'    WARN: Page content unchanged (same first permit: {first_permit_before}) - failure {consecutive_failures}/3')
                        if consecutive_failures >= 3:
                            print('    Stopping: 3 consecutive unchanged pages')
                            break
                        # Try scrolling to trigger lazy load
                        await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                        await asyncio.sleep(2)
                    else:
                        print(f'    Page changed: {first_permit_before} -> {check_data}')
                        consecutive_failures = 0  # Reset on successful page change

                page_num += 1

            print(f'\n    Total permits extracted: {len(permits)}')

        except Exception as e:
            print(f'\nFATAL ERROR: {e}')
            errors.append({'step': 'main', 'error': str(e)})
            await page.screenshot(path=f'debug_html/{city_key}_css_error.png')

        finally:
            await browser.close()

    # Filter for residential permits if this is Southlake
    if city_key.lower() == 'southlake':
        original_count = len(permits)
        permits = filter_residential_permits(permits)
        print(f'\n[FILTER] Filtered to {len(permits)} residential permits (from {original_count} total)')

    # Save results
    output = {
        'source': city_key,
        'portal_type': 'Citizen_Self_Service',
        'scraped_at': datetime.now().isoformat(),
        'target_count': target_count,
        'actual_count': len(permits),
        'errors': errors,
        'permits': permits[:target_count]
    }

    output_file = f'{city_key}_raw.json'
    Path(output_file).write_text(json.dumps(output, indent=2))

    print('\n' + '=' * 60)
    print('SUMMARY')
    print('=' * 60)
    print(f'City: {city_name}')
    print(f'Permits scraped: {output["actual_count"]}')
    print(f'Errors: {len(errors)}')
    print(f'Output: {output_file}')

    if errors:
        print('\nERRORS:')
        for e in errors[:5]:
            print(f'  - {e["step"]}: {e["error"][:100]}')

    if permits:
        print('\nSAMPLE PERMITS:')
        for p in permits[:5]:
            print(f'  {p["permit_id"]} | {p.get("type", "?")} | {p.get("address", "no address")[:40]}')

    return output


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Scrape permits from Citizen Self Service portals')
    parser.add_argument('city', nargs='?', default='mckinney',
                        help='City to scrape (mckinney, southlake, colleyville, allen, trophy_club, waxahachie)')
    parser.add_argument('count', nargs='?', type=int, default=100,
                        help='Target number of permits')
    parser.add_argument('--permit-type', '-t', dest='permit_type',
                        help='Filter by permit type (e.g., "Residential Remodel")')

    args = parser.parse_args()
    asyncio.run(scrape(args.city, args.count, args.permit_type))
