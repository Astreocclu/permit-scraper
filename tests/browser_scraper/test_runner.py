import pytest
import sys
from unittest.mock import AsyncMock, MagicMock, patch, Mock

# Mock browser_use before importing runner
sys.modules['browser_use'] = Mock()
sys.modules['browser_use.llm'] = Mock()
sys.modules['browser_use.llm.openai'] = Mock()
sys.modules['browser_use.llm.openai.chat'] = Mock()

from services.browser_scraper.runner import PermitScraperRunner
from services.browser_scraper.models import ScrapeContext


@pytest.fixture
def successful_context():
    """A ScrapeContext representing a successful scrape."""
    return ScrapeContext(
        city="Dallas",
        final_result='[{"permit_number": "BP-2025-001", "address": "123 Main St"}]',
        is_done=True,
        is_successful=True,
        errors=[],
        urls=["https://permits.dallas.gov"],
        actions=["navigate", "search", "extract"],
        screenshots=[],
        task_description="Scrape permits from Dallas",
    )


@pytest.fixture
def failed_context():
    """A ScrapeContext representing a failed scrape."""
    return ScrapeContext(
        city="Prosper",
        final_result="Task incomplete due to maximum steps...",
        is_done=True,
        is_successful=False,
        errors=[None, "Date picker blocked", None],
        urls=["https://permits.prospertx.gov"],
        actions=["navigate", "click", "click"],
        screenshots=["base64data"],
        task_description="Scrape permits from Prosper",
    )


@pytest.mark.asyncio
async def test_scrape_permit_success_parses_json(successful_context):
    """Successful scrape with valid JSON returns parsed data."""
    runner = PermitScraperRunner()

    with patch.object(runner, '_create_agent') as mock_create:
        mock_agent = AsyncMock()
        mock_agent.run_task = AsyncMock(return_value=successful_context)
        mock_agent.close = AsyncMock()
        mock_create.return_value = mock_agent

        result = await runner.scrape_permit("Dallas", mode="bulk")

        assert result["success"] == True
        assert result["data"][0]["permit_number"] == "BP-2025-001"
        assert result["context"] is not None
        assert result["context"]["city"] == "Dallas"


@pytest.mark.asyncio
async def test_scrape_permit_failure_includes_context(failed_context):
    """Failed scrape includes full context for review."""
    runner = PermitScraperRunner()

    with patch.object(runner, '_create_agent') as mock_create:
        mock_agent = AsyncMock()
        mock_agent.run_task = AsyncMock(return_value=failed_context)
        mock_agent.close = AsyncMock()
        mock_create.return_value = mock_agent

        result = await runner.scrape_permit("Prosper", mode="bulk")

        assert result["success"] == False
        assert result["context"]["is_successful"] == False
        assert "Date picker blocked" in result["context"]["errors"]
        assert len(result["context"]["screenshots"]) == 1


@pytest.mark.asyncio
async def test_batch_runner_queues_failures(failed_context, tmp_path):
    """BatchRunner adds failed scrapes to review queue."""
    from services.browser_scraper.runner import BatchRunner
    from services.browser_scraper.review_queue import ReviewQueue

    queue = ReviewQueue(tmp_path / "queue")
    batch_runner = BatchRunner(concurrency=1, review_queue=queue)

    with patch('services.browser_scraper.runner.PermitScraperRunner') as MockRunner:
        mock_instance = MagicMock()
        mock_instance.scrape_permit = AsyncMock(return_value={
            "success": False,
            "data": {"raw_output": "Task incomplete..."},
            "error": "Date picker blocked",
            "context": failed_context.to_dict()
        })
        MockRunner.return_value = mock_instance

        await batch_runner.run_batch(["Prosper"], mode="bulk")

        # Queue should have one item
        assert queue.pending_count() == 1


@pytest.mark.asyncio
async def test_batch_runner_creates_city_raw_json(tmp_path):
    """BatchRunner should create {city}_raw.json alongside jsonl."""
    import asyncio
    import json
    from services.browser_scraper.runner import BatchRunner

    # Mock the scraper to return fake data
    mock_result = {
        "success": True,
        "data": [{"permit_number": "TEST-001", "address": "123 Main St"}],
        "error": None,
        "context": None
    }

    runner = BatchRunner(concurrency=1)

    # Patch the raw data directory
    raw_dir = tmp_path / "data" / "raw"
    raw_dir.mkdir(parents=True)

    with patch.object(runner, '_get_raw_dir', return_value=raw_dir):
        with patch('services.browser_scraper.runner.PermitScraperRunner.scrape_permit',
                   new_callable=AsyncMock, return_value=mock_result):
            await runner.run_batch(["TestCity"], mode="bulk")

    # Check that city_raw.json was created
    expected_file = raw_dir / "testcity_raw.json"
    assert expected_file.exists(), f"Expected {expected_file} to exist"

    data = json.loads(expected_file.read_text())
    assert len(data) > 0

    # Validate structure matches pipeline expectations
    assert "source" in data, "Missing 'source' field"
    assert "portal_type" in data, "Missing 'portal_type' field"
    assert "scraped_at" in data, "Missing 'scraped_at' field"
    assert "permits" in data, "Missing 'permits' field"
    assert data["source"] == "testcity"
    assert data["portal_type"] == "browser_use"
    assert isinstance(data["permits"], list)
    assert len(data["permits"]) == 1
    assert data["permits"][0]["permit_number"] == "TEST-001"
