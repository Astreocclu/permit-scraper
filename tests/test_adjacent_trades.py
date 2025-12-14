# tests/test_adjacent_trades.py
"""Tests for adjacent_trades.py routing and scoring."""
import pytest
import sys
sys.path.insert(0, 'scripts')


class TestAdjacentTradeKeywords:
    """Test keyword detection for adjacent trade routing."""

    def test_electrical_panel_routed(self):
        from adjacent_trades import is_adjacent_electrical
        assert is_adjacent_electrical("electrical panel upgrade") is True
        assert is_adjacent_electrical("200 amp panel upgrade") is True
        assert is_adjacent_electrical("service upgrade") is True
        assert is_adjacent_electrical("panel replacement") is True

    def test_hvac_replacement_routed(self):
        from adjacent_trades import is_adjacent_hvac
        assert is_adjacent_hvac("hvac replacement") is True
        assert is_adjacent_hvac("ac replacement") is True
        assert is_adjacent_hvac("furnace replacement") is True
        assert is_adjacent_hvac("new hvac system") is True

    def test_water_heater_not_routed(self):
        """Water heater has weak adjacencies - should NOT be routed."""
        from adjacent_trades import is_adjacent_electrical, is_adjacent_hvac
        assert is_adjacent_electrical("water heater replacement") is False
        assert is_adjacent_hvac("water heater replacement") is False

    def test_sewer_not_routed(self):
        """Sewer repair has weak adjacencies - should NOT be routed."""
        from adjacent_trades import is_adjacent_electrical, is_adjacent_hvac
        assert is_adjacent_electrical("sewer repair") is False
        assert is_adjacent_hvac("sewer repair") is False


class TestAdjacentScoring:
    """Test freshness-weighted scoring for adjacent leads."""

    def test_fresh_permit_scores_higher(self):
        from adjacent_trades import score_adjacent_lead
        # 3 days old, $300k property
        fresh_score = score_adjacent_lead(days_old=3, market_value=300000)
        # 30 days old, $300k property
        stale_score = score_adjacent_lead(days_old=30, market_value=300000)
        assert fresh_score > stale_score

    def test_property_value_less_impact(self):
        from adjacent_trades import score_adjacent_lead
        # Same freshness, different values
        low_value = score_adjacent_lead(days_old=7, market_value=200000)
        high_value = score_adjacent_lead(days_old=7, market_value=800000)
        # High value should score higher, but not by much
        assert high_value > low_value
        assert high_value - low_value < 15  # Property value impact capped

    def test_score_capped_at_60(self):
        from adjacent_trades import score_adjacent_lead
        # Best possible lead: 1 day old, $2M property
        score = score_adjacent_lead(days_old=1, market_value=2000000)
        assert score <= 60

    def test_very_old_scores_zero(self):
        from adjacent_trades import score_adjacent_lead
        # 45+ days is too stale for adjacent trades
        score = score_adjacent_lead(days_old=45, market_value=500000)
        assert score == 0
