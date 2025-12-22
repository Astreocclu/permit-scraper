# tests/test_cad_delta_engine.py
"""Tests for CAD Delta Engine."""

import pytest
from scrapers.cad_delta_engine import is_new_construction, CADConfig


class TestNewConstructionDetection:
    """Test new construction detection logic."""

    def test_dcad_flag(self):
        """DCAD NEW_CONSTRUCTION flag should be authoritative."""
        record = {'new_construction': 'Y', 'year_built': 2010}
        assert is_new_construction(record, 2024) is True

    def test_recent_year_built(self):
        """Year built in last 2 years should count."""
        record = {'year_built': 2024}
        assert is_new_construction(record, 2024) is True

        record = {'year_built': 2023}
        assert is_new_construction(record, 2024) is True

    def test_old_year_built(self):
        """Old year built without flag should not count."""
        record = {'year_built': 2010}
        assert is_new_construction(record, 2024) is False

    def test_improvement_value_increase(self):
        """Large improvement value increase suggests new construction."""
        record = {'improvement_value': 250000, 'prior_improvement_value': 0}
        assert is_new_construction(record, 2024) is True

    def test_no_indicators(self):
        """Record with no new construction indicators should return False."""
        record = {'year_built': 2010, 'improvement_value': 100000, 'prior_improvement_value': 100000}
        assert is_new_construction(record, 2024) is False
