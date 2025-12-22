#!/usr/bin/env python3
"""
THE COLONY ADDRESS ENRICHMENT
Enriches The Colony permits with full addresses from Denton CAD.

The Colony's eTRAKiT portal only provides street names (e.g., "BAKER DR").
This script queries Denton CAD to find matching properties and assigns
the best-matching full address.

Usage:
    python3 scripts/enrich_colony_addresses.py                # Process raw JSON
    python3 scripts/enrich_colony_addresses.py --dry-run      # Preview only
    python3 scripts/enrich_colony_addresses.py --reload       # Reload to DB after
"""

import argparse
import json
import logging
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
load_dotenv()

# Add parent to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.enrich_cad import query_denton_by_street

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# Use absolute paths
BASE_DIR = Path(__file__).parent.parent.resolve()
DATA_DIR = BASE_DIR / "data" / "raw"


def extract_street_from_permit(permit: dict) -> Optional[str]:
    """Extract street name from permit raw_cells."""
    raw = permit.get('raw_cells', [])
    if len(raw) >= 2:
        street = raw[1]
        # Skip contractor codes
        if street and not street.startswith(('DKB', 'JJ_', 'KB_')):
            return street.strip().upper()
    return None


def build_address_lookup(street_names: set) -> dict:
    """
    Query Denton CAD for all unique street names.
    Returns {street_name: [list of full addresses]}
    """
    lookup = {}

    for street in sorted(street_names):
        print(f"  Querying Denton CAD for: {street}")
        results = query_denton_by_street(street, city_filter="THE COLONY", limit=50)

        addresses = []
        for r in results:
            addr = r.get('situs_addr', '').strip()
            if addr and addr[0].isdigit():
                addresses.append(addr)

        if addresses:
            lookup[street] = addresses
            print(f"    Found {len(addresses)} addresses")
        else:
            print(f"    No addresses found")

    return lookup


def enrich_permit(permit: dict, lookup: dict = None) -> dict:
    """
    Enrich a single permit with full address from CAD.

    Args:
        permit: Permit dict with raw_cells
        lookup: Pre-built address lookup (optional, will query if not provided)

    Returns:
        Permit dict with address filled in
    """
    # Already has address
    if permit.get('address'):
        return permit

    street = extract_street_from_permit(permit)
    if not street:
        return permit

    # Build lookup if not provided
    if lookup is None:
        results = query_denton_by_street(street, city_filter="THE COLONY", limit=10)
        addresses = [r.get('situs_addr', '').strip() for r in results
                    if r.get('situs_addr', '').strip() and r['situs_addr'][0].isdigit()]
        lookup = {street: addresses} if addresses else {}

    # Find matching addresses
    # Strip suffix for matching
    street_core = street.replace(' DR', '').replace(' ST', '').replace(' LN', '').replace(' AVE', '').strip()

    for lookup_street, addresses in lookup.items():
        lookup_core = lookup_street.replace(' DR', '').replace(' ST', '').replace(' LN', '').replace(' AVE', '').strip()
        if street_core in lookup_core or lookup_core in street_core:
            if addresses:
                if len(addresses) == 1:
                    # Exact match - safe to assign
                    permit['address'] = addresses[0]
                    permit['address_source'] = 'DENTON_CAD_EXACT'
                else:
                    # Multiple candidates - store for review, don't guess
                    permit['address'] = ''  # Leave blank - can't determine exact address
                    permit['street_name'] = street  # Store what we know
                    permit['address_candidates'] = addresses[:10]  # Store top candidates (list)
                    permit['address_source'] = 'DENTON_CAD_AMBIGUOUS'
                break

    return permit


def enrich_colony_permits(dry_run: bool = False) -> dict:
    """
    Enrich all The Colony permits from raw JSON.

    Returns:
        Summary stats
    """
    raw_file = DATA_DIR / 'the_colony_raw.json'
    if not raw_file.exists():
        logger.error(f"File not found: {raw_file}")
        return {'error': 'file not found'}

    with open(raw_file) as f:
        data = json.load(f)

    permits = data.get('permits', data) if isinstance(data, dict) else data
    print(f"Loaded {len(permits)} permits from The Colony")

    # Extract unique street names
    street_names = set()
    for p in permits:
        street = extract_street_from_permit(p)
        if street:
            street_names.add(street)

    print(f"Found {len(street_names)} unique streets to lookup")

    # Build address lookup
    print("\n[1/3] Querying Denton CAD...")
    lookup = build_address_lookup(street_names)

    print(f"\n[2/3] Enriching {len(permits)} permits...")
    enriched_count = 0
    ambiguous_count = 0
    for permit in permits:
        original_addr = permit.get('address')
        permit = enrich_permit(permit, lookup)
        if permit.get('address') and not original_addr:
            enriched_count += 1
            print(f"  {permit['permit_id']}: {permit['address']}")
        if permit.get('address_source') == 'DENTON_CAD_AMBIGUOUS':
            ambiguous_count += 1

    # Save enriched data
    output_file = DATA_DIR / 'the_colony_enriched.json'

    if not dry_run:
        print(f"\n[3/3] Saving to {output_file}...")
        output = {
            'source': 'the_colony',
            'enriched_at': datetime.now().isoformat(),
            'enrichment_method': 'DENTON_CAD',
            'permits': permits,
        }
        with open(output_file, 'w') as f:
            json.dump(output, f, indent=2)
    else:
        print(f"\n[3/3] DRY RUN - not saving")

    return {
        'total': len(permits),
        'enriched': enriched_count,
        'ambiguous': ambiguous_count,
        'streets_found': len([s for s in street_names if s in lookup]),
        'streets_missing': len([s for s in street_names if s not in lookup]),
    }


def main():
    parser = argparse.ArgumentParser(description='Enrich The Colony permits with Denton CAD addresses')
    parser.add_argument('--dry-run', action='store_true', help='Preview without saving')
    parser.add_argument('--reload', action='store_true', help='Reload enriched data to DB after')
    args = parser.parse_args()

    print("=" * 60)
    print("THE COLONY ADDRESS ENRICHMENT")
    print("=" * 60)
    print()

    result = enrich_colony_permits(dry_run=args.dry_run)

    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total permits: {result.get('total', 0)}")
    print(f"Enriched: {result.get('enriched', 0)}")
    print(f"Ambiguous (multiple candidates): {result.get('ambiguous', 0)}")
    print(f"Streets found in CAD: {result.get('streets_found', 0)}")
    print(f"Streets not found: {result.get('streets_missing', 0)}")

    if args.reload and not args.dry_run:
        print("\nReloading to database...")
        output_file = DATA_DIR / 'the_colony_enriched.json'
        try:
            result = subprocess.run(
                ['python3', str(BASE_DIR / 'scripts' / 'load_permits.py'),
                 '--file', str(output_file)],
                check=True,
                capture_output=True,
                text=True,
                cwd=str(BASE_DIR)
            )
            print(result.stdout)
            if result.stderr:
                print(result.stderr)
        except subprocess.CalledProcessError as e:
            logger.error(f"Database reload failed with exit code {e.returncode}")
            if e.stderr:
                logger.error(e.stderr)


if __name__ == '__main__':
    main()
