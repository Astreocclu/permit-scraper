#!/usr/bin/env python3
# scrapers/denton_socrata.py
"""
DENTON CITY PERMIT SCRAPER (Socrata API)
Source: City of Denton Open Data Portal
URL: https://data.cityofdenton.com

Scrapes building permit data from City of Denton's Socrata-based Open Data portal.
Follows the same pattern as collin_cad_socrata.py.

Usage:
    python3 scrapers/denton_socrata.py                  # All permits, 1000 limit
    python3 scrapers/denton_socrata.py --limit 5000     # More permits
    python3 scrapers/denton_socrata.py --days 30        # Last 30 days only
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

import requests
from tenacity import retry, stop_after_attempt, wait_exponential

OUTPUT_DIR = Path(__file__).parent.parent / "data" / "raw"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# City of Denton Socrata endpoint
# NOTE: This is a placeholder - need to verify actual dataset ID
# Check: https://data.cityofdenton.com/browse?category=Development+Services
SOCRATA_ENDPOINT = "https://data.cityofdenton.com/resource/xxxx-xxxx.json"


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def fetch_permits(limit: int = 1000, days: int = None, offset: int = 0) -> list:
    """
    Fetch permits from Denton City Socrata API.

    Uses tenacity for automatic retry with exponential backoff
    (addresses undocumented rate limits).
    """
    params = {
        '$limit': limit,
        '$offset': offset,
        '$order': 'issue_date DESC',
    }

    if days:
        cutoff = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%dT00:00:00.000')
        params['$where'] = f"issue_date >= '{cutoff}'"

    response = requests.get(SOCRATA_ENDPOINT, params=params, timeout=60)
    response.raise_for_status()
    return response.json()


def transform_permit(raw: dict) -> dict:
    """
    Transform Socrata record to standard format.

    Field mapping TBD based on actual Denton schema.
    """
    issued_date = raw.get('issue_date', '')
    if issued_date:
        issued_date = issued_date[:10]

    return {
        'permit_id': raw.get('permit_number', raw.get('permit_num', '')),
        'address': raw.get('address', raw.get('site_address', '')),
        'city': 'Denton',
        'zip': raw.get('zip_code', raw.get('zip', '')),
        'type': raw.get('permit_type', raw.get('type', '')),
        'subtype': raw.get('permit_subtype', ''),
        'date': issued_date,
        'value': raw.get('valuation', raw.get('value', '')),
        'owner_name': raw.get('owner', raw.get('owner_name', '')),
        'contractor': raw.get('contractor', raw.get('contractor_name', '')),
        'description': raw.get('description', raw.get('work_description', '')),
    }


def main():
    parser = argparse.ArgumentParser(description='Scrape Denton City permits from Open Data portal')
    parser.add_argument('--limit', '-l', type=int, default=1000, help='Max permits to fetch')
    parser.add_argument('--days', '-d', type=int, help='Only permits from last N days')
    parser.add_argument('--discover', action='store_true', help='Print API discovery info')
    args = parser.parse_args()

    if args.discover:
        print("Denton Open Data Discovery:")
        print(f"  Portal: https://data.cityofdenton.com")
        print(f"  Browse: https://data.cityofdenton.com/browse")
        print(f"  API Docs: https://dev.socrata.com/docs/endpoints.html")
        print("\nTo find the dataset ID:")
        print("  1. Visit the portal and find 'Building Safety Yearly Permit Report'")
        print("  2. Click 'API' button on the dataset page")
        print("  3. Copy the resource ID (e.g., 'xxxx-xxxx')")
        print("  4. Update SOCRATA_ENDPOINT in this file")
        return

    print('=' * 60)
    print('DENTON CITY PERMIT SCRAPER (Socrata API)')
    print('=' * 60)
    print(f'Limit: {args.limit}')
    print(f'Days filter: {args.days or "ALL"}')
    print(f'Time: {datetime.now().isoformat()}\n')

    print('[1] Fetching permits from Denton Open Data Portal...')
    try:
        raw_permits = fetch_permits(limit=args.limit, days=args.days)
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            print("\nERROR: Dataset not found. Run with --discover to find the correct endpoint.")
            return 1
        raise

    print(f'    Retrieved {len(raw_permits)} permits')

    print('[2] Transforming to standard format...')
    permits = [transform_permit(p) for p in raw_permits]
    permits = [p for p in permits if p['permit_id']]
    print(f'    {len(permits)} valid permits')

    types = {}
    for p in permits:
        t = p['type'] or 'Unknown'
        types[t] = types.get(t, 0) + 1

    print('\n[3] Permits by type:')
    for ptype, count in sorted(types.items(), key=lambda x: -x[1])[:10]:
        print(f'    {ptype}: {count}')

    output_file = OUTPUT_DIR / "denton_socrata_raw.json"

    output = {
        'source': 'denton_socrata',
        'portal_type': 'Socrata',
        'data_source': 'denton_socrata',
        'scraped_at': datetime.now().isoformat(),
        'target_count': args.limit,
        'actual_count': len(permits),
        'filters': {
            'days': args.days,
        },
        'permits': permits
    }

    output_file.write_text(json.dumps(output, indent=2))

    print(f'\n' + '=' * 60)
    print('SUMMARY')
    print('=' * 60)
    print(f'Permits: {len(permits)}')
    print(f'Output: {output_file}')

    if permits:
        print('\nSAMPLE:')
        for p in permits[:3]:
            print(f'  {p["date"]} | {p["permit_id"]} | {p["type"]} | {p["address"][:40]}')


if __name__ == '__main__':
    main()
