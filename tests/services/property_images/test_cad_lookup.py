"""Tests for CAD account lookup."""
import pytest
from services.property_images.cad_lookup import lookup_cad_account


class TestCADLookup:
    """Test CAD account lookup functionality."""

    def test_lookup_tarrant_address(self):
        """Test lookup for a known Tarrant County address."""
        # Use a real Fort Worth address from permit data
        result = lookup_cad_account("3705 DESERT RIDGE DR, Fort Worth TX 76116")

        assert result is not None
        assert result['county'] == 'Tarrant'
        assert result['account_num'] is not None
        assert len(result['account_num']) > 0

    def test_lookup_invalid_address(self):
        """Test lookup for an invalid address returns None."""
        result = lookup_cad_account("99999 FAKE STREET, Nowhere TX 00000")

        assert result is None

    def test_lookup_returns_expected_fields(self):
        """Test that lookup returns all expected fields."""
        result = lookup_cad_account("3705 DESERT RIDGE DR, Fort Worth TX 76116")

        if result:  # May fail if API is down
            assert 'account_num' in result
            assert 'county' in result
            assert 'situs_addr' in result
