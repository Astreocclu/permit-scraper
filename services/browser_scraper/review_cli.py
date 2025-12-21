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
