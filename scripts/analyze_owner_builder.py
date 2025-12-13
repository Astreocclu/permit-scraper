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


def normalize_name(name: str | None) -> str:
    """Normalize a name for comparison: lowercase, strip, remove punctuation."""
    if not name:
        return ""
    # Lowercase, remove non-alphanumeric except spaces
    cleaned = re.sub(r'[^a-z0-9 ]', '', name.lower())
    # Collapse multiple spaces
    return ' '.join(cleaned.split())


def is_contractor_entity(name: str) -> bool:
    """Placeholder - will implement next."""
    pass


def names_match(applicant: str, owner: str) -> tuple[bool, str]:
    """Placeholder - will implement next."""
    pass
