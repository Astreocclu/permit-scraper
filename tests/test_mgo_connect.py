"""Tests for MGO Connect scraper phased fallback."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


class TestMGOPhasedFallback:
    """Test the phased fallback strategy."""

    @pytest.mark.asyncio
    async def test_scrape_orchestrator_tries_headless_first(self):
        """Orchestrator should try headless mode before headed."""
        from scrapers.mgo_connect import scrape_orchestrator

        with patch('scrapers.mgo_connect.run_scraper_session') as mock_session:
            mock_session.return_value = [{'permit_id': '123'}]

            # Should call with headless=True first
            await scrape_orchestrator('Irving', 5)

            first_call = mock_session.call_args_list[0]
            assert first_call[1].get('headless', first_call[0][2] if len(first_call[0]) > 2 else True) == True

    @pytest.mark.asyncio
    async def test_scrape_orchestrator_falls_back_to_headed(self):
        """If headless fails, should try headed mode."""
        from scrapers.mgo_connect import scrape_orchestrator

        with patch('scrapers.mgo_connect.run_scraper_session') as mock_session:
            # First call (headless) returns None (failure), second returns data
            mock_session.side_effect = [None, [{'permit_id': '123'}]]

            await scrape_orchestrator('Irving', 5)

            assert mock_session.call_count == 2
            # Second call should be headed (headless=False)
            second_call = mock_session.call_args_list[1]
            # Check both positional and keyword argument forms
            if len(second_call[0]) > 2:
                assert second_call[0][2] == False  # headless parameter (positional)
            else:
                assert second_call[1]['headless'] == False  # headless parameter (keyword)


class TestStealthImport:
    """Test that stealth is properly imported and used."""

    def test_stealth_import_graceful_fallback(self):
        """Should not crash if playwright-stealth not installed."""
        # This tests the try/except import pattern
        import scrapers.mgo_connect as mgo
        # Should have stealth_async attribute (either function or None)
        assert hasattr(mgo, 'stealth_async') or 'stealth_async' in dir(mgo)
