#!/usr/bin/env python3
"""
Validate new categorization logic against existing data.
Compares old vs new category assignments to understand impact before deploying.
"""

import os
import re
from collections import defaultdict
from dotenv import load_dotenv
import psycopg2

load_dotenv()

# =============================================================================
# OLD LOGIC (current production)
# =============================================================================

OLD_CATEGORY_KEYWORDS = {
    "pool": ["pool", "swim", "spa", "hot tub", "gunite", "fiberglass pool"],
    "outdoor_living": ["patio", "deck", "pergola", "outdoor kitchen", "cabana",
                       "gazebo", "arbor", "screen enclosure", "covered patio",
                       "shade structure", "pavilion", "outdoor living"],
    "fence": ["fence", "fencing", "privacy fence", "iron fence", "wood fence"],
    "roof": ["roof", "roofing", "re-roof", "reroof", "shingle", "metal roof"],
    "siding": ["siding", "hardie", "stucco", "exterior finish"],
    "windows": ["window", "door replacement", "sliding door", "french door"],
    "concrete": ["driveway", "sidewalk", "concrete", "flatwork", "stamped concrete", "pavers"],
    "hvac": ["hvac", "air condition", "ac unit", "furnace", "heat pump", "ductwork", "mini split"],
    "plumbing": ["plumb", "water heater", "tankless", "water line", "gas line", "repipe"],
    "electrical": ["electric", "panel", "outlet", "circuit", "wire", "ev charger", "generator"],
    "solar": ["solar", "photovoltaic", "pv system"],
    "foundation": ["foundation", "pier", "underpinning", "slab repair", "leveling"],
    "new_construction": ["new home", "new construction", "new sfd", "custom home"],
    "addition": ["addition", "room addition", "add on", "expansion"],
    "remodel": ["remodel", "renovation", "kitchen remodel", "bath remodel"],
    "demolition": ["demo", "demolition", "tear down"],
    "temporary": ["temporary", "temp permit"],
    "signage": ["sign permit", "signage", "banner"],
}

def old_categorize(description: str, permit_type: str) -> str:
    """Original categorization logic (substring matching, dict order)."""
    desc = (description + " " + permit_type).lower()
    for category, keywords in OLD_CATEGORY_KEYWORDS.items():
        if any(kw in desc for kw in keywords):
            return category
    return "other"


# =============================================================================
# NEW LOGIC (proposed fix)
# =============================================================================

# Layer 1: permit_type takes priority (expanded to catch more variants)
# Order matters here too - more specific first
PERMIT_TYPE_PRIORITY = {
    "demolition": ["demolition", "demo"],
    "solar": ["solar", "photovoltaic", "pv"],
    "outdoor_living": ["patio", "carport", "pergola", "deck", "porch", "cover"],  # Before roof!
    "roof": ["roof", "roofing", "re-roof", "reroof"],
    "foundation": ["foundation"],
    "fence": ["fence"],
    "pool": ["pool", "swimming"],
    "electrical": ["electrical"],
    "plumbing": ["plumbing"],
    "hvac": ["mechanical", "hvac"],
}

# Keywords that need word boundary matching to prevent false positives
# These are the problematic ones that match inside other words
WORD_BOUNDARY_KEYWORDS = {"deck", "demo"}

# Layer 2: Priority-ordered categories
# Key insight: order matters! Check more specific categories first
NEW_CATEGORY_KEYWORDS = [
    # Check specific/override categories first
    ("demolition", ["demo", "demolition", "tear down"]),
    ("new_construction", ["new home", "new construction", "new sfd", "custom home"]),
    ("solar", ["solar", "photovoltaic", "pv system"]),

    # Roof before outdoor_living (to prevent "decking" false positives)
    ("roof", ["roof", "roofing", "re-roof", "reroof", "shingle", "metal roof"]),

    # Pool before outdoor_living
    ("pool", ["pool", "swim", "spa", "hot tub", "gunite", "fiberglass pool"]),

    # Now outdoor_living (deck will use word boundaries)
    ("outdoor_living", ["patio", "deck", "pergola", "outdoor kitchen", "cabana",
                        "gazebo", "arbor", "screen enclosure", "covered patio",
                        "shade structure", "pavilion", "outdoor living", "porch"]),

    ("fence", ["fence", "fencing", "privacy fence", "iron fence", "wood fence"]),
    ("siding", ["siding", "hardie", "stucco", "exterior finish"]),
    ("windows", ["window", "door replacement", "sliding door", "french door"]),

    # Concrete after demolition
    ("concrete", ["driveway", "sidewalk", "concrete", "flatwork", "stamped concrete", "pavers"]),

    ("hvac", ["hvac", "air condition", "ac unit", "furnace", "heat pump", "ductwork", "mini split"]),
    ("plumbing", ["plumb", "water heater", "tankless", "water line", "gas line", "repipe", "sewer"]),
    ("electrical", ["electric", "panel", "outlet", "circuit", "wire", "ev charger", "generator"]),
    ("foundation", ["foundation", "pier", "underpinning", "slab repair", "leveling"]),
    ("addition", ["addition", "room addition", "add on", "expansion"]),
    ("remodel", ["remodel", "renovation", "kitchen remodel", "bath remodel"]),
    ("temporary", ["temporary", "temp permit"]),
    ("signage", ["sign permit", "signage", "banner"]),
]

def new_categorize(description: str, permit_type: str) -> str:
    """New categorization logic with permit_type priority + selective word boundaries."""
    desc = (description + " " + permit_type).lower()
    ptype = permit_type.lower() if permit_type else ""

    # Layer 1: Check permit_type first (exact category signals)
    for category, type_keywords in PERMIT_TYPE_PRIORITY.items():
        if any(kw in ptype for kw in type_keywords):
            return category

    # Layer 2: Keyword matching in priority order
    for category, keywords in NEW_CATEGORY_KEYWORDS:
        for kw in keywords:
            # Use word boundary only for problematic keywords
            if kw in WORD_BOUNDARY_KEYWORDS:
                pattern = rf'\b{re.escape(kw)}\b'
                if re.search(pattern, desc):
                    return category
            else:
                # Standard substring matching for most keywords
                if kw in desc:
                    return category

    return "other"


# =============================================================================
# VALIDATION
# =============================================================================

def get_db_connection():
    url = os.environ.get('DATABASE_URL')
    if not url:
        raise ValueError("DATABASE_URL not set")
    return psycopg2.connect(url)


def main():
    conn = get_db_connection()

    # Get all scored leads with their permit data
    query = """
        SELECT
            sl.id,
            p.permit_id,
            sl.category as current_category,
            p.description,
            p.permit_type,
            p.city
        FROM clients_scoredlead sl
        JOIN leads_permit p ON sl.permit_id = p.id
        ORDER BY sl.id
    """

    with conn.cursor() as cur:
        cur.execute(query)
        rows = cur.fetchall()

    print(f"Analyzing {len(rows)} scored leads...\n")

    # Track changes
    changes = []
    category_changes = defaultdict(lambda: defaultdict(int))  # old -> new -> count

    for row in rows:
        sl_id, permit_id, current_cat, description, permit_type, city = row
        description = description or ""
        permit_type = permit_type or ""

        old_cat = old_categorize(description, permit_type)
        new_cat = new_categorize(description, permit_type)

        if old_cat != new_cat:
            changes.append({
                'permit_id': permit_id,
                'city': city,
                'old': old_cat,
                'new': new_cat,
                'current_db': current_cat,
                'description': description[:80],
                'permit_type': permit_type,
            })
            category_changes[old_cat][new_cat] += 1

    # Report
    print("=" * 70)
    print("CATEGORY CHANGE SUMMARY")
    print("=" * 70)
    print(f"Total leads analyzed: {len(rows)}")
    print(f"Leads that would change: {len(changes)} ({100*len(changes)/len(rows):.1f}%)")
    print()

    print("Changes by category transition:")
    for old_cat in sorted(category_changes.keys()):
        for new_cat, count in sorted(category_changes[old_cat].items(), key=lambda x: -x[1]):
            print(f"  {old_cat:20} -> {new_cat:20}: {count}")
    print()

    # Show samples of key transitions
    print("=" * 70)
    print("SAMPLE CHANGES (spot check these)")
    print("=" * 70)

    # Group by transition type
    transitions = defaultdict(list)
    for c in changes:
        key = f"{c['old']} -> {c['new']}"
        transitions[key].append(c)

    # Show up to 3 samples of each transition
    for transition, samples in sorted(transitions.items(), key=lambda x: -len(x[1])):
        print(f"\n--- {transition} ({len(samples)} total) ---")
        for sample in samples[:3]:
            print(f"  [{sample['permit_id']}] {sample['city']}")
            print(f"  Type: {sample['permit_type']}")
            print(f"  Desc: {sample['description']}...")
            print()

    conn.close()


if __name__ == "__main__":
    main()
