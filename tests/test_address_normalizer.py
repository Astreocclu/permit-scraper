"""Tests for address normalization utility."""

import pytest
from scrapers.utils.address_normalizer import normalize_address, match_addresses


class TestNormalizeAddress:
    """Test address normalization."""

    def test_basic_normalization(self):
        """Street type abbreviations should be standardized."""
        assert normalize_address("123 Main Street") == "123 MAIN ST"
        assert normalize_address("456 Oak Avenue") == "456 OAK AVE"
        assert normalize_address("789 First Boulevard") == "789 FIRST BLVD"

    def test_case_insensitive(self):
        """Should convert to uppercase."""
        assert normalize_address("123 main st") == "123 MAIN ST"
        assert normalize_address("123 MAIN ST") == "123 MAIN ST"

    def test_extra_whitespace(self):
        """Should collapse multiple spaces."""
        assert normalize_address("123   Main    St") == "123 MAIN ST"
        assert normalize_address("  123 Main St  ") == "123 MAIN ST"

    def test_punctuation_removal(self):
        """Should remove periods and commas."""
        assert normalize_address("123 Main St.") == "123 MAIN ST"
        assert normalize_address("123 Main St, Apt 4") == "123 MAIN ST APT 4"

    def test_unit_standardization(self):
        """Should standardize apartment/unit designations."""
        assert normalize_address("123 Main St Unit 4") == "123 MAIN ST UNIT 4"
        assert normalize_address("123 Main St #4") == "123 MAIN ST UNIT 4"
        assert normalize_address("123 Main St Apt 4") == "123 MAIN ST APT 4"

    def test_none_and_empty(self):
        """Should handle None and empty strings."""
        assert normalize_address(None) == ""
        assert normalize_address("") == ""
        assert normalize_address("   ") == ""

    def test_house_number_suffix(self):
        """Should handle hyphenated unit suffixes."""
        assert normalize_address("123-A Main St") == "123A MAIN ST"
        assert normalize_address("123-B Oak Ave") == "123B OAK AVE"


class TestMatchAddresses:
    """Test address matching logic."""

    def test_exact_match(self):
        """Identical normalized addresses should match."""
        assert match_addresses("123 Main St", "123 MAIN STREET") is True

    def test_with_without_street_type(self):
        """Should match with/without street type."""
        assert match_addresses("123 Main", "123 MAIN ST") is True

    def test_no_match(self):
        """Different addresses should not match."""
        assert match_addresses("123 Main St", "456 Main St") is False

    def test_close_match_threshold(self):
        """Minor typos within threshold should match."""
        assert match_addresses("123 Main St", "123 Main Str", threshold=2) is True
        assert match_addresses("123 Main St", "999 Other Rd", threshold=2) is False
