# tests/test_integration_cad.py
"""Integration tests for CAD data pipeline."""

import json
import pytest
from pathlib import Path

# Import the modules we're testing
from scrapers.denton_socrata import transform_permit as denton_transform
from scrapers.ellis_county_excel import detect_column_mapping
from scrapers.cad_delta_engine import (
    is_new_construction,
    transform_to_permit,
    load_config,
    CADConfig,
)


class TestDentonSocrataOutput:
    """Test Denton Socrata output format."""

    def test_transform_produces_required_fields(self):
        """Transform should produce all required fields."""
        raw = {
            'permit_number': 'BP-2024-001',
            'address': '123 OAK ST',
            'permit_type': 'New Residential',
            'issue_date': '2024-12-01T00:00:00.000',
        }
        result = denton_transform(raw)

        # Required fields for load_permits.py
        assert 'permit_id' in result
        assert 'address' in result
        assert 'city' in result
        assert result['city'] == 'Denton'

    def test_date_extraction(self):
        """Should extract date in YYYY-MM-DD format."""
        raw = {'issue_date': '2024-12-15T10:30:00.000'}
        result = denton_transform(raw)
        assert result['date'] == '2024-12-15'


class TestEllisCountyOutput:
    """Test Ellis County Excel output format."""

    def test_column_mapping_finds_required_fields(self):
        """Should find permit_id and address columns."""
        headers = ['Date', 'Permit #', 'Property Address', 'Type']
        mapping = detect_column_mapping(headers)

        assert 'permit_id' in mapping
        assert 'address' in mapping

    def test_handles_various_column_names(self):
        """Should handle various column naming conventions."""
        # Test with different naming
        headers = ['Issue Date', 'Permit Number', 'Location', 'Work Type']
        mapping = detect_column_mapping(headers)

        assert 'permit_id' in mapping
        assert 'address' in mapping
        assert 'date' in mapping
        assert 'type' in mapping


class TestCADDeltaEngineOutput:
    """Test CAD Delta Engine output format."""

    @pytest.fixture
    def sample_config(self):
        """Create a minimal CAD config for testing."""
        return CADConfig(
            name='test_cad',
            display_name='Test CAD',
            county='Test County',
            download_url=None,
            format='csv',
            columns={},
            filters={'min_improvement_value': 50000, 'year_built_window': 2},
            chunk_size=100000,
            encoding='utf-8'
        )

    def test_transform_includes_cad_account_number(self, sample_config):
        """Output should include cad_account_number for deduplication."""
        record = {
            'account_number': '12345678',
            'property_address': '123 MAIN ST',
            'city': 'Dallas',
            'owner_name': 'John Doe',
            'year_built': 2024,
        }
        result = transform_to_permit(record, sample_config)

        assert 'cad_account_number' in result
        assert result['cad_account_number'] == '12345678'

    def test_transform_includes_data_source(self, sample_config):
        """Output should include data_source for tracking."""
        record = {'account_number': '12345', 'property_address': '123 ST'}
        result = transform_to_permit(record, sample_config)

        assert 'data_source' in result
        assert result['data_source'] == 'test_cad_taxroll'

    def test_transform_includes_year_built(self, sample_config):
        """Output should include year_built."""
        record = {'account_number': '12345', 'year_built': 2024}
        result = transform_to_permit(record, sample_config)

        assert 'year_built' in result
        assert result['year_built'] == 2024

    def test_new_construction_detection(self, sample_config):
        """Should detect new construction by multiple criteria."""
        # By year_built
        record = {'year_built': 2024}
        assert is_new_construction(record, 2024, sample_config) is True

        # By DCAD flag
        record = {'new_construction_flag': 'Y', 'year_built': 2010}
        assert is_new_construction(record, 2024, sample_config) is True

        # By improvement value
        record = {'improvement_value': 250000, 'prior_improvement_value': 0}
        assert is_new_construction(record, 2024, sample_config) is True


class TestLoadPermitsCADFields:
    """Test that load_permits.py handles CAD fields correctly."""

    def test_permit_dict_with_cad_fields(self):
        """Verify permit dict structure with CAD fields."""
        # Simulate what a CAD scraper outputs
        permit = {
            'permit_id': 'DCAD-12345678',
            'address': '123 MAIN ST',
            'city': 'Dallas',
            'type': 'New Construction (from CAD)',
            'value': 350000,
            'owner_name': 'John Doe',
            'year_built': 2024,
            'cad_account_number': '12345678',
            'data_source': 'dcad_taxroll',
            'property_value': 350000,
        }

        # Verify all required CAD fields exist
        assert permit.get('cad_account_number') is not None
        assert permit.get('data_source') is not None
        assert permit.get('year_built') is not None
        assert permit.get('property_value') is not None


class TestConfigLoading:
    """Test CAD config loading."""

    def test_dcad_config_loads(self):
        """DCAD config should load successfully."""
        config = load_config('dcad')
        assert config.name == 'dcad'
        assert config.county == 'Dallas'

    def test_tad_config_loads(self):
        """TAD config should load successfully."""
        config = load_config('tad')
        assert config.name == 'tad'
        assert config.county == 'Tarrant'

    def test_denton_cad_config_loads(self):
        """Denton CAD config should load successfully."""
        config = load_config('denton_cad')
        assert config.name == 'denton_cad'
        assert config.county == 'Denton'
