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
