#!/usr/bin/env python3
"""
Southlake EnerGov API Direct Scraper

Bypasses the web interface to directly call the API for permit data.
Gets 1000 permits sorted by issue date descending (most recent first).
"""

import requests
import json
from pathlib import Path
from datetime import datetime
import time

API_URL = 'https://energov.cityofsouthlake.com/energov_prod/selfservice/api/energov/search/search'

HEADERS = {
    'Content-Type': 'application/json',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0',
    'Referer': 'https://energov.cityofsouthlake.com/EnerGov_Prod/SelfService',
    'Origin': 'https://energov.cityofsouthlake.com'
}


def build_request(page_number: int = 1, page_size: int = 100, sort_by: str = 'IssueDate', sort_asc: bool = False):
    """Build the search API request payload."""
    return {
        "Keyword": "",
        "ExactMatch": True,
        "SearchModule": 1,
        "FilterModule": 2,  # Permit module
        "SearchMainAddress": False,
        "PermitCriteria": {
            "PermitNumber": None,
            "PermitTypeId": "none",
            "PermitWorkclassId": None,
            "PermitStatusId": "none",
            "ProjectName": None,
            "IssueDateFrom": "2024-01-01",  # Recent permits only
            "IssueDateTo": "2024-12-31",
            "Address": None,
            "Description": None,
            "ExpireDateFrom": None,
            "ExpireDateTo": None,
            "FinalDateFrom": None,
            "FinalDateTo": None,
            "ApplyDateFrom": None,
            "ApplyDateTo": None,
            "SearchMainAddress": False,
            "ContactId": None,
            "TypeId": None,
            "WorkClassIds": None,
            "ParcelNumber": None,
            "ExcludeCases": None,
            "EnableDescriptionSearch": False,
            "PageNumber": page_number,
            "PageSize": page_size,
            "SortBy": sort_by,
            "SortAscending": sort_asc
        },
        "PlanCriteria": None,
        "LicenseCriteria": None,
        "CodeCaseCriteria": None,
        "ProjectCriteria": None,
        "InspectionCriteria": None,
        "PageNumber": page_number,
        "PageSize": page_size,
        "SortBy": sort_by,
        "SortAscending": sort_asc
    }


def fetch_page(page_number: int, page_size: int = 100):
    """Fetch a single page of permits from the API."""
    payload = build_request(page_number=page_number, page_size=page_size)

    try:
        response = requests.post(API_URL, json=payload, headers=HEADERS, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching page {page_number}: {e}")
        return None


def extract_permit(entity: dict) -> dict:
    """Extract permit fields from API response entity."""
    return {
        'permit_number': entity.get('CaseNumber', ''),
        'permit_type': entity.get('CaseType', ''),
        'status': entity.get('CaseStatus', ''),
        'issue_date': entity.get('IssueDate', '')[:10] if entity.get('IssueDate') else None,
        'apply_date': entity.get('ApplyDate', '')[:10] if entity.get('ApplyDate') else None,
        'address': entity.get('Address', {}).get('FullAddress', '') if entity.get('Address') else '',
        'description': entity.get('Description', ''),
        'parcel': entity.get('MainParcel', '')
    }


def main():
    print("=" * 60)
    print("SOUTHLAKE API DIRECT SCRAPER")
    print("=" * 60)
    print(f"Time: {datetime.now().isoformat()}")
    print()

    all_permits = []
    target = 1000
    page = 1
    page_size = 100

    print(f"Target: {target} permits")
    print(f"Fetching 2024 permits sorted by Issue Date descending...")
    print()

    while len(all_permits) < target:
        print(f"Page {page}... ", end="", flush=True)

        result = fetch_page(page, page_size)

        if not result or 'Result' not in result:
            print("No result")
            break

        entities = result['Result'].get('EntityResults', [])

        if not entities:
            print("No more results")
            break

        for entity in entities:
            permit = extract_permit(entity)
            all_permits.append(permit)

        total_found = result['Result'].get('PermitsFound', 0)
        print(f"Got {len(entities)} permits (total: {len(all_permits)}/{total_found})")

        page += 1

        if len(all_permits) >= target:
            break

        time.sleep(0.5)  # Be nice to the server

    print()
    print("=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"Total permits: {len(all_permits)}")

    # Categorize by type
    types = {}
    for p in all_permits:
        t = p['permit_type']
        types[t] = types.get(t, 0) + 1

    print(f"\nBy type (top 20):")
    for t, c in sorted(types.items(), key=lambda x: -x[1])[:20]:
        print(f"  {t}: {c}")

    # Save
    output_dir = Path(__file__).parent.parent / 'data' / 'extracts' / 'southlake_1000'
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / 'api_permits.json'
    with open(output_file, 'w') as f:
        json.dump(all_permits, f, indent=2)

    print(f"\nSaved to: {output_file}")


if __name__ == '__main__':
    main()
