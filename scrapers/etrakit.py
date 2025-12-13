#!/usr/bin/env python3
"""
FAST eTRAKiT PERMIT SCRAPER - DOM extraction (no LLM)
Extracts directly from page structure, much faster than LLM approach.

Usage:
  python scrapers/etrakit.py frisco 5000
"""

import asyncio
import json
import re
import sys
from datetime import datetime
from pathlib import Path

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

ETRAKIT_CITIES = {
    'frisco': {
        'name': 'Frisco',
        'base_url': 'https://etrakit.friscotexas.gov',
        'search_path': '/etrakit/Search/permit.aspx',
        'prefixes': ['B25', 'B24', 'B23', 'B22', 'B21', 'B20', 'B19'],
        'permit_regex': r'^[A-Z]\d{2}-\d{5}$',  # B25-00001 format
    },
    'flower_mound': {
        'name': 'Flower Mound',
        'base_url': 'https://etrakit.flower-mound.com',
        'search_path': '/etrakit/Search/permit.aspx',
        # Flower Mound uses type-based prefixes: BP (Building), EL (Electrical), PL (Plumbing), etc.
        # Format: XX-YY-NNNNN or XXNN-NNNNN (e.g., EL-00-0026, BP13-01542, RER-11-3040)
        'prefixes': [
            'BP',   # Building Permits
            'EL',   # Electrical
            'PL',   # Plumbing
            'ME',   # Mechanical
            'RO',   # Roofing
            'RF',   # Roofing (alt)
            'AC',   # A/C
            'HV',   # HVAC
            'RE',   # Residential
            'RER',  # Residential Remodel
            'CO',   # Certificate of Occupancy
            'DE',   # Demolition
            'PO',   # Pool
            'FE',   # Fence
            'IR',   # Irrigation
            'FR',   # Fire
            'SW',   # Swimming
            'DR',   # Driveway
            'GR',   # Grading
            'SI',   # Sign
            'PC',   # Plan Check
            'COM',  # Commercial
            'AD',   # Addition
        ],
        'permit_regex': r'^[A-Z]{1,4}\d{0,2}-?\d{2}-?\d{4,5}$',  # Flexible: EL-00-0026, BP13-01542, RER-11-3040
    },
    'denton': {
        'name': 'Denton',
        'base_url': 'https://dntn-trk.aspgov.com/eTRAKiT',
        'search_path': '/Search/permit.aspx',
        # Denton uses YYMM-#### format: 2501-0001 (2025-Jan), 2412-0001 (2024-Dec)
        # Need ~20 months to get 1000 permits (~50/month)
        'prefixes': ['2501', '2412', '2411', '2410', '2409', '2408', '2407', '2406',
                     '2405', '2404', '2403', '2402', '2401', '2312', '2311', '2310',
                     '2309', '2308', '2307', '2306'],
        'permit_regex': r'^\d{4}-\d{4}$',
    },
    'keller': {
        'name': 'Keller',
        'base_url': 'https://trakitweb.cityofkeller.com',
        'search_path': '/etrakit/Search/permit.aspx',
        # Keller uses BYY-#### format: B25-1234, B24-5678
        'prefixes': ['B25-', 'B24-', 'B23-', 'B22-', 'B21-', 'B20-'],
        'permit_regex': r'^[A-Z]\d{2}-\d{4,5}$',
    },
    'prosper': {
        'name': 'Prosper',
        'base_url': 'http://etrakit.prospertx.gov',
        'search_path': '/eTRAKIT/Search/permit.aspx',
        # Prosper uses type prefixes like Flower Mound - BP, EL, PL, ME, RO, RE, etc.
        'prefixes': ['BP', 'RE', 'RO', 'EL', 'PL', 'ME', 'PO', 'FE', 'AC', 'HV', 'AD', 'SW'],
        'permit_regex': r'^[A-Z]{2,4}[-\d]*\d{4,6}$',
    },
}


async def extract_permits_from_page(page, permit_regex: str = r'^[A-Z]{1,2}\d{2}-\d{5}$') -> list:
    """Extract permits directly from DOM - no LLM needed."""
    return await page.evaluate('''(regex) => {
        const permits = [];
        const rows = document.querySelectorAll('tr.rgRow, tr.rgAltRow');
        const permitPattern = new RegExp(regex);

        for (const row of rows) {
            const cells = row.querySelectorAll('td');
            if (cells.length < 3) continue;

            // Extract text from cells
            const cellTexts = Array.from(cells).map(c => c.innerText.trim());

            // Find permit ID - ALWAYS try link first (most reliable)
            let permit_id = null;
            let address = null;
            let permit_type = null;
            let status = null;
            let date = null;

            // Get permit_id from link (most reliable method)
            const link = row.querySelector('a');
            if (link) {
                const linkText = link.innerText.trim();
                // Accept any text that looks like a permit ID (has letters and numbers with dashes)
                if (/^[A-Z]{1,4}[\d-]+/i.test(linkText) && linkText.length < 20) {
                    permit_id = linkText;
                }
            }

            // Fallback: try regex on cell texts
            if (!permit_id) {
                for (const text of cellTexts) {
                    if (permitPattern.test(text)) {
                        permit_id = text;
                        break;
                    }
                }
            }

            // Extract other fields from cells
            for (const text of cellTexts) {
                if (!address && /^\d+\s+[A-Z]/i.test(text) && text.length > 10) {
                    address = text;
                } else if (!permit_type && /^(Building|Electrical|Plumbing|Mechanical|Roofing|Pool|Demolition|Fire|HVAC|Gas|Irrigation)/i.test(text)) {
                    permit_type = text;
                } else if (!status && /^(Issued|Active|Final|Expired|Closed|Pending|Approved|Void)/i.test(text)) {
                    status = text;
                } else if (!date && /^\d{1,2}\/\d{1,2}\/\d{4}$/.test(text)) {
                    date = text;
                }
            }

            if (permit_id) {
                permits.push({
                    permit_id: permit_id,
                    address: address || '',
                    type: permit_type || '',
                    status: status || '',
                    date: date || '',
                    raw_cells: cellTexts.slice(0, 6)  // Keep raw data for debugging
                });
            }
        }

        return permits;
    }''', permit_regex)


async def scrape_fast(city_key: str, target_count: int = 1000):
    """Fast scrape using DOM extraction, multiple year prefixes."""
    city_key = city_key.lower()
    if city_key not in ETRAKIT_CITIES:
        print(f'ERROR: Unknown city. Available: {list(ETRAKIT_CITIES.keys())}')
        sys.exit(1)

    config = ETRAKIT_CITIES[city_key]
    base_url = config['base_url']
    search_path = config['search_path']

    print('=' * 60)
    print(f'{config["name"].upper()} FAST PERMIT SCRAPER')
    print('=' * 60)
    print(f'Target: {target_count} permits')
    print(f'Time: {datetime.now().isoformat()}\n')

    all_permits = []
    errors = []

    # Use city-specific prefixes, or default to B-prefixed
    prefixes = config.get('prefixes', ['B25', 'B24', 'B23', 'B22', 'B21', 'B20', 'B19'])
    permit_regex = config.get('permit_regex', r'^[A-Z]{1,2}\d{2}-\d{5}$')

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1280, 'height': 900})
        page = await context.new_page()

        try:
            for prefix in prefixes:
                if len(all_permits) >= target_count:
                    break

                print(f'\n[{prefix}] Searching prefix "{prefix}"...')

                # Load search page
                await page.goto(f'{base_url}{search_path}', wait_until='networkidle', timeout=60000)
                await asyncio.sleep(2)

                # Fill search
                await page.fill('#cplMain_txtSearchString', prefix)
                await asyncio.sleep(0.5)

                # Click search
                await page.click('input[id*="btnSearch"]')
                await asyncio.sleep(4)

                # Get page count
                page_info = await page.evaluate('''() => {
                    const span = document.querySelector('span.font12.italic');
                    if (span) {
                        const match = span.textContent.match(/page (\d+) of (\d+)/);
                        if (match) return {current: parseInt(match[1]), total: parseInt(match[2])};
                    }
                    return {current: 1, total: 1};
                }''')

                print(f'    Found {page_info["total"]} pages')

                # Extract all pages for this prefix
                page_num = 1
                prefix_permits = []

                while page_num <= page_info['total'] and len(all_permits) + len(prefix_permits) < target_count:
                    permits = await extract_permits_from_page(page, permit_regex)
                    prefix_permits.extend(permits)

                    if page_num % 10 == 0 or page_num == 1:
                        print(f'    Page {page_num}/{page_info["total"]}: +{len(permits)} permits ({len(prefix_permits)} from {prefix})')

                    if page_num >= page_info['total']:
                        break

                    # Click next
                    has_next = await page.evaluate('''() => {
                        const nextBtn = document.querySelector('input.NextPage:not([disabled])');
                        if (nextBtn) { nextBtn.click(); return true; }
                        return false;
                    }''')

                    if not has_next:
                        break

                    await asyncio.sleep(2)
                    page_num += 1

                print(f'    {prefix}: Got {len(prefix_permits)} permits')
                all_permits.extend(prefix_permits)

        except Exception as e:
            print(f'\nERROR: {e}')
            errors.append(str(e))
            await page.screenshot(path='debug_html/frisco_fast_error.png')

        finally:
            await browser.close()

    # Deduplicate by permit_id
    seen = set()
    unique_permits = []
    for p in all_permits:
        if p['permit_id'] not in seen:
            seen.add(p['permit_id'])
            unique_permits.append(p)

    print(f'\n{"=" * 60}')
    print(f'Total collected: {len(all_permits)}')
    print(f'After dedup: {len(unique_permits)}')

    # Save results
    output = {
        'source': city_key,
        'portal_type': 'eTRAKiT',
        'scraped_at': datetime.now().isoformat(),
        'target_count': target_count,
        'actual_count': len(unique_permits),
        'errors': errors,
        'permits': unique_permits[:target_count]
    }

    output_file = f'{city_key}_raw.json'
    Path(output_file).write_text(json.dumps(output, indent=2))
    print(f'Saved to: {output_file}')

    # Sample
    print('\nSAMPLE:')
    for p in unique_permits[:5]:
        print(f'  {p["permit_id"]} | {p.get("type", "?")} | {p.get("address", "?")[:40]}')

    return output


if __name__ == '__main__':
    city = sys.argv[1] if len(sys.argv) > 1 else 'frisco'
    count = int(sys.argv[2]) if len(sys.argv) > 2 else 1000
    asyncio.run(scrape_fast(city, count))
