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

import httpx
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

from scrapers.utils import parse_excel_permits

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


async def download_excel_export(page, city: str, timeout_ms: int = 60000) -> Optional[str]:
    """
    Click Export button and wait for download.

    Args:
        page: Playwright page
        city: City name for filename
        timeout_ms: Max wait time for download (default 60s)

    Returns:
        Path to downloaded file, or None if failed
    """
    try:
        # Find and click the Export button
        export_btn = page.locator("button:has-text('Export'), a:has-text('Export')")

        if not await export_btn.count():
            print(f"[{city}] Export button not found")
            return None

        # Wait for download event
        async with page.expect_download(timeout=timeout_ms) as download_info:
            await export_btn.first.click()
            print(f"[{city}] Clicked Export, waiting for download...")

        download = await download_info.value

        # Save to our download directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{city.lower()}_{timestamp}.xlsx"
        dest_path = DOWNLOAD_DIR / filename

        await download.save_as(str(dest_path))

        print(f"[{city}] Downloaded: {dest_path}")
        return str(dest_path)

    except Exception as e:
        print(f"[{city}] Download failed: {e}")
        return None


async def scrape(city_key: str, target_count: int = 100):
    """Scrape permits from Citizen Self Service portal."""
    city_key = city_key.lower().replace(' ', '_')

    if city_key not in CSS_CITIES:
        print(f'ERROR: Unknown city "{city_key}". Available: {", ".join(CSS_CITIES.keys())}')
        sys.exit(1)

    city_config = CSS_CITIES[city_key]
    city_name = city_config['name']
    base_url = city_config['base_url']

    print('=' * 60)
    print(f'{city_name.upper()} PERMIT SCRAPER (Citizen Self Service)')
    print('=' * 60)
    print(f'Target: {target_count} permits')
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

        try:
            Path('debug_html').mkdir(exist_ok=True)

            # Step 1: Navigate directly to search via Angular hash route
            print('[1] Navigating directly to search (Angular hash route)...')
            search_url = f'{base_url}#/search'
            await page.goto(search_url, wait_until='networkidle', timeout=60000)
            await asyncio.sleep(5)  # Wait for Angular hydration

            await page.screenshot(path=f'debug_html/{city_key}_css_step1.png')
            print(f'    Current URL: {page.url}')

            # Check if Angular loaded
            angular_ready = await page.evaluate('''() => {
                return typeof window.angular !== 'undefined';
            }''')
            print(f'    Angular detected: {angular_ready}')

            # Step 2: Select "Permit" module in search dropdown
            print('\n[2] Selecting Permit module...')

            module_selected = await page.evaluate('''() => {
                // Look for module dropdown (various possible selectors)
                const selectors = [
                    'select[ng-model*="module"]',
                    'select[ng-model*="Module"]',
                    'select[id*="module"]',
                    'select[id*="Module"]',
                    'md-select[ng-model*="module"]',
                    '[ng-model*="selectedModule"]',
                    'select.form-control'
                ];

                for (const sel of selectors) {
                    const dropdown = document.querySelector(sel);
                    if (dropdown && dropdown.tagName === 'SELECT') {
                        // Find Permit option
                        for (const opt of dropdown.options) {
                            if (opt.textContent.toLowerCase().includes('permit')) {
                                dropdown.value = opt.value;
                                dropdown.dispatchEvent(new Event('change', {bubbles: true}));

                                // Trigger Angular digest if available
                                if (window.angular) {
                                    try {
                                        const scope = angular.element(dropdown).scope();
                                        if (scope && scope.$apply) {
                                            scope.$apply();
                                        }
                                    } catch(e) {}
                                }
                                return {found: true, value: opt.textContent, selector: sel};
                            }
                        }
                    }
                }

                // Try md-select (Angular Material)
                const mdSelect = document.querySelector('md-select');
                if (mdSelect) {
                    mdSelect.click();
                    return {found: 'md-select-clicked', note: 'Need to select option next'};
                }

                return {found: false};
            }''')

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

            # Fill in date range (last 60 days for more results) using Playwright
            start_date = (datetime.now() - timedelta(days=60)).strftime('%m/%d/%Y')
            end_date = datetime.now().strftime('%m/%d/%Y')

            # Find Applied Date row and fill the From/To inputs
            # The Applied Date row has: label "Applied Date", input (from), "To" text, input (to)
            date_filled = await page.evaluate(f'''() => {{
                const result = {{start: false, end: false}};

                // Find the row containing "Applied Date"
                const labels = document.querySelectorAll('label, td, th, div');
                for (const label of labels) {{
                    if (label.textContent?.trim() === 'Applied Date') {{
                        // Found the Applied Date label, now find inputs in same row
                        const row = label.closest('tr, div, .form-group');
                        if (row) {{
                            const inputs = row.querySelectorAll('input[type="text"], input:not([type])');
                            if (inputs.length >= 2) {{
                                // First input = From date, Second input = To date
                                inputs[0].value = '{start_date}';
                                inputs[0].dispatchEvent(new Event('input', {{bubbles: true}}));
                                inputs[0].dispatchEvent(new Event('change', {{bubbles: true}}));
                                result.start = '{start_date}';

                                inputs[1].value = '{end_date}';
                                inputs[1].dispatchEvent(new Event('input', {{bubbles: true}}));
                                inputs[1].dispatchEvent(new Event('change', {{bubbles: true}}));
                                result.end = '{end_date}';
                                break;
                            }}
                        }}
                    }}
                }}
                return result;
            }}''')
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

            # Click Permit filter if available
            if page_state.get('filters'):
                permit_filter_clicked = await page.evaluate('''() => {
                    const links = document.querySelectorAll('a');
                    for (const link of links) {
                        const text = link.textContent || '';
                        if (/^Permit\s*\d*/i.test(text.trim())) {
                            link.click();
                            return text.trim();
                        }
                    }
                    return false;
                }''')

                if permit_filter_clicked:
                    print(f'    Clicked filter: {permit_filter_clicked}')
                    await asyncio.sleep(3)

            await page.screenshot(path=f'debug_html/{city_key}_css_filtered.png')

            # Step 4b: Try Excel export first (more reliable than DOM scraping)
            print('\n[4b] Attempting Excel export download...')

            excel_path = await download_excel_export(page, city_name)

            if excel_path:
                # Parse the downloaded Excel file
                excel_permits = parse_excel_permits(excel_path, city_name)
                if excel_permits:
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

            # Step 4c: Change sort to Applied Date Descending (newest first)
            print('\n[4c] Changing sort to Applied Date Descending...')

            sort_changed = await page.evaluate('''() => {
                const result = {field: false, order: false};
                const selects = document.querySelectorAll('select');

                for (const select of selects) {
                    const options = Array.from(select.options);

                    // First dropdown: try to change to Applied Date
                    for (const opt of options) {
                        const text = opt.textContent.toLowerCase();
                        if (text.includes('applied') || text.includes('date')) {
                            select.value = opt.value;
                            select.dispatchEvent(new Event('change', {bubbles: true}));
                            result.field = opt.textContent.trim();
                            break;
                        }
                    }

                    // Second dropdown: change to Descending
                    for (const opt of options) {
                        if (opt.textContent.toLowerCase().includes('descend')) {
                            select.value = opt.value;
                            select.dispatchEvent(new Event('change', {bubbles: true}));
                            result.order = opt.textContent.trim();

                            // Trigger Angular digest
                            if (window.angular) {
                                try {
                                    const scope = angular.element(select).scope();
                                    if (scope && scope.$apply) scope.$apply();
                                } catch(e) {}
                            }
                        }
                    }
                }
                return result;
            }''')

            print(f'    Sort change result: {sort_changed}')
            await asyncio.sleep(5)  # Wait for results to re-sort

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

                clicked = await page.evaluate('''() => {
                    const links = document.querySelectorAll('a');
                    for (const link of links) {
                        if (link.textContent.trim() === 'Next') {
                            link.click();
                            return true;
                        }
                    }
                    return false;
                }''')

                if not clicked:
                    print('    Failed to click Next')
                    break

                # Wait for URL to change (indicates page navigation)
                old_url = page.url
                try:
                    await page.wait_for_function(
                        f'() => window.location.href !== "{old_url}"',
                        timeout=10000
                    )
                    print(f'    URL changed to page {page_num + 1}')
                except:
                    print(f'    WARN: URL did not change, waiting anyway...')

                # Additional wait for Angular to render new content
                await asyncio.sleep(2)
                page_num += 1

            print(f'\n    Total permits extracted: {len(permits)}')

        except Exception as e:
            print(f'\nFATAL ERROR: {e}')
            errors.append({'step': 'main', 'error': str(e)})
            await page.screenshot(path=f'debug_html/{city_key}_css_error.png')

        finally:
            await browser.close()

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
    city_arg = sys.argv[1] if len(sys.argv) > 1 else 'mckinney'
    count_arg = int(sys.argv[2]) if len(sys.argv) > 2 else 100
    asyncio.run(scrape(city_arg, count_arg))
