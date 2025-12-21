# tests/browser_scraper/test_permit_tasks.py

def test_burleson_uses_mygov_template():
    """Burleson should use MyGov, not eTRAKiT (which 404s)."""
    from services.browser_scraper.permit_tasks import CITY_TASKS

    task = CITY_TASKS.get('burleson')
    assert task is not None, "burleson not in CITY_TASKS"
    assert 'mygov' in task.lower() or 'public.mygov.us/burleson_tx' in task, \
        f"Burleson should use MyGov portal, got: {task[:100]}"
