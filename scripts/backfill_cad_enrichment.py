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
