# tests/browser_scraper/test_permit_tasks.py

def test_burleson_uses_mygov_template():
    """Burleson should use MyGov, not eTRAKiT (which 404s)."""
    from services.browser_scraper.permit_tasks import CITY_TASKS

    task = CITY_TASKS.get('burleson')
    assert task is not None, "burleson not in CITY_TASKS"
    assert 'mygov' in task.lower() or 'public.mygov.us/burleson_tx' in task, \
        f"Burleson should use MyGov portal, got: {task[:100]}"


def test_southlake_has_date_sort_instruction():
    """Southlake task must include date sorting to work around portal bug."""
    from services.browser_scraper.permit_tasks import get_task_for_city

    task = get_task_for_city("southlake", mode="bulk", start_date="01/01/2025", end_date="12/21/2025")

    assert 'Issued Date' in task or 'sort' in task.lower(), \
        "Southlake bulk task must instruct agent to sort by date"
    assert 'descending' in task.lower() or 'newest' in task.lower(), \
        "Southlake must sort newest first"
