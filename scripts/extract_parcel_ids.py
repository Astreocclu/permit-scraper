#!/usr/bin/env python3
"""
Extract and format parcel IDs from CAD parcel data.

For Denton County / Tyler eSuite:
- Prefix residential parcels with "R" (e.g., R00000123456)

Usage:
    python3 scripts/extract_parcel_ids.py data/parcels/lewisville_denton_parcels.json
    python3 scripts/extract_parcel_ids.py data/parcels/lewisville_denton_parcels.json --output parcel_ids.txt
    python3 scripts/extract_parcel_ids.py data/parcels/lewisville_denton_parcels.json --limit 100
"""

import argparse
import json
from pathlib import Path


def format_denton_parcel_id(prop_id) -> str:
    """
    Format Denton County parcel ID for Tyler eSuite.
    Residential parcels need "R" prefix.
    """
    if not prop_id:
        return ''

    prop_id = str(prop_id).strip()

    # If already has R prefix, return as-is
    if prop_id.upper().startswith('R'):
        return prop_id.upper()

    # Add R prefix for residential
    return f"R{prop_id}"


def extract_parcel_ids(input_file: Path, county: str = 'denton') -> list[str]:
    """Extract formatted parcel IDs from parcel JSON file."""
    data = json.loads(input_file.read_text())
    parcels = data.get('parcels', [])

    parcel_ids = []
    for parcel in parcels:
        if county == 'denton':
            prop_id = parcel.get('prop_id', '')
            formatted = format_denton_parcel_id(prop_id)
            if formatted:
                parcel_ids.append(formatted)
        elif county == 'tarrant':
            account = parcel.get('Account_Nu', '')
            if account:
                parcel_ids.append(str(account))
        elif county == 'dallas':
            parcel_id = parcel.get('PARCELID', '')
            if parcel_id:
                parcel_ids.append(str(parcel_id))

    return parcel_ids


def main():
    parser = argparse.ArgumentParser(
        description='Extract parcel IDs from CAD data',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python3 scripts/extract_parcel_ids.py data/parcels/lewisville_denton_parcels.json
    python3 scripts/extract_parcel_ids.py data/parcels/lewisville_denton_parcels.json --limit 100
    python3 scripts/extract_parcel_ids.py data/parcels/lewisville_denton_parcels.json -o ids.txt
        """
    )
    parser.add_argument('input_file', type=Path, help='Input parcel JSON file')
    parser.add_argument('--output', '-o', type=Path, help='Output file (default: stdout)')
    parser.add_argument('--limit', type=int, help='Limit number of IDs')
    parser.add_argument('--county', default='denton',
                        choices=['denton', 'tarrant', 'dallas'],
                        help='County format (default: denton)')

    args = parser.parse_args()

    if not args.input_file.exists():
        print(f"ERROR: File not found: {args.input_file}")
        return

    parcel_ids = extract_parcel_ids(args.input_file, args.county)

    if args.limit:
        parcel_ids = parcel_ids[:args.limit]

    print(f"Extracted {len(parcel_ids):,} parcel IDs")

    if args.output:
        args.output.write_text('\n'.join(parcel_ids))
        print(f"Saved to {args.output}")
    else:
        print("\nSample IDs:")
        for pid in parcel_ids[:10]:
            print(f"  {pid}")
        if len(parcel_ids) > 10:
            print(f"  ... and {len(parcel_ids) - 10:,} more")


if __name__ == '__main__':
    main()
