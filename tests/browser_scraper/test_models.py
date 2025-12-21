import pytest
from services.browser_scraper.models import ScrapeContext

def test_scrape_context_creation():
    """ScrapeContext can be created with all required fields."""
    ctx = ScrapeContext(
        city="Fort Worth",
        final_result='{"permit": "123"}',
        is_done=True,
        is_successful=True,
        errors=[],
        urls=["https://permits.fortworthtexas.gov"],
        actions=["click", "input_text", "extract"],
        screenshots=[],  # Empty list, no screenshots
    )
    assert ctx.city == "Fort Worth"
    assert ctx.is_successful == True
    assert len(ctx.urls) == 1

def test_scrape_context_needs_review():
    """needs_review returns True when is_successful is False."""
    ctx = ScrapeContext(
        city="Prosper",
        final_result=None,
        is_done=True,
        is_successful=False,
        errors=["Date picker failed"],
        urls=["https://permits.prospertx.gov"],
        actions=["click", "input_text"],
        screenshots=["base64data..."],
    )
    assert ctx.needs_review() == True

def test_scrape_context_to_dict():
    """to_dict returns serializable dictionary."""
    ctx = ScrapeContext(
        city="Dallas",
        final_result='[{"permit": "456"}]',
        is_done=True,
        is_successful=True,
        errors=[],
        urls=["https://permits.dallas.gov"],
        actions=["navigate", "extract"],
        screenshots=[],
    )
    d = ctx.to_dict()
    assert d["city"] == "Dallas"
    assert isinstance(d, dict)
