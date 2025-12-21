# Browser-Use Handoff System Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Capture rich context from Browser-Use runs (screenshots, actions, errors, URLs) and enable Claude Code to review and fix failed scrapes.

**Architecture:** Modify `agent.py` to return full `AgentHistoryList` data instead of just `final_result()`. Add a `ScrapeContext` dataclass to hold all handoff data. Create a reviewer CLI that loads failed scrapes and presents them to Claude Code with screenshots.

**Tech Stack:** Python 3.11, browser-use 0.11.1, dataclasses, base64 (screenshots), pytest

---

## Task 1: Create ScrapeContext Dataclass

**Files:**
- Create: `services/browser_scraper/models.py`
- Test: `tests/browser_scraper/test_models.py`

**Step 1: Create test directory and test file**

```bash
mkdir -p tests/browser_scraper
touch tests/browser_scraper/__init__.py
```

**Step 2: Write the failing test**

Create `tests/browser_scraper/test_models.py`:

```python
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
```

**Step 3: Run test to verify it fails**

Run: `pytest tests/browser_scraper/test_models.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'services.browser_scraper.models'"

**Step 4: Write minimal implementation**

Create `services/browser_scraper/models.py`:

```python
"""Data models for Browser-Use scraper handoff."""
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class ScrapeContext:
    """
    Rich context from a Browser-Use scrape attempt.

    This captures everything needed for Claude Code to review
    and potentially fix a failed scrape.
    """
    city: str
    final_result: Optional[str]  # JSON string if successful
    is_done: bool
    is_successful: Optional[bool]  # None if not done
    errors: list[Optional[str]]  # One error per step, None if no error
    urls: list[str]  # All URLs visited
    actions: list[str]  # Action names taken (click, input_text, etc.)
    screenshots: list[str] = field(default_factory=list)  # Base64 encoded, last N
    task_description: str = ""  # Original task given to agent
    raw_history: Optional[str] = None  # Full history JSON for deep debugging

    def needs_review(self) -> bool:
        """Return True if this scrape needs human/Claude review."""
        return self.is_successful is False or self.is_successful is None

    def has_errors(self) -> bool:
        """Return True if any step had an error."""
        return any(e is not None for e in self.errors)

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "ScrapeContext":
        """Create from dictionary (e.g., loaded from JSON)."""
        return cls(**data)
```

**Step 5: Run test to verify it passes**

Run: `pytest tests/browser_scraper/test_models.py -v`
Expected: PASS (3 tests)

**Step 6: Commit**

```bash
git add tests/browser_scraper/ services/browser_scraper/models.py
git commit -m "feat: add ScrapeContext dataclass for Browser-Use handoff"
```

---

## Task 2: Modify Agent to Return Rich Context

**Files:**
- Modify: `services/browser_scraper/agent.py`
- Test: `tests/browser_scraper/test_agent.py`

**Step 1: Write the failing test**

Create `tests/browser_scraper/test_agent.py`:

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
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
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/browser_scraper/test_agent.py -v`
Expected: FAIL with "TypeError: run_task() got an unexpected keyword argument 'city'"

**Step 3: Modify agent.py to return ScrapeContext**

Update `services/browser_scraper/agent.py`:

```python
import os
import asyncio
from typing import Optional, Dict, Any, List
from browser_use.llm.openai.chat import ChatOpenAI
from browser_use import Agent, Browser

from .utils import logger
from .models import ScrapeContext


class PermitScraperAgent:
    def __init__(self, headless: bool = True):
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        if not self.api_key:
            logger.warning("DEEPSEEK_API_KEY is not set.")

        self.headless = headless or os.getenv("BROWSER_USE_HEADLESS", "true").lower() == "true"

        # Configure DeepSeek LLM
        self.llm = ChatOpenAI(
            base_url="https://api.deepseek.com/v1",
            model="deepseek-chat",
            api_key=self.api_key,
            temperature=0.0,
            dont_force_structured_output=True,
            add_schema_to_system_prompt=True,
        )

        # Initialize Browser
        self.browser = Browser(
            headless=self.headless,
            disable_security=True,
        )

    async def run_task(self, task_description: str, city: str = "Unknown") -> ScrapeContext:
        """
        Run a scraping task using Browser-Use.

        Args:
            task_description: The natural language description of the task.
            city: The city name for context tracking.

        Returns:
            ScrapeContext with full history for handoff to Claude Code.
        """
        logger.info(f"Starting Browser-Use agent task for {city}...")

        agent = Agent(
            task=task_description,
            llm=self.llm,
            browser=self.browser,
            max_actions_per_step=1,
        )

        try:
            history = await agent.run(max_steps=30)

            # Extract rich context from history
            context = ScrapeContext(
                city=city,
                final_result=history.final_result() if hasattr(history, 'final_result') else None,
                is_done=history.is_done() if hasattr(history, 'is_done') else False,
                is_successful=history.is_successful() if hasattr(history, 'is_successful') else None,
                errors=history.errors() if hasattr(history, 'errors') else [],
                urls=history.urls() if hasattr(history, 'urls') else [],
                actions=history.action_names() if hasattr(history, 'action_names') else [],
                screenshots=history.screenshots(n_last=3) if hasattr(history, 'screenshots') else [],
                task_description=task_description,
            )

            return context

        except Exception as e:
            logger.error(f"Error running Browser-Use task: {e}")
            # Return context even on exception
            return ScrapeContext(
                city=city,
                final_result=None,
                is_done=False,
                is_successful=False,
                errors=[str(e)],
                urls=[],
                actions=[],
                screenshots=[],
                task_description=task_description,
            )
        finally:
            await self.browser.stop()

    async def close(self):
        await self.browser.stop()
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/browser_scraper/test_agent.py -v`
Expected: PASS (2 tests)

**Step 5: Commit**

```bash
git add services/browser_scraper/agent.py tests/browser_scraper/test_agent.py
git commit -m "feat: agent returns ScrapeContext with rich history data"
```

---

## Task 3: Update Runner to Handle ScrapeContext

**Files:**
- Modify: `services/browser_scraper/runner.py`
- Test: `tests/browser_scraper/test_runner.py`

**Step 1: Write the failing test**

Create `tests/browser_scraper/test_runner.py`:

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
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
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/browser_scraper/test_runner.py -v`
Expected: FAIL with "AttributeError: 'PermitScraperRunner' object has no attribute '_create_agent'"

**Step 3: Update runner.py**

Update `services/browser_scraper/runner.py` (key changes only, full file too long):

```python
import asyncio
import json
import argparse
from typing import Dict, Optional, Any, List
import datetime
import os

from .agent import PermitScraperAgent
from .permit_tasks import get_task_for_city
from .models import ScrapeContext
from .utils import log_scrape_attempt, logger


class PermitScraperRunner:
    def __init__(self):
        self.agent = None

    def _create_agent(self) -> PermitScraperAgent:
        """Factory method for creating agent (allows mocking in tests)."""
        return PermitScraperAgent()

    async def scrape_permit(
        self,
        city: str,
        address: str = "",
        permit_type: str = "Building",
        mode: str = "single",
        start_date: str = "",
        end_date: str = ""
    ) -> Dict[str, Any]:
        """
        Main entry point to scrape a permit.

        Returns dict with:
            success: bool
            data: parsed JSON or raw output
            error: error message if any
            context: ScrapeContext dict for review/handoff
        """
        success = False
        error_msg = None
        result_data = {}
        context: Optional[ScrapeContext] = None

        try:
            mgo_email = os.getenv("MGO_EMAIL", "")
            mgo_password = os.getenv("MGO_PASSWORD", "")

            task_desc = get_task_for_city(
                city=city,
                address=address,
                permit_type=permit_type,
                mgo_email=mgo_email,
                mgo_password=mgo_password,
                mode=mode,
                start_date=start_date,
                end_date=end_date
            )

            self.agent = self._create_agent()

            # Execute and get rich context
            context = await self.agent.run_task(task_desc, city=city)

            # Try to parse JSON from final_result
            if context.final_result and context.is_successful:
                clean_result = context.final_result.strip()
                # Strip markdown code blocks
                if clean_result.startswith("```json"):
                    clean_result = clean_result.replace("```json", "").replace("```", "")
                elif clean_result.startswith("```"):
                    clean_result = clean_result.replace("```", "")

                try:
                    result_data = json.loads(clean_result)
                    success = True
                except json.JSONDecodeError:
                    error_msg = "Failed to parse JSON response"
                    result_data = {"raw_output": context.final_result}
            else:
                error_msg = "Scrape incomplete or unsuccessful"
                result_data = {"raw_output": context.final_result}

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Scrape failed: {e}")
        finally:
            if self.agent:
                await self.agent.close()

            log_scrape_attempt(
                city,
                address if mode == 'single' else f"{start_date}-{end_date}",
                success,
                0,  # tokens placeholder
                error_msg
            )

        return {
            "success": success,
            "data": result_data,
            "error": error_msg,
            "context": context.to_dict() if context else None
        }
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/browser_scraper/test_runner.py -v`
Expected: PASS (2 tests)

**Step 5: Commit**

```bash
git add services/browser_scraper/runner.py tests/browser_scraper/test_runner.py
git commit -m "feat: runner returns ScrapeContext for handoff"
```

---

## Task 4: Create Review Queue Storage

**Files:**
- Create: `services/browser_scraper/review_queue.py`
- Test: `tests/browser_scraper/test_review_queue.py`

**Step 1: Write the failing test**

Create `tests/browser_scraper/test_review_queue.py`:

```python
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

    files = list(temp_queue_dir.glob("*.json"))
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
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/browser_scraper/test_review_queue.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'services.browser_scraper.review_queue'"

**Step 3: Write implementation**

Create `services/browser_scraper/review_queue.py`:

```python
"""Review queue for failed Browser-Use scrapes."""
import json
from datetime import datetime
from pathlib import Path
from typing import Optional
from .models import ScrapeContext


class ReviewQueue:
    """
    File-based queue for scrapes that need Claude Code review.

    Structure:
        queue_dir/
            pending/      <- Scrapes waiting for review
            reviewed/     <- Scrapes that have been reviewed
    """

    def __init__(self, queue_dir: Path | str = "data/review_queue"):
        self.queue_dir = Path(queue_dir)
        self.pending_dir = self.queue_dir / "pending"
        self.reviewed_dir = self.queue_dir / "reviewed"

        # Ensure directories exist
        self.pending_dir.mkdir(parents=True, exist_ok=True)
        self.reviewed_dir.mkdir(parents=True, exist_ok=True)

    def add(self, context: ScrapeContext) -> Path:
        """
        Add a ScrapeContext to the review queue.

        Returns the path to the created file.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{context.city.lower().replace(' ', '_')}.json"
        filepath = self.pending_dir / filename

        data = context.to_dict()
        data["queued_at"] = datetime.now().isoformat()

        filepath.write_text(json.dumps(data, indent=2))
        return filepath

    def get_pending(self, limit: int = 10) -> list[ScrapeContext]:
        """Get pending contexts, oldest first."""
        files = sorted(self.pending_dir.glob("*.json"))[:limit]
        contexts = []
        for f in files:
            data = json.loads(f.read_text())
            # Remove queue metadata before creating context
            data.pop("queued_at", None)
            data.pop("_filepath", None)
            ctx = ScrapeContext.from_dict(data)
            # Store filepath for mark_reviewed
            ctx._filepath = f  # type: ignore
            contexts.append(ctx)
        return contexts

    def mark_reviewed(
        self,
        context: ScrapeContext,
        resolution: str,
        notes: str = ""
    ) -> Path:
        """
        Mark a context as reviewed and move to reviewed directory.

        Args:
            context: The context to mark
            resolution: One of 'fixed', 'manual_fix', 'skip', 'permanent_block'
            notes: Any notes about the resolution

        Returns the path to the reviewed file.
        """
        # Get original filepath
        source = getattr(context, '_filepath', None)
        if not source or not source.exists():
            raise ValueError("Context was not loaded from queue")

        # Load and update data
        data = json.loads(source.read_text())
        data["reviewed_at"] = datetime.now().isoformat()
        data["resolution"] = resolution
        data["notes"] = notes

        # Move to reviewed
        dest = self.reviewed_dir / source.name
        dest.write_text(json.dumps(data, indent=2))
        source.unlink()

        return dest

    def pending_count(self) -> int:
        """Number of items waiting for review."""
        return len(list(self.pending_dir.glob("*.json")))
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/browser_scraper/test_review_queue.py -v`
Expected: PASS (3 tests)

**Step 5: Commit**

```bash
git add services/browser_scraper/review_queue.py tests/browser_scraper/test_review_queue.py
git commit -m "feat: add ReviewQueue for failed scrape handoff"
```

---

## Task 5: Integrate Queue into BatchRunner

**Files:**
- Modify: `services/browser_scraper/runner.py`
- Test: `tests/browser_scraper/test_runner.py` (add test)

**Step 1: Write the failing test**

Add to `tests/browser_scraper/test_runner.py`:

```python
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
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/browser_scraper/test_runner.py::test_batch_runner_queues_failures -v`
Expected: FAIL with "TypeError: BatchRunner.__init__() got an unexpected keyword argument 'review_queue'"

**Step 3: Update BatchRunner**

Update `services/browser_scraper/runner.py` BatchRunner class:

```python
from .review_queue import ReviewQueue


class BatchRunner:
    def __init__(
        self,
        concurrency: int = 5,
        review_queue: Optional[ReviewQueue] = None
    ):
        self.concurrency = concurrency
        self.semaphore = asyncio.Semaphore(concurrency)
        self.results = []
        self.review_queue = review_queue or ReviewQueue()

    async def _scrape_safe(
        self,
        city: str,
        address: str,
        permit_type: str,
        mode: str,
        start_date: str,
        end_date: str
    ) -> Dict[str, Any]:
        """Wrapper to run scrape with semaphore and exception handling."""
        async with self.semaphore:
            logger.info(f"Scraping city: {city}")
            runner = PermitScraperRunner()
            result_payload = {}
            try:
                result = await runner.scrape_permit(
                    city, address, permit_type, mode, start_date, end_date
                )
                result_payload = {
                    "city": city,
                    "status": "success" if result["success"] else "failed",
                    "data": result.get("data"),
                    "error": result.get("error"),
                    "context": result.get("context"),
                    "timestamp": datetime.datetime.now().isoformat()
                }

                # Queue failures for review
                if not result["success"] and result.get("context"):
                    context = ScrapeContext.from_dict(result["context"])
                    self.review_queue.add(context)
                    logger.info(f"Added {city} to review queue")

            except Exception as e:
                logger.error(f"Critical failure for {city}: {e}")
                result_payload = {
                    "city": city,
                    "status": "error",
                    "error": str(e),
                    "timestamp": datetime.datetime.now().isoformat()
                }

            self._append_result(result_payload)
            return result_payload
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/browser_scraper/test_runner.py -v`
Expected: PASS (3 tests)

**Step 5: Commit**

```bash
git add services/browser_scraper/runner.py tests/browser_scraper/test_runner.py
git commit -m "feat: BatchRunner queues failed scrapes for review"
```

---

## Task 6: Create Review CLI for Claude Code

**Files:**
- Create: `services/browser_scraper/review_cli.py`
- Test: Manual testing with actual review queue

**Step 1: Write implementation**

Create `services/browser_scraper/review_cli.py`:

```python
#!/usr/bin/env python3
"""
CLI for reviewing failed Browser-Use scrapes.

Usage:
    python -m services.browser_scraper.review_cli --list
    python -m services.browser_scraper.review_cli --review
    python -m services.browser_scraper.review_cli --show <city>
"""
import argparse
import json
import base64
from pathlib import Path
from .review_queue import ReviewQueue
from .models import ScrapeContext


def list_pending(queue: ReviewQueue):
    """List all pending reviews."""
    pending = queue.get_pending(limit=50)
    if not pending:
        print("No pending reviews.")
        return

    print(f"\n{'='*60}")
    print(f"PENDING REVIEWS: {len(pending)}")
    print(f"{'='*60}\n")

    for i, ctx in enumerate(pending, 1):
        status = "FAILED" if ctx.is_successful is False else "INCOMPLETE"
        errors = [e for e in ctx.errors if e]
        error_summary = errors[0][:50] if errors else "No specific error"

        print(f"{i}. {ctx.city}")
        print(f"   Status: {status}")
        print(f"   URLs visited: {len(ctx.urls)}")
        print(f"   Actions taken: {len(ctx.actions)}")
        print(f"   Screenshots: {len(ctx.screenshots)}")
        print(f"   Error: {error_summary}")
        print()


def show_detail(queue: ReviewQueue, city: str):
    """Show detailed context for a specific city."""
    pending = queue.get_pending(limit=50)
    match = next((c for c in pending if c.city.lower() == city.lower()), None)

    if not match:
        print(f"No pending review for '{city}'")
        return

    print(f"\n{'='*60}")
    print(f"REVIEW: {match.city}")
    print(f"{'='*60}\n")

    print("## Status")
    print(f"- is_done: {match.is_done}")
    print(f"- is_successful: {match.is_successful}")
    print()

    print("## Task Description")
    print(match.task_description[:500] + "..." if len(match.task_description) > 500 else match.task_description)
    print()

    print("## URLs Visited")
    for url in match.urls:
        print(f"  - {url}")
    print()

    print("## Actions Taken")
    for action in match.actions:
        print(f"  - {action}")
    print()

    print("## Errors")
    errors = [e for e in match.errors if e]
    if errors:
        for err in errors:
            print(f"  - {err}")
    else:
        print("  (none)")
    print()

    print("## Final Result (raw)")
    if match.final_result:
        print(match.final_result[:1000])
    else:
        print("  (none)")
    print()

    print("## Screenshots")
    if match.screenshots:
        print(f"  {len(match.screenshots)} screenshots available")
        print("  Use --save-screenshots to save to disk")
    else:
        print("  (none)")


def save_screenshots(queue: ReviewQueue, city: str, output_dir: Path):
    """Save screenshots for a city to disk."""
    pending = queue.get_pending(limit=50)
    match = next((c for c in pending if c.city.lower() == city.lower()), None)

    if not match:
        print(f"No pending review for '{city}'")
        return

    output_dir.mkdir(parents=True, exist_ok=True)

    for i, screenshot in enumerate(match.screenshots):
        if screenshot:
            # Screenshots are base64 encoded
            try:
                img_data = base64.b64decode(screenshot)
                filepath = output_dir / f"{city.lower()}_{i+1}.png"
                filepath.write_bytes(img_data)
                print(f"Saved: {filepath}")
            except Exception as e:
                print(f"Failed to save screenshot {i+1}: {e}")


def interactive_review(queue: ReviewQueue):
    """Interactive review mode."""
    pending = queue.get_pending(limit=1)
    if not pending:
        print("No pending reviews.")
        return

    ctx = pending[0]
    show_detail(queue, ctx.city)

    print("\n## Actions")
    print("1. Mark as 'fixed' (data extracted successfully after review)")
    print("2. Mark as 'manual_fix' (will scrape manually)")
    print("3. Mark as 'skip' (not worth pursuing)")
    print("4. Mark as 'permanent_block' (portal is unscrappable)")
    print("5. Skip (leave in queue)")
    print()

    choice = input("Choice [1-5]: ").strip()

    resolution_map = {
        "1": "fixed",
        "2": "manual_fix",
        "3": "skip",
        "4": "permanent_block",
    }

    if choice in resolution_map:
        notes = input("Notes (optional): ").strip()
        queue.mark_reviewed(ctx, resolution_map[choice], notes)
        print(f"\nMarked {ctx.city} as '{resolution_map[choice]}'")
    else:
        print("Skipped.")


def main():
    parser = argparse.ArgumentParser(description="Review failed Browser-Use scrapes")
    parser.add_argument("--list", action="store_true", help="List pending reviews")
    parser.add_argument("--show", type=str, help="Show detail for a city")
    parser.add_argument("--review", action="store_true", help="Interactive review mode")
    parser.add_argument("--save-screenshots", type=str, help="Save screenshots for city to directory")
    parser.add_argument("--queue-dir", default="data/review_queue", help="Queue directory")

    args = parser.parse_args()
    queue = ReviewQueue(args.queue_dir)

    if args.list:
        list_pending(queue)
    elif args.show:
        show_detail(queue, args.show)
    elif args.save_screenshots:
        city = args.save_screenshots
        save_screenshots(queue, city, Path(f"data/screenshots/{city.lower()}"))
    elif args.review:
        interactive_review(queue)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
```

**Step 2: Test manually**

Run: `python -m services.browser_scraper.review_cli --list`
Expected: "No pending reviews." (or list of any existing items)

**Step 3: Commit**

```bash
git add services/browser_scraper/review_cli.py
git commit -m "feat: add review CLI for Claude Code handoff"
```

---

## Task 7: Add Screenshot Saving to Agent

**Files:**
- Modify: `services/browser_scraper/agent.py`
- Modify: `services/browser_scraper/models.py`

**Step 1: Update ScrapeContext to track screenshot paths**

Add to `services/browser_scraper/models.py`:

```python
@dataclass
class ScrapeContext:
    # ... existing fields ...
    screenshot_paths: list[str] = field(default_factory=list)  # Paths to saved PNG files
```

**Step 2: Modify agent to save screenshots to disk**

Update agent.py `run_task` method:

```python
import base64
from pathlib import Path
from datetime import datetime

# In run_task, after getting history:
screenshot_paths = []
screenshots_dir = Path("data/screenshots") / city.lower().replace(" ", "_")
screenshots_dir.mkdir(parents=True, exist_ok=True)

raw_screenshots = history.screenshots(n_last=3) if hasattr(history, 'screenshots') else []
for i, screenshot in enumerate(raw_screenshots):
    if screenshot:
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = screenshots_dir / f"{timestamp}_{i+1}.png"
            img_data = base64.b64decode(screenshot)
            filepath.write_bytes(img_data)
            screenshot_paths.append(str(filepath))
        except Exception as e:
            logger.warning(f"Failed to save screenshot {i+1}: {e}")

# Include in context
context = ScrapeContext(
    # ... other fields ...
    screenshots=raw_screenshots,  # Keep base64 for JSONL
    screenshot_paths=screenshot_paths,  # Add paths
)
```

**Step 3: Commit**

```bash
git add services/browser_scraper/agent.py services/browser_scraper/models.py
git commit -m "feat: save screenshots to disk for review"
```

---

## Task 8: Update .gitignore for Review Queue

**Files:**
- Modify: `.gitignore`

**Step 1: Add review queue and screenshots to gitignore**

Add to `.gitignore`:

```gitignore
# Browser-Use review queue (contains screenshots and debug data)
data/review_queue/
data/screenshots/
```

**Step 2: Commit**

```bash
git add .gitignore
git commit -m "chore: gitignore review queue and screenshots"
```

---

## Summary

This plan implements a complete handoff system:

| Component | Purpose |
|-----------|---------|
| `ScrapeContext` | Rich dataclass with all history data |
| Modified `agent.py` | Returns ScrapeContext instead of string |
| Modified `runner.py` | Preserves context, queues failures |
| `ReviewQueue` | File-based queue for pending reviews |
| `review_cli.py` | CLI for Claude Code to review failures |
| Screenshot saving | PNG files saved to disk for visual debugging |

**After Implementation:**
1. Browser-Use runs gather full context
2. Failed scrapes go to `data/review_queue/pending/`
3. Claude Code runs `python -m services.browser_scraper.review_cli --list`
4. Reviews include screenshots, URLs, actions, errors
5. Claude Code can fix the approach and retry

**Total: 8 tasks, ~16 commits**
