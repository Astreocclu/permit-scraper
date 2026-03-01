"""Tests for Accela fast scraper configuration and migration handoffs."""


def test_grand_prairie_is_migrated_to_css_handoff():
    """Grand Prairie should route to Citizen Self Service, not Accela."""
    from scrapers.accela_fast import ACCELA_CITIES, MIGRATED_CITY_HANDOFFS

    assert 'grand_prairie' not in ACCELA_CITIES
    handoff = MIGRATED_CITY_HANDOFFS.get('grand_prairie')
    assert handoff is not None
    assert handoff['script'] == 'citizen_self_service.py'
    assert handoff['city_arg'] == 'grand_prairie'
