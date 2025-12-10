#!/usr/bin/env python3
"""
Load permits from JSON files into SQLite database.

This script bridges the gap between scrapers (which output JSON) and
the enrichment pipeline (which reads from SQLite).

Usage:
    python3 scripts/load_permits.py                    # Load all JSON files
    python3 scripts/load_permits.py --file fort_worth_raw.json  # Load specific file
    python3 scripts/load_permits.py --db path/to/db    # Custom database
"""

import argparse
import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = "data/permits.db"


def setup_database(conn: sqlite3.Connection):
    """Create the permits table if it doesn't exist."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS permits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            permit_id TEXT,
            city TEXT,
            property_address TEXT,
            property_address_normalized TEXT,
            city_name TEXT,
            zip_code TEXT,
            permit_type TEXT,
            description TEXT,
            status TEXT,
            issued_date TEXT,
            applicant_name TEXT,
            contractor_name TEXT,
            estimated_value REAL,
            owner_name TEXT,
            scraped_at TEXT,
            source_file TEXT,
            portal_type TEXT,
            UNIQUE(permit_id, city)
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_permits_address ON permits(property_address)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_permits_city ON permits(city)")
    conn.commit()


def normalize_address(address: str) -> Optional[str]:
    """Normalize address for matching."""
    if not address:
        return None
    import re
    addr = address.upper().strip()
    # Remove extra whitespace
    addr = re.sub(r'\s+', ' ', addr)
    return addr


def extract_city_from_source(source: str) -> str:
    """Extract city name from source identifier."""
    # Handle formats like "fort_worth", "Fort Worth", etc.
    city = source.replace('_', ' ').title()
    return city


def load_json_file(filepath: Path, conn: sqlite3.Connection) -> tuple[int, int]:
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
    portal_type = data.get('portal_type', 'unknown')
    scraped_at = data.get('scraped_at', datetime.now().isoformat())
    permits = data.get('permits', [])

    if not permits:
        logger.warning(f"{filepath.name}: No permits found")
        return 0, 0

    city = source.replace('_', ' ').lower()
    city_name = extract_city_from_source(source)

    loaded = 0
    skipped = 0

    for permit in permits:
        permit_id = permit.get('permit_id', permit.get('id', ''))
        address = permit.get('address', permit.get('property_address', ''))

        if not permit_id:
            skipped += 1
            continue

        try:
            conn.execute("""
                INSERT OR REPLACE INTO permits (
                    permit_id, city, property_address, property_address_normalized,
                    city_name, zip_code, permit_type, description, status,
                    issued_date, applicant_name, contractor_name, estimated_value,
                    owner_name, scraped_at, source_file, portal_type
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                permit_id,
                city,
                address,
                normalize_address(address),
                city_name,
                permit.get('zip_code'),
                permit.get('type', permit.get('permit_type')),
                permit.get('description'),
                permit.get('status'),
                permit.get('date', permit.get('issued_date')),
                permit.get('applicant', permit.get('applicant_name')),
                permit.get('contractor', permit.get('contractor_name')),
                permit.get('value', permit.get('estimated_value')),
                permit.get('owner', permit.get('owner_name')),
                scraped_at,
                filepath.name,
                portal_type
            ))
            loaded += 1
        except sqlite3.Error as e:
            logger.warning(f"Failed to insert permit {permit_id}: {e}")
            skipped += 1

    conn.commit()
    return loaded, skipped


def main():
    parser = argparse.ArgumentParser(
        description='Load permits from JSON files into SQLite database'
    )
    parser.add_argument('--db', default=DEFAULT_DB_PATH, help='Path to SQLite database')
    parser.add_argument('--file', help='Specific JSON file to load (default: all *_raw.json)')
    parser.add_argument('--dir', default='.', help='Directory to search for JSON files')
    args = parser.parse_args()

    # Setup database
    db_path = Path(args.db)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    setup_database(conn)

    # Find JSON files
    search_dir = Path(args.dir)
    if args.file:
        json_files = [search_dir / args.file]
    else:
        json_files = list(search_dir.glob('*_raw.json'))

    if not json_files:
        logger.warning("No JSON files found to load")
        return

    print(f"=== LOADING PERMITS INTO DATABASE ===")
    print(f"Database: {db_path}")
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
    cursor = conn.execute("SELECT COUNT(*) FROM permits")
    total_in_db = cursor.fetchone()[0]
    print(f"Total in database: {total_in_db}")

    conn.close()


if __name__ == "__main__":
    main()
