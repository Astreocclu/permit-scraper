#!/usr/bin/env python3
"""
Dual-Source Scraping Script

Runs both city portal scraper AND Collin CAD scraper for cities with dual sources.
Ensures maximum permit coverage by combining both data sources.

Usage:
    python scripts/scrape_dual_source.py frisco 1000
    python scripts/scrape_dual_source.py --all 500
    python scripts/scrape_dual_source.py --list
"""

import argparse
import subprocess
import sys
from pathlib import Path

SCRAPERS_DIR = Path(__file__).parent.parent / "scrapers"

# Cities with dual sources: city portal + Collin CAD
DUAL_SOURCE_CITIES = {
    'frisco': {
        'city_scraper': 'etrakit.py',
        'city_args': ['frisco'],
        'cad_city': 'frisco',
    },
    'plano': {
        'city_scraper': 'etrakit_auth.py',
        'city_args': ['plano'],
        'cad_city': 'plano',
    },
    'allen': {
        'city_scraper': 'citizen_self_service.py',
        'city_args': ['allen'],
        'cad_city': 'allen',
    },
    'mckinney': {
        'city_scraper': 'citizen_self_service.py',
        'city_args': ['mckinney'],
        'cad_city': 'mckinney',
    },
    'prosper': {
        'city_scraper': 'etrakit.py',
        'city_args': ['prosper'],
        'cad_city': 'prosper',
    },
    'celina': {
        'city_scraper': 'mygov_multi.py',
        'city_args': ['celina'],
        'cad_city': 'celina',
    },
}

# Cities with Collin CAD only (no city portal scraper)
CAD_ONLY_CITIES = [
    'princeton', 'wylie', 'anna', 'melissa', 'murphy',
    'lucas', 'lavon', 'farmersville', 'fairview', 'parker',
    'richardson', 'sachse',
]


def run_city_scraper(city: str, limit: int) -> bool:
    """Run the city-specific portal scraper."""
    config = DUAL_SOURCE_CITIES.get(city)
    if not config:
        print(f"  [SKIP] No city portal scraper for {city}")
        return False

    scraper = SCRAPERS_DIR / config['city_scraper']
    if not scraper.exists():
        print(f"  [ERROR] Scraper not found: {scraper}")
        return False

    args = ['python3', str(scraper)] + config['city_args'] + [str(limit)]

    print(f"  [CITY] Running {config['city_scraper']} {city} {limit}...")
    result = subprocess.run(args, capture_output=False)
    return result.returncode == 0


def run_cad_scraper(city: str, limit: int, days: int = 90) -> bool:
    """Run the Collin CAD Socrata scraper."""
    scraper = SCRAPERS_DIR / 'collin_cad_socrata.py'
    if not scraper.exists():
        print(f"  [ERROR] CAD scraper not found: {scraper}")
        return False

    args = ['python3', str(scraper), '--city', city, '--limit', str(limit), '--days', str(days)]

    print(f"  [CAD] Running collin_cad_socrata.py --city {city} --limit {limit} --days {days}...")
    result = subprocess.run(args, capture_output=False)
    return result.returncode == 0


def scrape_city(city: str, limit: int) -> dict:
    """Scrape a city from all available sources. Returns success status."""
    print(f"\n{'='*60}")
    print(f"SCRAPING: {city.upper()}")
    print(f"{'='*60}")

    city_lower = city.lower()
    results = {'city': None, 'cad': None}

    # Run city portal scraper if available
    if city_lower in DUAL_SOURCE_CITIES:
        results['city'] = run_city_scraper(city_lower, limit)
        if results['city'] is False:
            print(f"  [ERROR] City portal scraper failed")

    # Run Collin CAD scraper
    cad_city = DUAL_SOURCE_CITIES.get(city_lower, {}).get('cad_city', city_lower)
    results['cad'] = run_cad_scraper(cad_city, limit, days=90)
    if results['cad'] is False:
        print(f"  [ERROR] CAD scraper failed")

    print(f"  [DONE] {city} complete")
    return results


def main():
    parser = argparse.ArgumentParser(description='Dual-source scraping for Collin County cities')
    parser.add_argument('city', nargs='?', help='City to scrape')
    parser.add_argument('limit', nargs='?', type=int, default=500, help='Permit limit per source')
    parser.add_argument('--all', action='store_true', help='Scrape all dual-source cities')
    parser.add_argument('--list', action='store_true', help='List available cities')
    parser.add_argument('--cad-only', action='store_true', help='Also scrape CAD-only cities')
    args = parser.parse_args()

    if args.list:
        print("Dual-source cities (city portal + CAD):")
        for city in sorted(DUAL_SOURCE_CITIES.keys()):
            print(f"  {city}")
        print("\nCAD-only cities:")
        for city in sorted(CAD_ONLY_CITIES):
            print(f"  {city}")
        return

    failures = []

    if args.all:
        for city in DUAL_SOURCE_CITIES:
            results = scrape_city(city, args.limit)
            if results['cad'] is False:
                failures.append(city)
        if args.cad_only:
            for city in CAD_ONLY_CITIES:
                results = scrape_city(city, args.limit)
                if results['cad'] is False:
                    failures.append(city)
    elif args.city:
        results = scrape_city(args.city, args.limit)
        if results['cad'] is False:
            failures.append(args.city)
    else:
        parser.print_help()
        return

    if failures:
        print(f"\n[WARNING] Failed cities: {', '.join(failures)}")
        sys.exit(1)


if __name__ == '__main__':
    main()
