#!/usr/bin/env python3
"""
Load permits from JSON files into PostgreSQL database.

This script bridges the gap between scrapers (which output JSON) and
the enrichment pipeline (which reads from PostgreSQL).

Usage:
    python3 scripts/load_permits.py                    # Load all JSON files
    python3 scripts/load_permits.py --file fort_worth_raw.json  # Load specific file
"""

import argparse
import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
load_dotenv()

import psycopg2
from psycopg2.extras import execute_values

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


def get_connection():
    """Get PostgreSQL connection from DATABASE_URL."""
    url = os.environ.get('DATABASE_URL')
    if not url:
        raise ValueError("DATABASE_URL environment variable not set")
    return psycopg2.connect(url)


def normalize_address(address: str) -> Optional[str]:
    """Normalize address for matching."""
    if not address:
        return None
    addr = address.upper().strip()
    # Remove extra whitespace
    addr = re.sub(r'\s+', ' ', addr)
    return addr


def extract_city_from_source(source: str) -> str:
    """Extract city name from source identifier."""
    # Handle formats like "fort_worth", "Fort Worth", etc.
    city = source.replace('_', ' ').title()
    return city


def load_json_file(filepath: Path, conn) -> tuple[int, int]:
    """
    Load permits from a JSON file into the database.
    Returns (loaded_count, skipped_count).
    """
    try:
        with open(filepath) as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse {filepath}: {e}")
        return 0, 0

    # Handle both dict format (standard) and list format (some mygov scrapers)
    if isinstance(data, list):
        # List format: permits directly in the file
        permits = data
        source = filepath.stem.replace('_raw', '').replace('_mygov', '').replace('_opengov', '')
        scraped_at = datetime.now().isoformat()
    else:
        # Dict format: standard scraper output
        source = data.get('source', filepath.stem.replace('_raw', ''))
        scraped_at = data.get('scraped_at', datetime.now().isoformat())
        permits = data.get('permits', [])

    if not permits:
        logger.warning(f"{filepath.name}: No permits found")
        return 0, 0

    default_city = source.replace('_', ' ').lower()

    # Transform to PostgreSQL rows
    pg_rows = []
    skipped = 0

    for permit in permits:
        permit_id = permit.get('permit_id', permit.get('id', permit.get('permit_number', '')))
        address = permit.get('address', permit.get('property_address', ''))
        # Use permit's own city if available, otherwise fall back to source-derived city
        city = permit.get('city', default_city)
        if city:
            city = city.lower().strip()

        if not permit_id or not address:
            skipped += 1
            continue

        # Handle issued_date - try multiple formats
        issued_date = permit.get('date', permit.get('issued_date'))
        issued = None
        if issued_date:
            date_formats = [
                '%m/%d/%Y',   # 12/12/2025 (most common from scrapers)
                '%m/%d/%y',   # 12/12/25
                '%Y-%m-%d',   # 2025-12-12 (ISO)
                '%Y/%m/%d',   # 2025/12/12
                '%d-%m-%Y',   # 12-12-2025
            ]
            for fmt in date_formats:
                try:
                    issued = datetime.strptime(issued_date.strip()[:10], fmt).date()
                    break
                except (ValueError, TypeError):
                    continue

        # Handle scraped_at
        scraped = datetime.now()
        if scraped_at:
            try:
                scraped = datetime.fromisoformat(scraped_at.replace('Z', '+00:00'))
            except (ValueError, TypeError):
                pass

        # Parse year_built (convert to int)
        year_built = permit.get('year_built')
        if year_built:
            try:
                year_built = int(year_built)
            except (ValueError, TypeError):
                year_built = None

        # Parse property_value (convert to float)
        property_value = permit.get('property_value') or permit.get('value')
        if property_value:
            try:
                property_value = float(str(property_value).replace(',', '').replace('$', ''))
            except (ValueError, TypeError):
                property_value = None

        pg_rows.append((
            permit_id,
            city,
            address,
            permit.get('type', permit.get('permit_type')),
            permit.get('description'),
            permit.get('status'),
            issued,
            permit.get('applicant', permit.get('applicant_name', permit.get('owner_name'))),
            permit.get('contractor', permit.get('contractor_name')),
            permit.get('value', permit.get('estimated_value')) or None,  # Empty string -> None
            scraped,
            None,  # lead_type
            # NEW COLUMNS
            permit.get('data_source') or source,  # data_source - use source as fallback
            permit.get('cad_account_number'),     # cad_account_number
            year_built,                            # year_built (converted to int)
            property_value,                        # property_value (converted to float)
        ))

    if pg_rows:
        # Deduplicate by (city, permit_id) - keep last occurrence
        seen = {}
        for row in pg_rows:
            key = (row[1], row[0])  # (city, permit_id)
            seen[key] = row
        pg_rows = list(seen.values())

        insert_sql = """
            INSERT INTO leads_permit (
                permit_id, city, property_address, permit_type, description,
                status, issued_date, applicant_name, contractor_name,
                estimated_value, scraped_at, lead_type,
                data_source, cad_account_number, year_built, property_value
            ) VALUES %s
            ON CONFLICT ON CONSTRAINT clients_permit_city_permit_id_33861e17_uniq DO UPDATE SET
                property_address = COALESCE(EXCLUDED.property_address, leads_permit.property_address),
                permit_type = COALESCE(EXCLUDED.permit_type, leads_permit.permit_type),
                description = COALESCE(EXCLUDED.description, leads_permit.description),
                status = COALESCE(EXCLUDED.status, leads_permit.status),
                issued_date = COALESCE(EXCLUDED.issued_date, leads_permit.issued_date),
                estimated_value = COALESCE(EXCLUDED.estimated_value, leads_permit.estimated_value),
                applicant_name = COALESCE(EXCLUDED.applicant_name, leads_permit.applicant_name),
                contractor_name = COALESCE(EXCLUDED.contractor_name, leads_permit.contractor_name),
                scraped_at = EXCLUDED.scraped_at,
                lead_type = COALESCE(EXCLUDED.lead_type, leads_permit.lead_type),
                data_source = COALESCE(EXCLUDED.data_source, leads_permit.data_source),
                cad_account_number = COALESCE(EXCLUDED.cad_account_number, leads_permit.cad_account_number),
                year_built = COALESCE(EXCLUDED.year_built, leads_permit.year_built),
                property_value = COALESCE(EXCLUDED.property_value, leads_permit.property_value)
        """
        with conn.cursor() as cur:
            execute_values(cur, insert_sql, pg_rows, page_size=500)
        conn.commit()

    return len(pg_rows), skipped


def main():
    parser = argparse.ArgumentParser(
        description='Load permits from JSON files into PostgreSQL database'
    )
    parser.add_argument('--file', help='Specific JSON file to load (default: all *_raw.json)')
    parser.add_argument('--dir', default='.', help='Directory to search for JSON files')
    args = parser.parse_args()

    # Connect to database
    try:
        conn = get_connection()
    except ValueError as e:
        print(f"ERROR: {e}")
        return 1

    # Find JSON files
    search_dir = Path(args.dir)
    if args.file:
        json_files = [search_dir / args.file]
    else:
        json_files = list(search_dir.glob('*_raw.json'))

    if not json_files:
        logger.warning("No JSON files found to load")
        return 0

    print(f"=== LOADING PERMITS INTO DATABASE ===")
    print(f"Database: PostgreSQL (from DATABASE_URL)")
    print(f"Files: {len(json_files)}\n")

    total_loaded = 0
    total_skipped = 0

    for filepath in sorted(json_files):
        if not filepath.exists():
            logger.warning(f"File not found: {filepath}")
            continue

        loaded, skipped = load_json_file(filepath, conn)
        total_loaded += loaded
        total_skipped += skipped

        status = f"{loaded} loaded" + (f", {skipped} skipped" if skipped else "")
        print(f"  {filepath.name}: {status}")

    print(f"\n{'='*40}")
    print(f"Total loaded: {total_loaded}")
    print(f"Total skipped: {total_skipped}")

    # Show current database stats
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM leads_permit")
        total_in_db = cur.fetchone()[0]
    print(f"Total in database: {total_in_db}")

    conn.close()
    return 0


if __name__ == "__main__":
    exit(main())
