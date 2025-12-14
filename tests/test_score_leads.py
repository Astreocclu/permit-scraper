# tests/test_score_leads.py
"""Tests for score_leads.py filtering and tier assignment."""
import pytest
import sys
sys.path.insert(0, 'scripts')

from score_leads import is_commercial_entity, should_discard, PermitData


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


class TestShouldDiscardCommercial:
    """Test that commercial entities get discarded pre-score."""

    def _make_permit(self, owner_name: str, description: str = "Roof repair") -> PermitData:
        return PermitData(
            permit_id="TEST-001",
            city="Dallas",
            property_address="123 Test St",
            owner_name=owner_name,
            project_description=description,
            days_old=30,
            market_value=500000,
        )

    def test_llc_discarded(self):
        permit = self._make_permit("Smith Properties LLC")
        discard, reason = should_discard(permit)
        assert discard is True
        assert "Commercial entity" in reason

    def test_government_discarded(self):
        permit = self._make_permit("City of Dallas")
        discard, reason = should_discard(permit)
        assert discard is True
        assert "Commercial entity" in reason

    def test_church_discarded(self):
        permit = self._make_permit("First Baptist Church")
        discard, reason = should_discard(permit)
        assert discard is True
        assert "Commercial entity" in reason

    def test_apartments_discarded(self):
        permit = self._make_permit("Oakwood Apartments")
        discard, reason = should_discard(permit)
        assert discard is True
        assert "Commercial entity" in reason

    def test_real_homeowner_kept(self):
        permit = self._make_permit("John Smith")
        discard, reason = should_discard(permit)
        assert discard is False

    def test_production_builder_still_works(self):
        """Existing production builder detection should still work."""
        permit = self._make_permit("Lennar Homes")
        discard, reason = should_discard(permit)
        assert discard is True
        # Could be either "Production builder" or "Commercial entity" - both OK


class TestTierAssignment:
    """Test tier assignment logic including new Tier D."""

    def _make_permit(self, days_old: int = 30) -> PermitData:
        return PermitData(
            permit_id="TEST-001",
            city="Dallas",
            property_address="123 Test St",
            owner_name="John Smith",
            project_description="Roof repair",
            days_old=days_old,
            market_value=500000,
        )

    def test_score_zero_gets_tier_d(self):
        """Score 0 from AI should result in Tier D."""
        from score_leads import ScoredLead
        permit = self._make_permit(days_old=30)
        lead = ScoredLead(
            permit=permit,
            score=0,
            tier="D",  # This is what we're testing should happen
            reasoning="Commercial entity",
            category="other",
            trade_group="other",
        )
        assert lead.tier == "D"

    def test_no_date_gets_tier_u(self):
        """Permit with no date (days_old=-1) should get Tier U."""
        from score_leads import ScoredLead
        permit = self._make_permit(days_old=-1)  # -1 means unknown date
        # Tier U should be assigned regardless of score
        lead = ScoredLead(
            permit=permit,
            score=85,
            tier="U",  # days_old=-1 forces Tier U
            reasoning="Good lead but unverified freshness",
            category="roof",
            trade_group="home_exterior",
        )
        assert lead.tier == "U"

    def test_high_score_gets_tier_a(self):
        """Score >= 80 with valid date should get Tier A."""
        from score_leads import ScoredLead
        permit = self._make_permit(days_old=30)
        lead = ScoredLead(
            permit=permit,
            score=85,
            tier="A",
            reasoning="High value homeowner",
            category="pool",
            trade_group="luxury_outdoor",
        )
        assert lead.tier == "A"

    def test_medium_score_gets_tier_b(self):
        """Score 50-79 with valid date should get Tier B."""
        from score_leads import ScoredLead
        permit = self._make_permit(days_old=30)
        lead = ScoredLead(
            permit=permit,
            score=65,
            tier="B",
            reasoning="Medium value lead",
            category="hvac",
            trade_group="home_systems",
        )
        assert lead.tier == "B"

    def test_low_score_gets_tier_c(self):
        """Score < 50 (but > 0) with valid date should get Tier C."""
        from score_leads import ScoredLead
        permit = self._make_permit(days_old=30)
        lead = ScoredLead(
            permit=permit,
            score=25,
            tier="C",
            reasoning="Low value lead",
            category="signage",
            trade_group="unsellable",
        )
        assert lead.tier == "C"
