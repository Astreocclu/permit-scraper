#!/usr/bin/env python3
"""
CAD Parcel Fetcher - Bulk download parcels from County CAD APIs.

Supports:
- Denton County (gis.dentoncounty.gov)
- Tarrant County (tad.newedgeservices.com)
- Dallas County (maps.dcad.org)
- Collin County (gismaps.cityofallen.org)

Usage:
    python3 scrapers/cad_parcel_fetcher.py denton --city lewisville
    python3 scrapers/cad_parcel_fetcher.py denton --city "flower mound"
    python3 scrapers/cad_parcel_fetcher.py tarrant --city southlake
"""

import argparse
import asyncio
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Generator, Optional

import httpx

# Output directory for parcel data
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "parcels"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# CAD API configurations
CAD_CONFIGS = {
    'denton': {
        'name': 'Denton County',
        'base_url': 'https://gis.dentoncounty.gov/arcgis/rest/services/CAD/MapServer/0/query',
        'city_field': 'situs_city',
        'parcel_id_field': 'prop_id',
        'fields': [
            'prop_id', 'situs_num', 'situs_street', 'situs_street_sufix',
            'situs_city', 'situs_zip', 'owner_name', 'addr_line1',
            'addr_city', 'addr_zip', 'cert_mkt_val', 'yr_blt', 'living_area'
        ],
        'max_records': 1000,
    },
    'tarrant': {
        'name': 'Tarrant County',
        'base_url': 'https://tad.newedgeservices.com/arcgis/rest/services/TAD/ParcelView/MapServer/1/query',
        'city_field': 'City',
        'parcel_id_field': 'Account_Nu',
        'fields': [
            'Account_Nu', 'Situs_Addr', 'Owner_Name', 'Owner_Addr',
            'Owner_City', 'Owner_Zip', 'Total_Valu', 'Year_Built', 'Living_Are'
        ],
        'max_records': 1000,
    },
    'dallas': {
        'name': 'Dallas County',
        'base_url': 'https://maps.dcad.org/prdwa/rest/services/Property/ParcelQuery/MapServer/4/query',
        'city_field': 'SITUSCITY',
        'parcel_id_field': 'PARCELID',
        'fields': [
            'PARCELID', 'SITEADDRESS', 'OWNERNME1', 'PSTLADDRESS',
            'PSTLCITY', 'PSTLZIP5', 'CNTASSDVAL', 'RESYRBLT', 'BLDGAREA'
        ],
        'max_records': 1000,
    },
}


async def fetch_parcel_count(county: str, city: str) -> int:
    """Get total count of parcels for a city."""
    config = CAD_CONFIGS[county]

    params = {
        'where': f"{config['city_field']}='{city.upper()}'",
        'returnCountOnly': 'true',
        'f': 'json',
    }

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(config['base_url'], params=params)
        response.raise_for_status()
        data = response.json()
        return data.get('count', 0)


async def fetch_parcels_page(
    county: str,
    city: str,
    offset: int = 0,
    limit: int = 1000
) -> list[dict]:
    """Fetch a single page of parcels."""
    config = CAD_CONFIGS[county]

    params = {
        'where': f"{config['city_field']}='{city.upper()}'",
        'outFields': ','.join(config['fields']),
        'resultOffset': offset,
        'resultRecordCount': limit,
        'f': 'json',
    }

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(config['base_url'], params=params)
        response.raise_for_status()
        data = response.json()

        features = data.get('features', [])
        return [f['attributes'] for f in features]


async def fetch_all_parcels(
    county: str,
    city: str,
    delay: float = 0.5,
    progress_callback: Optional[callable] = None
) -> list[dict]:
    """
    Fetch all parcels for a city with pagination.

    Args:
        county: County key (denton, tarrant, dallas)
        city: City name (e.g., 'lewisville')
        delay: Delay between API calls (rate limiting)
        progress_callback: Optional callback(fetched, total)

    Returns:
        List of parcel dictionaries
    """
    config = CAD_CONFIGS[county]
    max_records = config['max_records']

    # Get total count
    total = await fetch_parcel_count(county, city)
    print(f"Total parcels for {city} in {config['name']}: {total:,}")

    if total == 0:
        return []

    all_parcels = []
    offset = 0

    while len(all_parcels) < total:
        parcels = await fetch_parcels_page(county, city, offset, max_records)

        if not parcels:
            break

        all_parcels.extend(parcels)

        if progress_callback:
            progress_callback(len(all_parcels), total)
        else:
            pct = 100 * len(all_parcels) / total
            print(f"  Fetched {len(all_parcels):,} / {total:,} ({pct:.1f}%)")

        offset += max_records

        if offset < total:
            await asyncio.sleep(delay)

    return all_parcels


async def save_parcels_to_file(county: str, city: str, delay: float = 0.5) -> Path:
    """
    Fetch all parcels and save to JSON file.

    Returns:
        Path to saved file
    """
    city_slug = city.lower().replace(' ', '_')
    output_file = OUTPUT_DIR / f"{city_slug}_{county}_parcels.json"

    print(f"\n{'='*60}")
    print(f"FETCHING PARCELS: {city.title()} ({county.title()} County)")
    print(f"{'='*60}")

    parcels = await fetch_all_parcels(county, city, delay)

    output = {
        'county': county,
        'city': city,
        'fetched_at': datetime.now().isoformat(),
        'count': len(parcels),
        'parcels': parcels
    }

    output_file.write_text(json.dumps(output, indent=2))
    print(f"\nSaved {len(parcels):,} parcels to {output_file}")

    return output_file


def main():
    parser = argparse.ArgumentParser(
        description='Fetch parcels from County CAD APIs',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python3 scrapers/cad_parcel_fetcher.py denton --city lewisville
    python3 scrapers/cad_parcel_fetcher.py denton --city "flower mound" --count-only
    python3 scrapers/cad_parcel_fetcher.py tarrant --city southlake --delay 1.0
        """
    )
    parser.add_argument('county', choices=list(CAD_CONFIGS.keys()),
                        help='County to fetch from')
    parser.add_argument('--city', required=True,
                        help='City name (e.g., lewisville, "flower mound")')
    parser.add_argument('--delay', type=float, default=0.5,
                        help='Delay between API calls (default: 0.5s)')
    parser.add_argument('--count-only', action='store_true',
                        help='Only show count, do not fetch')

    args = parser.parse_args()

    if args.count_only:
        count = asyncio.run(fetch_parcel_count(args.county, args.city))
        print(f"Parcels for {args.city} in {args.county}: {count:,}")
    else:
        asyncio.run(save_parcels_to_file(args.county, args.city, args.delay))


if __name__ == '__main__':
    main()
