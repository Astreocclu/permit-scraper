#!/usr/bin/env python3
"""
One-time sync script to migrate SQLite data to PostgreSQL.

This merges permit-scraper's SQLite data into the existing PostgreSQL
tables managed by contractor-auditor Django models.

SQLite tables → PostgreSQL tables:
  permits      → leads_permit
  properties   → leads_property
  scored_leads → clients_scoredlead

Usage:
    export DATABASE_URL='postgresql://contractors_user:localdev123@localhost/contractors_dev'
    python3 scripts/sync_to_postgres.py
    python3 scripts/sync_to_postgres.py --dry-run
"""

import argparse
import json
import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import psycopg2
from psycopg2.extras import execute_values

SQLITE_DB = "data/permits.db"


def get_postgres_conn():
    """Get PostgreSQL connection from DATABASE_URL."""
    url = os.environ.get('DATABASE_URL')
    if not url:
        raise ValueError("DATABASE_URL environment variable not set")
    return psycopg2.connect(url)


def sync_permits(sqlite_conn, pg_conn, dry_run=False):
    """Sync permits from SQLite to PostgreSQL leads_permit table."""
    # SQLite schema: id, permit_id, city, property_address, permit_type, description, 
    #                status, issued_date, applicant_name, contractor_name, owner_name, 
    #                estimated_value, lead_type, source, scraped_at
    cursor = sqlite_conn.execute("""
        SELECT 
            permit_id, city, property_address, permit_type, description,
            status, issued_date, applicant_name, contractor_name, 
            estimated_value, scraped_at, lead_type
        FROM permits
    """)
    
    rows = cursor.fetchall()
    print(f"  Found {len(rows)} permits in SQLite")
    
    if dry_run or not rows:
        return len(rows)
    
    # PostgreSQL INSERT with ON CONFLICT using the proper unique constraint
    # Use ON CONFLICT DO NOTHING to skip duplicates, since the data should be the same
    insert_sql = """
        INSERT INTO leads_permit (
            permit_id, city, property_address, permit_type, description,
            status, issued_date, applicant_name, contractor_name,
            estimated_value, scraped_at, lead_type, processing_bin
        ) VALUES %s
        ON CONFLICT ON CONSTRAINT clients_permit_city_permit_id_33861e17_uniq DO UPDATE SET
            property_address = EXCLUDED.property_address,
            description = EXCLUDED.description,
            status = EXCLUDED.status,
            estimated_value = EXCLUDED.estimated_value,
            processing_bin = EXCLUDED.processing_bin
    """
    
    pg_rows = []
    cutoff_date = (datetime.now() - timedelta(days=60)).date()

    for row in rows:
        permit_id, city, prop_addr, permit_type, description, status, \
        issued_date, applicant, contractor, est_value, scraped_at, lead_type = row

        # Handle issued_date conversion
        issued = None
        if issued_date:
            try:
                issued = datetime.strptime(issued_date[:10], '%Y-%m-%d').date()
            except (ValueError, TypeError):
                pass

        # Handle scraped_at - ensure it's a datetime
        scraped = datetime.now()
        if scraped_at:
            try:
                scraped = datetime.fromisoformat(scraped_at.replace('Z', '+00:00'))
            except (ValueError, TypeError):
                try:
                    scraped = datetime.strptime(scraped_at[:19], '%Y-%m-%d %H:%M:%S')
                except (ValueError, TypeError):
                    pass

        # Calculate processing bin: active if recent or unknown, archive if old
        if issued is None or issued >= cutoff_date:
            processing_bin = 'active'
        else:
            processing_bin = 'archive'

        pg_rows.append((
            permit_id, city, prop_addr, permit_type, description,
            status, issued, applicant, contractor, est_value, scraped, lead_type,
            processing_bin
        ))
    
    with pg_conn.cursor() as cur:
        execute_values(cur, insert_sql, pg_rows, page_size=500)
    
    pg_conn.commit()
    return len(rows)


def sync_properties(sqlite_conn, pg_conn, dry_run=False):
    """Sync properties from SQLite to PostgreSQL leads_property table."""
    cursor = sqlite_conn.execute("""
        SELECT 
            property_address, property_address_normalized, cad_account_id,
            county, owner_name, mailing_address, mailing_address_normalized,
            market_value, land_value, improvement_value, year_built,
            square_feet, lot_size, property_type, neighborhood_code,
            neighborhood_median, is_absentee, homestead_exempt,
            enrichment_status, enriched_at
        FROM properties
    """)
    
    rows = cursor.fetchall()
    print(f"  Found {len(rows)} properties in SQLite")
    
    if dry_run or not rows:
        return len(rows)
    
    insert_sql = """
        INSERT INTO leads_property (
            property_address, property_address_normalized, cad_account_id,
            county, owner_name, mailing_address, mailing_address_normalized,
            market_value, land_value, improvement_value, year_built,
            square_feet, lot_size, property_type, neighborhood_code,
            neighborhood_median, is_absentee, homestead_exempt,
            enrichment_status, enriched_at
        ) VALUES %s
        ON CONFLICT (property_address) DO UPDATE SET
            owner_name = EXCLUDED.owner_name,
            market_value = EXCLUDED.market_value,
            enrichment_status = EXCLUDED.enrichment_status,
            enriched_at = EXCLUDED.enriched_at
    """
    
    pg_rows = []
    for row in rows:
        prop_addr, prop_addr_norm, cad_id, county, owner, mail_addr, mail_norm, \
        market_val, land_val, impr_val, year_built, sqft, lot_size, prop_type, \
        neighborhood, neighborhood_med, is_absent, homestead, enr_status, enr_at = row
        
        # Handle enriched_at datetime
        enriched = None
        if enr_at:
            try:
                enriched = datetime.fromisoformat(enr_at.replace('Z', '+00:00'))
            except (ValueError, TypeError):
                try:
                    enriched = datetime.strptime(enr_at[:19], '%Y-%m-%d %H:%M:%S')
                except (ValueError, TypeError):
                    pass
        
        # Convert SQLite booleans (0/1) to Python bool
        is_absentee = bool(is_absent) if is_absent is not None else None
        homestead_ex = bool(homestead) if homestead is not None else False
        
        pg_rows.append((
            prop_addr, prop_addr_norm, cad_id, county, owner, mail_addr, mail_norm,
            market_val, land_val, impr_val, year_built, sqft, lot_size, prop_type,
            neighborhood, neighborhood_med, is_absentee, homestead_ex,
            enr_status or 'pending', enriched
        ))
    
    with pg_conn.cursor() as cur:
        execute_values(cur, insert_sql, pg_rows, page_size=500)
    
    pg_conn.commit()
    return len(rows)


def sync_scored_leads(sqlite_conn, pg_conn, dry_run=False):
    """Sync scored_leads from SQLite to PostgreSQL clients_scoredlead table."""
    cursor = sqlite_conn.execute("""
        SELECT 
            permit_id, city, property_address, owner_name, market_value,
            is_absentee, days_old, score, tier, category, trade_group,
            reasoning, chain_of_thought, flags, ideal_contractor,
            contact_priority, scoring_method, scored_at
        FROM scored_leads
    """)
    
    rows = cursor.fetchall()
    print(f"  Found {len(rows)} scored leads in SQLite")
    
    if dry_run or not rows:
        return len(rows)
    
    # First, build a lookup of (city, permit_id) -> leads_permit.id
    with pg_conn.cursor() as cur:
        cur.execute("SELECT id, city, permit_id FROM leads_permit")
        permit_lookup = {(row[1], row[2]): row[0] for row in cur.fetchall()}
    
    print(f"  Built permit lookup with {len(permit_lookup)} entries")
    
    # Also build property lookup to validate FK
    with pg_conn.cursor() as cur:
        cur.execute("SELECT property_address FROM leads_property")
        property_set = {row[0] for row in cur.fetchall()}
    
    print(f"  Built property lookup with {len(property_set)} entries")
    
    insert_sql = """
        INSERT INTO clients_scoredlead (
            permit_id, category, trade_group, is_commercial, score, tier,
            reasoning, chain_of_thought, flags, ideal_contractor,
            contact_priority, scoring_method, scored_at, status, sold_to,
            cad_property_id
        ) VALUES %s
        ON CONFLICT (permit_id) DO UPDATE SET
            score = EXCLUDED.score,
            tier = EXCLUDED.tier,
            reasoning = EXCLUDED.reasoning
    """
    
    pg_rows = []
    skipped = 0
    
    for row in rows:
        sqlite_permit_id, city, prop_addr, owner, market_val, is_absent, \
        days_old, score, tier, category, trade_group, reasoning, chain, \
        flags_str, ideal_contractor, contact_priority, scoring_method, scored_at_str = row
        
        # Look up the PostgreSQL permit_id
        pg_permit_id = permit_lookup.get((city, sqlite_permit_id))
        if not pg_permit_id:
            skipped += 1
            continue
        
        # Handle scored_at datetime
        scored = datetime.now()
        if scored_at_str:
            try:
                scored = datetime.fromisoformat(scored_at_str.replace('Z', '+00:00'))
            except (ValueError, TypeError):
                try:
                    scored = datetime.strptime(scored_at_str[:19], '%Y-%m-%d %H:%M:%S')
                except (ValueError, TypeError):
                    pass
        
        # Handle flags - should be JSONB
        flags = []
        if flags_str:
            try:
                flags = json.loads(flags_str) if isinstance(flags_str, str) else flags_str
            except (json.JSONDecodeError, TypeError):
                flags = []
        
        # Determine is_commercial from trade_group
        is_commercial = trade_group == 'commercial' if trade_group else False
        
        pg_rows.append((
            pg_permit_id,
            (category or 'other')[:50],
            (trade_group or 'other')[:50],
            is_commercial,
            score or 0,
            (tier or 'C')[:5],
            reasoning or '',
            chain or '',
            json.dumps(flags),
            (ideal_contractor or '')[:200],  # VARCHAR(200) limit
            (contact_priority or 'email')[:20],
            (scoring_method or 'ai')[:20],
            scored,
            'available',  # Default status
            '',  # sold_to
            prop_addr if prop_addr in property_set else None  # FK to leads_property, NULL if not found
        ))
    
    if pg_rows:
        with pg_conn.cursor() as cur:
            execute_values(cur, insert_sql, pg_rows, page_size=500)
        pg_conn.commit()
    
    if skipped:
        print(f"  Skipped {skipped} leads (no matching permit in PostgreSQL)")
    
    return len(pg_rows)


def main():
    parser = argparse.ArgumentParser(description='Sync SQLite to PostgreSQL')
    parser.add_argument('--dry-run', action='store_true', help='Preview without changes')
    parser.add_argument('--sqlite', default=SQLITE_DB, help='SQLite database path')
    args = parser.parse_args()
    
    sqlite_path = Path(args.sqlite)
    if not sqlite_path.exists():
        print(f"ERROR: SQLite database not found: {sqlite_path}")
        return 1
    
    print("=== SYNC: SQLite → PostgreSQL ===")
    print(f"Source: {sqlite_path}")
    print(f"Target: {os.environ.get('DATABASE_URL', 'NOT SET')[:50]}...")
    if args.dry_run:
        print("Mode: DRY RUN\n")
    else:
        print()
    
    # Connect to databases
    sqlite_conn = sqlite3.connect(str(sqlite_path))
    sqlite_conn.row_factory = sqlite3.Row
    
    try:
        pg_conn = get_postgres_conn()
    except ValueError as e:
        print(f"ERROR: {e}")
        return 1
    
    # Sync in order (permits first, then properties, then scored_leads)
    print("Syncing permits...")
    permit_count = sync_permits(sqlite_conn, pg_conn, args.dry_run)
    print(f"  ✓ {permit_count} permits")
    
    print("Syncing properties...")
    property_count = sync_properties(sqlite_conn, pg_conn, args.dry_run)
    print(f"  ✓ {property_count} properties")
    
    print("Syncing scored leads...")
    lead_count = sync_scored_leads(sqlite_conn, pg_conn, args.dry_run)
    print(f"  ✓ {lead_count} scored leads")
    
    print(f"\n{'='*50}")
    if args.dry_run:
        print("DRY RUN COMPLETE - No changes made")
    else:
        print("SYNC COMPLETE")
        
        # Show PostgreSQL counts
        with pg_conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM leads_permit")
            print(f"PostgreSQL leads_permit: {cur.fetchone()[0]}")
            cur.execute("SELECT COUNT(*) FROM leads_property")
            print(f"PostgreSQL leads_property: {cur.fetchone()[0]}")
            cur.execute("SELECT COUNT(*) FROM clients_scoredlead")
            print(f"PostgreSQL clients_scoredlead: {cur.fetchone()[0]}")
    
    sqlite_conn.close()
    pg_conn.close()
    return 0


if __name__ == "__main__":
    exit(main())
