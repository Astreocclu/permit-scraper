#!/usr/bin/env python3
"""
Westlake Address Harvester (Recursive A-Z Search)

Discovers ALL addresses in Westlake via recursive prefix search.
Uses MyGov API endpoint with exponential backoff for rate limiting.

Algorithm:
1. Search A, B, C... Z, 0-9
2. If any search hits result limit (50), drill down (AA, AB, AC...)
3. Recurse up to depth 3 to handle dense prefixes
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


def main():
    """Run the recursive address harvest."""
    print("Westlake Recursive Address Harvester")
    print("=" * 50)

    # Load any existing addresses
    all_addresses = load_existing_addresses()
    print(f"Loaded {len(all_addresses)} existing addresses")

    # Search A-Z, 0-9
    start_chars = string.ascii_uppercase + string.digits

    print(f"\nStarting recursive search for {len(start_chars)} prefixes...")

    for char in start_chars:
        recursive_search(char, all_addresses, depth=0)
        time.sleep(BASE_SLEEP)

    # Final save
    save_addresses(all_addresses)

    print("\n" + "=" * 50)
    print(f"COMPLETE: Harvested {len(all_addresses)} unique addresses")
    print(f"Output: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
