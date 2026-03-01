#!/usr/bin/env python3
"""
Southlake Multi-Vertical Scraper

Extracts 1000 permits from Southlake across multiple verticals:
- Pool/Spa
- Roofing
- HVAC/Mechanical
- Electrical
- Fence/Deck
- Patio/Outdoor Living
- Foundation
- General Building

Strategy: Run separate Browser-Use extractions for each permit type filter.
"""

import argparse
import asyncio
import json
from datetime import datetime
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from services.browser_scraper.agent import PermitScraperAgent
from services.browser_scraper.permit_tasks import EFFICIENCY_DIRECTIVE

# Target verticals with expected permit type names in EnerGov
VERTICALS = {
    "pool": {
        "type_filters": ["Pool", "Swimming Pool", "Spa", "Pool/Spa"],
        "target_count": 150,
    },
    "roofing": {
        "type_filters": ["Roofing", "Roof", "Re-Roof", "Reroof"],
        "target_count": 150,
    },
    "hvac": {
        "type_filters": ["HVAC", "Mechanical", "AC", "Air Conditioning", "Heating"],
        "target_count": 100,
    },
    "electrical": {
        "type_filters": ["Electrical", "Electric"],
        "target_count": 100,
    },
    "fence": {
        "type_filters": ["Fence", "Deck", "Fence/Deck"],
        "target_count": 100,
    },
    "patio": {
        "type_filters": ["Patio", "Outdoor", "Covered Patio", "Arbor", "Pergola"],
        "target_count": 100,
    },
    "foundation": {
        "type_filters": ["Foundation", "Slab"],
        "target_count": 100,
    },
    "addition": {
        "type_filters": ["Addition", "Remodel", "Alteration", "Renovation"],
        "target_count": 100,
    },
    "new_construction": {
        "type_filters": ["New Construction", "New Home", "Residential New", "New Single Family"],
        "target_count": 100,
    },
}

SOUTHLAKE_VERTICAL_TASK = EFFICIENCY_DIRECTIVE + """
Go to the Southlake EnerGov portal at https://energov.cityofsouthlake.com/EnerGov_Prod/SelfService#/search

1. Select "Permit" from the Module dropdown.

2. Click "Advanced" to open advanced search.

3. IMPORTANT - Set Type Filter:
   - Find the "Type" or "Permit Type" dropdown/field
   - Search for or select types containing: {type_keywords}
   - If exact match not found, try partial matches

4. Set date filters to get recent permits:
   - Issued Date from: 01/01/2023
   - Issued Date to: 12/25/2024

5. Click "Search" button.

6. After results load:
   - Click "Issued Date" column header to sort DESCENDING (newest first)
   - Verify results match the permit type filter

7. EXTRACTION - Extract up to {target_count} permits:
   - permit_number (Case Number)
   - issue_date (Issued Date - format mm/dd/yyyy)
   - permit_type (Type column - MUST match {vertical} category)
   - status (Status column)
   - address (Address column)
   - description (Description if available)
   - valuation (if available)

8. If pagination exists, click "Next" and continue extracting until you reach {target_count} or run out of pages.

9. Extract in chunks of 10 permits at a time to avoid JSON errors.

Return the data as a valid JSON list of objects.

CRITICAL: Only include permits that match the {vertical} category. Skip water heaters, general plumbing, and unrelated permits.
"""

async def extract_vertical(vertical: str, config: dict, output_dir: Path) -> list:
    """Extract permits for a specific vertical."""
    print(f"\n{'='*60}")
    print(f"Extracting {vertical.upper()} permits...")
    print(f"Target: {config['target_count']} permits")
    print(f"Type filters: {config['type_filters']}")
    print(f"{'='*60}")

    type_keywords = ", ".join(config['type_filters'])
    task = SOUTHLAKE_VERTICAL_TASK.format(
        type_keywords=type_keywords,
        target_count=config['target_count'],
        vertical=vertical,
    )

    agent = PermitScraperAgent(headless=True, model="deepseek")

    try:
        context = await agent.run_task(task, f"southlake_{vertical}")

        # Save extracted content
        if hasattr(context, 'extracted_content') and context.extracted_content:
            vertical_dir = output_dir / vertical
            vertical_dir.mkdir(parents=True, exist_ok=True)

            all_permits = []
            for i, content in enumerate(context.extracted_content):
                chunk_file = vertical_dir / f"chunk_{i}.md"
                chunk_file.write_text(content)
                print(f"  Saved: {chunk_file}")

                # Try to parse JSON from content
                try:
                    # Find JSON array in content
                    import re
                    json_match = re.search(r'\[[\s\S]*\]', content)
                    if json_match:
                        permits = json.loads(json_match.group())
                        all_permits.extend(permits)
                except:
                    pass

            # Save combined JSON
            if all_permits:
                combined_file = vertical_dir / "permits.json"
                with open(combined_file, 'w') as f:
                    json.dump(all_permits, f, indent=2)
                print(f"  Combined: {len(all_permits)} permits saved to {combined_file}")

            return all_permits

        print(f"  No extraction data captured for {vertical}")
        return []

    except Exception as e:
        print(f"  ERROR extracting {vertical}: {e}")
        return []


async def main():
    parser = argparse.ArgumentParser(description="Southlake Multi-Vertical Extractor")
    parser.add_argument("--verticals", nargs="+", choices=list(VERTICALS.keys()) + ["all"],
                        default=["all"], help="Verticals to extract")
    parser.add_argument("--target", type=int, default=1000, help="Total permit target")
    parser.add_argument("--output-dir", type=str, default="data/extracts/southlake_verticals",
                        help="Output directory")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Determine which verticals to run
    if "all" in args.verticals:
        verticals_to_run = list(VERTICALS.keys())
    else:
        verticals_to_run = args.verticals

    print(f"\n{'='*60}")
    print(f"SOUTHLAKE MULTI-VERTICAL EXTRACTION")
    print(f"Target: {args.target} permits total")
    print(f"Verticals: {verticals_to_run}")
    print(f"Output: {output_dir}")
    print(f"{'='*60}")

    all_permits = []
    vertical_counts = {}

    for vertical in verticals_to_run:
        config = VERTICALS[vertical]
        permits = await extract_vertical(vertical, config, output_dir)
        all_permits.extend(permits)
        vertical_counts[vertical] = len(permits)

        print(f"\n[{vertical}] Extracted: {len(permits)} permits")
        print(f"Running total: {len(all_permits)} permits")

        # Brief delay between verticals
        if vertical != verticals_to_run[-1]:
            print("Waiting 10 seconds before next vertical...")
            await asyncio.sleep(10)

    # Final summary
    print(f"\n{'='*60}")
    print("EXTRACTION COMPLETE")
    print(f"{'='*60}")
    print(f"Total permits: {len(all_permits)}")
    print("\nBy vertical:")
    for v, count in vertical_counts.items():
        print(f"  {v}: {count}")

    # Save master combined file
    master_file = output_dir / "all_permits.json"
    with open(master_file, 'w') as f:
        json.dump(all_permits, f, indent=2)
    print(f"\nMaster file: {master_file}")

    # Save summary
    summary = {
        "timestamp": datetime.now().isoformat(),
        "total_permits": len(all_permits),
        "by_vertical": vertical_counts,
        "target": args.target,
    }
    summary_file = output_dir / "extraction_summary.json"
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)


if __name__ == "__main__":
    asyncio.run(main())
