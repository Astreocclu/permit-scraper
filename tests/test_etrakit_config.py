"""Tests for eTRAKiT city configurations."""
import re
import pytest

def test_the_colony_permit_format():
    """The Colony uses AEC##### format, not B25-#####."""
    from scrapers.etrakit import ETRAKIT_CITIES

    config = ETRAKIT_CITIES.get('the_colony')
    assert config is not None, "the_colony not in ETRAKIT_CITIES"

    # Real permit numbers from The Colony portal
    real_permits = ['AEC10007', 'AEC10008', 'AEC10023', 'AEC11108']

    pattern = re.compile(config['permit_regex'])
    for permit in real_permits:
        assert pattern.match(permit), f"Regex should match {permit}"

    # Should NOT match old B25 format
    assert not pattern.match('B25-00001'), "Should not match B25 format"

def test_the_colony_has_aec_prefix():
    """The Colony should search for AEC prefix, not B25."""
    from scrapers.etrakit import ETRAKIT_CITIES

    config = ETRAKIT_CITIES.get('the_colony')
    assert 'AEC' in config['prefixes'], "The Colony must have AEC prefix"
    assert 'B25' not in config['prefixes'], "The Colony should NOT have B25 prefix"
