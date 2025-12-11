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

    # Extract metadata
    source = data.get('source', filepath.stem.replace('_raw', ''))
    scraped_at = data.get('scraped_at', datetime.now().isoformat())
    permits = data.get('permits', [])

    if not permits:
        logger.warning(f"{filepath.name}: No permits found")
        return 0, 0

    city = source.replace('_', ' ').lower()

    # Transform to PostgreSQL rows
    pg_rows = []
    skipped = 0

    for permit in permits:
        permit_id = permit.get('permit_id', permit.get('id', ''))
        address = permit.get('address', permit.get('property_address', ''))

        if not permit_id:
            skipped += 1
            continue

        # Handle issued_date
        issued_date = permit.get('date', permit.get('issued_date'))
        issued = None
        if issued_date:
            try:
                issued = datetime.strptime(issued_date[:10], '%Y-%m-%d').date()
            except (ValueError, TypeError):
                pass

        # Handle scraped_at
        scraped = datetime.now()
        if scraped_at:
            try:
                scraped = datetime.fromisoformat(scraped_at.replace('Z', '+00:00'))
            except (ValueError, TypeError):
                pass

        pg_rows.append((
            permit_id,
            city,
            address,
            permit.get('type', permit.get('permit_type')),
            permit.get('description'),
            permit.get('status'),
            issued,
            permit.get('applicant', permit.get('applicant_name')),
            permit.get('contractor', permit.get('contractor_name')),
            permit.get('value', permit.get('estimated_value')),
            scraped,
            None  # lead_type
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
                estimated_value, scraped_at, lead_type
            ) VALUES %s
            ON CONFLICT ON CONSTRAINT clients_permit_city_permit_id_33861e17_uniq DO UPDATE SET
                property_address = EXCLUDED.property_address,
                description = EXCLUDED.description,
                status = EXCLUDED.status,
                estimated_value = EXCLUDED.estimated_value
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
