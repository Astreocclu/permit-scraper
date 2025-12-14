# tests/test_score_leads.py
"""Tests for score_leads.py filtering and tier assignment."""
import pytest
import sys
sys.path.insert(0, 'scripts')

from score_leads import is_commercial_entity


class TestIsCommercialEntity:
    """Test is_commercial_entity function for pre-score filtering."""

    def test_llc_detected(self):
        assert is_commercial_entity("Smith Family LLC") is True
        assert is_commercial_entity("ACME PROPERTIES LLC") is True

    def test_inc_corp_detected(self):
        assert is_commercial_entity("Jones Holdings Inc") is True
        assert is_commercial_entity("ABC Corp") is True
        assert is_commercial_entity("Mega Development Corp") is True

    def test_government_detected(self):
        assert is_commercial_entity("City of Dallas") is True
        assert is_commercial_entity("CITY OF FORT WORTH") is True
        assert is_commercial_entity("Tarrant County") is True
        assert is_commercial_entity("Dallas ISD") is True
        assert is_commercial_entity("Plano Independent School District") is True

    def test_institutional_detected(self):
        assert is_commercial_entity("First Baptist Church") is True
        assert is_commercial_entity("Methodist Hospital") is True
        assert is_commercial_entity("Texas A&M University") is True
        assert is_commercial_entity("Habitat for Humanity Foundation") is True

    def test_multifamily_detected(self):
        assert is_commercial_entity("Oak Park Apartments") is True
        assert is_commercial_entity("Sunrise Property Management") is True
        assert is_commercial_entity("Multifamily Residential Services") is True

    def test_production_builder_detected(self):
        assert is_commercial_entity("Lennar Homes") is True
        assert is_commercial_entity("DR Horton") is True
        assert is_commercial_entity("KB Home") is True
        assert is_commercial_entity("Toll Brothers") is True
        assert is_commercial_entity("David Weekley Homes") is True
        assert is_commercial_entity("Highland Homes") is True
        assert is_commercial_entity("Chesmar Homes") is True
        assert is_commercial_entity("History Maker Homes") is True

    def test_real_person_allowed(self):
        """Real homeowner names should NOT be filtered."""
        assert is_commercial_entity("John Smith") is False
        assert is_commercial_entity("MARIA GARCIA") is False
        assert is_commercial_entity("Robert Johnson Jr") is False
        assert is_commercial_entity("The Williams Family") is False

    def test_edge_cases(self):
        """Edge cases that look commercial but aren't."""
        # "Inc" inside a word shouldn't trigger
        assert is_commercial_entity("Lincoln Street") is False
        # Common false positive - person with "Corp" in name
        assert is_commercial_entity("James Corpening") is False

    def test_empty_and_none(self):
        assert is_commercial_entity("") is False
        assert is_commercial_entity(None) is False
        assert is_commercial_entity("Unknown") is False
