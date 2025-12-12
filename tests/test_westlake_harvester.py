"""Tests for Westlake Address Harvester."""
import pytest
from unittest.mock import patch, MagicMock
import json


class TestRecursiveSearch:
    """Test the recursive A-Z search algorithm."""

    def test_recursive_search_single_letter(self):
        """Single letter search should query API."""
        from scrapers.westlake_harvester import recursive_search

        all_addresses = {}

        with patch('scrapers.westlake_harvester.search_addresses') as mock_search:
            mock_search.return_value = [
                {'address': '100 Apple St', 'location_id': '1'},
                {'address': '200 Acorn Ln', 'location_id': '2'},
            ]

            recursive_search('A', all_addresses, depth=0)

            mock_search.assert_called_once_with('A')
            assert len(all_addresses) == 2
            assert '100 Apple St' in all_addresses

    def test_recursive_search_drills_down_on_limit(self):
        """When results hit limit (50+), should recurse with next character."""
        from scrapers.westlake_harvester import recursive_search

        all_addresses = {}

        with patch('scrapers.westlake_harvester.search_addresses') as mock_search:
            # First call returns 50 results (hit limit)
            first_results = [{'address': f'{i} A St', 'location_id': str(i)} for i in range(50)]
            # Subsequent calls return fewer
            subsequent = [{'address': '1 AA St', 'location_id': '100'}]

            mock_search.side_effect = [first_results] + [subsequent] * 36  # A-Z + 0-9

            recursive_search('A', all_addresses, depth=0)

            # Should have drilled down
            assert mock_search.call_count > 1

    def test_recursive_search_respects_max_depth(self):
        """Should not recurse beyond max depth."""
        from scrapers.westlake_harvester import recursive_search

        all_addresses = {}

        with patch('scrapers.westlake_harvester.search_addresses') as mock_search:
            mock_search.return_value = []

            recursive_search('AAAA', all_addresses, depth=4)

            # Should not call API at depth > 3
            mock_search.assert_not_called()


class TestRetryLogic:
    """Test urllib3 retry/backoff integration."""

    def test_session_has_retry_adapter(self):
        """Session should have retry adapter configured."""
        from scrapers.westlake_harvester import get_session

        session = get_session()

        # Check HTTPS adapter exists
        adapter = session.get_adapter('https://')
        assert adapter is not None
        # Should have retry config
        assert adapter.max_retries.total >= 3


class TestCheckpointing:
    """Test progress saving for resumability."""

    def test_save_addresses_creates_file(self, tmp_path):
        """Should save addresses to JSON file."""
        from scrapers.westlake_harvester import save_addresses

        addresses = {
            '100 Test St': {'address': '100 Test St', 'location_id': '1'}
        }

        with patch('scrapers.westlake_harvester.OUTPUT_FILE', tmp_path / 'addresses.json'):
            save_addresses(addresses)

            saved = json.loads((tmp_path / 'addresses.json').read_text())
            assert len(saved) == 1
            assert saved[0]['address'] == '100 Test St'
