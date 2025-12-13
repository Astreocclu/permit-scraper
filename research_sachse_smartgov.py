#!/usr/bin/env python3
"""
Research script for Sachse SmartGov platform
Investigates scrapability without building a full scraper
"""

import asyncio
import json
from playwright.async_api import async_playwright
from datetime import datetime

async def research_smartgov():
    """Research the Sachse SmartGov platform"""

    url = "https://pl-sachse-tx.smartgovcommunity.com/Public/Home"

    findings = {
        "url": url,
        "timestamp": datetime.now().isoformat(),
        "public_access": None,
        "framework": None,
        "login_required": None,
        "permit_search_available": None,
        "api_endpoints": [],
        "page_structure": {},
        "scrapability": None,
        "notes": []
    }

    async with async_playwright() as p:
        # Launch browser with headless=False for debugging
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        page = await context.new_page()

        # Track network requests to find API endpoints
        api_endpoints = []

        def handle_request(request):
            url = request.url
            # Look for API-like endpoints
            if any(keyword in url.lower() for keyword in ['api', 'service', 'data', 'permit', 'json', 'graphql']):
                api_endpoints.append({
                    'url': url,
                    'method': request.method,
                    'resource_type': request.resource_type
                })

        page.on('request', handle_request)

        print(f"\n{'='*80}")
        print(f"RESEARCHING: {url}")
        print(f"{'='*80}\n")

        try:
            # Navigate to the site
            print("1. Navigating to site...")
            response = await page.goto(url, wait_until='networkidle', timeout=30000)
            print(f"   Status: {response.status}")
            findings['notes'].append(f"Initial load status: {response.status}")

            # Take initial screenshot
            await page.screenshot(path='/home/reid/testhome/permit-scraper/sachse_home.png')
            print("   Screenshot saved: sachse_home.png")

            # Wait a moment for any dynamic content
            await asyncio.sleep(3)

            # Check page title
            title = await page.title()
            print(f"   Page title: {title}")
            findings['page_structure']['title'] = title

            # 2. Check for login requirements
            print("\n2. Checking for login requirements...")
            login_elements = await page.locator('text=/login|sign in/i').count()
            login_forms = await page.locator('form[action*="login"], input[type="password"]').count()

            if login_elements > 0 or login_forms > 0:
                print(f"   Found {login_elements} login text elements and {login_forms} login forms")
                findings['login_required'] = True
                findings['notes'].append("Login elements detected on page")
            else:
                print("   No obvious login requirements detected")
                findings['login_required'] = False

            # 3. Look for permit search functionality
            print("\n3. Looking for permit search functionality...")

            # Check for search-related elements
            search_inputs = await page.locator('input[type="search"], input[placeholder*="search" i], input[name*="search" i]').count()
            search_buttons = await page.locator('button:has-text("Search"), input[type="submit"][value*="Search" i]').count()
            permit_text = await page.locator('text=/permit/i').count()

            print(f"   Search inputs: {search_inputs}")
            print(f"   Search buttons: {search_buttons}")
            print(f"   'Permit' mentions: {permit_text}")

            findings['permit_search_available'] = search_inputs > 0 or search_buttons > 0
            findings['page_structure']['search_inputs'] = search_inputs
            findings['page_structure']['search_buttons'] = search_buttons
            findings['page_structure']['permit_mentions'] = permit_text

            # Look for navigation/menu items
            print("\n4. Checking navigation structure...")
            nav_items = await page.locator('nav a, .nav a, .menu a, [role="navigation"] a').all()
            nav_texts = []
            for item in nav_items[:20]:  # Limit to first 20
                try:
                    text = await item.inner_text()
                    nav_texts.append(text.strip())
                except:
                    pass

            print(f"   Found {len(nav_items)} navigation items")
            if nav_texts:
                print(f"   Sample nav items: {nav_texts[:10]}")
            findings['page_structure']['navigation_items'] = nav_texts

            # 4. Detect framework
            print("\n5. Detecting JavaScript framework...")

            # Check page content for framework indicators
            html_content = await page.content()

            frameworks = {
                'Angular': ['ng-app', 'ng-controller', 'ng-', '[ng-', 'angular', '_angular'],
                'React': ['react', '_react', 'data-reactroot', 'data-reactid'],
                'Vue': ['v-app', 'v-bind', 'v-if', 'vue', '_vue'],
                'jQuery': ['jquery', '$'],
                'Blazor': ['blazor', '_blazor'],
            }

            detected_frameworks = []
            for framework, indicators in frameworks.items():
                for indicator in indicators:
                    if indicator.lower() in html_content.lower():
                        detected_frameworks.append(framework)
                        break

            if detected_frameworks:
                findings['framework'] = detected_frameworks
                print(f"   Detected frameworks: {', '.join(detected_frameworks)}")
            else:
                findings['framework'] = "Unknown/Vanilla JS"
                print("   No specific framework detected")

            # Check for __NEXT_DATA__ or other SSR indicators
            next_data = await page.locator('#__NEXT_DATA__').count()
            if next_data > 0:
                print("   Next.js SSR detected")
                findings['notes'].append("Next.js Server-Side Rendering detected")

            # 5. Check for public access to data
            print("\n6. Testing public access...")

            # Try to find any data tables or lists
            tables = await page.locator('table').count()
            lists = await page.locator('ul, ol').count()

            print(f"   Tables found: {tables}")
            print(f"   Lists found: {lists}")

            if tables > 0 or lists > 0:
                findings['public_access'] = True
                findings['notes'].append(f"Found {tables} tables and {lists} lists")

            # 6. Wait for any API calls to complete
            print("\n7. Waiting for API calls...")
            await asyncio.sleep(2)

            # Analyze captured API endpoints
            if api_endpoints:
                print(f"   Captured {len(api_endpoints)} API-like requests:")
                for endpoint in api_endpoints[:10]:  # Show first 10
                    print(f"   - {endpoint['method']} {endpoint['url'][:100]}")
                findings['api_endpoints'] = api_endpoints
            else:
                print("   No obvious API endpoints detected")

            # Try to interact with search if available
            if findings['permit_search_available']:
                print("\n8. Testing search functionality...")
                try:
                    # Look for the first search input
                    search_input = page.locator('input[type="search"], input[placeholder*="search" i]').first
                    if await search_input.count() > 0:
                        await search_input.fill("test")
                        await asyncio.sleep(1)

                        # Take screenshot after search
                        await page.screenshot(path='/home/reid/testhome/permit-scraper/sachse_search.png')
                        print("   Search test screenshot saved: sachse_search.png")
                        findings['notes'].append("Search functionality tested")
                except Exception as e:
                    print(f"   Error testing search: {e}")

            # Final assessment
            print("\n" + "="*80)
            print("SCRAPABILITY ASSESSMENT")
            print("="*80)

            # Determine scrapability
            if findings['login_required']:
                scrapability = "Hard"
                recommendation = "Login required - need to implement authentication"
            elif not findings['public_access'] and not findings['permit_search_available']:
                scrapability = "Blocked"
                recommendation = "No public data access detected - may not be scrapable"
            elif findings['framework'] and 'Angular' in findings.get('framework', []):
                scrapability = "Medium"
                recommendation = "Angular app - requires JavaScript rendering, use Playwright"
            elif findings['api_endpoints']:
                scrapability = "Easy-Medium"
                recommendation = "API endpoints detected - may be able to use direct API calls"
            else:
                scrapability = "Medium"
                recommendation = "Standard scraping with Playwright should work"

            findings['scrapability'] = scrapability
            findings['recommendation'] = recommendation

            print(f"\nScrapability: {scrapability}")
            print(f"Recommendation: {recommendation}")

            # Keep browser open for manual inspection
            print("\n" + "="*80)
            print("Browser will remain open for 30 seconds for manual inspection...")
            print("="*80)
            await asyncio.sleep(30)

        except Exception as e:
            print(f"\nError during research: {e}")
            findings['notes'].append(f"Error: {str(e)}")
            findings['scrapability'] = "Unknown"
            findings['recommendation'] = f"Error during research: {e}"

        finally:
            await browser.close()

    # Save findings to JSON
    output_file = '/home/reid/testhome/permit-scraper/sachse_research_findings.json'
    with open(output_file, 'w') as f:
        json.dump(findings, f, indent=2)

    print(f"\n\nFindings saved to: {output_file}")

    return findings

if __name__ == "__main__":
    print("Starting SmartGov research...")
    findings = asyncio.run(research_smartgov())

    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Public Access: {findings.get('public_access', 'Unknown')}")
    print(f"Framework: {findings.get('framework', 'Unknown')}")
    print(f"Login Required: {findings.get('login_required', 'Unknown')}")
    print(f"Permit Search: {findings.get('permit_search_available', 'Unknown')}")
    print(f"API Endpoints: {len(findings.get('api_endpoints', []))}")
    print(f"Scrapability: {findings.get('scrapability', 'Unknown')}")
    print(f"Recommendation: {findings.get('recommendation', 'N/A')}")
    print("="*80)
