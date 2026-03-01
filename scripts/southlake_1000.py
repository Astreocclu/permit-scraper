#!/usr/bin/env python3
"""
Southlake 1000 Permit Extractor

Extracts 1000 permits from Southlake, sorted by most recent first.
Uses pagination and incremental saving to handle DeepSeek JSON limits.

Strategy:
- Search all permits from 2023-2024
- Sort by issued date descending
- Extract in batches of 25 per page
- Paginate through 40+ pages to get 1000
"""

import argparse
import asyncio
import json
import glob
import os
from datetime import datetime
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from services.browser_scraper.agent import PermitScraperAgent
from services.browser_scraper.permit_tasks import EFFICIENCY_DIRECTIVE

# High-volume extraction task with pagination
SOUTHLAKE_1000_TASK = EFFICIENCY_DIRECTIVE + """
Go to the Southlake EnerGov portal at https://energov.cityofsouthlake.com/EnerGov_Prod/SelfService#/search

GOAL: Extract {batch_size} permits from page {page_num}, starting from the most recent.

1. SETUP (if this is page 1):
   - Select "Permit" from the Module dropdown
   - Click "Advanced" to open advanced search
   - Set "Issued Date" from: 01/01/2023
   - Set "Issued Date" to: 12/25/2024
   - Click "Search" button
   - Wait for results to load
   - Click "Issued Date" column header TWICE to sort DESCENDING (newest first)
   - If there's a "Page Size" dropdown, set it to 25 or 50

2. NAVIGATE TO PAGE {page_num}:
   - Look for pagination controls at bottom of results
   - Click "Next" {pages_to_skip} times, OR
   - If page number links exist, click on page {page_num}
   - Wait for page to load

3. EXTRACT from current page:
   For each permit row visible, extract:
   - permit_number (Case Number column - e.g., "POOL24-0123")
   - issue_date (Issued Date - mm/dd/yyyy format)
   - permit_type (Type column - FULL type name like "Pool/Spa", "Roofing", "Electrical")
   - status (Status column)
   - address (Full address including street number)
   - description (Description column if visible)

4. EXTRACTION TECHNIQUE:
   - Extract in small chunks (10 permits at a time)
   - After each chunk, continue to next 10
   - Total: {batch_size} permits from this page

Return all permits as a JSON array:
[
  {{"permit_number": "POOL24-0123", "issue_date": "12/20/2024", "permit_type": "Pool/Spa", ...}},
  ...
]

IMPORTANT:
- Include ALL permit types (pools, roofing, electrical, HVAC, etc.)
- Do NOT filter out any permit types
- We want a diverse mix of verticals
"""

# Simplified all-in-one extraction
SOUTHLAKE_ALL_PAGES_TASK = EFFICIENCY_DIRECTIVE + """
Go to the Southlake EnerGov portal at https://energov.cityofsouthlake.com/EnerGov_Prod/SelfService#/search

GOAL: Extract as many permits as possible, sorted by most recent first.

1. SETUP:
   - Select "Permit" from the Module dropdown
   - Click "Advanced" to open advanced search
   - Set "Issued Date" from: 01/01/2023
   - Set "Issued Date" to: 12/25/2024
   - Click "Search" button
   - Wait for results to load

2. SORT:
   - Find the "Issued Date" column header in the results table
   - Click it to sort
   - Click it AGAIN to ensure DESCENDING order (newest first)
   - Verify top rows show December 2024 dates

3. MAXIMIZE PAGE SIZE:
   - Look for "Show entries" or "Page Size" dropdown
   - If found, select the largest option (50, 100, or "All")

4. EXTRACTION LOOP:
   Repeat until you have {target_count} permits or run out of pages:

   a) Extract 10 visible permits:
      - permit_number (Case Number)
      - issue_date (mm/dd/yyyy)
      - permit_type (FULL type name)
      - status
      - address
      - description

   b) Scroll down or click "Next" to load more

   c) Continue extracting next batch of 10

   d) After every 50 permits, briefly pause

5. RETURN:
   Return all permits as a JSON array.

TARGET: {target_count} permits minimum

Include ALL permit types - we want pools, roofing, electrical, HVAC, fence, patio, foundation, additions, etc.
"""

async def run_extraction(target_count: int = 200, output_dir: Path = None):
    """Run a single extraction attempt."""
    if output_dir is None:
        output_dir = Path("data/extracts/southlake_1000")
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    task = SOUTHLAKE_ALL_PAGES_TASK.format(target_count=target_count)

    print(f"\n{'='*60}")
    print(f"SOUTHLAKE EXTRACTION - Target: {target_count} permits")
    print(f"Timestamp: {timestamp}")
    print(f"{'='*60}")

    agent = PermitScraperAgent(headless=True, model="deepseek", max_steps=60)  # More steps for pagination

    try:
        context = await agent.run_task(task, "southlake_1000")

        # Collect all extracted content
        all_permits = []

        if hasattr(context, 'extracted_content') and context.extracted_content:
            for i, content in enumerate(context.extracted_content):
                # Save raw content
                chunk_file = output_dir / f"extract_{timestamp}_chunk{i}.md"
                chunk_file.write_text(content)
                print(f"  Saved chunk: {chunk_file}")

                # Parse JSON from content
                try:
                    import re
                    # Find JSON arrays in content
                    json_matches = re.findall(r'\[[\s\S]*?\]', content)
                    for match in json_matches:
                        try:
                            permits = json.loads(match)
                            if isinstance(permits, list):
                                all_permits.extend(permits)
                        except:
                            pass
                except Exception as e:
                    print(f"  Warning: Could not parse JSON from chunk {i}: {e}")

        # Also check final_result
        if context.final_result:
            result_str = str(context.final_result)
            try:
                import re
                json_matches = re.findall(r'\[[\s\S]*?\]', result_str)
                for match in json_matches:
                    try:
                        permits = json.loads(match)
                        if isinstance(permits, list):
                            all_permits.extend(permits)
                    except:
                        pass
            except:
                pass

        # Deduplicate by permit_number
        seen = set()
        unique_permits = []
        for p in all_permits:
            if isinstance(p, dict):
                pn = p.get('permit_number', '')
                if pn and pn not in seen:
                    seen.add(pn)
                    unique_permits.append(p)

        # Save combined JSON
        combined_file = output_dir / f"permits_{timestamp}.json"
        with open(combined_file, 'w') as f:
            json.dump(unique_permits, f, indent=2)

        print(f"\n{'='*60}")
        print(f"EXTRACTION COMPLETE")
        print(f"  Unique permits: {len(unique_permits)}")
        print(f"  Saved to: {combined_file}")
        print(f"{'='*60}")

        # Show vertical breakdown
        if unique_permits:
            types = {}
            for p in unique_permits:
                t = p.get('permit_type', 'Unknown')
                types[t] = types.get(t, 0) + 1
            print("\nBy permit type:")
            for t, count in sorted(types.items(), key=lambda x: -x[1])[:15]:
                print(f"  {t}: {count}")

        return unique_permits

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return []


async def run_batched_extraction(total_target: int = 1000, batch_size: int = 100, output_dir: Path = None):
    """Run multiple extraction batches to reach target count."""
    if output_dir is None:
        output_dir = Path("data/extracts/southlake_1000")
    output_dir.mkdir(parents=True, exist_ok=True)

    all_permits = []
    batch_num = 0

    while len(all_permits) < total_target:
        batch_num += 1
        print(f"\n{'#'*60}")
        print(f"BATCH {batch_num} - Current total: {len(all_permits)}/{total_target}")
        print(f"{'#'*60}")

        permits = await run_extraction(target_count=batch_size, output_dir=output_dir)

        # Add new unique permits
        existing_ids = {p.get('permit_number') for p in all_permits}
        new_permits = [p for p in permits if p.get('permit_number') not in existing_ids]
        all_permits.extend(new_permits)

        print(f"Added {len(new_permits)} new permits (total: {len(all_permits)})")

        if len(new_permits) < 10:
            print("Diminishing returns - may have hit extraction limit")
            break

        # Brief delay between batches
        if len(all_permits) < total_target:
            print("Waiting 30 seconds before next batch...")
            await asyncio.sleep(30)

    # Save final combined file
    final_file = output_dir / "all_permits_combined.json"
    with open(final_file, 'w') as f:
        json.dump(all_permits, f, indent=2)

    print(f"\n{'='*60}")
    print(f"FINAL RESULTS")
    print(f"  Total permits: {len(all_permits)}")
    print(f"  Saved to: {final_file}")
    print(f"{'='*60}")

    # Vertical breakdown
    types = {}
    for p in all_permits:
        t = p.get('permit_type', 'Unknown')
        types[t] = types.get(t, 0) + 1
    print("\nBy permit type:")
    for t, count in sorted(types.items(), key=lambda x: -x[1]):
        print(f"  {t}: {count}")

    return all_permits


async def main():
    parser = argparse.ArgumentParser(description="Southlake 1000 Permit Extractor")
    parser.add_argument("--target", type=int, default=200,
                        help="Target permit count per batch")
    parser.add_argument("--total", type=int, default=1000,
                        help="Total target with batching")
    parser.add_argument("--batched", action="store_true",
                        help="Run in batched mode for large extractions")
    parser.add_argument("--output-dir", type=str, default="data/extracts/southlake_1000")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)

    if args.batched:
        await run_batched_extraction(
            total_target=args.total,
            batch_size=args.target,
            output_dir=output_dir
        )
    else:
        await run_extraction(
            target_count=args.target,
            output_dir=output_dir
        )


if __name__ == "__main__":
    asyncio.run(main())
