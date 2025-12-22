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


def test_enrich_colony_permit():
    """Can enrich a Colony permit with partial address - integration test."""
    from scripts.enrich_colony_addresses import enrich_permit

    permit = {
        'permit_id': '0701-4211',
        'address': '',
        'raw_cells': ['0701-4211', 'BAKER DR', 'DKB_00558883']
    }

    enriched = enrich_permit(permit)

    # BAKER DR has multiple addresses in The Colony, so should be marked ambiguous
    # This test now validates that we DON'T guess when multiple candidates exist
    if enriched.get('address_source') == 'DENTON_CAD_AMBIGUOUS':
        # Multiple addresses found - should NOT assign a specific one
        assert enriched['address'] == '', "Should not guess when multiple candidates"
        assert isinstance(enriched.get('address_candidates'), list)
        assert len(enriched['address_candidates']) > 1
    elif enriched.get('address_source') == 'DENTON_CAD_EXACT':
        # Only one address found - safe to assign
        assert enriched['address'], "Address should be enriched"
        assert enriched['address'][0].isdigit(), "Should start with house number"
        assert 'BAKER' in enriched['address'].upper()
    else:
        # No addresses found
        assert enriched['address'] == ''


def test_enrich_handles_multiple_candidates():
    """Should not assign address when multiple candidates exist."""
    from scripts.enrich_colony_addresses import enrich_permit

    permit = {
        'permit_id': '0701-4211',
        'address': '',
        'raw_cells': ['0701-4211', 'BAKER DR', 'DKB_00558883']
    }

    # Mock lookup with multiple addresses
    mock_lookup = {
        'BAKER': ['100 BAKER DR', '200 BAKER DR', '300 BAKER DR']
    }

    enriched = enrich_permit(permit, lookup=mock_lookup)

    # Should NOT assign a specific address (too ambiguous)
    assert enriched['address'] == '', "Should not guess when multiple candidates"
    assert enriched.get('address_source') == 'DENTON_CAD_AMBIGUOUS'
    assert len(enriched.get('address_candidates', [])) == 3


def test_enrich_assigns_single_candidate():
    """Should assign address when only one candidate exists."""
    from scripts.enrich_colony_addresses import enrich_permit

    permit = {
        'permit_id': '0701-4211',
        'address': '',
        'raw_cells': ['0701-4211', 'UNIQUE ST', 'DKB_00558883']
    }

    # Mock lookup with single address
    mock_lookup = {
        'UNIQUE': ['123 UNIQUE ST']
    }

    enriched = enrich_permit(permit, lookup=mock_lookup)

    # Should assign the single candidate
    assert enriched['address'] == '123 UNIQUE ST'
    assert enriched.get('address_source') == 'DENTON_CAD_EXACT'
