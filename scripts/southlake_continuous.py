#!/usr/bin/env python3
"""
Southlake Continuous Extraction

Runs Browser-Use extractions continuously until we reach target permit count.
Each run navigates to different pages to get new permits.
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from datetime import datetime
import time

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))
os.chdir(Path(__file__).parent.parent)

from services.browser_scraper.agent import PermitScraperAgent

TARGET = 1000
OUTPUT_DIR = Path('data/extracts/southlake_1000')
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
MASTER_FILE = OUTPUT_DIR / 'final_all_permits.json'


def load_existing():
    """Load existing permits from master file."""
    if MASTER_FILE.exists():
        with open(MASTER_FILE) as f:
            return json.load(f)
    return []


def save_permits(permits):
    """Save permits to master file."""
    with open(MASTER_FILE, 'w') as f:
        json.dump(permits, f, indent=2)


def deduplicate(permits):
    """Remove duplicate permits by permit_number."""
    seen = set()
    unique = []
    for p in permits:
        pnum = p.get('permit_number', '')
        if pnum and pnum not in seen:
            seen.add(pnum)
            unique.append(p)
    return unique


def parse_extracted_content(content: str) -> list:
    """Parse permit data from extracted markdown content."""
    permits = []
    current = {}

    for line in content.split('\n'):
        line = line.strip()
        if not line:
            continue

        if ':' in line:
            key, val = line.split(':', 1)
            key = key.strip().lower().replace(' ', '_').replace('-', '_')
            val = val.strip()

            if key == 'permit_number' and current.get('permit_number'):
                permits.append(current)
                current = {}

            current[key] = val

    if current.get('permit_number'):
        permits.append(current)

    return permits


async def run_extraction(start_page: int = 1, max_steps: int = 80):
    """Run a single Browser-Use extraction."""

    task = f"""Go to https://energov.cityofsouthlake.com/EnerGov_Prod/SelfService#/search

1. Select "Permit" from the Module dropdown
2. Click "Advanced" to open advanced search
3. Set date filters:
   - Issued Date From: 01/01/2024
   - Issued Date To: 12/31/2024
4. Click "Search" and wait for results
5. Sort results by "Issued Date" Descending (most recent first)
6. Set page size to 100
7. Navigate to page {start_page} using the page navigation
8. Extract from THIS page and the next 5 pages:
   - For each page, extract: permit_number, issue_date, permit_type, status, address, description
   - Use the extract tool for each page
   - Click Next to go to next page
   - Continue until you've extracted 5 pages worth of data

Return all extracted permits.

IMPORTANT: Make sure to get permit_number, permit_type, and address for each permit.
"""

    agent = PermitScraperAgent(headless=True, model='deepseek', max_steps=max_steps)
    result = await agent.run_task(task, city='Southlake')

    # Parse results from extracted content
    permits = []
    if result.extracted_content:
        for content in result.extracted_content if isinstance(result.extracted_content, list) else [result.extracted_content]:
            if isinstance(content, str):
                permits.extend(parse_extracted_content(content))

    return permits, result


async def main():
    print("=" * 60)
    print("SOUTHLAKE CONTINUOUS EXTRACTION")
    print("=" * 60)
    print(f"Target: {TARGET} permits")
    print(f"Time: {datetime.now().isoformat()}")
    print()

    # Load existing
    all_permits = load_existing()
    print(f"Starting with {len(all_permits)} existing permits")

    run_number = 0
    start_page = 1

    while len(all_permits) < TARGET:
        run_number += 1
        print(f"\n{'='*60}")
        print(f"RUN {run_number} - Starting from page {start_page}")
        print(f"{'='*60}")
        print(f"Current: {len(all_permits)} / {TARGET} permits")

        try:
            new_permits, result = await run_extraction(start_page=start_page, max_steps=100)

            print(f"Extracted {len(new_permits)} permits from Browser-Use")

            # Also check temp files for additional data
            import glob
            temp_dirs = glob.glob('/tmp/browser_use_agent_*/browseruse_agent_data')
            for temp_dir in sorted(temp_dirs, key=os.path.getmtime, reverse=True)[:1]:
                for md_file in Path(temp_dir).glob('extracted_content*.md'):
                    try:
                        content = md_file.read_text()
                        parsed = parse_extracted_content(content)
                        new_permits.extend(parsed)
                    except:
                        pass

            if new_permits:
                # Add to master list
                all_permits.extend(new_permits)
                all_permits = deduplicate(all_permits)
                save_permits(all_permits)

                print(f"Total unique permits: {len(all_permits)}")

                # Show types
                types = {}
                for p in all_permits:
                    t = p.get('permit_type', 'Unknown')
                    types[t] = types.get(t, 0) + 1

                print(f"\nTop permit types:")
                for t, c in sorted(types.items(), key=lambda x: -x[1])[:10]:
                    print(f"  {t}: {c}")

            # Move to next page range
            start_page += 5

            # Reset to page 1 after page 50 to cycle through
            if start_page > 50:
                start_page = 1

        except Exception as e:
            print(f"Error in run {run_number}: {e}")
            import traceback
            traceback.print_exc()

            # Wait a bit and try again
            await asyncio.sleep(10)
            continue

        # Brief pause between runs
        await asyncio.sleep(5)

    print(f"\n{'='*60}")
    print("TARGET REACHED!")
    print(f"{'='*60}")
    print(f"Total permits: {len(all_permits)}")
    print(f"Saved to: {MASTER_FILE}")


if __name__ == '__main__':
    asyncio.run(main())
