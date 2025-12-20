#!/usr/bin/env python3
"""
Explore Lewisville Tyler eSuite permit portal structure.
Output: debug_html/lewisville_exploration.json
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path

from playwright.async_api import async_playwright

OUTPUT_DIR = Path('debug_html')
OUTPUT_DIR.mkdir(exist_ok=True)

async def explore():
    """Explore the Tyler eSuite portal structure."""
    print('=' * 60)
    print('LEWISVILLE TYLER eSUITE EXPLORATION')
    print('=' * 60)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            java_script_enabled=True
        )
        page = await context.new_page()

        # Enable console logging
        page.on('console', lambda msg: print(f'    CONSOLE: {msg.text}'))

        results = {
            'timestamp': datetime.now().isoformat(),
            'url': 'https://etools.cityoflewisville.com/esuite.permits/',
            'pages_explored': [],
            'forms': [],
            'api_endpoints': [],
        }

        # Capture API calls
        api_calls = []
        def log_request(request):
            if '/api/' in request.url or '.json' in request.url:
                api_calls.append({
                    'url': request.url,
                    'method': request.method
                })
        page.on('request', log_request)

        try:
            # Step 1: Load main portal
            print('\n[1] Loading portal...')
            await page.goto('https://etools.cityoflewisville.com/esuite.permits/',
                          wait_until='networkidle', timeout=60000)

            # Wait for any dynamic content to render
            await asyncio.sleep(5)

            # Check if there's a parcel number input that might be hidden
            print('    Waiting for any hidden elements to appear...')
            try:
                await page.wait_for_selector('input[type="text"]', timeout=5000)
                print('    Found text input!')
            except:
                print('    No text inputs found after waiting')

            await page.screenshot(path='debug_html/lewisville_home.png', full_page=True)
            print(f'    URL: {page.url}')

            # Step 2: Get full page HTML for analysis
            print('\n[2] Extracting full HTML...')
            full_html = await page.content()
            with open('debug_html/lewisville_full.html', 'w') as f:
                f.write(full_html)
            print('    Saved full HTML to debug_html/lewisville_full.html')

            # Step 3: Analyze page structure (detailed)
            print('\n[3] Analyzing page structure...')
            structure = await page.evaluate('''() => {
                return {
                    title: document.title,
                    html_preview: document.body.innerText.slice(0, 500),
                    forms: Array.from(document.forms).map(f => ({
                        id: f.id,
                        action: f.action,
                        method: f.method,
                        inputs: Array.from(f.querySelectorAll('input, select, textarea')).map(i => ({
                            type: i.type || i.tagName.toLowerCase(),
                            name: i.name,
                            id: i.id,
                            placeholder: i.placeholder,
                            value: i.value
                        }))
                    })),
                    links: Array.from(document.querySelectorAll('a')).map(a => ({
                        text: a.textContent.trim().slice(0, 80),
                        href: a.href,
                        id: a.id,
                        class: a.className
                    })).filter(l => l.text && l.href && !l.href.startsWith('javascript')),
                    buttons: Array.from(document.querySelectorAll('button, input[type="button"], input[type="submit"]')).map(b => ({
                        text: b.textContent.trim().slice(0, 80) || b.value,
                        type: b.type,
                        id: b.id,
                        name: b.name
                    })),
                    menuItems: Array.from(document.querySelectorAll('[class*="menu"], [class*="nav"], li')).map(m => ({
                        text: m.textContent.trim().slice(0, 80),
                        class: m.className
                    })).filter(m => m.text && m.text.length < 50),
                    tables: document.querySelectorAll('table').length,
                    iframes: Array.from(document.querySelectorAll('iframe')).map(i => i.src),
                    divs_with_onclick: Array.from(document.querySelectorAll('[onclick]')).map(d => ({
                        text: d.textContent.trim().slice(0, 80),
                        onclick: d.getAttribute('onclick').slice(0, 100)
                    }))
                };
            }''')

            results['pages_explored'].append({
                'url': page.url,
                'structure': structure
            })
            print(f'    Title: {structure["title"]}')
            print(f'    Forms: {len(structure["forms"])}')
            print(f'    Links: {len(structure["links"])}')
            print(f'    Buttons: {len(structure["buttons"])}')
            print(f'    Menu items: {len(structure["menuItems"])}')

            # Step 4: Look for navigation menu or search links
            print('\n[4] Looking for permit search or navigation...')

            # Try common Tyler eSuite paths
            common_paths = [
                '/esuite.permits/#/permits',
                '/esuite.permits/#/search',
                '/esuite.permits/modules/permits/search',
            ]

            for path in common_paths:
                try:
                    print(f'    Trying: {path}')
                    test_url = f'https://etools.cityoflewisville.com{path}'
                    await page.goto(test_url, wait_until='networkidle', timeout=10000)
                    await asyncio.sleep(2)

                    current_structure = await page.evaluate('''() => {
                        return {
                            url: window.location.href,
                            title: document.title,
                            forms: document.forms.length,
                            text_preview: document.body.innerText.slice(0, 300)
                        };
                    }''')

                    if current_structure['url'] != 'https://etools.cityoflewisville.com/esuite.permits/':
                        print(f'      Found different page: {current_structure["title"]}')
                        await page.screenshot(path=f'debug_html/lewisville_attempt_{len(results["pages_explored"])}.png', full_page=True)
                        results['pages_explored'].append(current_structure)
                        break
                except Exception as e:
                    print(f'      Failed: {str(e)[:50]}')
                    continue

            # Step 5: Explore deeper structure
            print('\n[5] Exploring deeper DOM structure...')
            deep_structure = await page.evaluate('''() => {
                return {
                    url: window.location.href,
                    all_text_inputs: Array.from(document.querySelectorAll('input[type="text"]')).map(i => ({
                        id: i.id,
                        name: i.name,
                        placeholder: i.placeholder
                    })),
                    all_selects: Array.from(document.querySelectorAll('select')).map(s => ({
                        id: s.id,
                        name: s.name,
                        options: Array.from(s.options).map(o => o.text).slice(0, 5)
                    })),
                    all_clickable: Array.from(document.querySelectorAll('a, button, [onclick], [role="button"]')).map(el => ({
                        tag: el.tagName,
                        text: el.textContent.trim().slice(0, 60),
                        id: el.id,
                        href: el.href || '',
                        onclick: el.getAttribute('onclick') ? el.getAttribute('onclick').slice(0, 80) : ''
                    })).filter(el => el.text && el.text.length > 0 && el.text.length < 60),
                    scripts: Array.from(document.querySelectorAll('script[src]')).map(s => s.src)
                };
            }''')

            results['deep_structure'] = deep_structure
            print(f'    Text inputs: {len(deep_structure["all_text_inputs"])}')
            print(f'    Select dropdowns: {len(deep_structure["all_selects"])}')
            print(f'    Clickable elements: {len(deep_structure["all_clickable"])}')

            if deep_structure['all_clickable']:
                print('\n    First 10 clickable elements:')
                for el in deep_structure['all_clickable'][:10]:
                    print(f'      {el["tag"]}: {el["text"][:50]}')

            results['api_endpoints'] = api_calls
            print(f'\n[6] API endpoints captured: {len(api_calls)}')
            for call in api_calls[:10]:
                print(f'    {call["method"]} {call["url"][:80]}')

        except Exception as e:
            print(f'\nERROR: {e}')
            import traceback
            results['error'] = {
                'message': str(e),
                'traceback': traceback.format_exc()
            }

        finally:
            await browser.close()

        # Save results
        output_file = OUTPUT_DIR / 'lewisville_exploration.json'
        output_file.write_text(json.dumps(results, indent=2))
        print(f'\nSaved exploration to: {output_file}')

        return results

if __name__ == '__main__':
    asyncio.run(explore())
