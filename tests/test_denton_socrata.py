# tests/test_denton_socrata.py
"""Tests for Denton City Socrata permit scraper."""

import pytest
from scrapers.denton_socrata import transform_permit, SOCRATA_ENDPOINT


class TestTransformPermit:
    """Test permit transformation."""

    def test_basic_transform(self):
        """Should transform Socrata record to standard format."""
        raw = {
            'permit_number': 'BP-2024-001',
            'address': '123 OAK ST',
            'permit_type': 'New Residential',
            'issue_date': '2024-12-01T00:00:00.000',
            'valuation': '350000',
            'contractor': 'ABC Builders'
        }
        result = transform_permit(raw)

        assert result['permit_id'] == 'BP-2024-001'
        assert result['address'] == '123 OAK ST'
        assert result['city'] == 'Denton'
        assert result['type'] == 'New Residential'
        assert result['date'] == '2024-12-01'
        assert result['value'] == '350000'

    def test_handles_missing_fields(self):
        """Should handle records with missing optional fields."""
        raw = {
            'permit_number': 'BP-2024-002',
            'address': '456 MAIN AVE',
        }
        result = transform_permit(raw)

        assert result['permit_id'] == 'BP-2024-002'
        assert result['date'] is None or result['date'] == ''
        assert result['value'] is None or result['value'] == ''


class TestSocrataEndpoint:
    """Test Socrata configuration."""

    def test_endpoint_configured(self):
        """Should have valid Socrata endpoint."""
        assert 'data.cityofdenton.com' in SOCRATA_ENDPOINT or 'data.texas.gov' in SOCRATA_ENDPOINT
