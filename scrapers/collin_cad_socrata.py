#!/usr/bin/env python3
"""
COLLIN CAD PERMIT SCRAPER (Socrata API)
Source: Texas Open Data Portal - Collin Central Appraisal District
URL: https://data.texas.gov/dataset/Collin-CAD-Building-Permits/82ee-gbj5

This scrapes permit data from the Collin CAD which covers ALL Collin County cities:
- McKinney (20K+), Allen (14K+), Frisco (11K+), Celina (8K+)
- Princeton, Wylie, Prosper, Plano, Anna, Melissa, Murphy
- Richardson (was blocked!), Sachse, and more

Data includes: owner names, addresses, permit types, values, builder names

Usage:
    python scrapers/collin_cad_socrata.py                    # All cities, 1000 permits
    python scrapers/collin_cad_socrata.py --city mckinney    # Specific city
    python scrapers/collin_cad_socrata.py --limit 5000       # More permits
    python scrapers/collin_cad_socrata.py --days 30          # Last 30 days only
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

import requests

OUTPUT_DIR = Path(__file__).parent.parent / "data" / "raw"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SOCRATA_ENDPOINT = "https://data.texas.gov/resource/82ee-gbj5.json"

# City name mapping (Socrata uses "CITY_NAME CITY" format)
CITY_MAP = {
    'mckinney': 'MCKINNEY CITY',
    'allen': 'ALLEN CITY',
    'frisco': 'FRISCO CITY',
    'celina': 'CELINA CITY',
    'princeton': 'PRINCETON CITY',
    'wylie': 'WYLIE CITY',
    'prosper': 'PROSPER TOWN',
    'plano': 'PLANO CITY',
    'anna': 'ANNA CITY',
    'melissa': 'MELISSA CITY',
    'murphy': 'MURPHY CITY',
    'richardson': 'RICHARDSON CITY',
    'sachse': 'SACHSE CITY',
    'lucas': 'LUCAS CITY',
    'lavon': 'LAVON CITY',
    'farmersville': 'FARMERSVILLE CITY',
    'fairview': 'FAIRVIEW TOWN',
    'parker': 'PARKER CITY',
}


def fetch_permits(city: str = None, limit: int = 1000, days: int = None, offset: int = 0) -> list:
    """Fetch permits from Collin CAD Socrata API."""
    params = {
        '$limit': limit,
        '$offset': offset,
        '$order': 'permitissueddate DESC',
    }

    # Build WHERE clause
    where_clauses = []

    if city:
        city_filter = CITY_MAP.get(city.lower(), city.upper())
        where_clauses.append(f"permitissuedby = '{city_filter}'")

    if days:
        cutoff = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%dT00:00:00.000')
        where_clauses.append(f"permitissueddate >= '{cutoff}'")

    # Only residential
    where_clauses.append("proprescom = 'Residential'")

    if where_clauses:
        params['$where'] = ' AND '.join(where_clauses)

    response = requests.get(SOCRATA_ENDPOINT, params=params, timeout=60)
    response.raise_for_status()
    return response.json()


def transform_permit(raw: dict) -> dict:
    """Transform Socrata record to our standard format."""
    # Parse date
    issued_date = raw.get('permitissueddate', '')
    if issued_date:
        issued_date = issued_date[:10]  # Just YYYY-MM-DD

    # Extract city from permitissuedby (e.g., "MCKINNEY CITY" -> "mckinney")
    issuer = raw.get('permitissuedby', '')
    city = issuer.replace(' CITY', '').replace(' TOWN', '').lower()

    return {
        'permit_id': raw.get('permitnum', raw.get('permitid', '')),
        'address': raw.get('situsconcatshort', raw.get('situsconcat', '')),
        'city': city.title(),
        'zip': raw.get('situszip', ''),
        'type': raw.get('permittypedescr', ''),
        'subtype': raw.get('permitsubtypedescr', ''),
        'date': issued_date,
        'value': raw.get('permitvalue', ''),
        'owner_name': raw.get('propownername', ''),
        'builder': raw.get('permitbuildername', ''),
        'description': raw.get('permitcomments', ''),
        'area_sqft': raw.get('permitbldgarea', ''),
        'property_type': raw.get('proprescom', ''),
    }


def main():
    parser = argparse.ArgumentParser(description='Scrape Collin CAD permits from Texas Open Data')
    parser.add_argument('--city', '-c', help='Filter by city (e.g., mckinney, allen, frisco)')
    parser.add_argument('--limit', '-l', type=int, default=1000, help='Max permits to fetch')
    parser.add_argument('--days', '-d', type=int, help='Only permits from last N days')
    parser.add_argument('--list-cities', action='store_true', help='List available cities')
    args = parser.parse_args()

    if args.list_cities:
        print("Available cities in Collin CAD:")
        for key, value in sorted(CITY_MAP.items()):
            print(f"  {key}: {value}")
        return

    print('=' * 60)
    print('COLLIN CAD PERMIT SCRAPER (Socrata API)')
    print('=' * 60)
    print(f'City filter: {args.city or "ALL"}')
    print(f'Limit: {args.limit}')
    print(f'Days filter: {args.days or "ALL"}')
    print(f'Time: {datetime.now().isoformat()}\n')

    # Fetch permits
    print('[1] Fetching permits from Texas Open Data Portal...')
    raw_permits = fetch_permits(
        city=args.city,
        limit=args.limit,
        days=args.days
    )
    print(f'    Retrieved {len(raw_permits)} permits')

    # Transform
    print('[2] Transforming to standard format...')
    permits = [transform_permit(p) for p in raw_permits]

    # Filter out empty permit IDs
    permits = [p for p in permits if p['permit_id']]
    print(f'    {len(permits)} valid permits')

    # Analyze
    cities = {}
    for p in permits:
        c = p['city']
        cities[c] = cities.get(c, 0) + 1

    print('\n[3] Permits by city:')
    for city, count in sorted(cities.items(), key=lambda x: -x[1])[:15]:
        print(f'    {city}: {count}')

    # Save
    city_suffix = f"_{args.city}" if args.city else ""
    output_file = OUTPUT_DIR / f"collin_cad{city_suffix}_raw.json"

    output = {
        'source': f'collin_cad{city_suffix}',
        'portal_type': 'Socrata',
        'scraped_at': datetime.now().isoformat(),
        'target_count': args.limit,
        'actual_count': len(permits),
        'filters': {
            'city': args.city,
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
        for p in permits[:5]:
            print(f'  {p["date"]} | {p["permit_id"]} | {p["type"]} | {p["address"][:40]}')
            if p.get('owner_name'):
                print(f'    Owner: {p["owner_name"]}')


if __name__ == '__main__':
    main()
