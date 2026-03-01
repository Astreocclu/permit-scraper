#!/usr/bin/env python3
"""
Process extracted permit data from Browser-Use temp files.
Combine all extracts, deduplicate, and save as structured JSON.
"""

import glob
import json
import re
from pathlib import Path
from collections import defaultdict

def parse_permit_markdown(content: str) -> list:
    """Parse permits from markdown extraction content."""
    permits = []

    # Try to find JSON array first
    json_match = re.search(r'\[[\s\S]*?\]', content)
    if json_match:
        try:
            data = json.loads(json_match.group())
            if isinstance(data, list):
                return data
        except:
            pass

    # Parse markdown format
    current_permit = {}
    for line in content.split('\n'):
        line = line.strip()
        if not line:
            continue

        # Look for permit_number patterns
        if 'permit_number' in line.lower() or line.startswith('- **permit_number'):
            # Save previous permit if exists
            if current_permit and current_permit.get('permit_number'):
                permits.append(current_permit)
            current_permit = {}

            # Extract value
            match = re.search(r'(?:permit_number[:\s]*\**\s*)([A-Z]{2,6}\d{2}-\d{4})', line, re.I)
            if match:
                current_permit['permit_number'] = match.group(1)

        elif 'issue_date' in line.lower():
            match = re.search(r'(\d{1,2}/\d{1,2}/\d{4})', line)
            if match:
                current_permit['issue_date'] = match.group(1)

        elif 'permit_type' in line.lower():
            match = re.search(r'permit_type[:\s]*\**\s*([^*\n]+)', line, re.I)
            if match:
                current_permit['permit_type'] = match.group(1).strip()

        elif 'status' in line.lower() and 'status' not in current_permit:
            match = re.search(r'status[:\s]*\**\s*([A-Za-z ]+)', line, re.I)
            if match:
                current_permit['status'] = match.group(1).strip()

        elif 'address' in line.lower():
            match = re.search(r'address[:\s]*\**\s*([^\n*]+)', line, re.I)
            if match:
                current_permit['address'] = match.group(1).strip()

        elif 'description' in line.lower():
            match = re.search(r'description[:\s]*\**\s*([^\n]+)', line, re.I)
            if match:
                current_permit['description'] = match.group(1).strip()

    # Don't forget last permit
    if current_permit and current_permit.get('permit_number'):
        permits.append(current_permit)

    return permits


def main():
    # Find all extraction files
    extract_patterns = [
        "/tmp/browser_use_agent_*/browseruse_agent_data/extracted_content_*.md",
        "data/extracts/southlake/*.md",
        "data/extracts/southlake_1000/*.md",
    ]

    all_files = []
    for pattern in extract_patterns:
        all_files.extend(glob.glob(pattern))

    print(f"Found {len(all_files)} extraction files")

    all_permits = []
    for filepath in sorted(all_files):
        print(f"  Processing: {filepath}")
        try:
            with open(filepath, 'r') as f:
                content = f.read()
            permits = parse_permit_markdown(content)
            print(f"    Found {len(permits)} permits")
            all_permits.extend(permits)
        except Exception as e:
            print(f"    Error: {e}")

    # Deduplicate by permit_number
    seen = set()
    unique_permits = []
    for p in all_permits:
        if isinstance(p, dict):
            pn = p.get('permit_number', '')
            if pn and pn not in seen:
                seen.add(pn)
                unique_permits.append(p)

    print(f"\nTotal unique permits: {len(unique_permits)}")

    # Count by permit type
    types = defaultdict(int)
    for p in unique_permits:
        t = p.get('permit_type', 'Unknown')
        types[t] += 1

    print("\nBy permit type:")
    for t, count in sorted(types.items(), key=lambda x: -x[1])[:20]:
        print(f"  {t}: {count}")

    # Save combined JSON
    output_dir = Path("data/extracts/southlake_1000")
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "combined_permits.json"
    with open(output_file, 'w') as f:
        json.dump(unique_permits, f, indent=2)

    print(f"\nSaved to: {output_file}")

    # Show sample permits
    print("\nSample permits:")
    for p in unique_permits[:5]:
        print(f"  {p.get('permit_number')}: {p.get('permit_type')} @ {p.get('address')}")


if __name__ == "__main__":
    main()
