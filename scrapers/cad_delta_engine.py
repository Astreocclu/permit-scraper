#!/usr/bin/env python3
# scrapers/cad_delta_engine.py
"""
CAD DELTA ENGINE
Processes Central Appraisal District tax rolls to identify new construction.

Lightweight approach:
1. Stream process CSV in chunks (no full memory load)
2. Filter for new construction (year_built, flags, value changes)
3. Output only matching records as permits
4. Track file hash for change detection

Supports: DCAD (Dallas), TAD (Tarrant), Denton CAD

Usage:
    python3 scrapers/cad_delta_engine.py dcad --file data.csv
    python3 scrapers/cad_delta_engine.py tad --file data.csv
    python3 scrapers/cad_delta_engine.py --list
"""

import argparse
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Generator, List, Optional

import pandas as pd
import yaml

from dotenv import load_dotenv
load_dotenv()

OUTPUT_DIR = Path(__file__).parent.parent / "data" / "raw"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

CONFIG_DIR = Path(__file__).parent / "cad_configs"
CACHE_DIR = Path(__file__).parent.parent / ".scraper_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class CADConfig:
    """Configuration for a Central Appraisal District."""
    name: str
    display_name: str
    county: str
    download_url: Optional[str]
    format: str
    columns: Dict[str, str]
    filters: Dict
    chunk_size: int = 100000
    encoding: str = 'utf-8'


def load_config(cad_name: str) -> CADConfig:
    """Load CAD configuration from YAML file."""
    config_file = CONFIG_DIR / f"{cad_name}.yaml"
    if not config_file.exists():
        raise ValueError(f"No config for '{cad_name}'. Available: {list_available_cads()}")

    with open(config_file) as f:
        data = yaml.safe_load(f)

    return CADConfig(
        name=data['name'],
        display_name=data['display_name'],
        county=data['county'],
        download_url=data.get('download', {}).get('url'),
        format=data.get('download', {}).get('format', 'csv'),
        columns=data.get('columns', {}),
        filters=data.get('filters', {}),
        chunk_size=data.get('processing', {}).get('chunk_size', 100000),
        encoding=data.get('processing', {}).get('encoding', 'utf-8'),
    )


def list_available_cads() -> List[str]:
    """List available CAD configurations."""
    return [f.stem for f in CONFIG_DIR.glob('*.yaml')]


def get_file_hash(file_path: Path) -> str:
    """Calculate SHA256 hash of a file (streaming for large files)."""
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            sha256.update(chunk)
    return sha256.hexdigest()


def is_new_construction(record: dict, current_year: int, config: CADConfig = None) -> bool:
    """
    Determine if a record represents new construction.

    Logic:
    1. If NEW_CONSTRUCTION flag exists and is 'Y', return True (DCAD only)
    2. If year_built is current year or previous year, return True
    3. If improvement value increased from 0 to significant value, return True
    """
    # Check DCAD-specific flag
    new_const_flag = record.get('new_construction_flag')
    if new_const_flag and str(new_const_flag).upper() == 'Y':
        return True

    # Check year built
    year_built = record.get('year_built')
    if year_built:
        try:
            year = int(year_built)
            year_window = config.filters.get('year_built_window', 2) if config else 2
            if year >= current_year - year_window + 1:
                return True
        except (ValueError, TypeError):
            pass

    # Check improvement value increase
    improvement = record.get('improvement_value', 0)
    prior_improvement = record.get('prior_improvement_value', 0)

    try:
        current_val = float(improvement) if improvement else 0
        prior_val = float(prior_improvement) if prior_improvement else 0

        min_value = config.filters.get('min_improvement_value', 50000) if config else 50000
        if prior_val == 0 and current_val >= min_value:
            return True
    except (ValueError, TypeError):
        pass

    return False


def stream_csv_records(
    file_path: Path,
    config: CADConfig,
    current_year: int
) -> Generator[dict, None, None]:
    """
    Stream CSV records, filtering for new construction.

    Uses pandas chunked reading to keep memory low.
    """
    col_mapping = {v: k for k, v in config.columns.items()}

    try:
        for chunk in pd.read_csv(
            file_path,
            chunksize=config.chunk_size,
            encoding=config.encoding,
            low_memory=False,
            dtype=str
        ):
            chunk = chunk.rename(columns=col_mapping)

            for _, row in chunk.iterrows():
                record = row.to_dict()

                if 'property_type' in record and 'property_types' in config.filters:
                    if record['property_type'] not in config.filters['property_types']:
                        continue

                if 'sptb_code' in record and 'sptb_codes' in config.filters:
                    if record['sptb_code'] not in config.filters['sptb_codes']:
                        continue

                if is_new_construction(record, current_year, config):
                    yield record
    except pd.errors.ParserError as e:
        print(f"ERROR: CSV parsing failed: {e}")
        return
    except UnicodeDecodeError as e:
        print(f"ERROR: Encoding issue: {e}")
        return


def transform_to_permit(record: dict, config: CADConfig) -> dict:
    """Transform CAD record to standard permit format."""
    return {
        'permit_id': f"{config.name.upper()}-{record.get('account_number', '')}",
        'address': record.get('property_address', ''),
        'city': record.get('city', config.county),
        'zip': record.get('zip', ''),
        'type': 'New Construction (from CAD)',
        'date': None,
        'value': record.get('total_value') or record.get('improvement_value'),
        'owner_name': record.get('owner_name'),
        'year_built': record.get('year_built'),
        'cad_account_number': record.get('account_number'),
        'data_source': f"{config.name}_taxroll",
    }


def process_cad(cad_name: str, file_path: Path, dry_run: bool = False) -> dict:
    """Process a CAD tax roll file."""
    config = load_config(cad_name)
    current_year = datetime.now().year

    print(f'[1] Loading config for {config.display_name}...')
    print(f'    County: {config.county}')
    print(f'    Chunk size: {config.chunk_size:,}')

    print(f'[2] Checking file hash...')
    file_hash = get_file_hash(file_path)
    print(f'    Hash: {file_hash[:16]}...')

    print(f'[3] Processing records...')
    permits = []
    total_processed = 0

    for record in stream_csv_records(file_path, config, current_year):
        permit = transform_to_permit(record, config)
        permits.append(permit)
        total_processed += 1

        if total_processed % 1000 == 0:
            print(f'    Found {total_processed:,} new construction records...')

    print(f'    Total new construction: {len(permits):,}')

    cities = {}
    for p in permits:
        c = p['city'] or 'Unknown'
        cities[c] = cities.get(c, 0) + 1

    print(f'\n[4] By city (top 15):')
    for city, count in sorted(cities.items(), key=lambda x: -x[1])[:15]:
        print(f'    {city}: {count:,}')

    if dry_run:
        print('\n[DRY RUN] Not saving output')
        return {'status': 'dry_run', 'permits': len(permits)}

    output_file = OUTPUT_DIR / f"{cad_name}_taxroll_raw.json"

    output = {
        'source': f'{cad_name}_taxroll',
        'portal_type': 'CAD Tax Roll',
        'data_source': f'{cad_name}_taxroll',
        'scraped_at': datetime.now().isoformat(),
        'file_hash': file_hash,
        'total_processed': total_processed,
        'actual_count': len(permits),
        'permits': permits
    }

    output_file.write_text(json.dumps(output, indent=2))

    return {
        'status': 'success',
        'permits': len(permits),
        'output_file': str(output_file),
        'file_hash': file_hash
    }


def main() -> int:
    parser = argparse.ArgumentParser(description='Process CAD tax rolls for new construction')
    parser.add_argument('cad', nargs='?', help='CAD to process (dcad, tad, denton_cad)')
    parser.add_argument('--file', '-f', help='Local tax roll file to process')
    parser.add_argument('--list', '-l', action='store_true', help='List available CADs')
    parser.add_argument('--dry-run', action='store_true', help='Process without saving')
    args = parser.parse_args()

    if args.list:
        print("Available CAD configurations:")
        for cad in list_available_cads():
            config = load_config(cad)
            print(f"  {cad}: {config.display_name} ({config.county} County)")
        return 0

    if not args.cad:
        parser.print_help()
        return 1

    if not args.file:
        print(f"ERROR: --file required (download from CAD website)")
        config = load_config(args.cad)
        print(f"\nFor {args.cad.upper()}:")
        print(f"  Download from: {config.download_url or 'See CAD website'}")
        return 1

    file_path = Path(args.file)
    if not file_path.exists():
        print(f"ERROR: File not found: {file_path}")
        return 1

    print('=' * 60)
    print(f'CAD DELTA ENGINE: {args.cad.upper()}')
    print('=' * 60)
    print(f'Input: {file_path}')
    print(f'Time: {datetime.now().isoformat()}\n')

    result = process_cad(args.cad, file_path, dry_run=args.dry_run)

    print(f'\n' + '=' * 60)
    print('SUMMARY')
    print('=' * 60)
    print(f'Status: {result["status"]}')
    print(f'New construction permits: {result["permits"]:,}')
    if result.get('output_file'):
        print(f'Output: {result["output_file"]}')

    return 0


if __name__ == '__main__':
    exit(main())
