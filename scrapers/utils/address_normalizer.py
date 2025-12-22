"""
Address normalization and matching utilities.

Used for deduplicating permits from multiple sources (CAD, municipal portals).
"""

import re
from typing import Optional


# Street type standardization map
STREET_TYPES = {
    'STREET': 'ST',
    'AVENUE': 'AVE',
    'BOULEVARD': 'BLVD',
    'ROAD': 'RD',
    'DRIVE': 'DR',
    'LANE': 'LN',
    'COURT': 'CT',
    'PLACE': 'PL',
    'TERRACE': 'TER',
    'CIRCLE': 'CIR',
    'HIGHWAY': 'HWY',
    'PARKWAY': 'PKWY',
    'WAY': 'WAY',
    'TRAIL': 'TRL',
}

# Direction standardization
DIRECTIONS = {
    'NORTH': 'N',
    'SOUTH': 'S',
    'EAST': 'E',
    'WEST': 'W',
    'NORTHEAST': 'NE',
    'NORTHWEST': 'NW',
    'SOUTHEAST': 'SE',
    'SOUTHWEST': 'SW',
}


def normalize_address(address: Optional[str]) -> str:
    """
    Normalize an address string for consistent matching.

    Transforms:
    - Uppercase
    - Remove punctuation (except hyphens in house numbers)
    - Standardize street types (STREET -> ST)
    - Standardize directions (NORTH -> N)
    - Collapse whitespace
    - Handle unit designations (# -> UNIT)

    Args:
        address: Raw address string

    Returns:
        Normalized address string, or empty string if input is None/empty
    """
    if not address or not isinstance(address, str):
        return ""

    # Uppercase and strip
    addr = address.upper().strip()

    if not addr:
        return ""

    # Convert # to UNIT for standardization
    addr = re.sub(r'#(\d+)', r'UNIT \1', addr)

    # Remove punctuation (keep hyphens for now)
    addr = re.sub(r'[.,]', '', addr)

    # Standardize hyphenated house number suffixes (123-A -> 123A)
    addr = re.sub(r'(\d+)-([A-Z])\b', r'\1\2', addr)

    # Collapse whitespace
    addr = ' '.join(addr.split())

    # Standardize street types (word boundaries)
    for full, abbr in STREET_TYPES.items():
        addr = re.sub(rf'\b{full}\b', abbr, addr)

    # Standardize directions
    for full, abbr in DIRECTIONS.items():
        addr = re.sub(rf'\b{full}\b', abbr, addr)

    return addr


def _levenshtein_distance(s1: str, s2: str) -> int:
    """Calculate Levenshtein distance between two strings."""
    if len(s1) < len(s2):
        return _levenshtein_distance(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


def _strip_street_type(addr: str) -> str:
    """Remove street type suffix from address."""
    for abbr in STREET_TYPES.values():
        addr = re.sub(rf'\b{abbr}$', '', addr).strip()
    return addr


def match_addresses(addr1: str, addr2: str, threshold: int = 2) -> bool:
    """
    Check if two addresses match (after normalization).

    Matching logic:
    1. Exact match after normalization
    2. Match without street type (123 MAIN == 123 MAIN ST)
    3. Levenshtein distance within threshold (for typos)

    Args:
        addr1: First address
        addr2: Second address
        threshold: Maximum Levenshtein distance for fuzzy match

    Returns:
        True if addresses match, False otherwise
    """
    norm1 = normalize_address(addr1)
    norm2 = normalize_address(addr2)

    # Empty addresses don't match
    if not norm1 or not norm2:
        return False

    # Exact match
    if norm1 == norm2:
        return True

    # Match without street type
    stripped1 = _strip_street_type(norm1)
    stripped2 = _strip_street_type(norm2)
    if stripped1 == stripped2:
        return True

    # Fuzzy match with Levenshtein
    if _levenshtein_distance(norm1, norm2) <= threshold:
        return True

    return False
