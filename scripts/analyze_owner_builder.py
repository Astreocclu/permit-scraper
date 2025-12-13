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


def names_match(applicant: str | None, owner: str | None) -> tuple[bool, str]:
    """
    Check if applicant name matches owner name (indicating owner-builder/DIY).

    Returns: (is_match, reason)
    """
    app_norm = normalize_name(applicant)
    own_norm = normalize_name(owner)

    if not app_norm:
        return False, "No applicant name"

    if not own_norm:
        return False, "No owner name"

    # Exact match after normalization
    if app_norm == own_norm:
        return True, "Exact match"

    # Token-based matching
    app_tokens = set(app_norm.split())
    own_tokens = set(own_norm.split())

    # Remove common filler words
    filler = {'and', '&', 'the', 'of', 'a', 'an'}
    app_tokens -= filler
    own_tokens -= filler

    if not app_tokens or not own_tokens:
        return False, "Empty after filtering"

    # All applicant tokens appear in owner (subset match)
    if app_tokens <= own_tokens:
        return True, "Applicant subset of owner"

    # All owner tokens appear in applicant
    if own_tokens <= app_tokens:
        return True, "Owner subset of applicant"

    # Shared last name heuristic (at least one significant token overlap)
    # This catches spouse scenarios: "Mary Smith" vs "John Smith"
    overlap = app_tokens & own_tokens
    if overlap:
        # Check if overlap contains a likely last name (3+ chars, not a common first name)
        common_first_names = {'john', 'mary', 'james', 'michael', 'david', 'robert', 'william'}
        significant_overlap = {t for t in overlap if len(t) >= 3 and t not in common_first_names}
        if significant_overlap:
            return True, f"Family match ({', '.join(significant_overlap)})"

    return False, "No match"
