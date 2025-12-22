#!/usr/bin/env python3
"""
CAD Enrichment Backfill Script.

Fixes address matching by building full addresses from permit data,
querying CAD APIs, and populating leads_property for scoring.

Problem: Permits have "14108 SANTA ANN ST", properties have "14108 SANTA ANN ST, Frisco TX 75071"
Solution: Build full address using permit's city column, query CAD, store with original address as key.

Usage:
    python3 scripts/backfill_cad_enrichment.py --limit 10      # Test run
    python3 scripts/backfill_cad_enrichment.py                  # Full backfill
    python3 scripts/backfill_cad_enrichment.py --city frisco    # Single city
    python3 scripts/backfill_cad_enrichment.py --dry-run        # Preview without DB writes
"""

import argparse
import logging
import os
import sys
import time
from datetime import datetime
from typing import Optional, Tuple

from dotenv import load_dotenv
load_dotenv()

import psycopg2

# Import CAD query functions from existing enrich_cad.py
# These handle the actual API calls to county CAD systems
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from enrich_cad import (
    query_cad_with_retry,
    parse_float,
    parse_int,
    is_absentee_owner,
    COUNTY_CONFIGS,
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


def get_db_connection():
    """Get PostgreSQL connection from DATABASE_URL."""
    url = os.environ.get('DATABASE_URL')
    if not url:
        raise ValueError("DATABASE_URL environment variable not set")
    return psycopg2.connect(url)


# City to county mapping for DFW area
# Only includes cities in counties with FREE CAD APIs
CITY_TO_COUNTY = {
    # Collin County (free API)
    'frisco': 'collin',
    'mckinney': 'collin',
    'allen': 'collin',
    'plano': 'collin',
    'prosper': 'collin',
    'celina': 'collin',
    'anna': 'collin',
    'princeton': 'collin',
    'melissa': 'collin',
    'fairview': 'collin',
    'lucas': 'collin',
    'murphy': 'collin',
    'wylie': 'collin',
    'sachse': 'collin',

    # Tarrant County (free API)
    'fort worth': 'tarrant',
    'arlington': 'tarrant',
    'north richland hills': 'tarrant',
    'hurst': 'tarrant',
    'bedford': 'tarrant',
    'euless': 'tarrant',
    'grapevine': 'tarrant',
    'colleyville': 'tarrant',
    'southlake': 'tarrant',
    'keller': 'tarrant',
    'watauga': 'tarrant',
    'haltom city': 'tarrant',
    'richland hills': 'tarrant',
    'mansfield': 'tarrant',

    # Dallas County (free API)
    'dallas': 'dallas',
    'irving': 'dallas',
    'grand prairie': 'dallas',
    'mesquite': 'dallas',
    'garland': 'dallas',
    'richardson': 'dallas',
    'carrollton': 'dallas',
    'farmers branch': 'dallas',
    'coppell': 'dallas',
    'desoto': 'dallas',
    'duncanville': 'dallas',
    'cedar hill': 'dallas',
    'lancaster': 'dallas',
    'rowlett': 'dallas',

    # Denton County (free API)
    'denton': 'denton',
    'lewisville': 'denton',
    'flower mound': 'denton',
    'highland village': 'denton',
    'the colony': 'denton',
    'little elm': 'denton',
    'corinth': 'denton',
    'aubrey': 'denton',
    'pilot point': 'denton',
    'sanger': 'denton',
    'argyle': 'denton',
    'bartonville': 'denton',
    'trophy club': 'denton',

    # Kaufman County (free API)
    'forney': 'kaufman',
    'terrell': 'kaufman',
    'kaufman': 'kaufman',

    # Rockwall County (free API)
    'rockwall': 'rockwall',
    'royse city': 'rockwall',
    'heath': 'rockwall',
    'fate': 'rockwall',
}


def get_county_for_city(city: Optional[str]) -> Optional[str]:
    """
    Get the county for a city.

    Args:
        city: City name (case-insensitive)

    Returns:
        County name (lowercase) or None if not found
    """
    if not city:
        return None
    return CITY_TO_COUNTY.get(city.lower().strip())


def build_full_address(street_address: Optional[str], city: Optional[str]) -> Optional[str]:
    """
    Build a full queryable address from permit data.

    Args:
        street_address: Street address from permit (e.g., "14108 SANTA ANN ST")
        city: City from permit (e.g., "frisco")

    Returns:
        Full address like "14108 SANTA ANN ST, Frisco, TX" or None if invalid
    """
    if not street_address or not city:
        return None

    street = street_address.strip()
    city_clean = city.strip().title()

    if not street or not city_clean:
        return None

    return f"{street}, {city_clean}, TX"


def build_unenriched_permits_query(city: Optional[str] = None, limit: Optional[int] = None) -> str:
    """
    Build SQL query to fetch permits needing CAD enrichment.

    A permit needs enrichment if:
    - No matching leads_property record exists, OR
    - The leads_property record has enrichment_status != 'success'

    Args:
        city: Optional city filter (case-insensitive)
        limit: Optional limit on results

    Returns:
        SQL query string
    """
    query = """
        SELECT DISTINCT
            p.id,
            p.property_address,
            p.city
        FROM leads_permit p
        LEFT JOIN leads_property prop ON p.property_address = prop.property_address
        WHERE p.property_address IS NOT NULL
          AND p.city IS NOT NULL
          AND p.processing_bin = 'active'
          AND (prop.property_address IS NULL OR prop.enrichment_status != 'success')
    """

    if city:
        query += f"\n          AND LOWER(p.city) = LOWER('{city}')"

    query += "\n        ORDER BY p.id"

    if limit:
        query += f"\n        LIMIT {limit}"

    return query


def build_upsert_property_sql() -> str:
    """
    Build SQL for upserting CAD data into leads_property.

    Uses the ORIGINAL permit address as the key (not CAD canonical address)
    so that JOINs in score_leads.py work correctly.

    Returns:
        SQL query with placeholders for psycopg2
    """
    return """
        INSERT INTO leads_property (
            property_address,
            property_address_normalized,
            cad_account_id,
            county,
            owner_name,
            mailing_address,
            market_value,
            land_value,
            improvement_value,
            year_built,
            square_feet,
            lot_size,
            is_absentee,
            homestead_exempt,
            enrichment_status,
            enriched_at
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, false, 'success', %s
        )
        ON CONFLICT (property_address) DO UPDATE SET
            property_address_normalized = EXCLUDED.property_address_normalized,
            cad_account_id = EXCLUDED.cad_account_id,
            county = EXCLUDED.county,
            owner_name = EXCLUDED.owner_name,
            mailing_address = EXCLUDED.mailing_address,
            market_value = EXCLUDED.market_value,
            land_value = EXCLUDED.land_value,
            improvement_value = EXCLUDED.improvement_value,
            year_built = EXCLUDED.year_built,
            square_feet = EXCLUDED.square_feet,
            lot_size = EXCLUDED.lot_size,
            is_absentee = EXCLUDED.is_absentee,
            enrichment_status = 'success',
            enriched_at = EXCLUDED.enriched_at
    """


def process_permit(
    permit_id: int,
    property_address: str,
    city: str,
    conn,
    dry_run: bool = False
) -> Tuple[str, Optional[str]]:
    """
    Process a single permit for CAD enrichment.

    Args:
        permit_id: Database ID of the permit
        property_address: Original permit address (will be used as key)
        city: City from permit
        conn: Database connection
        dry_run: If True, don't write to database

    Returns:
        Tuple of (status, detail) where status is 'success', 'not_found', 'skip', or 'error'
    """
    # Get county for this city
    county = get_county_for_city(city)
    if not county:
        return ('skip', f'No CAD API for city: {city}')

    if county not in COUNTY_CONFIGS:
        return ('skip', f'No CAD config for county: {county}')

    # Build full address for CAD query
    full_address = build_full_address(property_address, city)
    if not full_address:
        return ('skip', 'Could not build full address')

    # Query CAD API
    try:
        cad_data, county_name, variant_used = query_cad_with_retry(full_address, county, timeout=30)
    except Exception as e:
        return ('error', str(e))

    if not cad_data:
        return ('not_found', f'No CAD match for: {full_address}')

    if dry_run:
        market_value = parse_float(cad_data.get('market_value'))
        return ('success', f'DRY RUN: Would save ${market_value:,.0f}' if market_value else 'DRY RUN: Would save (no value)')

    # Extract CAD data
    owner_name = (cad_data.get('owner_name') or '').strip()
    market_value = parse_float(cad_data.get('market_value'))
    land_value = parse_float(cad_data.get('land_value'))
    improvement_value = parse_float(cad_data.get('improvement_value'))
    year_built = parse_int(cad_data.get('year_built'))
    square_feet = parse_int(cad_data.get('square_feet'))
    lot_size = parse_float(cad_data.get('lot_size'))
    situs_addr = cad_data.get('situs_addr', '')
    account_num = cad_data.get('account_num')

    # Build mailing address
    owner_addr = (cad_data.get('owner_addr') or '').strip()
    owner_city = (cad_data.get('owner_city') or '').strip()
    owner_zip = (cad_data.get('owner_zip') or '').strip()
    mailing_address = f"{owner_addr}, {owner_city} {owner_zip}".strip(", ")

    # Detect absentee owner
    absentee = is_absentee_owner(situs_addr, mailing_address) if owner_addr else None

    # Upsert into leads_property using ORIGINAL permit address as key
    sql = build_upsert_property_sql()
    with conn.cursor() as cur:
        cur.execute(sql, (
            property_address,           # Original permit address (KEY)
            situs_addr,                 # CAD canonical address (for reference)
            account_num,
            county_name.lower() if county_name else county,
            owner_name,
            mailing_address if mailing_address else None,
            market_value,
            land_value,
            improvement_value,
            year_built,
            square_feet,
            lot_size,
            absentee,
            datetime.now()
        ))
    conn.commit()

    value_str = f'${market_value:,.0f}' if market_value else 'N/A'
    return ('success', f'{owner_name[:30]} | {value_str}')
