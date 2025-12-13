#!/usr/bin/env python3
"""
Owner-Builder Analysis Report

Analyzes permit leads to determine the percentage filed by homeowners (DIY/Owner-Builder)
vs contractors. Used to validate lead quality.

Usage:
    python3 scripts/analyze_owner_builder.py
    python3 scripts/analyze_owner_builder.py --output report.md
"""

import re


# Business entity suffixes
ENTITY_SUFFIXES = {'llc', 'inc', 'corp', 'ltd', 'lp', 'llp', 'pllc', 'pc'}

# Contractor industry keywords
CONTRACTOR_KEYWORDS = {
    'construction', 'roofing', 'plumbing', 'electric', 'electrical', 'builders',
    'homes', 'custom', 'remodeling', 'restoration', 'services', 'solutions',
    'contractors', 'contracting', 'mechanical', 'hvac', 'solar', 'energy',
    'pool', 'pools', 'landscape', 'landscaping', 'fence', 'fencing',
    'foundation', 'renovation', 'renovations', 'repair', 'repairs',
    'exteriors', 'interiors', 'design', 'development', 'properties',
    'investments', 'holdings', 'partners', 'group', 'enterprises'
}


def normalize_name(name: str | None) -> str:
    """Normalize a name for comparison: lowercase, strip, remove punctuation."""
    if not name:
        return ""
    # Lowercase, remove non-alphanumeric except spaces
    cleaned = re.sub(r'[^a-z0-9 ]', '', name.lower())
    # Collapse multiple spaces
    return ' '.join(cleaned.split())


def is_contractor_entity(name: str | None) -> bool:
    """Check if name appears to be a contractor/business entity."""
    if not name:
        return False

    name_lower = name.lower()
    tokens = set(re.sub(r'[^a-z0-9 ]', '', name_lower).split())

    # Check for business entity suffixes
    if tokens & ENTITY_SUFFIXES:
        return True

    # Check for contractor industry keywords
    if tokens & CONTRACTOR_KEYWORDS:
        return True

    return False


def names_match(applicant: str, owner: str) -> tuple[bool, str]:
    """Placeholder - will implement next."""
    pass
