#!/usr/bin/env python3
"""
Pre-filter permits BEFORE enrichment to save CAD API calls.

Applies the same filters as score_leads.py:
- Production builder detection (description only - owner requires enrichment)
- Junk project detection
- Age filter (>90 days old)
- Commercial indicators

Usage:
    python3 scripts/prefilter_permits.py --dry-run     # Preview what would be filtered
    python3 scripts/prefilter_permits.py               # Mark permits as filtered in DB
"""

import argparse
import os
import re
from datetime import datetime, date

from dotenv import load_dotenv
load_dotenv()

import psycopg2
from psycopg2.extras import RealDictCursor

# =============================================================================
# FILTER LISTS (from score_leads.py)
# =============================================================================

PRODUCTION_BUILDERS = [
    "dr horton", "d.r. horton", "lennar", "pulte", "meritage",
    "toll brothers", "kb home", "kb homes", "taylor morrison",
    "ashton woods", "standard pacific", "centex", "beazer",
    "m/i homes", "mi homes", "david weekley", "highland homes",
    "shaddock", "grand homes", "megatel", "tri pointe", "mattamy",
    "dream finders", "landsea", "gehan", "perry homes", "trendmaker",
    "bloomfield homes", "history maker", "impression homes", "antares homes",
    "first texas", "plantation homes", "altura homes",
    "coventry homes", "newmark homes", "westin homes",
    "saratoga homes", "chesmar", "sitterle", "empire communities",
    "mcguyer homebuilders", "stylecraft", "pacesetter", "dunhill",
    "brightland", "southgate", "chesmar homes", "trophy signature",
    "landon homes", "ashton dallas",
    "homes llc", "homes inc", "homebuilders", "home builders",
    "development llc", "development inc", "developers llc",
    "builders llc", "builders inc", "construction llc",
    "communities llc", "communities inc", "residential llc",
    "habitat for humanity", "city of", " isd", "church",
]

PRODUCTION_BUILDER_PATTERNS = [
    r"\bhomes\s+(of|at|in)\s+",
    r"\bhome\s+builders?\b",
    r"\bdevelopment\s+(group|corp|co)\b",
    r"\bbuilders?\s+(group|corp|co)\b",
    r"\bresidential\s+(group|corp|co)\b",
]

JUNK_PROJECTS = [
    "shed", "storage building", "carport",
    "fire repair", "fire damage",
    "storm damage", "hail damage", "water damage",
    "electrical panel", "water heater",
    "hvac replacement", "ac replacement", "furnace replacement",
    "sewer repair", "sewer replacement", "sewer line",
    "demolition", "demo permit", "tear down",
    "temporary", "temp permit", "construction trailer",
    "sign permit", "signage", "banner",
    "tenant finish", "tenant improvement", "ti permit",
    "gas test", "meter release", "air test",
    "irrigation", "sprinkler system",
    "certificate of occupancy", "certificate of compliance",
    "permit extension", "extension permit",
    "fire prevention", "fire alarm", "fire sprinkler",
    "licensed professional", "add/change",
    "umbrella permit",
]

# Junk permit TYPE codes - EXACT match only for 2-letter codes
JUNK_PERMIT_TYPE_EXACT = ["co", "cp", "fe", "si"]  # Arlington codes

# Junk permit TYPE codes - PREFIX match
JUNK_PERMIT_TYPES = [
    "certificate of occupancy",
    "permit extension",
    "fire prevention",
    "umbrella permit",
    "add/change licensed",
    "zoning verification", "zoning determination",
    "change of scope", "change of contact",
    "water and wastewater",
    "phase -",  # Phase permits (usually production builders)
    "commercial ",  # Commercial anything (with space to avoid matching "commercial-grade residential")
]

# Administrative junk (no sellable lead value)
ADMIN_JUNK = [
    "zoning", "variance", "plat", "subdivision",
    "right-of-way", "row permit", "encroachment",
    "driveway approach", "sidewalk waiver",
    "site plan", "tree removal",
]

REMODEL_INDICATORS = [
    "addition", "remodel", "rebuild", "new construction",
    "second story", "second-story", "2nd story", "expansion",
    "renovate", "renovation", "convert", "build new",
]

COMMERCIAL_INDICATORS = [
    "commercial", "office", "retail", "restaurant", "warehouse", "industrial",
    "tenant", "suite", "shopping", "plaza", "mall", "store", "business",
    "corp", "inc.", "llc", "church", "school", "hospital", "medical", "clinic",
    "apartment complex", "multi-family", "multifamily",
]

# High-value residential keywords (keep these)
RESIDENTIAL_KEEP = [
    "pool", "swim", "spa", "patio", "deck", "pergola", "outdoor kitchen",
    "addition", "remodel", "renovation", "kitchen", "bath", "master",
    "roof replacement", "reroof", "new roof",
    "fence", "privacy fence",
    "adu", "accessory dwelling", "guest house", "casita",
    "custom home", "new home", "single family",
]


def is_production_builder(text: str) -> bool:
    if not text:
        return False
    text_lower = text.lower().strip()
    for builder in PRODUCTION_BUILDERS:
        if builder in text_lower:
            return True
    for pattern in PRODUCTION_BUILDER_PATTERNS:
        if re.search(pattern, text_lower):
            return True
    return False


def is_junk_project(description: str) -> bool:
    if not description:
        return False
    desc_lower = description.lower()
    for junk in JUNK_PROJECTS:
        if junk in desc_lower:
            if junk in ["demolition", "demo permit"]:
                if any(ind in desc_lower for ind in REMODEL_INDICATORS):
                    continue
            return True
    return False


def is_junk_permit_type(permit_type: str) -> bool:
    if not permit_type:
        return False
    pt_lower = permit_type.lower().strip()

    # Exact match for short codes (to avoid false positives like "Fence" matching "fe")
    if pt_lower in JUNK_PERMIT_TYPE_EXACT:
        return True

    # Prefix match for longer patterns
    for junk in JUNK_PERMIT_TYPES:
        if pt_lower.startswith(junk):
            return True
    return False


def is_admin_junk(permit_type: str) -> bool:
    if not permit_type:
        return False
    pt_lower = permit_type.lower()
    return any(junk in pt_lower for junk in ADMIN_JUNK)


def is_commercial(text: str) -> bool:
    if not text:
        return False
    text_lower = text.lower()
    return any(ind in text_lower for ind in COMMERCIAL_INDICATORS)


def is_high_value_residential(text: str) -> bool:
    if not text:
        return False
    text_lower = text.lower()
    return any(kw in text_lower for kw in RESIDENTIAL_KEEP)


def should_discard(permit: dict) -> tuple[bool, str]:
    """Pre-enrichment filter. Returns (discard, reason)."""
    desc = permit.get('description') or ''
    permit_type = permit.get('permit_type') or ''
    address = permit.get('property_address') or ''
    issued_date = permit.get('issued_date')

    combined_text = f"{desc} {permit_type} {address}"

    # Age filter
    if issued_date:
        if isinstance(issued_date, str):
            try:
                issued_date = datetime.strptime(issued_date, '%Y-%m-%d').date()
            except:
                issued_date = None
        if issued_date:
            days_old = (date.today() - issued_date).days
            if days_old > 90:
                return True, f"Too old ({days_old} days)"

    # Empty description AND empty/generic permit type = no lead value
    if not desc.strip() and (not permit_type or permit_type in ('None', '')):
        return True, "No description or type"

    # Junk permit type (CO, CP, FE, SI, etc.)
    if is_junk_permit_type(permit_type):
        return True, f"Junk permit type: {permit_type}"

    # Administrative junk (zoning, variance, plat, etc.)
    if is_admin_junk(permit_type):
        return True, f"Admin junk: {permit_type}"

    # Production builder in description
    if is_production_builder(desc):
        return True, "Production builder"

    # Junk project description
    if is_junk_project(desc):
        return True, "Junk project"

    # Junk in permit type name
    if is_junk_project(permit_type):
        return True, f"Junk permit type name: {permit_type}"

    # Commercial (unless high-value residential keywords present)
    if is_commercial(combined_text) and not is_high_value_residential(combined_text):
        return True, "Commercial"

    return False, ""


def main():
    parser = argparse.ArgumentParser(description='Pre-filter permits before enrichment')
    parser.add_argument('--dry-run', action='store_true', help='Preview without modifying DB')
    parser.add_argument('--limit', type=int, help='Limit permits to process')
    args = parser.parse_args()

    conn = psycopg2.connect(os.environ['DATABASE_URL'])
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # Get unenriched permits within 90 days
    query = '''
        SELECT p.id, p.permit_id, p.city, p.property_address, p.property_address_normalized,
               p.permit_type, p.description, p.issued_date, p.contractor_name
        FROM leads_permit p
        LEFT JOIN leads_property prop ON p.property_address_normalized = prop.property_address
        WHERE prop.property_address IS NULL
        AND (p.issued_date IS NULL OR p.issued_date > NOW() - INTERVAL '90 days')
    '''
    if args.limit:
        query += f' LIMIT {args.limit}'

    cur.execute(query)
    permits = cur.fetchall()

    print(f"=== PRE-FILTER PERMITS ===")
    print(f"Unenriched recent permits: {len(permits):,}")
    print()

    stats = {
        'total': len(permits),
        'keep': 0,
        'discard': 0,
        'reasons': {}
    }

    keep_permits = []

    for permit in permits:
        discard, reason = should_discard(dict(permit))
        if discard:
            stats['discard'] += 1
            reason_key = reason.split('(')[0].strip()
            stats['reasons'][reason_key] = stats['reasons'].get(reason_key, 0) + 1
        else:
            stats['keep'] += 1
            keep_permits.append(permit)

    # Print stats
    discard_pct = (stats['discard'] / stats['total'] * 100) if stats['total'] > 0 else 0
    print(f"Results:")
    print(f"  Keep: {stats['keep']:,} ({100-discard_pct:.1f}%)")
    print(f"  Discard: {stats['discard']:,} ({discard_pct:.1f}%)")
    print()

    if stats['reasons']:
        print("Discard reasons:")
        for reason, count in sorted(stats['reasons'].items(), key=lambda x: -x[1]):
            print(f"  {reason}: {count:,}")
    print()

    # Show sample of keepers by city
    city_counts = {}
    for p in keep_permits:
        city = p['city']
        city_counts[city] = city_counts.get(city, 0) + 1

    print("Keepers by city:")
    for city, count in sorted(city_counts.items(), key=lambda x: -x[1])[:10]:
        print(f"  {city}: {count:,}")
    print()

    # Sample keepers
    print("Sample keepers:")
    for p in keep_permits[:5]:
        desc = (p['description'] or '')[:60]
        print(f"  [{p['city']}] {p['permit_type']}: {desc}...")
    print()

    if args.dry_run:
        print("DRY RUN - no changes made")
        print(f"\nTo enrich these {stats['keep']:,} permits, run:")
        print("  python3 scripts/enrich_cad.py")
    else:
        # Output the keeper IDs for enrichment
        keeper_ids = [p['id'] for p in keep_permits]
        print(f"Keepers ready for enrichment: {len(keeper_ids):,}")

        # Save keeper IDs to a temp file for the enrichment script
        with open('/tmp/prefiltered_permit_ids.txt', 'w') as f:
            for pid in keeper_ids:
                f.write(f"{pid}\n")
        print(f"Saved to /tmp/prefiltered_permit_ids.txt")

    conn.close()
    return stats


if __name__ == '__main__':
    main()
