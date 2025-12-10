#!/usr/bin/env python3
"""
One-time migration script to import permits and properties from contractor-auditor.

This migrates data from the Django-based contractor-auditor system to the
standalone permit-scraper system.

Usage:
    python3 scripts/migrate_from_contractor_auditor.py
    python3 scripts/migrate_from_contractor_auditor.py --source ../contractor-auditor/db.sqlite3
    python3 scripts/migrate_from_contractor_auditor.py --dry-run
"""

import argparse
import sqlite3
from datetime import datetime
from pathlib import Path

DEFAULT_SOURCE = "../contractor-auditor/db.sqlite3"
DEFAULT_TARGET = "data/permits.db"


def setup_target_database(conn: sqlite3.Connection):
    """Create tables in target database if they don't exist."""

    # Permits table
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
            lead_type TEXT,
            lead_subtypes TEXT,
            categorization_confidence REAL,
            UNIQUE(permit_id, city)
        )
    """)

    # Properties table (for CAD enrichment)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS properties (
            property_address TEXT PRIMARY KEY,
            property_address_normalized TEXT,
            cad_account_id TEXT,
            county TEXT,
            owner_name TEXT,
            mailing_address TEXT,
            mailing_address_normalized TEXT,
            market_value REAL,
            land_value REAL,
            improvement_value REAL,
            year_built INTEGER,
            square_feet INTEGER,
            lot_size REAL,
            property_type TEXT,
            neighborhood_code TEXT,
            neighborhood_median REAL,
            is_absentee INTEGER,
            homestead_exempt INTEGER,
            enrichment_status TEXT DEFAULT 'pending',
            enriched_at TEXT,
            raw_data TEXT
        )
    """)

    conn.execute("CREATE INDEX IF NOT EXISTS idx_permits_address ON permits(property_address)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_permits_city ON permits(city)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_properties_status ON properties(enrichment_status)")
    conn.commit()


def migrate_permits(source_conn: sqlite3.Connection, target_conn: sqlite3.Connection, dry_run: bool = False) -> int:
    """Migrate permits from leads_permit table."""

    cursor = source_conn.execute("""
        SELECT
            permit_id, city, property_address, property_address_normalized,
            city_name, zip_code, permit_type, description, status,
            issued_date, applicant_name, contractor_name, estimated_value,
            scraped_at, lead_type, lead_subtypes, categorization_confidence
        FROM leads_permit
    """)

    rows = cursor.fetchall()
    count = len(rows)

    if dry_run:
        print(f"  Would migrate {count} permits")
        return count

    for row in rows:
        try:
            target_conn.execute("""
                INSERT OR REPLACE INTO permits (
                    permit_id, city, property_address, property_address_normalized,
                    city_name, zip_code, permit_type, description, status,
                    issued_date, applicant_name, contractor_name, estimated_value,
                    scraped_at, lead_type, lead_subtypes, categorization_confidence,
                    source_file
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (*row, 'migrated_from_contractor_auditor'))
        except sqlite3.Error as e:
            print(f"  Warning: Failed to insert permit {row[0]}: {e}")

    target_conn.commit()
    return count


def migrate_properties(source_conn: sqlite3.Connection, target_conn: sqlite3.Connection, dry_run: bool = False) -> int:
    """Migrate properties from leads_property table."""

    cursor = source_conn.execute("""
        SELECT
            property_address, property_address_normalized, cad_account_id,
            county, owner_name, mailing_address, mailing_address_normalized,
            market_value, land_value, improvement_value, year_built,
            square_feet, lot_size, property_type, neighborhood_code,
            neighborhood_median, is_absentee, homestead_exempt,
            enrichment_status, enriched_at
        FROM leads_property
    """)

    rows = cursor.fetchall()
    count = len(rows)

    if dry_run:
        print(f"  Would migrate {count} properties")
        return count

    for row in rows:
        try:
            target_conn.execute("""
                INSERT OR REPLACE INTO properties (
                    property_address, property_address_normalized, cad_account_id,
                    county, owner_name, mailing_address, mailing_address_normalized,
                    market_value, land_value, improvement_value, year_built,
                    square_feet, lot_size, property_type, neighborhood_code,
                    neighborhood_median, is_absentee, homestead_exempt,
                    enrichment_status, enriched_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, row)
        except sqlite3.Error as e:
            print(f"  Warning: Failed to insert property {row[0][:50]}...: {e}")

    target_conn.commit()
    return count


def main():
    parser = argparse.ArgumentParser(
        description='Migrate permits and properties from contractor-auditor'
    )
    parser.add_argument('--source', default=DEFAULT_SOURCE,
                        help=f'Source database (default: {DEFAULT_SOURCE})')
    parser.add_argument('--target', default=DEFAULT_TARGET,
                        help=f'Target database (default: {DEFAULT_TARGET})')
    parser.add_argument('--dry-run', action='store_true',
                        help='Show what would be migrated without making changes')
    args = parser.parse_args()

    source_path = Path(args.source)
    target_path = Path(args.target)

    if not source_path.exists():
        print(f"ERROR: Source database not found: {source_path}")
        print(f"Make sure contractor-auditor is at the expected location.")
        return 1

    # Ensure target directory exists
    target_path.parent.mkdir(parents=True, exist_ok=True)

    print("=== MIGRATION: contractor-auditor → permit-scraper ===")
    print(f"Source: {source_path}")
    print(f"Target: {target_path}")
    if args.dry_run:
        print("Mode: DRY RUN (no changes will be made)\n")
    else:
        print()

    # Connect to databases
    source_conn = sqlite3.connect(str(source_path))
    source_conn.row_factory = sqlite3.Row

    target_conn = sqlite3.connect(str(target_path))

    if not args.dry_run:
        setup_target_database(target_conn)

    # Migrate permits
    print("Migrating permits...")
    permit_count = migrate_permits(source_conn, target_conn, args.dry_run)
    print(f"  ✓ {permit_count} permits")

    # Migrate properties
    print("Migrating properties...")
    property_count = migrate_properties(source_conn, target_conn, args.dry_run)
    print(f"  ✓ {property_count} properties")

    # Summary
    print(f"\n{'='*50}")
    if args.dry_run:
        print("DRY RUN COMPLETE - No changes made")
        print(f"Would migrate: {permit_count} permits, {property_count} properties")
    else:
        print("MIGRATION COMPLETE")
        print(f"Migrated: {permit_count} permits, {property_count} properties")

        # Show target database stats
        cursor = target_conn.execute("SELECT COUNT(*) FROM permits")
        total_permits = cursor.fetchone()[0]
        cursor = target_conn.execute("SELECT COUNT(*) FROM properties WHERE enrichment_status = 'success'")
        enriched = cursor.fetchone()[0]

        print(f"\nTarget database stats:")
        print(f"  Total permits: {total_permits}")
        print(f"  Enriched properties: {enriched}")

    source_conn.close()
    target_conn.close()

    return 0


if __name__ == "__main__":
    exit(main())
