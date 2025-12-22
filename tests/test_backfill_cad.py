"""Tests for CAD enrichment backfill."""
import pytest


class TestBuildFullAddress:
    """Test address construction from permit data."""

    def test_basic_address(self):
        from scripts.backfill_cad_enrichment import build_full_address

        result = build_full_address("14108 SANTA ANN ST", "frisco")
        assert result == "14108 SANTA ANN ST, Frisco, TX"

    def test_uppercase_city(self):
        from scripts.backfill_cad_enrichment import build_full_address

        result = build_full_address("123 MAIN DR", "MCKINNEY")
        assert result == "123 MAIN DR, Mckinney, TX"

    def test_lowercase_city(self):
        from scripts.backfill_cad_enrichment import build_full_address

        result = build_full_address("456 OAK LN", "allen")
        assert result == "456 OAK LN, Allen, TX"

    def test_multi_word_city(self):
        from scripts.backfill_cad_enrichment import build_full_address

        result = build_full_address("789 ELM ST", "fort worth")
        assert result == "789 ELM ST, Fort Worth, TX"

    def test_empty_address_returns_none(self):
        from scripts.backfill_cad_enrichment import build_full_address

        assert build_full_address("", "frisco") is None
        assert build_full_address(None, "frisco") is None

    def test_empty_city_returns_none(self):
        from scripts.backfill_cad_enrichment import build_full_address

        assert build_full_address("123 MAIN ST", "") is None
        assert build_full_address("123 MAIN ST", None) is None

    def test_strips_whitespace(self):
        from scripts.backfill_cad_enrichment import build_full_address

        result = build_full_address("  123 MAIN ST  ", "  frisco  ")
        assert result == "123 MAIN ST, Frisco, TX"


class TestGetCountyForCity:
    """Test city to county mapping."""

    def test_collin_cities(self):
        from scripts.backfill_cad_enrichment import get_county_for_city

        assert get_county_for_city("frisco") == "collin"
        assert get_county_for_city("mckinney") == "collin"
        assert get_county_for_city("allen") == "collin"
        assert get_county_for_city("plano") == "collin"
        assert get_county_for_city("prosper") == "collin"

    def test_tarrant_cities(self):
        from scripts.backfill_cad_enrichment import get_county_for_city

        assert get_county_for_city("fort worth") == "tarrant"
        assert get_county_for_city("arlington") == "tarrant"
        assert get_county_for_city("southlake") == "tarrant"
        assert get_county_for_city("keller") == "tarrant"

    def test_dallas_cities(self):
        from scripts.backfill_cad_enrichment import get_county_for_city

        assert get_county_for_city("dallas") == "dallas"
        assert get_county_for_city("irving") == "dallas"
        assert get_county_for_city("grand prairie") == "dallas"
        assert get_county_for_city("mesquite") == "dallas"

    def test_denton_cities(self):
        from scripts.backfill_cad_enrichment import get_county_for_city

        assert get_county_for_city("denton") == "denton"
        assert get_county_for_city("flower mound") == "denton"
        assert get_county_for_city("lewisville") == "denton"

    def test_case_insensitive(self):
        from scripts.backfill_cad_enrichment import get_county_for_city

        assert get_county_for_city("FRISCO") == "collin"
        assert get_county_for_city("Frisco") == "collin"
        assert get_county_for_city("FrIsCo") == "collin"

    def test_unknown_city_returns_none(self):
        from scripts.backfill_cad_enrichment import get_county_for_city

        assert get_county_for_city("unknown_city") is None
        assert get_county_for_city("") is None
        assert get_county_for_city(None) is None
