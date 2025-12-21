import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys

# Mock browser_use modules before importing agent
sys.modules['browser_use'] = MagicMock()
sys.modules['browser_use.llm'] = MagicMock()
sys.modules['browser_use.llm.openai'] = MagicMock()
sys.modules['browser_use.llm.openai.chat'] = MagicMock()

from services.browser_scraper.agent import PermitScraperAgent
from services.browser_scraper.models import ScrapeContext


@pytest.fixture
def mock_history():
    """Create a mock AgentHistoryList with expected methods."""
    history = MagicMock()
    history.final_result.return_value = '{"permit": "123"}'
    history.is_done.return_value = True
    history.is_successful.return_value = True
    history.errors.return_value = [None, None]  # No errors
    history.urls.return_value = ["https://example.com", "https://example.com/search"]
    history.action_names.return_value = ["navigate", "click", "extract"]
    history.screenshots.return_value = ["base64screenshot1", "base64screenshot2"]
    return history


@pytest.mark.asyncio
async def test_run_task_returns_scrape_context(mock_history):
    """run_task should return a ScrapeContext, not a string."""
    with patch.object(PermitScraperAgent, '__init__', lambda x, **kwargs: None):
        agent = PermitScraperAgent()
        agent.api_key = "test-key"
        agent.headless = True
        agent.llm = MagicMock()
        agent.browser = AsyncMock()
        agent.browser.stop = AsyncMock()

        # Mock the Agent class
        with patch('services.browser_scraper.agent.Agent') as MockAgent:
            mock_agent_instance = AsyncMock()
            mock_agent_instance.run = AsyncMock(return_value=mock_history)
            MockAgent.return_value = mock_agent_instance

            result = await agent.run_task("Test task", city="TestCity")

            assert isinstance(result, ScrapeContext)
            assert result.city == "TestCity"
            assert result.final_result == '{"permit": "123"}'
            assert result.is_successful == True
            assert len(result.screenshots) == 2


@pytest.mark.asyncio
async def test_run_task_captures_errors(mock_history):
    """run_task should capture errors from history."""
    mock_history.is_successful.return_value = False
    mock_history.errors.return_value = [None, "Date picker failed", None]

    with patch.object(PermitScraperAgent, '__init__', lambda x, **kwargs: None):
        agent = PermitScraperAgent()
        agent.api_key = "test-key"
        agent.headless = True
        agent.llm = MagicMock()
        agent.browser = AsyncMock()
        agent.browser.stop = AsyncMock()

        with patch('services.browser_scraper.agent.Agent') as MockAgent:
            mock_agent_instance = AsyncMock()
            mock_agent_instance.run = AsyncMock(return_value=mock_history)
            MockAgent.return_value = mock_agent_instance

            result = await agent.run_task("Test task", city="TestCity")

            assert result.is_successful == False
            assert result.needs_review() == True
            assert "Date picker failed" in result.errors
