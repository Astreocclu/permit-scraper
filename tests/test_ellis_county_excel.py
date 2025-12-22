# tests/test_ellis_county_excel.py
"""Tests for Ellis County Excel permit scraper."""

import pytest
from scrapers.ellis_county_excel import detect_column_mapping


class TestColumnMapping:
    """Test dynamic column detection."""

    def test_finds_permit_number_column(self):
        """Should find permit number column by various names."""
        headers = ['Date', 'Permit #', 'Address', 'Type']
        mapping = detect_column_mapping(headers)
        assert mapping['permit_id'] == 1  # Index of 'Permit #'

    def test_finds_address_column(self):
        """Should find address column by various names."""
        headers = ['Permit', 'Location', 'Issued']
        mapping = detect_column_mapping(headers)
        assert mapping['address'] == 1  # 'Location' maps to address

    def test_finds_permit_number_variations(self):
        """Should handle various permit number column names."""
        for name in ['permit #', 'permit number', 'permit no', 'permit id']:
            headers = ['Date', name, 'Address']
            mapping = detect_column_mapping(headers)
            assert 'permit_id' in mapping, f"Failed to find permit_id for '{name}'"

    def test_finds_address_variations(self):
        """Should handle various address column names."""
        for name in ['address', 'location', 'property address', 'site address']:
            headers = ['Permit', name, 'Date']
            mapping = detect_column_mapping(headers)
            assert 'address' in mapping, f"Failed to find address for '{name}'"
