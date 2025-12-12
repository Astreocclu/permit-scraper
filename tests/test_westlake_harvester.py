"""Tests for Westlake address harvester."""
import pytest
from scrapers.westlake_harvester import (
    parse_api_response,
    RESIDENTIAL_STREETS,
    search_addresses
)


def test_residential_streets_defined():
    """Verify we have target streets configured."""
    assert len(RESIDENTIAL_STREETS) >= 5
    assert 'Vaquero' in ' '.join(RESIDENTIAL_STREETS)


def test_parse_api_response_extracts_addresses():
    """Test parsing API response from getLookupResults."""
    # Actual MyGov API response format
    response = [
        {'address': '2204 Vaquero Club Dr., Westlake, TX 76262', 'location_id': 5493},
        {'address': '2206 Vaquero Club Dr., Westlake, TX 76262', 'location_id': 5492},
    ]

    addresses = parse_api_response(response)

    assert len(addresses) == 2
    assert addresses[0]['address'] == '2204 Vaquero Club Dr., Westlake, TX 76262'
    assert addresses[0]['location_id'] == 5493
    assert addresses[1]['address'] == '2206 Vaquero Club Dr., Westlake, TX 76262'
    assert addresses[1]['location_id'] == 5492


def test_parse_api_response_handles_empty():
    """Handle empty or invalid responses gracefully."""
    assert parse_api_response([]) == []
    assert parse_api_response(None) == []


def test_parse_api_response_handles_malformed():
    """Handle malformed data gracefully."""
    # Missing location_id
    response = [{'address': '123 Main St'}]
    addresses = parse_api_response(response)
    assert len(addresses) == 0  # Skip invalid entries

    # Missing address
    response = [{'location_id': 123}]
    addresses = parse_api_response(response)
    assert len(addresses) == 0  # Skip invalid entries


def test_search_addresses_basic():
    """Test basic address search functionality."""
    # This will make a real API call - use a known street
    results = search_addresses('Vaquero')

    # Should return list of address dicts
    assert isinstance(results, list)

    # Should have at least a few results
    assert len(results) > 0

    # Each result should have address and location_id
    for result in results:
        assert 'address' in result
        assert 'location_id' in result
        assert 'Vaquero' in result['address'] or 'vaquero' in result['address'].lower()


def test_search_addresses_handles_no_results():
    """Handle searches with no results."""
    # Search for something that won't exist
    results = search_addresses('XYZNONEXISTENT9999')
    assert isinstance(results, list)
    assert len(results) == 0
