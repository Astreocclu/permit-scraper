#!/usr/bin/env python3
"""
Westlake Address Harvester (Numeric Prefix Search)

Discovers ALL addresses in Westlake via numeric prefix search.
Uses MyGov API endpoint with exponential backoff for rate limiting.

Algorithm:
1. Search numeric prefixes: 100-199, 200-299, ... 1000-1099, etc.
2. Addresses start with street numbers, so numeric search is more effective
3. Uses recursive drill-down if results hit limit (50)
4. Checkpoint progress for resumability

Run: python scrapers/westlake_harvester.py
Output: data/westlake_addresses.json
"""
import json
import time
import string
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Configuration
API_URL = "https://public.mygov.us/westlake_tx/getLookupResults"
OUTPUT_FILE = Path(__file__).parent.parent / "data" / "westlake_addresses.json"
STATE_FILE = Path(__file__).parent.parent / "data" / "westlake_harvest_state.json"

# Search parameters
RESULT_LIMIT = 50  # If we get this many, we need to drill down
MAX_DEPTH = 3  # Don't recurse deeper than this
BASE_SLEEP = 1.0  # Seconds between requests


def get_session():
    """Create requests session with retry/backoff for rate limiting."""
    session = requests.Session()

    retries = Retry(
        total=5,
        backoff_factor=1,  # Wait 1s, 2s, 4s, 8s, 16s on retry
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["POST"]
    )

    adapter = HTTPAdapter(max_retries=retries)
    session.mount('https://', adapter)
    session.mount('http://', adapter)

    return session


# Global session for reuse
_session = None


def get_global_session():
    """Get or create global session."""
    global _session
    if _session is None:
        _session = get_session()
    return _session


def search_addresses(search_term: str) -> list:
    """Search MyGov API for addresses matching term.

    Args:
        search_term: Prefix to search (e.g., "A", "AB", "100")

    Returns:
        List of address dicts with 'address' and 'location_id' keys
    """
    session = get_global_session()

    try:
        response = session.post(
            API_URL,
            data={'address_search': search_term},
            headers={
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'Accept': 'application/json, text/javascript, */*; q=0.01',
                'X-Requested-With': 'XMLHttpRequest',
                'Referer': 'https://public.mygov.us/westlake_tx/lookup',
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
            },
            timeout=30
        )

        response.raise_for_status()
        data = response.json()

        # Parse response - extract address items
        results = []
        for item in data if isinstance(data, list) else []:
            if isinstance(item, dict) and item.get('address'):
                results.append({
                    'address': item.get('address'),
                    'location_id': item.get('location_id')
                })

        return results

    except requests.exceptions.RequestException as e:
        print(f"  ERROR searching '{search_term}': {e}")
        return []
    except json.JSONDecodeError as e:
        print(f"  ERROR parsing response for '{search_term}': {e}")
        return []


def recursive_search(prefix: str, all_addresses: dict, depth: int = 0):
    """Recursively search addresses by prefix.

    Args:
        prefix: Current search prefix (e.g., "A", "AB")
        all_addresses: Dict to accumulate results (address -> item dict)
        depth: Current recursion depth
    """
    # Safety: Don't recurse too deep
    if depth > MAX_DEPTH:
        return

    print(f"{'  ' * depth}Scanning: {prefix}* ...")
    results = search_addresses(prefix)

    # Add new addresses
    new_count = 0
    for item in results:
        addr = item.get('address')
        if addr and addr not in all_addresses:
            all_addresses[addr] = item
            new_count += 1

    print(f"{'  ' * depth}  Found {len(results)} results ({new_count} new)")

    # If we hit the limit, need to drill down
    if len(results) >= RESULT_LIMIT:
        print(f"{'  ' * depth}  HIT LIMIT - drilling down...")
        chars = string.ascii_uppercase + string.digits
        for char in chars:
            recursive_search(prefix + char, all_addresses, depth + 1)
            time.sleep(BASE_SLEEP * 0.5)  # Shorter sleep for drill-down

    # Checkpoint after significant progress
    if new_count > 0 and depth == 0:
        save_addresses(all_addresses)


def save_addresses(addresses: dict):
    """Save addresses to JSON file.

    Args:
        addresses: Dict mapping address string to full item dict
    """
    # Convert dict to list for JSON
    data = list(addresses.values())

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_FILE, 'w') as f:
        json.dump(data, f, indent=2)

    print(f"  Checkpointed {len(data)} addresses to {OUTPUT_FILE}")


def load_existing_addresses() -> dict:
    """Load previously harvested addresses for resumption."""
    if not OUTPUT_FILE.exists():
        return {}

    try:
        data = json.loads(OUTPUT_FILE.read_text())
        return {item['address']: item for item in data if item.get('address')}
    except Exception as e:
        print(f"Could not load existing addresses: {e}")
        return {}


def harvest_numeric_range(start: int, end: int, all_addresses: dict):
    """Harvest addresses for a numeric range (e.g., 100-199).

    Args:
        start: Starting number (inclusive)
        end: Ending number (exclusive)
        all_addresses: Dict to accumulate results
    """
    for num in range(start, end):
        prefix = str(num)
        results = search_addresses(prefix)

        new_count = 0
        for item in results:
            addr = item.get('address')
            if addr and addr not in all_addresses:
                all_addresses[addr] = item
                new_count += 1

        if new_count > 0:
            print(f"{prefix}*: +{new_count} new (total: {len(all_addresses)})")

        # Checkpoint periodically
        if new_count > 0 and num % 50 == 0:
            save_addresses(all_addresses)

        time.sleep(BASE_SLEEP * 0.3)  # Faster for numeric search


def main():
    """Run the numeric address harvest."""
    print("Westlake Numeric Address Harvester")
    print("=" * 50)

    # Load any existing addresses
    all_addresses = load_existing_addresses()
    print(f"Loaded {len(all_addresses)} existing addresses")

    # Numeric ranges to search (street numbers)
    # Most Westlake addresses are in 100-2000 range
    ranges = [
        (100, 200),   # 100-199
        (200, 300),   # 200-299
        (300, 400),   # 300-399
        (400, 500),   # 400-499
        (500, 600),   # 500-599
        (600, 700),   # 600-699
        (700, 800),   # 700-799
        (800, 900),   # 800-899
        (900, 1000),  # 900-999
        (1000, 1100), # 1000-1099
        (1100, 1200), # 1100-1199
        (1200, 1300), # 1200-1299
        (1300, 1400), # 1300-1399
        (1400, 1500), # 1400-1499
        (1500, 1600), # 1500-1599
        (1600, 1700), # 1600-1699
        (1700, 1800), # 1700-1799
        (1800, 1900), # 1800-1899
        (1900, 2000), # 1900-1999
        (2000, 2100), # 2000-2099
    ]

    total_ranges = len(ranges)
    for i, (start, end) in enumerate(ranges):
        print(f"\n[{i+1}/{total_ranges}] Scanning range {start}-{end-1}...")
        harvest_numeric_range(start, end, all_addresses)
        save_addresses(all_addresses)

    # Final save
    save_addresses(all_addresses)

    print("\n" + "=" * 50)
    print(f"COMPLETE: Harvested {len(all_addresses)} unique addresses")
    print(f"Output: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
