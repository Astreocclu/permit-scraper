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
import glob
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

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


def analyze_failure(attempt: AttemptRecord) -> dict:
    """
    Analyze a failed attempt and return specific fixes.
    Returns dict with 'failure_type', 'root_cause', 'task_modification'.
    """
    error = (attempt.error or "").lower()
    actions = attempt.actions_taken or []
    last_actions = actions[-5:] if actions else []

    # Check for LLM/JSON output errors
    if any(x in error for x in ["invalid json", "validation error", "json_invalid", "field required", "llm json", "llm output", "malformed json", "deepseek"]):
        return {
            "failure_type": "llm_output_error",
            "root_cause": "DeepSeek returned malformed JSON during extraction",
            "task_modification": """
CRITICAL EXTRACTION RULES (DeepSeek compatibility):
- Extract MAXIMUM 10 permits per extraction call - DO NOT try to extract 50 at once
- Use simple field names without special characters
- If extraction fails, try extracting just permit_number and address first
- Avoid nested JSON structures in extraction queries
- Keep extraction queries under 200 characters
- DO NOT use JavaScript evaluate() for extraction - use the extract tool only
- If you need to extract from a large table, extract in chunks of 10 rows at a time
"""
        }

    # Check for extraction-specific failures
    if actions and actions[-1] == "extract":
        return {
            "failure_type": "extraction_failed",
            "root_cause": "Data extraction step failed",
            "task_modification": """
EXTRACTION STRATEGY:
- Break extraction into smaller chunks (5-10 items at a time)
- Extract basic fields first (permit_number, address), then details
- If page has infinite scroll, extract visible items before scrolling more
- Use simpler CSS selectors if possible
"""
        }

    # Check for navigation/timeout issues
    if any(x in error for x in ["timeout", "not found", "cannot find", "no element"]):
        return {
            "failure_type": "navigation_error",
            "root_cause": "Element not found or page timeout",
            "task_modification": """
NAVIGATION STRATEGY:
- Wait longer after page loads (5-10 seconds)
- Try alternative selectors (id, class, aria-label, text content)
- Check if element is in iframe or shadow DOM
- Scroll to bring element into view before clicking
"""
        }

    # Check for authentication issues
    if any(x in error for x in ["login", "401", "403", "unauthorized", "forbidden"]):
        return {
            "failure_type": "auth_required",
            "root_cause": "Authentication or access denied",
            "task_modification": None  # Can't fix without credentials
        }

    # Generic failure - look at actions for clues
    if "scroll" in last_actions and "extract" in last_actions:
        return {
            "failure_type": "scroll_extraction_issue",
            "root_cause": "Failed during scroll/extract cycle",
            "task_modification": """
SCROLL-EXTRACT STRATEGY:
- After scrolling, wait 2 seconds for content to load
- Extract items currently visible before scrolling again
- Track which items already extracted to avoid duplicates
- If page size dropdown exists, set to maximum (50 or 100)
"""
        }

    # Default - provide general guidance
    return {
        "failure_type": "unknown",
        "root_cause": attempt.error or "Unknown error",
        "task_modification": """
GENERAL RETRY STRATEGY:
- Wait for page to fully load before interacting
- Take screenshots before critical actions
- If stuck on same step 3+ times, try alternative approach
- Report any unexpected portal behavior in observations
"""
    }

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

    async def attempt_city(self, city: str) -> Tuple[bool, Optional[ScrapeContext]]:
        """Make one Browser-Use attempt for a city."""
        state = self.get_or_create_state(city)
        attempt_num = len(state.attempts) + 1

        print(f"\n{'='*60}")
        print(f"[{city}] Attempt {attempt_num}/{self.max_attempts}")
        print(f"{'='*60}")

        # Get task (possibly adjusted from previous attempts)
        # Use mode="bulk" with proper date range params (not address/permit_type)
        task = state.current_task or get_task_for_city(city, mode="bulk", start_date="2024-01-01", end_date="2024-12-24")
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

            # Build comprehensive error message
            error_msg = None

            # Filter out None values from errors list
            actual_errors = [e for e in (context.errors or []) if e is not None]

            if actual_errors:
                error_msg = actual_errors[0]
            elif not context.is_successful:
                # Check final_result for error clues
                result_str = str(context.final_result or "")

                if "error" in result_str.lower() or "fail" in result_str.lower():
                    error_msg = result_str[:500]
                elif "invalid json" in result_str.lower() or "validation" in result_str.lower():
                    error_msg = f"JSON validation error in result: {result_str[:200]}"
                elif not context.final_result or result_str.strip() in ["", "None", "null"]:
                    # No result + failure = likely LLM output error
                    # Check if actions end with "evaluate" - common pattern when DeepSeek JSON fails
                    last_actions = context.actions[-5:] if context.actions else []
                    if "evaluate" in last_actions:
                        error_msg = "LLM JSON validation error: DeepSeek returned malformed JSON during extraction (evaluate action failed)"
                    elif "extract" in last_actions:
                        error_msg = "LLM JSON validation error: DeepSeek returned malformed JSON during extraction"
                    else:
                        error_msg = "LLM output error: No result returned, likely JSON validation failure"
                else:
                    # Have some result but failed - check actions
                    if context.actions:
                        last_action = context.actions[-1] if context.actions else "unknown"
                        error_msg = f"Failed during/after action: {last_action}"
                    else:
                        error_msg = "Unknown error - no actions recorded"

            # Capture and save extracted content even if attempt failed
            # This preserves data extracted before the JSON error at the end
            extracted_data_saved = False
            if hasattr(context, 'extracted_content') and context.extracted_content:
                extracts_dir = Path("data/extracts") / city.lower().replace(" ", "_")
                extracts_dir.mkdir(parents=True, exist_ok=True)

                # Save each extraction chunk
                for i, content in enumerate(context.extracted_content):
                    chunk_file = extracts_dir / f"attempt{attempt_num}_chunk{i}.md"
                    try:
                        chunk_file.write_text(content)
                        print(f"  Saved extraction chunk: {chunk_file}")
                        extracted_data_saved = True
                    except Exception as e:
                        print(f"  Warning: Failed to save chunk {i}: {e}")

                # Also save combined file
                if context.extracted_content:
                    combined_file = extracts_dir / f"attempt{attempt_num}_combined.md"
                    try:
                        combined_file.write_text("\n\n---\n\n".join(context.extracted_content))
                        print(f"  Saved combined extractions: {combined_file}")
                    except Exception as e:
                        print(f"  Warning: Failed to save combined file: {e}")

            # Clean up Browser-Use temp files (move to city-specific dir)
            for temp_file in glob.glob("extracted_content_*.md"):
                try:
                    os.remove(temp_file)
                except:
                    pass

            # Record attempt
            attempt = AttemptRecord(
                attempt_num=attempt_num,
                timestamp=datetime.now().isoformat(),
                success=context.is_successful or False,
                error=error_msg,
                screenshot_paths=context.screenshot_paths or [],
                actions_taken=context.actions or [],
            )
            state.attempts.append(attempt)

            if context.is_successful:
                state.status = "success"
                state.final_result = str(context.final_result)
                print(f"  SUCCESS!")
            elif extracted_data_saved:
                print(f"  Failed but extracted data saved: {attempt.error}")
            else:
                print(f"  Failed: {attempt.error}")

            self.save_state()
            return context.is_successful or False, context

        except Exception as e:
            error_str = str(e)
            # Capture specific error types for better analysis
            if "invalid json" in error_str.lower() or "validation error" in error_str.lower():
                error_str = f"JSON validation error: {error_str[:300]}"
            elif "timeout" in error_str.lower():
                error_str = f"Timeout error: {error_str[:200]}"

            print(f"  Exception: {error_str}")
            attempt = AttemptRecord(
                attempt_num=attempt_num,
                timestamp=datetime.now().isoformat(),
                success=False,
                error=error_str,
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
                "pending": "[PENDING]",
                "in_progress": "[RUNNING]",
                "success": "[SUCCESS]",
                "failed": "[FAILED]",
                "blocked": "[BLOCKED]",
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
    parser.add_argument("--delay", type=int, default=5, help="Delay between retries (seconds)")
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

    # AUTONOMOUS LOOP: Keep retrying until all cities are done
    iteration = 0
    while True:
        iteration += 1
        pending = orchestrator.get_pending_cities(cities)

        if not pending:
            print(f"\n{'='*60}")
            print("ALL CITIES COMPLETE (success, blocked, or max attempts reached)")
            break

        print(f"\n{'='*60}")
        print(f"ITERATION {iteration} - {len(pending)} cities remaining: {pending}")
        print(f"{'='*60}")

        for city in pending:
            state = orchestrator.get_or_create_state(city)

            # Check if we've hit max attempts
            if len(state.attempts) >= args.max_attempts:
                print(f"[{city}] Max attempts ({args.max_attempts}) reached - marking as failed")
                state.status = "failed"
                state.final_result = f"FAILED after {args.max_attempts} attempts"
                orchestrator.save_state()
                continue

            # If last attempt failed, apply intelligent analysis before retry
            if state.attempts and not state.attempts[-1].success:
                last = state.attempts[-1]

                # Run intelligent failure analysis
                analysis = analyze_failure(last)
                failure_type = analysis["failure_type"]
                root_cause = analysis["root_cause"]
                task_mod = analysis.get("task_modification")

                print(f"[{city}] Failure analysis for attempt {last.attempt_num}:")
                print(f"  Type: {failure_type}")
                print(f"  Cause: {root_cause}")

                # Record analysis in attempt
                last.analysis = root_cause
                last.adjustment = task_mod[:100] if task_mod else None

                # Check if failure is unrecoverable
                if failure_type == "auth_required":
                    print(f"[{city}] BLOCKED - authentication required, cannot retry")
                    state.status = "blocked"
                    state.final_result = f"BLOCKED: {root_cause}"
                    orchestrator.save_state()
                    continue

                # Build task with specific fixes
                if task_mod:
                    base_task = get_task_for_city(city, mode="bulk", start_date="2024-01-01", end_date="2024-12-24")

                    # Include failure context and specific fix instructions
                    state.current_task = f"""{base_task}

PREVIOUS ATTEMPT FAILED - APPLY THESE FIXES:
Failure type: {failure_type}
Root cause: {root_cause}

{task_mod}

If this approach still fails, simplify further and report what's blocking progress.
"""
                    print(f"[{city}] Applied {failure_type} fixes to task")
                    orchestrator.save_state()

            # Make the attempt
            success, context = await orchestrator.attempt_city(city)

            if success:
                print(f"[{city}] SUCCESS!")
            else:
                remaining = args.max_attempts - len(state.attempts)
                if remaining > 0:
                    print(f"[{city}] Failed - {remaining} attempts remaining, will retry...")
                else:
                    print(f"[{city}] Failed - no attempts remaining")

            # Brief delay between cities
            if pending.index(city) < len(pending) - 1:
                await asyncio.sleep(args.delay)

        # Delay between iterations
        remaining_cities = orchestrator.get_pending_cities(cities)
        if remaining_cities:
            print(f"\n--- Waiting {args.delay}s before next iteration ---")
            await asyncio.sleep(args.delay)

    orchestrator.print_summary()
    print(f"\nState saved to: {STATE_FILE}")


if __name__ == "__main__":
    asyncio.run(main())
