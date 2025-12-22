"""Test The Colony address enrichment via Denton CAD."""
import pytest


def test_query_denton_by_street_name():
    """Can query Denton CAD by street name only."""
    from scripts.enrich_cad import query_denton_by_street

    results = query_denton_by_street("BAKER", city_filter="THE COLONY", limit=10)

    assert isinstance(results, list)
    # Should return property records with full addresses
    for r in results:
        assert 'situs_addr' in r or 'address' in r


def test_query_returns_full_addresses():
    """Results should have full addresses (number + street)."""
    from scripts.enrich_cad import query_denton_by_street

    results = query_denton_by_street("BAKER", city_filter="THE COLONY", limit=5)

    # At least some results should have house numbers
    addresses_with_numbers = [
        r for r in results
        if r.get('situs_addr', '').strip() and
           r['situs_addr'][0].isdigit()
    ]
    assert len(addresses_with_numbers) > 0, "No full addresses found"
