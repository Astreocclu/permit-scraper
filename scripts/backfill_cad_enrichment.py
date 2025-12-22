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

from typing import Optional


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
