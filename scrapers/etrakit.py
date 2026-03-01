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
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

# Output directory for raw JSON
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "raw"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

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
    # BLOCKED: Keller's eTRAKiT portal requires contractor login for searches
    # No public permit search available - only contractor access
    # 'keller': {
    #     'name': 'Keller',
    #     'base_url': 'https://trakitweb.cityofkeller.com',
    #     'search_path': '/etrakit/Search/permit.aspx',
    #     'prefixes': ['B25-', 'B24-'],
    #     'permit_regex': r'^[A-Z]\d{2}-\d{4,5}$',
    # },
    # DEPRECATED: Prosper migrated to EnerGov CSS (Dec 2022)
    # Use citizen_self_service.py prosper instead
    # Old eTRAKiT portal (etrakit.prospertx.gov) is defunct
    # 'prosper': {
    #     'name': 'Prosper',
    #     'base_url': 'http://etrakit.prospertx.gov',
    #     'search_path': '/eTRAKIT/Search/permit.aspx',
    #     'prefixes': ['BP', 'RE', 'RO', 'EL', 'PL', 'ME', 'PO', 'FE', 'AC', 'HV', 'AD', 'SW'],
    #     'permit_regex': r'^[A-Z]{2,4}[-\d]*\d{4,6}$',
    # },
    'the_colony': {
        'name': 'The Colony',
        'base_url': 'https://tcol-trk.aspgov.com',
        'search_path': '/etrakit/Search/permit.aspx',
        # The Colony uses letter prefixes: B, P, E (Building, Plumbing, Electrical)
        # Format: MMYY-NNNN (0701-4211) - month/year prefix
        'prefixes': ['B', 'P', 'E', 'M', 'R', 'H', 'F'],
        'permit_regex': r'^\d{4}-\d{4}$',
        # The Colony search results only show street names (no numbers)
        # Must click into detail page to get full address
        'needs_detail_extraction': True,
    },
}

# Cities that used to run on eTRAKiT but migrated to other portal types.
# Keep this map so legacy commands can still complete.
MIGRATED_CITY_HANDOFFS = {
    'prosper': {
        'name': 'Prosper',
        'script': 'citizen_self_service.py',
        'city_arg': 'prosper',
        'reason': 'City migrated from eTRAKiT to EnerGov CSS (Dec 2022)',
    },
}


def run_migrated_city_handoff(city_key: str, target_count: int) -> int:
    """Delegate migrated-city runs to the owning scraper."""
    handoff = MIGRATED_CITY_HANDOFFS[city_key]
    script_path = Path(__file__).parent / handoff['script']
    cmd = [sys.executable, str(script_path), handoff['city_arg'], str(target_count)]
    print(f'INFO: {handoff["name"]} is no longer on eTRAKiT. {handoff["reason"]}.')
    print(f'INFO: Delegating to: {" ".join(cmd)}')
    result = subprocess.run(cmd, check=False)
    return result.returncode


async def goto_search_page(page, search_url: str, city_name: str, attempts: int = 3) -> None:
    """
    Navigate to eTRAKiT search page with timeout-safe waits.

    `networkidle` is brittle on some portals due long-lived requests.
    We use `domcontentloaded` plus an explicit search-input wait.
    """
    last_error = None
    for attempt in range(1, attempts + 1):
        try:
            await page.goto(search_url, wait_until='domcontentloaded', timeout=60000)
            await page.wait_for_selector('#cplMain_txtSearchString', timeout=25000)
            return
        except PlaywrightTimeout as exc:
            last_error = exc
            print(f'    WARN: {city_name} search page timeout (attempt {attempt}/{attempts})')
            if attempt < attempts:
                await asyncio.sleep(1.5 * attempt)
    if last_error:
        raise last_error
    raise RuntimeError(f'{city_name} search page timed out')


async def extract_permits_from_page(page, permit_regex: str = r'^[A-Z]{1,2}\d{2}-\d{5}$') -> list:
    """Extract permits directly from DOM - no LLM needed."""
    return await page.evaluate(r'''(regex) => {
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
                // Infer type from permit ID prefix if not found in table
                if (!permit_type) {
                    const prefixMap = {
                        'RE': 'Residential', 'RES': 'Residential',
                        'RO': 'Roofing', 'RF': 'Roofing',
                        'EL': 'Electrical', 'ELEC': 'Electrical',
                        'PL': 'Plumbing', 'PLB': 'Plumbing',
                        'ME': 'Mechanical', 'MECH': 'Mechanical',
                        'BP': 'Building Permit', 'BLD': 'Building',
                        'PO': 'Pool', 'SW': 'Swimming Pool',
                        'FE': 'Fence', 'FEN': 'Fence',
                        'AC': 'A/C', 'HV': 'HVAC',
                        'AD': 'Addition', 'ADD': 'Addition',
                        'CO': 'Certificate of Occupancy',
                        'DE': 'Demolition', 'DEM': 'Demolition',
                        'IR': 'Irrigation', 'FR': 'Fire',
                        'GA': 'Gas', 'GAS': 'Gas',
                        'SI': 'Sign', 'COM': 'Commercial',
                        'H': 'HVAC', 'B': 'Building',
                        'BF': 'Building Final', 'GS': 'Grading/Site',
                        'RER': 'Residential Remodel', 'NR': 'New Residential',
                        'NC': 'New Commercial', 'TI': 'Tenant Improvement'
                    };
                    const match = permit_id.match(/^([A-Z]+)/i);
                    if (match) {
                        permit_type = prefixMap[match[1].toUpperCase()] || match[1];
                    }
                }

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


async def extract_detail_address(page, permit_id: str) -> str:
    """
    Click into permit detail page and extract full address.
    Used for The Colony where search results only show street names.
    """
    try:
        # Find and click the permit link
        link = await page.query_selector(f'a:has-text("{permit_id}")')
        if not link:
            return ''

        await link.click()
        await asyncio.sleep(2)  # Wait for detail page to load

        # Try to extract address from detail page
        # Common eTRAKiT patterns: "Site Address", "Property Address", "Address", "Location"
        address = await page.evaluate('''() => {
            // Look for address in table rows
            const rows = document.querySelectorAll('tr');
            for (const row of rows) {
                const cells = row.querySelectorAll('td, th');
                for (let i = 0; i < cells.length - 1; i++) {
                    const label = cells[i].innerText.toLowerCase().trim();
                    if (label.includes('site address') || label.includes('property address') ||
                        label.includes('location') || label === 'address') {
                        const value = cells[i + 1]?.innerText?.trim();
                        if (value && /^\\d+\\s+[A-Za-z]/.test(value)) {
                            return value;
                        }
                    }
                }
            }

            // Try span/label patterns
            const spans = document.querySelectorAll('span, label');
            for (const span of spans) {
                if (span.innerText.toLowerCase().includes('address')) {
                    const next = span.nextElementSibling;
                    if (next) {
                        const value = next.innerText?.trim();
                        if (value && /^\\d+\\s+[A-Za-z]/.test(value)) {
                            return value;
                        }
                    }
                }
            }

            // Look for any text that looks like an address (number + street)
            const allText = document.body.innerText;
            const addressMatch = allText.match(/\\b(\\d{1,5}\\s+[A-Z][A-Za-z]+(?:\\s+[A-Za-z]+)*(?:\\s+(?:ST|DR|AVE|BLVD|CT|CIR|LN|RD|WAY|PL|TRL|PKWY|HWY))?)\\b/);
            if (addressMatch) {
                return addressMatch[1];
            }

            return '';
        }''')

        # Go back to search results
        await page.go_back()
        await asyncio.sleep(1)

        return address or ''

    except Exception as e:
        print(f'      Warning: Could not extract detail for {permit_id}: {e}')
        try:
            await page.go_back()
            await asyncio.sleep(1)
        except:
            pass
        return ''


async def scrape_fast(city_key: str, target_count: int = 1000):
    """Fast scrape using DOM extraction, multiple year prefixes."""
    city_key = city_key.lower()
    if city_key in MIGRATED_CITY_HANDOFFS:
        rc = run_migrated_city_handoff(city_key, target_count)
        if rc != 0:
            print(f'ERROR: Delegated scraper exited with code {rc}')
            sys.exit(rc)
        return

    if city_key not in ETRAKIT_CITIES:
        migrated = list(MIGRATED_CITY_HANDOFFS.keys())
        print(f'ERROR: Unknown city. eTRAKiT cities: {list(ETRAKIT_CITIES.keys())}. Migrated cities: {migrated}')
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
                search_url = f'{base_url}{search_path}'
                await goto_search_page(page, search_url, config["name"])
                await asyncio.sleep(1)

                # Fill search
                await page.wait_for_selector('#cplMain_txtSearchString', timeout=10000)
                await page.fill('#cplMain_txtSearchString', prefix)
                await asyncio.sleep(0.5)

                # Click search
                search_clicked = False
                for selector in ['input[id*="btnSearch"]', 'button[id*="btnSearch"]', 'input[value="Search"]']:
                    btn = await page.query_selector(selector)
                    if btn:
                        await btn.click()
                        search_clicked = True
                        break
                if not search_clicked:
                    raise RuntimeError(f'Could not find search button for {config["name"]}')

                try:
                    await page.wait_for_selector(
                        'tr.rgRow, tr.rgAltRow, span.font12.italic, td.rgPagerCell, .rgNoRecords',
                        timeout=20000
                    )
                except PlaywrightTimeout:
                    # Continue; some prefixes legitimately return no rows.
                    pass
                await asyncio.sleep(1)

                # Get page count
                page_info = await page.evaluate(r'''() => {
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

                needs_detail = config.get('needs_detail_extraction', False)

                while page_num <= page_info['total'] and len(all_permits) + len(prefix_permits) < target_count:
                    permits = await extract_permits_from_page(page, permit_regex)

                    # For cities like The Colony that need detail extraction
                    if needs_detail:
                        print(f'    Page {page_num}: Extracting details for {len(permits)} permits...')
                        for i, permit in enumerate(permits):
                            if not permit.get('address'):  # Only if address is empty
                                full_addr = await extract_detail_address(page, permit['permit_id'])
                                if full_addr:
                                    permit['address'] = full_addr
                                    if (i + 1) % 5 == 0:
                                        print(f'      Detail {i+1}/{len(permits)}: {full_addr[:40]}...')

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

                    try:
                        await page.wait_for_selector('tr.rgRow, tr.rgAltRow, .rgNoRecordsText', timeout=15000)
                    except PlaywrightTimeout:
                        pass
                    await asyncio.sleep(1)
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

    output_file = OUTPUT_DIR / f'{city_key}_raw.json'
    output_file.write_text(json.dumps(output, indent=2))
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
