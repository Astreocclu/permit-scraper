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


def test_query_with_empty_street():
    """Empty street name returns empty list."""
    from scripts.enrich_cad import query_denton_by_street
    results = query_denton_by_street("")
    assert results == []


def test_query_with_special_chars():
    """Special characters are handled safely."""
    from scripts.enrich_cad import query_denton_by_street
    # Should not raise, should return empty or valid list (no SQL injection)
    results = query_denton_by_street("'; DROP TABLE--")
    assert isinstance(results, list)


def test_query_with_sql_injection_attempt():
    """SQL injection attempts are sanitized."""
    from scripts.enrich_cad import query_denton_by_street
    # Try injection in both street and city filter
    results = query_denton_by_street(
        "'; DROP TABLE--",
        city_filter="THE COLONY' OR '1'='1"
    )
    assert isinstance(results, list)
    # Should return empty or valid results, not crash or execute malicious SQL
