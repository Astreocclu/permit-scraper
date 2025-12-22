"""Tests for eTRAKiT city configurations."""
import re
import pytest

def test_the_colony_permit_format():
    """The Colony uses MMYY-NNNN format (e.g., 0701-4211)."""
    from scrapers.etrakit import ETRAKIT_CITIES

    config = ETRAKIT_CITIES.get('the_colony')
    assert config is not None, "the_colony not in ETRAKIT_CITIES"

    # Real permit numbers from The Colony portal (MMYY-NNNN format)
    real_permits = ['0701-4211', '0708-0263', '0709-0222', '0711-0088']

    pattern = re.compile(config['permit_regex'])
    for permit in real_permits:
        assert pattern.match(permit), f"Regex should match {permit}"

    # Should NOT match old B25 format
    assert not pattern.match('B25-00001'), "Should not match B25 format"

def test_the_colony_has_letter_prefixes():
    """The Colony should search for B, P, E prefixes (Building, Plumbing, Electrical)."""
    from scrapers.etrakit import ETRAKIT_CITIES

    config = ETRAKIT_CITIES.get('the_colony')
    assert 'B' in config['prefixes'], "The Colony must have B prefix"
    assert 'B25' not in config['prefixes'], "The Colony should NOT have B25 prefix"
