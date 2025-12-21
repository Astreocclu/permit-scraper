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
