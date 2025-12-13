#!/usr/bin/env python3
"""
Research the correct Sachse SmartGov URLs
"""

import asyncio
import json
from playwright.async_api import async_playwright
from datetime import datetime

async def research_correct_urls():
    """Research the correct Sachse URLs found via search"""

    urls_to_test = [
        "https://ci-sachse-tx.smartgovcommunity.com",
        "https://ci-sachse-tx.smartgovcommunity.com/Public/Home",
        "https://ci-sachse-tx.training.smartgovcommunity.com",
        "https://ci-sachse-tx.validation.smartgovcommunity.com/ApplicationPublic/ApplicationSearchAdvanced",
    ]

    all_findings = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )

        for url in urls_to_test:
            print(f"\n{'='*80}")
            print(f"TESTING: {url}")
            print(f"{'='*80}\n")

            findings = {
                'url': url,
                'timestamp': datetime.now().isoformat(),
                'accessible': False,
                'status': None,
                'title': None,
                'framework': None,
                'api_endpoints': [],
                'notes': []
            }

            page = await context.new_page()

            # Track API requests
            api_endpoints = []
            def handle_request(request):
                req_url = request.url
                if any(keyword in req_url.lower() for keyword in ['api', 'service', 'data', 'permit', 'json', 'application']):
                    api_endpoints.append({
                        'url': req_url,
                        'method': request.method,
                        'type': request.resource_type
                    })

            page.on('request', handle_request)

            try:
                response = await page.goto(url, wait_until='networkidle', timeout=30000)
                status = response.status
                findings['status'] = status

                print(f"Status: {status}")

                if status < 400:
                    findings['accessible'] = True

                    # Get title
                    title = await page.title()
                    findings['title'] = title
                    print(f"Title: {title}")

                    # Take screenshot
                    screenshot_name = url.replace('https://', '').replace('/', '_')[:50] + '.png'
                    screenshot_path = f'/home/reid/testhome/permit-scraper/{screenshot_name}'
                    await page.screenshot(path=screenshot_path, full_page=True)
                    print(f"Screenshot: {screenshot_name}")

                    # Wait for dynamic content
                    await asyncio.sleep(3)

                    # Check for framework
                    html = await page.content()
                    if 'ng-' in html or 'angular' in html.lower():
                        findings['framework'] = 'Angular'
                    elif 'react' in html.lower():
                        findings['framework'] = 'React'
                    elif 'vue' in html.lower():
                        findings['framework'] = 'Vue'
                    else:
                        findings['framework'] = 'Unknown/Standard'

                    print(f"Framework: {findings['framework']}")

                    # Look for search functionality
                    search_inputs = await page.locator('input[type="search"], input[placeholder*="search" i], input[name*="search" i]').count()
                    search_buttons = await page.locator('button:has-text("Search"), input[type="submit"]').count()

                    print(f"Search inputs: {search_inputs}")
                    print(f"Search buttons: {search_buttons}")

                    findings['has_search'] = search_inputs > 0 or search_buttons > 0

                    # Look for permit-related text
                    permit_count = await page.locator('text=/permit/i').count()
                    application_count = await page.locator('text=/application/i').count()

                    print(f"'Permit' mentions: {permit_count}")
                    print(f"'Application' mentions: {application_count}")

                    # Check for login requirements
                    login_elements = await page.locator('text=/login|sign in/i').count()
                    findings['login_required'] = login_elements > 0
                    print(f"Login required: {findings['login_required']}")

                    # Get navigation items
                    nav_links = await page.locator('nav a, .nav a, .menu a').all()
                    nav_texts = []
                    for link in nav_links[:15]:
                        try:
                            text = await link.inner_text()
                            nav_texts.append(text.strip())
                        except:
                            pass

                    if nav_texts:
                        print(f"Navigation: {nav_texts}")
                        findings['navigation'] = nav_texts

                    # Wait for API calls
                    await asyncio.sleep(2)

                    if api_endpoints:
                        print(f"\nAPI Endpoints ({len(api_endpoints)}):")
                        for endpoint in api_endpoints[:5]:
                            print(f"  - {endpoint['method']} {endpoint['url'][:80]}")
                        findings['api_endpoints'] = api_endpoints

                    # Assessment
                    if findings['login_required']:
                        scrapability = "Medium-Hard"
                        recommendation = "Requires authentication - need to implement login flow"
                    elif api_endpoints:
                        scrapability = "Easy-Medium"
                        recommendation = "API endpoints available - can potentially use direct API calls"
                    elif findings['framework'] == 'Angular':
                        scrapability = "Medium"
                        recommendation = "Angular SPA - requires JavaScript rendering with Playwright"
                    else:
                        scrapability = "Medium"
                        recommendation = "Standard HTML scraping with Playwright should work"

                    findings['scrapability'] = scrapability
                    findings['recommendation'] = recommendation

                    print(f"\nScrapability: {scrapability}")
                    print(f"Recommendation: {recommendation}")

                    # Keep page open for inspection
                    print("\nPage will stay open for 15 seconds...")
                    await asyncio.sleep(15)

                else:
                    print(f"Page returned {status} - not accessible")
                    findings['notes'].append(f"HTTP {status} error")

            except Exception as e:
                print(f"Error: {e}")
                findings['notes'].append(f"Error: {str(e)}")

            await page.close()
            all_findings.append(findings)

        await browser.close()

    # Save all findings
    output_file = '/home/reid/testhome/permit-scraper/sachse_complete_research.json'
    with open(output_file, 'w') as f:
        json.dump(all_findings, f, indent=2)

    print(f"\n{'='*80}")
    print("FINAL SUMMARY")
    print(f"{'='*80}\n")

    for finding in all_findings:
        print(f"URL: {finding['url']}")
        print(f"  Accessible: {finding['accessible']}")
        print(f"  Status: {finding.get('status', 'N/A')}")
        if finding['accessible']:
            print(f"  Title: {finding.get('title', 'N/A')}")
            print(f"  Framework: {finding.get('framework', 'N/A')}")
            print(f"  Has Search: {finding.get('has_search', 'N/A')}")
            print(f"  Login Required: {finding.get('login_required', 'N/A')}")
            print(f"  API Endpoints: {len(finding.get('api_endpoints', []))}")
            print(f"  Scrapability: {finding.get('scrapability', 'N/A')}")
            print(f"  Recommendation: {finding.get('recommendation', 'N/A')}")
        print()

    print(f"\nAll findings saved to: {output_file}")

    return all_findings

if __name__ == "__main__":
    asyncio.run(research_correct_urls())
