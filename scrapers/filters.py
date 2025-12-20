# scrapers/filters.py
"""Post-processing filters for permit data."""

# Southlake-specific residential permit types for batch scraping
# (Migrated from southlake_residential_batch.py)
SOUTHLAKE_RESIDENTIAL_TYPES = [
    "Residential New Building (Single Family Home)",
    "Residential New Building (Duplex)",
    "Residential New Building (Townhome)",
    "Residential Remodel",
    "Residential Addition Conditioned Space",
    "Residential Addition Conditioned & Uncond",
    "Pool & Spa (Residential)",
    "Pool (Residential)",
    "Electrical Permit (Residential)",
    "Mechanical Permit (Residential)",
    "Plumbing Permit (Residential)",
    "Residential Reroof",
    "Fence (Residential)",
    "Solar Panel - Residential",
]


def filter_residential_permits(permits: list[dict]) -> list[dict]:
    """
    Filter permits to keep only residential-related types.

    Includes: residential, pool, spa, roof, foundation, accessory, patio, remodel, addition
    Excludes: commercial, business, sign, fire, certificate of occupancy
    """
    residential_keywords = [
        'residential', 'res ', 'pool', 'spa', 'roof',
        'foundation', 'accessory', 'patio', 'remodel', 'addition'
    ]
    commercial_keywords = [
        'commercial', 'business', 'sign', 'fire',
        'certificate of occupancy', 'certificate of compliance'
    ]

    filtered = []
    for permit in permits:
        permit_type = permit.get('type', '').lower()

        # Skip if no type or empty type
        if not permit_type:
            continue

        # Exclude explicit commercial
        if any(keyword in permit_type for keyword in commercial_keywords):
            continue

        # Include explicit residential keywords
        if any(keyword in permit_type for keyword in residential_keywords):
            filtered.append(permit)

    return filtered
