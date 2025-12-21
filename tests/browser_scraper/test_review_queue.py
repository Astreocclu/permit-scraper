import pytest
import json
import tempfile
from pathlib import Path
from services.browser_scraper.review_queue import ReviewQueue
from services.browser_scraper.models import ScrapeContext


@pytest.fixture
def temp_queue_dir(tmp_path):
    """Create temp directory for queue storage."""
    queue_dir = tmp_path / "review_queue"
    queue_dir.mkdir()
    return queue_dir


@pytest.fixture
def sample_context():
    """Sample failed context for testing."""
    return ScrapeContext(
        city="Prosper",
        final_result=None,
        is_done=True,
        is_successful=False,
        errors=["Date picker failed"],
        urls=["https://permits.prospertx.gov"],
        actions=["navigate", "click"],
        screenshots=["base64data"],
        task_description="Scrape Prosper permits",
    )


def test_add_to_queue(temp_queue_dir, sample_context):
    """Adding a context creates a JSON file in the queue."""
    queue = ReviewQueue(temp_queue_dir)
    queue.add(sample_context)

    pending_dir = temp_queue_dir / "pending"
    files = list(pending_dir.glob("*.json"))
    assert len(files) == 1

    data = json.loads(files[0].read_text())
    assert data["city"] == "Prosper"


def test_get_pending_returns_unreviewed(temp_queue_dir, sample_context):
    """get_pending returns contexts that haven't been reviewed."""
    queue = ReviewQueue(temp_queue_dir)
    queue.add(sample_context)

    pending = queue.get_pending()
    assert len(pending) == 1
    assert pending[0].city == "Prosper"


def test_mark_reviewed_moves_file(temp_queue_dir, sample_context):
    """Marking as reviewed moves file to 'reviewed' subdirectory."""
    queue = ReviewQueue(temp_queue_dir)
    queue.add(sample_context)

    pending = queue.get_pending()
    queue.mark_reviewed(pending[0], resolution="manual_fix", notes="Used direct URL")

    # Pending should now be empty
    assert len(queue.get_pending()) == 0

    # Reviewed dir should have one file
    reviewed_dir = temp_queue_dir / "reviewed"
    assert reviewed_dir.exists()
    reviewed_files = list(reviewed_dir.glob("*.json"))
    assert len(reviewed_files) == 1
