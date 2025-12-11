#!/usr/bin/env python3
"""
WESTLAKE MYGOV PORTAL INVESTIGATION
Purpose: Determine if Westlake's MyGov portal is scrapeable.

Known facts:
- URL: https://public.mygov.us/westlake_tx
- Same platform as Rowlett/Grapevine (marked "not scrapeable")
- High-value leads per the user

This script will:
1. Load the portal
2. Check for login requirements
3. Try to find permit search
4. Document what we find
"""

import asyncio
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright

async def investigate():
    print('=' * 60)
    print('WESTLAKE MYGOV INVESTIGATION')
    print('=' * 60)
    print(f'Time: {datetime.now().isoformat()}\n')

    findings = {
        'url': 'https://public.mygov.us/westlake_tx',
        'timestamp': datetime.now().isoformat(),
        'accessible': False,
        'requires_login': None,
        'has_permit_search': None,
        'blockers': [],
        'notes': []
    }

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 900},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        page = await context.new_page()

        Path('debug_html').mkdir(exist_ok=True)

        try:
            # Step 1: Load the portal
            print('[1] Loading Westlake MyGov portal...')
            response = await page.goto(findings['url'], timeout=30000)

            findings['status_code'] = response.status if response else None
            findings['final_url'] = page.url
            print(f'    Status: {findings["status_code"]}')
            print(f'    Final URL: {findings["final_url"]}')

            await asyncio.sleep(3)
            await page.screenshot(path='debug_html/westlake_mygov_initial.png')

            # Step 2: Check for login wall
            print('\n[2] Checking for login requirements...')
            page_text = await page.inner_text('body')

            login_indicators = ['sign in', 'log in', 'login', 'username', 'password', 'authenticate']
            has_login = any(ind in page_text.lower() for ind in login_indicators)
            findings['requires_login'] = has_login
            print(f'    Login wall detected: {has_login}')

            if has_login:
                findings['blockers'].append('Login required')

            # Step 3: Look for permit/project links
            print('\n[3] Searching for permit/project links...')
            links = await page.evaluate('''() => {
                return Array.from(document.querySelectorAll('a'))
                    .map(a => ({href: a.href, text: a.textContent?.trim()}))
                    .filter(l => l.text && l.text.length < 50);
            }''')

            permit_links = [l for l in links if any(
                kw in (l.get('text', '') + l.get('href', '')).lower()
                for kw in ['permit', 'project', 'search', 'public']
            )]

            findings['permit_related_links'] = permit_links[:10]
            print(f'    Found {len(permit_links)} permit-related links')
            for link in permit_links[:5]:
                print(f'      - {link.get("text")}: {link.get("href", "")[:60]}')

            # Step 4: Try clicking "Projects" or similar
            if permit_links:
                print('\n[4] Attempting to navigate to projects/permits...')
                for link in permit_links[:3]:
                    if 'project' in link.get('text', '').lower() or 'permit' in link.get('text', '').lower():
                        try:
                            await page.click(f'a:has-text("{link["text"]}")', timeout=5000)
                            await asyncio.sleep(3)
                            await page.screenshot(path='debug_html/westlake_mygov_projects.png')

                            # Check if we got to a search or list
                            new_text = await page.inner_text('body')
                            if 'search' in new_text.lower() or 'results' in new_text.lower():
                                findings['has_permit_search'] = True
                                findings['notes'].append(f'Found search via: {link["text"]}')
                            break
                        except Exception as e:
                            findings['notes'].append(f'Click failed: {link["text"]} - {e}')

            # Step 5: Check for heavy JS/Canvas issues
            print('\n[5] Checking for technical blockers...')
            tech_check = await page.evaluate('''() => {
                return {
                    hasCanvas: document.querySelectorAll('canvas').length > 0,
                    hasIframe: document.querySelectorAll('iframe').length > 0,
                    hasCaptcha: document.body.innerHTML.toLowerCase().includes('captcha'),
                    angularApp: typeof window.angular !== 'undefined',
                    reactApp: typeof window.React !== 'undefined' || document.querySelector('[data-reactroot]') !== null,
                };
            }''')

            findings['technical'] = tech_check
            print(f'    Canvas rendering: {tech_check["hasCanvas"]}')
            print(f'    Iframe detected: {tech_check["hasIframe"]}')
            print(f'    CAPTCHA detected: {tech_check["hasCaptcha"]}')

            if tech_check['hasCanvas']:
                findings['blockers'].append('Canvas rendering (may be difficult to scrape)')
            if tech_check['hasCaptcha']:
                findings['blockers'].append('CAPTCHA detected')

            findings['accessible'] = len(findings['blockers']) == 0

        except Exception as e:
            print(f'\nERROR: {e}')
            findings['error'] = str(e)
            findings['blockers'].append(f'Exception: {e}')
            await page.screenshot(path='debug_html/westlake_mygov_error.png')

        finally:
            await browser.close()

    # Summary
    print('\n' + '=' * 60)
    print('INVESTIGATION SUMMARY')
    print('=' * 60)
    print(f'Portal URL: {findings["url"]}')
    print(f'Accessible: {findings["accessible"]}')
    print(f'Requires Login: {findings["requires_login"]}')
    print(f'Has Permit Search: {findings["has_permit_search"]}')
    print(f'Blockers: {findings["blockers"]}')
    print(f'Notes: {findings["notes"]}')

    # Write findings
    import json
    Path('westlake_investigation.json').write_text(json.dumps(findings, indent=2))
    print(f'\nFindings saved to: westlake_investigation.json')

    # Verdict
    print('\n' + '-' * 60)
    if findings['accessible'] and findings['has_permit_search']:
        print('VERDICT: PROCEED - Portal appears scrapeable')
        print('NEXT: Build proper scraper based on findings')
    elif findings['requires_login']:
        print('VERDICT: BLOCKED - Login required')
        print('NEXT: Check if public access is available, or skip this city')
    else:
        print('VERDICT: INVESTIGATE FURTHER - See debug screenshots')
        print('NEXT: Review westlake_mygov_initial.png for manual analysis')

    return findings


if __name__ == '__main__':
    asyncio.run(investigate())
