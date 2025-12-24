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


def test_the_colony_has_detail_extraction():
    """The Colony task must click into detail pages to get full addresses."""
    from services.browser_scraper.permit_tasks import CITY_TASKS

    task = CITY_TASKS.get('the_colony')
    assert task is not None, "the_colony not in CITY_TASKS"

    # Must instruct to click into detail pages
    assert 'detail' in task.lower() or 'click' in task.lower(), \
        "The Colony task must instruct agent to click into detail pages"

    # Must extract full address
    assert 'full address' in task.lower() or 'street number' in task.lower(), \
        "The Colony task must extract full address from detail page"


def test_the_colony_bulk_extracts_multiple_permits():
    """The Colony bulk task must handle multiple permits with detail extraction."""
    from services.browser_scraper.permit_tasks import get_task_for_city

    task = get_task_for_city("the_colony", mode="bulk", start_date="01/01/2025", end_date="12/22/2025")

    # Must handle multiple permits
    assert 'each' in task.lower() or 'all' in task.lower() or 'multiple' in task.lower(), \
        "Bulk task must handle multiple permits"

    # Must return JSON array
    assert 'json' in task.lower(), \
        "Task must return JSON"


def test_the_colony_bulk_mode_uses_bulk_template():
    """The Colony bulk mode should use THE_COLONY_BULK_TASK."""
    from services.browser_scraper.permit_tasks import get_task_for_city

    task = get_task_for_city("the_colony", mode="bulk", start_date="01/01/2025", end_date="12/22/2025")

    # Should have date range
    assert "01/01/2025" in task or "start_date" in task.lower(), \
        "Bulk task should include start date"
    assert "12/22/2025" in task or "end_date" in task.lower(), \
        "Bulk task should include end date"
