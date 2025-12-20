# Browser-Use Scraper Shepherding System Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create a guided, token-efficient browser-use scraper system that processes cities one-by-one with human review, tracks status, and prevents infinite loops.

**Architecture:**
- Add a `city_status.json` tracker to record pass/fail/needs-attention for each city
- Implement prompt refinement templates that get more specific based on failure modes
- Add a shepherd CLI that runs one city, reports results, waits for human decision before continuing
- Cap retries at 2 per city, then mark as "needs_manual_review"

**Tech Stack:** Python 3, browser-use, DeepSeek, asyncio, JSON for state

---

## Current State Analysis

**What exists:**
- `services/browser_scraper/agent.py` - Browser-use agent wrapper
- `services/browser_scraper/runner.py` - CLI runner with batch support
- `services/browser_scraper/permit_tasks.py` - 42 city task templates
- `data/target_cities.json` - 50 target cities
- `data/incremental_batch_results.jsonl` - Raw run results

**Problems identified from logs:**
1. **JSON parse failures** - Agent returns prose instead of JSON when stuck
2. **Date picker issues** - Shadow DOM components block interaction
3. **Portal down** - McKinney HTTP/2 errors
4. **URL redirects** - Forney redirects to marketing page
5. **No retry tracking** - Same cities fail repeatedly without learning
6. **No human gate** - Batch runs burn tokens on hopeless cities

**Success rate from logs:** 4/20 runs succeeded (20%)

---

## Task 1: Create City Status Tracker

**Files:**
- Create: `services/browser_scraper/status_tracker.py`
- Create: `data/city_status.json`

**Step 1: Write the failing test**

Create file `tests/services/browser_scraper/test_status_tracker.py`:

```python
import pytest
import json
import os
from pathlib import Path

# Will create this module
from services.browser_scraper.status_tracker import CityStatusTracker

@pytest.fixture
def temp_status_file(tmp_path):
    return tmp_path / "city_status.json"

def test_tracker_initializes_empty(temp_status_file):
    tracker = CityStatusTracker(str(temp_status_file))
    assert tracker.get_status("Dallas") == "pending"

def test_tracker_marks_success(temp_status_file):
    tracker = CityStatusTracker(str(temp_status_file))
    tracker.mark_success("Dallas", permits_count=15)
    status = tracker.get_status("Dallas")
    assert status == "success"

def test_tracker_marks_failure_with_reason(temp_status_file):
    tracker = CityStatusTracker(str(temp_status_file))
    tracker.mark_failure("Irving", reason="date_picker_blocked", attempt=1)
    data = tracker.get_city_data("Irving")
    assert data["status"] == "failed"
    assert data["attempts"] == 1
    assert data["last_failure_reason"] == "date_picker_blocked"

def test_tracker_caps_retries_at_two(temp_status_file):
    tracker = CityStatusTracker(str(temp_status_file))
    tracker.mark_failure("Irving", reason="timeout", attempt=1)
    tracker.mark_failure("Irving", reason="timeout", attempt=2)
    data = tracker.get_city_data("Irving")
    assert data["status"] == "needs_manual_review"
    assert data["attempts"] == 2

def test_tracker_persists_to_file(temp_status_file):
    tracker = CityStatusTracker(str(temp_status_file))
    tracker.mark_success("Dallas", permits_count=15)

    # Load fresh tracker from same file
    tracker2 = CityStatusTracker(str(temp_status_file))
    assert tracker2.get_status("Dallas") == "success"

def test_get_pending_cities(temp_status_file):
    tracker = CityStatusTracker(str(temp_status_file))
    tracker.mark_success("Dallas", permits_count=15)
    tracker.mark_failure("Irving", reason="blocked", attempt=2)

    all_cities = ["Dallas", "Irving", "Frisco", "Plano"]
    pending = tracker.get_pending_cities(all_cities)
    assert pending == ["Frisco", "Plano"]
```

**Step 2: Run test to verify it fails**

Run: `cd /home/reid/testhome/permit-scraper && pytest tests/services/browser_scraper/test_status_tracker.py -v`

Expected: FAIL with "ModuleNotFoundError: No module named 'services.browser_scraper.status_tracker'"

**Step 3: Create the tests directory structure**

```bash
mkdir -p tests/services/browser_scraper
touch tests/services/__init__.py
touch tests/services/browser_scraper/__init__.py
```

**Step 4: Write the implementation**

Create file `services/browser_scraper/status_tracker.py`:

```python
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

class CityStatusTracker:
    """
    Tracks scraping status for each city.

    Statuses:
    - pending: Not yet attempted
    - success: Successfully scraped permits
    - failed: Failed but can retry (attempts < 2)
    - needs_manual_review: Failed 2+ times, requires human intervention
    - skipped: Manually marked to skip (portal down, etc.)
    """

    def __init__(self, status_file: str = "data/city_status.json"):
        self.status_file = Path(status_file)
        self.data: Dict[str, Dict[str, Any]] = {}
        self._load()

    def _load(self):
        if self.status_file.exists():
            with open(self.status_file, 'r') as f:
                self.data = json.load(f)

    def _save(self):
        self.status_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.status_file, 'w') as f:
            json.dump(self.data, f, indent=2)

    def get_status(self, city: str) -> str:
        if city not in self.data:
            return "pending"
        return self.data[city].get("status", "pending")

    def get_city_data(self, city: str) -> Dict[str, Any]:
        return self.data.get(city, {"status": "pending", "attempts": 0})

    def mark_success(self, city: str, permits_count: int = 0):
        self.data[city] = {
            "status": "success",
            "permits_count": permits_count,
            "last_run": datetime.now().isoformat(),
            "attempts": self.data.get(city, {}).get("attempts", 0) + 1
        }
        self._save()

    def mark_failure(self, city: str, reason: str, attempt: int):
        current = self.data.get(city, {"attempts": 0})

        # Cap at 2 retries, then mark for manual review
        if attempt >= 2:
            status = "needs_manual_review"
        else:
            status = "failed"

        self.data[city] = {
            "status": status,
            "attempts": attempt,
            "last_failure_reason": reason,
            "last_run": datetime.now().isoformat()
        }
        self._save()

    def mark_skipped(self, city: str, reason: str):
        self.data[city] = {
            "status": "skipped",
            "skip_reason": reason,
            "last_run": datetime.now().isoformat()
        }
        self._save()

    def reset_city(self, city: str):
        if city in self.data:
            del self.data[city]
            self._save()

    def get_pending_cities(self, all_cities: List[str]) -> List[str]:
        """Return cities that haven't been processed or need retry."""
        pending = []
        for city in all_cities:
            status = self.get_status(city)
            if status in ("pending", "failed"):
                pending.append(city)
        return pending

    def get_summary(self) -> Dict[str, int]:
        summary = {"pending": 0, "success": 0, "failed": 0, "needs_manual_review": 0, "skipped": 0}
        for city_data in self.data.values():
            status = city_data.get("status", "pending")
            summary[status] = summary.get(status, 0) + 1
        return summary
```

**Step 5: Run tests to verify they pass**

Run: `cd /home/reid/testhome/permit-scraper && pytest tests/services/browser_scraper/test_status_tracker.py -v`

Expected: All 6 tests PASS

**Step 6: Commit**

```bash
git add services/browser_scraper/status_tracker.py tests/services/browser_scraper/
git commit -m "feat: add city status tracker for browser-use scraper"
```

---

## Task 2: Create Failure Classifier

**Files:**
- Create: `services/browser_scraper/failure_classifier.py`
- Test: `tests/services/browser_scraper/test_failure_classifier.py`

**Step 1: Write the failing test**

Create file `tests/services/browser_scraper/test_failure_classifier.py`:

```python
import pytest
from services.browser_scraper.failure_classifier import classify_failure

def test_classifies_json_parse_error():
    raw = "I was unable to complete the task. The portal showed..."
    result = classify_failure(raw, "Failed to parse JSON response")
    assert result["category"] == "json_parse_failure"
    assert result["retryable"] == True

def test_classifies_date_picker_issue():
    raw = "Failed to set date range from 11/17/2025 due to persistent issues with date picker"
    result = classify_failure(raw, None)
    assert result["category"] == "date_picker_blocked"
    assert result["retryable"] == True
    assert "date picker" in result["suggestion"].lower()

def test_classifies_portal_down():
    raw = "ERR_HTTP2_PROTOCOL_ERROR across all access attempts"
    result = classify_failure(raw, None)
    assert result["category"] == "portal_down"
    assert result["retryable"] == False

def test_classifies_url_redirect():
    raw = "The URL redirects to a generic Tyler Tech marketing page"
    result = classify_failure(raw, None)
    assert result["category"] == "url_invalid"
    assert result["retryable"] == False

def test_classifies_shadow_dom():
    raw = "shadow DOM; despite numerous attempts I could not expand it"
    result = classify_failure(raw, None)
    assert result["category"] == "shadow_dom_blocked"
    assert result["retryable"] == True

def test_classifies_max_steps():
    raw = "Task incomplete due to reaching maximum steps"
    result = classify_failure(raw, None)
    assert result["category"] == "max_steps_exceeded"
    assert result["retryable"] == True
```

**Step 2: Run test to verify it fails**

Run: `cd /home/reid/testhome/permit-scraper && pytest tests/services/browser_scraper/test_failure_classifier.py -v`

Expected: FAIL with "ModuleNotFoundError"

**Step 3: Write the implementation**

Create file `services/browser_scraper/failure_classifier.py`:

```python
from typing import Dict, Any
import re

FAILURE_PATTERNS = [
    {
        "category": "portal_down",
        "patterns": [
            r"ERR_HTTP2_PROTOCOL_ERROR",
            r"ERR_CONNECTION_REFUSED",
            r"website appears.*down",
            r"server.*unavailable",
            r"503 Service Unavailable",
        ],
        "retryable": False,
        "suggestion": "Portal is down. Skip this city and try again later."
    },
    {
        "category": "url_invalid",
        "patterns": [
            r"redirects to.*(marketing|generic|different)",
            r"URL.*not found",
            r"404 Not Found",
            r"could not reach.*portal",
        ],
        "retryable": False,
        "suggestion": "URL is invalid or redirected. Need to research correct portal URL."
    },
    {
        "category": "date_picker_blocked",
        "patterns": [
            r"date picker.*not finalizing",
            r"failed to set date range",
            r"date.*fields remained empty",
            r"calendar.*did not",
        ],
        "retryable": True,
        "suggestion": "Try alternative date entry: type MM/DD/YYYY directly, or use JavaScript to set values."
    },
    {
        "category": "shadow_dom_blocked",
        "patterns": [
            r"shadow DOM",
            r"custom.*component.*prevented",
            r"could not expand.*dropdown",
        ],
        "retryable": True,
        "suggestion": "Shadow DOM issue. Try using JavaScript evaluation to interact with elements."
    },
    {
        "category": "max_steps_exceeded",
        "patterns": [
            r"reaching maximum steps",
            r"step limit",
            r"Task incomplete due to",
        ],
        "retryable": True,
        "suggestion": "Increase max_steps or simplify the task instructions."
    },
    {
        "category": "login_required",
        "patterns": [
            r"authentication required",
            r"login.*required",
            r"must.*sign in",
            r"access denied",
        ],
        "retryable": False,
        "suggestion": "Portal requires login. Need credentials or public access URL."
    },
    {
        "category": "json_parse_failure",
        "patterns": [
            r"Failed to parse JSON",
        ],
        "retryable": True,
        "suggestion": "Agent returned prose instead of JSON. Emphasize JSON-only output in task."
    },
]

def classify_failure(raw_output: str, error_msg: str = None) -> Dict[str, Any]:
    """
    Classify a failure based on raw output and error message.

    Returns:
        {
            "category": str,
            "retryable": bool,
            "suggestion": str,
            "matched_pattern": str
        }
    """
    combined_text = f"{raw_output or ''} {error_msg or ''}".lower()

    for pattern_group in FAILURE_PATTERNS:
        for pattern in pattern_group["patterns"]:
            if re.search(pattern, combined_text, re.IGNORECASE):
                return {
                    "category": pattern_group["category"],
                    "retryable": pattern_group["retryable"],
                    "suggestion": pattern_group["suggestion"],
                    "matched_pattern": pattern
                }

    # Default: unknown failure
    return {
        "category": "unknown",
        "retryable": True,
        "suggestion": "Unknown failure. Review raw output manually.",
        "matched_pattern": None
    }
```

**Step 4: Run tests to verify they pass**

Run: `cd /home/reid/testhome/permit-scraper && pytest tests/services/browser_scraper/test_failure_classifier.py -v`

Expected: All 6 tests PASS

**Step 5: Commit**

```bash
git add services/browser_scraper/failure_classifier.py tests/services/browser_scraper/test_failure_classifier.py
git commit -m "feat: add failure classifier for browser-use scraper"
```

---

## Task 3: Create Shepherd CLI

**Files:**
- Create: `services/browser_scraper/shepherd.py`
- Modify: `services/browser_scraper/runner.py` (minor integration)

**Step 1: Write the shepherd CLI**

Create file `services/browser_scraper/shepherd.py`:

```python
#!/usr/bin/env python3
"""
Shepherd CLI for browser-use scraper.

Runs one city at a time with human review between each.
Tracks status and prevents infinite retry loops.

Usage:
    python -m services.browser_scraper.shepherd --next
    python -m services.browser_scraper.shepherd --city Dallas
    python -m services.browser_scraper.shepherd --status
    python -m services.browser_scraper.shepherd --skip Irving --reason "portal down"
    python -m services.browser_scraper.shepherd --reset Dallas
    python -m services.browser_scraper.shepherd --auto  # Continuous mode until stopped
"""

import asyncio
import argparse
import json
import sys
from pathlib import Path
from typing import Optional

from .status_tracker import CityStatusTracker
from .failure_classifier import classify_failure
from .runner import PermitScraperRunner
from .utils import logger

# Load target cities
CITIES_FILE = Path("data/target_cities.json")

def load_target_cities():
    if CITIES_FILE.exists():
        with open(CITIES_FILE) as f:
            return json.load(f)
    return []

def print_status_summary(tracker: CityStatusTracker, all_cities: list):
    """Print a summary table of city statuses."""
    print("\n" + "="*60)
    print("CITY STATUS SUMMARY")
    print("="*60)

    summary = tracker.get_summary()
    pending = tracker.get_pending_cities(all_cities)

    print(f"\nPending:              {len(pending)}")
    print(f"Success:              {summary.get('success', 0)}")
    print(f"Failed (retryable):   {summary.get('failed', 0)}")
    print(f"Needs manual review:  {summary.get('needs_manual_review', 0)}")
    print(f"Skipped:              {summary.get('skipped', 0)}")
    print(f"Total:                {len(all_cities)}")

    # Show next 5 pending
    if pending:
        print(f"\nNext pending cities: {pending[:5]}")

    # Show cities needing review
    needs_review = [c for c in all_cities if tracker.get_status(c) == "needs_manual_review"]
    if needs_review:
        print(f"\nNeeds manual review: {needs_review}")

    print("="*60 + "\n")

async def run_single_city(city: str, tracker: CityStatusTracker, mode: str = "bulk", days: int = 30):
    """Run scraper for a single city and handle result."""
    import datetime

    # Calculate date range
    end = datetime.datetime.now()
    start = end - datetime.timedelta(days=days)
    end_date = end.strftime("%m/%d/%Y")
    start_date = start.strftime("%m/%d/%Y")

    print(f"\n{'='*60}")
    print(f"SCRAPING: {city}")
    print(f"Date range: {start_date} to {end_date}")
    print(f"{'='*60}\n")

    # Get current attempt count
    city_data = tracker.get_city_data(city)
    attempt = city_data.get("attempts", 0) + 1

    if attempt > 2:
        print(f"⚠️  {city} has already failed {attempt-1} times. Marked for manual review.")
        return False

    print(f"Attempt {attempt}/2")

    runner = PermitScraperRunner()
    try:
        result = await runner.scrape_permit(
            city=city,
            address="",
            permit_type="Building",
            mode=mode,
            start_date=start_date,
            end_date=end_date
        )

        if result["success"]:
            # Count permits
            data = result.get("data", {})
            if isinstance(data, list):
                count = len(data)
            elif isinstance(data, dict) and "permits" in data:
                count = len(data["permits"])
            else:
                count = 1 if data else 0

            tracker.mark_success(city, permits_count=count)
            print(f"\n✅ SUCCESS: {city} - {count} permits extracted")
            return True
        else:
            # Classify failure
            raw = result.get("data", {}).get("raw_output", "")
            error = result.get("error", "")
            failure = classify_failure(raw, error)

            tracker.mark_failure(city, reason=failure["category"], attempt=attempt)

            print(f"\n❌ FAILED: {city}")
            print(f"   Category: {failure['category']}")
            print(f"   Retryable: {failure['retryable']}")
            print(f"   Suggestion: {failure['suggestion']}")

            if not failure["retryable"]:
                tracker.mark_skipped(city, reason=failure["category"])
                print(f"   → Marked as skipped (not retryable)")

            return False

    except Exception as e:
        logger.error(f"Exception scraping {city}: {e}")
        tracker.mark_failure(city, reason=str(e), attempt=attempt)
        print(f"\n💥 EXCEPTION: {city} - {e}")
        return False

async def shepherd_next(tracker: CityStatusTracker, all_cities: list, mode: str = "bulk", days: int = 30):
    """Run the next pending city."""
    pending = tracker.get_pending_cities(all_cities)

    if not pending:
        print("🎉 All cities processed! Nothing pending.")
        return None

    city = pending[0]
    success = await run_single_city(city, tracker, mode, days)

    # Show updated status
    print_status_summary(tracker, all_cities)

    # Prompt for next action
    remaining = tracker.get_pending_cities(all_cities)
    if remaining:
        print(f"Next city would be: {remaining[0]}")
        print("\nRun again with --next to continue, or --city <name> to pick specific city.")

    return success

async def shepherd_auto(tracker: CityStatusTracker, all_cities: list, mode: str = "bulk", days: int = 30):
    """Run continuously until all cities done or interrupted."""
    print("🚀 AUTO MODE: Will process all pending cities.")
    print("Press Ctrl+C to stop at any time.\n")

    processed = 0
    successes = 0

    try:
        while True:
            pending = tracker.get_pending_cities(all_cities)
            if not pending:
                print("\n🎉 All cities processed!")
                break

            city = pending[0]
            success = await run_single_city(city, tracker, mode, days)
            processed += 1
            if success:
                successes += 1

            print(f"\nProgress: {processed} processed, {successes} successful")
            print(f"Remaining: {len(pending) - 1} cities\n")

            # Small delay between cities
            await asyncio.sleep(2)

    except KeyboardInterrupt:
        print("\n\n⏸️  Stopped by user.")

    print_status_summary(tracker, all_cities)
    print(f"Session total: {processed} processed, {successes} successful")

def main():
    parser = argparse.ArgumentParser(description="Shepherd browser-use scraper")
    parser.add_argument("--next", action="store_true", help="Run next pending city")
    parser.add_argument("--city", type=str, help="Run specific city")
    parser.add_argument("--status", action="store_true", help="Show status summary")
    parser.add_argument("--skip", type=str, help="Mark city as skipped")
    parser.add_argument("--reason", type=str, default="manual skip", help="Reason for skip")
    parser.add_argument("--reset", type=str, help="Reset city status to pending")
    parser.add_argument("--auto", action="store_true", help="Run all pending cities continuously")
    parser.add_argument("--mode", default="bulk", choices=["single", "bulk"], help="Scraping mode")
    parser.add_argument("--days", type=int, default=30, help="Days of permits to fetch (bulk mode)")

    args = parser.parse_args()

    all_cities = load_target_cities()
    tracker = CityStatusTracker()

    if args.status:
        print_status_summary(tracker, all_cities)
        return

    if args.skip:
        tracker.mark_skipped(args.skip, args.reason)
        print(f"Marked {args.skip} as skipped: {args.reason}")
        return

    if args.reset:
        tracker.reset_city(args.reset)
        print(f"Reset {args.reset} to pending")
        return

    if args.city:
        asyncio.run(run_single_city(args.city, tracker, args.mode, args.days))
        print_status_summary(tracker, all_cities)
        return

    if args.next:
        asyncio.run(shepherd_next(tracker, all_cities, args.mode, args.days))
        return

    if args.auto:
        asyncio.run(shepherd_auto(tracker, all_cities, args.mode, args.days))
        return

    # Default: show status
    print_status_summary(tracker, all_cities)
    print("Usage:")
    print("  --next          Run next pending city")
    print("  --city <name>   Run specific city")
    print("  --auto          Run all pending continuously")
    print("  --status        Show status summary")
    print("  --skip <city>   Skip a city")
    print("  --reset <city>  Reset city to pending")

if __name__ == "__main__":
    main()
```

**Step 2: Test manually**

Run: `cd /home/reid/testhome/permit-scraper && python -m services.browser_scraper.shepherd --status`

Expected: Shows status summary with 50 pending cities

**Step 3: Commit**

```bash
git add services/browser_scraper/shepherd.py
git commit -m "feat: add shepherd CLI for guided browser-use scraping"
```

---

## Task 4: Add Prompt Refinement for Retries

**Files:**
- Modify: `services/browser_scraper/permit_tasks.py`

**Step 1: Add retry-aware prompt generation**

Add to `services/browser_scraper/permit_tasks.py` at the end:

```python
# Retry hint templates based on failure category
RETRY_HINTS = {
    "date_picker_blocked": """
IMPORTANT: The date picker has issues. Try this instead:
1. Look for text input fields for dates (not calendar popups)
2. If text inputs exist, type the date directly as MM/DD/YYYY
3. If only calendar popup exists, try using JavaScript:
   document.querySelector('[name*="date"]').value = '{start_date}'
4. After setting dates, immediately click Search
""",
    "shadow_dom_blocked": """
IMPORTANT: Some dropdowns use Shadow DOM. Try this:
1. Instead of clicking dropdowns, type directly in any visible search/filter box
2. If a dropdown must be used, try pressing Enter or Tab after typing
3. Skip dropdown selection if you can search by other means (address, keyword)
""",
    "json_parse_failure": """
CRITICAL: You MUST return ONLY valid JSON.
- No explanations before or after the JSON
- No markdown code blocks
- Just the raw JSON array or object
- If you cannot extract data, return: {"error": "description", "permits": []}
""",
    "max_steps_exceeded": """
EFFICIENCY: Complete this task in fewer steps:
1. Go directly to the search page URL if known
2. Fill all form fields at once before clicking Search
3. Extract data from the first page only (don't paginate)
4. Return JSON immediately after extraction
""",
}

def get_task_with_retry_hints(city: str, failure_category: str = None, **kwargs) -> str:
    """
    Get task template with optional retry hints based on previous failure.
    """
    base_task = get_task_for_city(city, **kwargs)

    if failure_category and failure_category in RETRY_HINTS:
        hint = RETRY_HINTS[failure_category].format(**kwargs)
        return f"{hint}\n\n{base_task}"

    return base_task
```

**Step 2: Update shepherd to use retry hints**

Modify `services/browser_scraper/shepherd.py` - update the `run_single_city` function to pass failure hints.

In `run_single_city`, after getting `city_data`, add:

```python
    # Get previous failure reason for retry hints
    prev_failure = city_data.get("last_failure_reason")
```

Then modify the runner call to use hints (this requires updating runner.py to accept hints).

**Step 3: Commit**

```bash
git add services/browser_scraper/permit_tasks.py services/browser_scraper/shepherd.py
git commit -m "feat: add retry hints based on failure category"
```

---

## Task 5: Create Integration Test

**Files:**
- Create: `tests/services/browser_scraper/test_shepherd_integration.py`

**Step 1: Write integration test (mocked)**

```python
import pytest
import json
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

from services.browser_scraper.shepherd import run_single_city, shepherd_next
from services.browser_scraper.status_tracker import CityStatusTracker

@pytest.fixture
def temp_status_file(tmp_path):
    return tmp_path / "city_status.json"

@pytest.fixture
def mock_cities():
    return ["Dallas", "Irving", "Frisco"]

@pytest.mark.asyncio
async def test_successful_scrape_updates_tracker(temp_status_file):
    tracker = CityStatusTracker(str(temp_status_file))

    with patch('services.browser_scraper.shepherd.PermitScraperRunner') as MockRunner:
        mock_runner = MagicMock()
        mock_runner.scrape_permit = AsyncMock(return_value={
            "success": True,
            "data": [{"permit_number": "123"}],
            "error": None
        })
        MockRunner.return_value = mock_runner

        result = await run_single_city("Dallas", tracker)

        assert result == True
        assert tracker.get_status("Dallas") == "success"

@pytest.mark.asyncio
async def test_failed_scrape_classifies_failure(temp_status_file):
    tracker = CityStatusTracker(str(temp_status_file))

    with patch('services.browser_scraper.shepherd.PermitScraperRunner') as MockRunner:
        mock_runner = MagicMock()
        mock_runner.scrape_permit = AsyncMock(return_value={
            "success": False,
            "data": {"raw_output": "Failed to set date range due to date picker issues"},
            "error": None
        })
        MockRunner.return_value = mock_runner

        result = await run_single_city("Irving", tracker)

        assert result == False
        data = tracker.get_city_data("Irving")
        assert data["last_failure_reason"] == "date_picker_blocked"

@pytest.mark.asyncio
async def test_second_failure_marks_for_review(temp_status_file):
    tracker = CityStatusTracker(str(temp_status_file))
    # Simulate first failure
    tracker.mark_failure("Irving", "date_picker_blocked", attempt=1)

    with patch('services.browser_scraper.shepherd.PermitScraperRunner') as MockRunner:
        mock_runner = MagicMock()
        mock_runner.scrape_permit = AsyncMock(return_value={
            "success": False,
            "data": {"raw_output": "Same issue again"},
            "error": None
        })
        MockRunner.return_value = mock_runner

        result = await run_single_city("Irving", tracker)

        assert result == False
        assert tracker.get_status("Irving") == "needs_manual_review"
```

**Step 2: Run tests**

Run: `cd /home/reid/testhome/permit-scraper && pytest tests/services/browser_scraper/test_shepherd_integration.py -v`

Expected: All tests PASS

**Step 3: Commit**

```bash
git add tests/services/browser_scraper/test_shepherd_integration.py
git commit -m "test: add integration tests for shepherd CLI"
```

---

## Task 6: Add Convenience Scripts

**Files:**
- Create: `scripts/shepherd.sh`

**Step 1: Create wrapper script**

Create file `scripts/shepherd.sh`:

```bash
#!/bin/bash
# Shepherd wrapper script
# Usage: ./scripts/shepherd.sh [args]

set -e
cd "$(dirname "$0")/.."

# Load environment
if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

# Run shepherd
python3 -m services.browser_scraper.shepherd "$@"
```

**Step 2: Make executable**

```bash
chmod +x scripts/shepherd.sh
```

**Step 3: Commit**

```bash
git add scripts/shepherd.sh
git commit -m "feat: add shepherd wrapper script"
```

---

## Task 7: Update Documentation

**Files:**
- Modify: `CLAUDE.md`

**Step 1: Add shepherd section to CLAUDE.md**

Add after the "Common Commands" section:

```markdown
## Browser-Use Shepherd (AI-Guided Scraping)

Universal scraper using DeepSeek + browser-use. Processes cities one-by-one with status tracking.

### Quick Start
```bash
# Check status
./scripts/shepherd.sh --status

# Run next pending city
./scripts/shepherd.sh --next

# Run specific city
./scripts/shepherd.sh --city Dallas

# Auto mode (continuous until Ctrl+C)
./scripts/shepherd.sh --auto

# Skip a problematic city
./scripts/shepherd.sh --skip Irving --reason "portal requires login"

# Reset a city to retry
./scripts/shepherd.sh --reset Dallas
```

### Status Tracking
- Status stored in `data/city_status.json`
- Cities get max 2 retry attempts
- After 2 failures, marked "needs_manual_review"
- Use `--skip` for known-broken portals
```

**Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: add shepherd usage to CLAUDE.md"
```

---

## Verification Checklist

After completing all tasks, verify:

1. [ ] `pytest tests/services/browser_scraper/ -v` - All tests pass
2. [ ] `./scripts/shepherd.sh --status` - Shows 50 pending cities
3. [ ] `./scripts/shepherd.sh --city "Fort Worth"` - Runs successfully (known working city)
4. [ ] `cat data/city_status.json` - Shows Fort Worth as success
5. [ ] `./scripts/shepherd.sh --skip "Irving" --reason "test"` - Marks Irving skipped
6. [ ] `./scripts/shepherd.sh --reset Irving` - Resets Irving to pending

---

## Summary

| Task | Description | Files Changed |
|------|-------------|---------------|
| 1 | City status tracker | `status_tracker.py`, tests |
| 2 | Failure classifier | `failure_classifier.py`, tests |
| 3 | Shepherd CLI | `shepherd.py` |
| 4 | Retry hints | `permit_tasks.py` |
| 5 | Integration tests | test file |
| 6 | Wrapper script | `scripts/shepherd.sh` |
| 7 | Documentation | `CLAUDE.md` |

Total: 7 tasks, ~15-20 steps each
