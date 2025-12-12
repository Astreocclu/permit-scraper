#!/usr/bin/env python3
"""
Westlake Address Harvester

Collects valid residential addresses via MyGov API endpoint.
Uses the discovered API: https://public.mygov.us/westlake_tx/getLookupResults

The API requires POST with form data: address_search=<term>
Returns: [{'address': '...', 'location_id': 123}, ...]
"""
import json
import time
from pathlib import Path
import requests

API_URL = "https://public.mygov.us/westlake_tx/getLookupResults"
OUTPUT_FILE = Path(__file__).parent.parent / "data" / "westlake_addresses.json"

# High-value residential streets in Westlake
RESIDENTIAL_STREETS = [
    # Vaquero Club area
    "Cedar Elm",
    "Post Oak",
    "Fountain Grass",
    "Wills Ct",
    "White Wing",
    "Vaquero Club",
    "Vaquero",  # General search
    "Saddle White",
    "King Fisher",
    # Glenwyck area
    "Paigebrooke",
    "Wimbledon",
    # General residential
    "Dove Rd",
    "Dove",
    "Ottinger",
    "Sam School",
    "Oak Ridge",
]


def parse_api_response(response):
    """
    Extract addresses from API response.

    Args:
        response: List of dicts with 'address' and 'location_id' keys

    Returns:
        List of dicts with both address and location_id, or empty list
    """
    if not response:
        return []

    addresses = []
    for item in response:
        if not isinstance(item, dict):
            continue

        # Both address and location_id are required
        address = item.get('address')
        location_id = item.get('location_id')

        if address and location_id:
            addresses.append({
                'address': address,
                'location_id': location_id
            })

    return addresses


def search_addresses(search_term):
    """
    Search for addresses using the MyGov API.

    Args:
        search_term: Street name or partial address to search

    Returns:
        List of dicts with 'address' and 'location_id' keys
    """
    try:
        # The API expects form-encoded POST data with 'address_search' parameter
        response = requests.post(
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

        if response.status_code == 200:
            data = response.json()
            return parse_api_response(data)
        else:
            print(f"Warning: API returned status {response.status_code} for '{search_term}'")
            return []

    except requests.exceptions.RequestException as e:
        print(f"Error searching for '{search_term}': {e}")
        return []
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON response for '{search_term}': {e}")
        return []


def harvest_all_addresses():
    """
    Harvest addresses for all residential streets.

    Returns:
        Dict mapping street name to list of address dicts
    """
    all_addresses = {}

    for street in RESIDENTIAL_STREETS:
        print(f"Searching: {street}...")
        addresses = search_addresses(street)
        all_addresses[street] = addresses
        print(f"  Found {len(addresses)} addresses")

        # Rate limit to be respectful
        time.sleep(0.5)

    return all_addresses


def save_addresses(addresses):
    """
    Save harvested addresses to JSON.

    Args:
        addresses: Dict mapping street name to list of address dicts
    """
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_FILE, 'w') as f:
        json.dump(addresses, f, indent=2)

    print(f"\nSaved to {OUTPUT_FILE}")


def main():
    """Main entry point for harvesting addresses."""
    print("Westlake Address Harvester")
    print("=" * 50)

    addresses = harvest_all_addresses()
    save_addresses(addresses)

    # Print summary
    total = sum(len(v) for v in addresses.values())
    print(f"\nTotal addresses harvested: {total}")

    # Print breakdown by street
    print("\nBreakdown by street:")
    for street, addrs in sorted(addresses.items(), key=lambda x: len(x[1]), reverse=True):
        print(f"  {street}: {len(addrs)} addresses")


if __name__ == "__main__":
    main()
