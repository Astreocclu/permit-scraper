> LEGACY (archived 2026-01-31): Historical plan; superseded by current priorities.

# Autonomous Shepherding Loop Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build an overnight autonomous loop where DeepSeek attempts scraping, Claude Code analyzes failures via screenshots, adjusts approach, and retries until success.

**Architecture:** Two-tier system - cheap DeepSeek for browsing attempts, Claude Code vision for failure analysis. Loop continues until success or max attempts per city.

**Tech Stack:** Browser-Use, DeepSeek API, Playwright, Python asyncio

---

## Task 1: Create State Tracking Model

**Files:**
- Modify: `services/browser_scraper/models.py`

**Step 1: Add ShepherdState dataclass**

```python
# Add to models.py after ScrapeContext

@dataclass
class AttemptRecord:
    """Record of a single scraping attempt."""
    attempt_num: int
    timestamp: str
    success: bool
    error: Optional[str] = None
    screenshot_paths: List[str] = field(default_factory=list)
    actions_taken: List[str] = field(default_factory=list)
    analysis: Optional[str] = None  # Claude's analysis of what went wrong
    adjustment: Optional[str] = None  # What was changed for next attempt

@dataclass
class CityShepherdState:
    """Track shepherding progress for a city."""
    city: str
    status: str  # "pending", "in_progress", "success", "failed", "blocked"
    attempts: List[AttemptRecord] = field(default_factory=list)
    current_task: Optional[str] = None  # The task template being used
    task_adjustments: List[str] = field(default_factory=list)  # History of modifications
    final_result: Optional[str] = None
    permits_extracted: int = 0
```

**Step 2: Verify**

```bash
source venv/bin/activate
python3 -c "from services.browser_scraper.models import AttemptRecord, CityShepherdState; print('OK')"
```

---

## Task 2: Create Failure Analyzer

**Files:**
- Create: `services/browser_scraper/analyzer.py`

**Step 1: Write the analyzer module**

```python
"""
Failure Analyzer - Claude Code analyzes Browser-Use failures via screenshots.

This module is designed to be called BY Claude Code (not as standalone).
It provides structured analysis of what went wrong and suggests adjustments.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict

@dataclass
class FailureAnalysis:
    """Structured analysis of a scraping failure."""
    root_cause: str  # What went wrong
    portal_state: str  # What the portal is showing
    suggested_fix: str  # How to adjust the approach
    confidence: float  # 0-1 confidence in analysis
    needs_manual_verification: bool  # Should Claude use Playwright to verify?

def get_latest_screenshots(city: str, n: int = 3) -> List[Path]:
    """Get the N most recent screenshots for a city."""
    screenshots_dir = Path("data/screenshots") / city.lower().replace(" ", "_")
    if not screenshots_dir.exists():
        return []

    pngs = sorted(screenshots_dir.glob("*.png"), key=lambda p: p.stat().st_mtime, reverse=True)
    return pngs[:n]

def get_attempt_context(city: str) -> Dict:
    """Load the most recent attempt context from review queue."""
    review_dir = Path("data/review_queue/pending")
    city_file = review_dir / f"{city.lower()}.json"

    if city_file.exists():
        with open(city_file) as f:
            return json.load(f)
    return {}

def format_analysis_prompt(city: str, error: str, screenshot_paths: List[Path]) -> str:
    """Format a prompt for Claude to analyze the failure.

    Note: This returns a prompt string. The actual analysis happens when
    Claude Code reads the screenshots and this prompt together.
    """
    return f"""## Browser-Use Failure Analysis Request

**City:** {city}
**Error:** {error}

**Screenshots:** {[str(p) for p in screenshot_paths]}

Please analyze these screenshots and the error to determine:
1. **Root Cause**: What specifically went wrong? (e.g., wrong selector, portal changed, date format issue)
2. **Portal State**: What is the portal currently showing?
3. **Suggested Fix**: How should the task template be modified?
4. **Confidence**: How confident are you in this analysis? (0-1)
5. **Manual Verification Needed**: Should we use Playwright to manually test before retrying?

Return your analysis as a FailureAnalysis object.
"""

def save_analysis(city: str, analysis: FailureAnalysis, attempt_num: int):
    """Save analysis to the review queue."""
    analysis_dir = Path("data/review_queue/analyzed")
    analysis_dir.mkdir(parents=True, exist_ok=True)

    output_file = analysis_dir / f"{city.lower()}_attempt_{attempt_num}.json"
    with open(output_file, 'w') as f:
        json.dump(asdict(analysis), f, indent=2)
```

**Step 2: Verify**

```bash
python3 -c "from services.browser_scraper.analyzer import FailureAnalysis, get_latest_screenshots; print('OK')"
```

---

## Task 3: Create Shepherd Orchestrator

**Files:**
- Create: `scripts/shepherd_loop.py`

**Step 1: Write the orchestrator**

```python
#!/usr/bin/env python3
"""
Autonomous Shepherding Loop

Runs Browser-Use attempts, analyzes failures, adjusts, and retries.
Designed to run overnight with Claude Code monitoring.

Usage:
    python3 scripts/shepherd_loop.py --cities southlake sachse anna
    python3 scripts/shepherd_loop.py --all --max-attempts 3
    python3 scripts/shepherd_loop.py --resume  # Continue from saved state
"""

import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from services.browser_scraper.agent import PermitScraperAgent
from services.browser_scraper.permit_tasks import get_task_for_city, CITY_TASKS
from services.browser_scraper.models import ScrapeContext, AttemptRecord, CityShepherdState
from services.browser_scraper.analyzer import (
    get_latest_screenshots,
    format_analysis_prompt,
    save_analysis,
    FailureAnalysis
)

STATE_FILE = Path("data/shepherd_state.json")

class ShepherdOrchestrator:
    def __init__(self, max_attempts: int = 3):
        self.max_attempts = max_attempts
        self.state: dict[str, CityShepherdState] = {}
        self.load_state()

    def load_state(self):
        """Load state from disk."""
        if STATE_FILE.exists():
            with open(STATE_FILE) as f:
                data = json.load(f)
                for city, state_dict in data.items():
                    # Reconstruct dataclass from dict
                    attempts = [AttemptRecord(**a) for a in state_dict.get('attempts', [])]
                    self.state[city] = CityShepherdState(
                        city=city,
                        status=state_dict.get('status', 'pending'),
                        attempts=attempts,
                        current_task=state_dict.get('current_task'),
                        task_adjustments=state_dict.get('task_adjustments', []),
                        final_result=state_dict.get('final_result'),
                        permits_extracted=state_dict.get('permits_extracted', 0),
                    )

    def save_state(self):
        """Save state to disk."""
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)

        data = {}
        for city, state in self.state.items():
            data[city] = {
                'city': state.city,
                'status': state.status,
                'attempts': [
                    {
                        'attempt_num': a.attempt_num,
                        'timestamp': a.timestamp,
                        'success': a.success,
                        'error': a.error,
                        'screenshot_paths': a.screenshot_paths,
                        'actions_taken': a.actions_taken,
                        'analysis': a.analysis,
                        'adjustment': a.adjustment,
                    }
                    for a in state.attempts
                ],
                'current_task': state.current_task,
                'task_adjustments': state.task_adjustments,
                'final_result': state.final_result,
                'permits_extracted': state.permits_extracted,
            }

        with open(STATE_FILE, 'w') as f:
            json.dump(data, f, indent=2)

    def get_or_create_state(self, city: str) -> CityShepherdState:
        """Get existing state or create new one for city."""
        if city not in self.state:
            self.state[city] = CityShepherdState(city=city, status="pending")
        return self.state[city]

    async def attempt_city(self, city: str) -> Tuple[bool, ScrapeContext]:
        """Make one Browser-Use attempt for a city."""
        state = self.get_or_create_state(city)
        attempt_num = len(state.attempts) + 1

        print(f"\n{'='*60}")
        print(f"[{city}] Attempt {attempt_num}/{self.max_attempts}")
        print(f"{'='*60}")

        # Get task (possibly adjusted from previous attempts)
        task = state.current_task or get_task_for_city(city, "2024-01-01", "2024-12-24")
        if not task:
            print(f"  No task template for {city}")
            return False, None

        state.current_task = task
        state.status = "in_progress"
        self.save_state()

        # Run Browser-Use
        try:
            agent = PermitScraperAgent(headless=True, model="deepseek")
            context = await agent.run_task(task, city)

            # Record attempt
            attempt = AttemptRecord(
                attempt_num=attempt_num,
                timestamp=datetime.now().isoformat(),
                success=context.is_successful or False,
                error=context.errors[0] if context.errors else None,
                screenshot_paths=context.screenshot_paths or [],
                actions_taken=context.actions or [],
            )
            state.attempts.append(attempt)

            if context.is_successful:
                state.status = "success"
                state.final_result = str(context.final_result)
                print(f"  ✓ SUCCESS!")
            else:
                print(f"  ✗ Failed: {attempt.error or 'Unknown error'}")

            self.save_state()
            return context.is_successful or False, context

        except Exception as e:
            print(f"  ✗ Exception: {e}")
            attempt = AttemptRecord(
                attempt_num=attempt_num,
                timestamp=datetime.now().isoformat(),
                success=False,
                error=str(e),
            )
            state.attempts.append(attempt)
            self.save_state()
            return False, None

    def needs_analysis(self, city: str) -> bool:
        """Check if city needs Claude analysis."""
        state = self.get_or_create_state(city)
        if state.status in ["success", "blocked"]:
            return False
        if len(state.attempts) >= self.max_attempts:
            return False
        if not state.attempts:
            return False
        # Need analysis if last attempt failed and wasn't analyzed yet
        last_attempt = state.attempts[-1]
        return not last_attempt.success and not last_attempt.analysis

    def get_analysis_request(self, city: str) -> Optional[str]:
        """Get the analysis request for Claude to process."""
        state = self.get_or_create_state(city)
        if not self.needs_analysis(city):
            return None

        last_attempt = state.attempts[-1]
        screenshots = get_latest_screenshots(city)

        return format_analysis_prompt(
            city=city,
            error=last_attempt.error or "Unknown",
            screenshot_paths=screenshots
        )

    def apply_analysis(self, city: str, analysis: FailureAnalysis, adjusted_task: Optional[str] = None):
        """Apply Claude's analysis and prepare for retry."""
        state = self.get_or_create_state(city)
        if not state.attempts:
            return

        last_attempt = state.attempts[-1]
        last_attempt.analysis = analysis.root_cause
        last_attempt.adjustment = analysis.suggested_fix

        if adjusted_task:
            state.current_task = adjusted_task
            state.task_adjustments.append(f"Attempt {last_attempt.attempt_num}: {analysis.suggested_fix}")

        save_analysis(city, analysis, last_attempt.attempt_num)
        self.save_state()

    def mark_blocked(self, city: str, reason: str):
        """Mark city as blocked (can't be scraped)."""
        state = self.get_or_create_state(city)
        state.status = "blocked"
        state.final_result = f"BLOCKED: {reason}"
        self.save_state()

    def get_pending_cities(self, cities: List[str]) -> List[str]:
        """Get cities that still need work."""
        pending = []
        for city in cities:
            state = self.get_or_create_state(city)
            if state.status not in ["success", "blocked"]:
                if len(state.attempts) < self.max_attempts:
                    pending.append(city)
        return pending

    def print_summary(self):
        """Print current state summary."""
        print(f"\n{'='*60}")
        print("SHEPHERD STATE SUMMARY")
        print(f"{'='*60}")

        for city, state in sorted(self.state.items()):
            status_emoji = {
                "pending": "⏳",
                "in_progress": "🔄",
                "success": "✅",
                "failed": "❌",
                "blocked": "🚫",
            }.get(state.status, "?")

            print(f"{status_emoji} {city}: {state.status} ({len(state.attempts)} attempts)")
            if state.attempts and not state.attempts[-1].success:
                print(f"   Last error: {state.attempts[-1].error or 'Unknown'}")


async def main():
    parser = argparse.ArgumentParser(description="Autonomous Shepherding Loop")
    parser.add_argument("--cities", nargs="+", help="Cities to process")
    parser.add_argument("--all", action="store_true", help="Process all configured cities")
    parser.add_argument("--max-attempts", type=int, default=3, help="Max attempts per city")
    parser.add_argument("--resume", action="store_true", help="Resume from saved state")
    parser.add_argument("--status", action="store_true", help="Just print status and exit")
    args = parser.parse_args()

    orchestrator = ShepherdOrchestrator(max_attempts=args.max_attempts)

    if args.status:
        orchestrator.print_summary()
        return

    # Determine cities to process
    if args.all:
        cities = list(CITY_TASKS.keys())
    elif args.cities:
        cities = args.cities
    else:
        print("Specify --cities or --all")
        return

    print(f"Shepherd Loop Starting")
    print(f"Cities: {len(cities)}")
    print(f"Max attempts per city: {args.max_attempts}")

    # Initial attempt for all pending cities
    pending = orchestrator.get_pending_cities(cities)

    for city in pending:
        success, context = await orchestrator.attempt_city(city)

        if not success and orchestrator.needs_analysis(city):
            print(f"\n>>> ANALYSIS NEEDED FOR {city} <<<")
            print(orchestrator.get_analysis_request(city))
            print(">>> Claude Code should now analyze and call apply_analysis() <<<\n")

    orchestrator.print_summary()
    print(f"\nState saved to: {STATE_FILE}")


if __name__ == "__main__":
    asyncio.run(main())
```

**Step 2: Verify**

```bash
python3 scripts/shepherd_loop.py --status
```

---

## Task 4: Create Claude Integration Helper

**Files:**
- Create: `scripts/shepherd_analyze.py`

**Purpose:** Helper script for Claude Code to easily analyze failures and apply fixes.

**Step 1: Write helper script**

```python
#!/usr/bin/env python3
"""
Helper for Claude Code to analyze and fix shepherd failures.

Usage (by Claude Code):
    # Check what needs analysis
    python3 scripts/shepherd_analyze.py --needs-analysis

    # Get screenshots for a city
    python3 scripts/shepherd_analyze.py --show southlake

    # Apply analysis after Claude reviews
    python3 scripts/shepherd_analyze.py --apply southlake \
        --cause "Wrong search field" \
        --fix "Use address field instead of date" \
        --confidence 0.9

    # Mark as blocked
    python3 scripts/shepherd_analyze.py --block southlake --reason "Portal requires login"
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.browser_scraper.analyzer import (
    FailureAnalysis,
    get_latest_screenshots,
)

STATE_FILE = Path("data/shepherd_state.json")

def load_state():
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {}

def get_needs_analysis():
    """List cities that need Claude's analysis."""
    state = load_state()
    needs = []

    for city, data in state.items():
        if data.get('status') in ['success', 'blocked']:
            continue
        attempts = data.get('attempts', [])
        if attempts:
            last = attempts[-1]
            if not last.get('success') and not last.get('analysis'):
                needs.append({
                    'city': city,
                    'attempts': len(attempts),
                    'last_error': last.get('error'),
                    'screenshots': [str(p) for p in get_latest_screenshots(city)],
                })

    return needs

def show_city(city: str):
    """Show details for a city including screenshot paths."""
    state = load_state()
    data = state.get(city.lower(), {})

    print(f"City: {city}")
    print(f"Status: {data.get('status', 'unknown')}")
    print(f"Attempts: {len(data.get('attempts', []))}")

    if data.get('attempts'):
        last = data['attempts'][-1]
        print(f"Last error: {last.get('error')}")
        print(f"Last actions: {last.get('actions_taken', [])[:5]}...")

    screenshots = get_latest_screenshots(city)
    print(f"\nScreenshots to analyze:")
    for s in screenshots:
        print(f"  {s}")

    print(f"\n>>> Use Read tool on screenshots above <<<")

def apply_analysis(city: str, cause: str, fix: str, confidence: float, portal_state: str = ""):
    """Apply Claude's analysis to the state."""
    # Import here to avoid circular
    from scripts.shepherd_loop import ShepherdOrchestrator

    orchestrator = ShepherdOrchestrator()
    analysis = FailureAnalysis(
        root_cause=cause,
        portal_state=portal_state,
        suggested_fix=fix,
        confidence=confidence,
        needs_manual_verification=confidence < 0.7,
    )

    orchestrator.apply_analysis(city, analysis)
    print(f"Analysis applied for {city}")
    print(f"  Root cause: {cause}")
    print(f"  Fix: {fix}")
    print(f"Ready for retry!")

def block_city(city: str, reason: str):
    """Mark city as blocked."""
    from scripts.shepherd_loop import ShepherdOrchestrator

    orchestrator = ShepherdOrchestrator()
    orchestrator.mark_blocked(city, reason)
    print(f"Marked {city} as BLOCKED: {reason}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--needs-analysis", action="store_true")
    parser.add_argument("--show", type=str)
    parser.add_argument("--apply", type=str)
    parser.add_argument("--cause", type=str)
    parser.add_argument("--fix", type=str)
    parser.add_argument("--confidence", type=float, default=0.8)
    parser.add_argument("--portal-state", type=str, default="")
    parser.add_argument("--block", type=str)
    parser.add_argument("--reason", type=str)
    args = parser.parse_args()

    if args.needs_analysis:
        needs = get_needs_analysis()
        if not needs:
            print("No cities need analysis!")
        else:
            print(f"{len(needs)} cities need analysis:\n")
            for item in needs:
                print(f"  {item['city']}: {item['last_error']}")
                for s in item['screenshots'][:1]:
                    print(f"    Screenshot: {s}")

    elif args.show:
        show_city(args.show)

    elif args.apply:
        if not args.cause or not args.fix:
            print("--apply requires --cause and --fix")
            return
        apply_analysis(args.apply, args.cause, args.fix, args.confidence, args.portal_state)

    elif args.block:
        if not args.reason:
            print("--block requires --reason")
            return
        block_city(args.block, args.reason)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
```

**Step 2: Verify**

```bash
python3 scripts/shepherd_analyze.py --needs-analysis
```

---

## Task 5: Update permit_tasks.py for Dynamic Adjustments

**Files:**
- Modify: `services/browser_scraper/permit_tasks.py`

**Step 1: Add function to update task at runtime**

```python
# Add at end of permit_tasks.py

def update_city_task(city: str, new_task: str):
    """Update the task template for a city (runtime only, not persisted)."""
    CITY_TASKS[city.lower()] = new_task

def get_task_with_hints(city: str, start_date: str, end_date: str, hints: list[str] = None) -> str:
    """Get task with additional hints from previous failure analysis."""
    base_task = get_task_for_city(city, start_date, end_date)
    if not base_task or not hints:
        return base_task

    hints_text = "\n".join(f"- {h}" for h in hints)
    return f"""{base_task}

IMPORTANT HINTS FROM PREVIOUS ATTEMPTS:
{hints_text}
"""
```

**Step 2: Verify**

```bash
python3 -c "from services.browser_scraper.permit_tasks import update_city_task, get_task_with_hints; print('OK')"
```

---

## Task 6: Test the Full Loop

**Step 1: Run initial attempt on one city**

```bash
source venv/bin/activate && source .env
python3 scripts/shepherd_loop.py --cities southlake --max-attempts 1
```

**Step 2: Check what needs analysis**

```bash
python3 scripts/shepherd_analyze.py --needs-analysis
```

**Step 3: Show city details (Claude reads screenshots)**

```bash
python3 scripts/shepherd_analyze.py --show southlake
```

**Step 4: Claude analyzes and applies fix**

```bash
# After Claude reads screenshots and understands the issue:
python3 scripts/shepherd_analyze.py --apply southlake \
    --cause "Searched for date string instead of using date picker" \
    --fix "Click Advanced, use date range fields instead of main search box" \
    --confidence 0.85
```

**Step 5: Retry**

```bash
python3 scripts/shepherd_loop.py --cities southlake --resume
```

---

## Summary

| Phase | Description |
|-------|-------------|
| Attempt | `shepherd_loop.py` runs Browser-Use with DeepSeek |
| Capture | Screenshots + logs saved automatically |
| Analyze | Claude Code reads screenshots, runs `shepherd_analyze.py --show` |
| Fix | Claude applies analysis via `shepherd_analyze.py --apply` |
| Retry | Loop continues with `--resume` |

**Expected Workflow (Overnight):**

```bash
# Start the loop
python3 scripts/shepherd_loop.py --cities southlake sachse anna --max-attempts 3

# When it pauses for analysis, Claude Code:
# 1. Reads the screenshots
# 2. Identifies the issue
# 3. Applies the fix
# 4. Continues the loop

# Check progress anytime
python3 scripts/shepherd_loop.py --status
```

**Cost:** Only DeepSeek API costs (~$0.01-0.05 per city). Claude Code analysis is "free" (part of your Claude Code session).
