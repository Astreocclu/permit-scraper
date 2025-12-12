# tests/test_filters.py
import pytest
from scrapers.filters import filter_residential_permits

def test_filter_keeps_residential_permits():
    permits = [
        {'type': 'Residential Remodel', 'address': '123 Oak St'},
        {'type': 'Residential New Construction', 'address': '456 Elm St'},
        {'type': 'Pool/Spa', 'address': '789 Pine St'},
    ]
    result = filter_residential_permits(permits)
    assert len(result) == 3
    assert all('Residential' in p['type'] or 'Pool' in p['type'] for p in result)

def test_filter_excludes_commercial_permits():
    permits = [
        {'type': 'Commercial New Building', 'address': '100 Main St'},
        {'type': 'Commercial Electrical', 'address': '200 Business Blvd'},
        {'type': 'Business Sign', 'address': '300 Corp Dr'},
    ]
    result = filter_residential_permits(permits)
    assert len(result) == 0

def test_filter_mixed_permits():
    permits = [
        {'type': 'Residential Remodel', 'address': '123 Oak St'},
        {'type': 'Commercial New Building', 'address': '100 Main St'},
        {'type': 'Roof Replacement', 'address': '456 Elm St'},
        {'type': 'Certificate of Occupancy', 'address': '789 Pine St'},
    ]
    result = filter_residential_permits(permits)
    assert len(result) == 2
    types = [p['type'] for p in result]
    assert 'Residential Remodel' in types
    assert 'Roof Replacement' in types

def test_filter_handles_missing_type():
    permits = [
        {'address': '123 Oak St'},  # No type field
        {'type': '', 'address': '456 Elm St'},  # Empty type
    ]
    result = filter_residential_permits(permits)
    assert len(result) == 0  # Conservative: exclude if we can't classify
