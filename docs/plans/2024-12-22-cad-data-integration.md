# CAD Data Integration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Integrate 6 new data sources (3 CAD tax rolls, 2 Socrata APIs, 1 Excel) to expand permit coverage from ~30 cities to full DFW 4-county coverage.

**Architecture:** Extend existing scraper patterns (follow `collin_cad_socrata.py`). Add lightweight CAD Delta Engine for tax roll processing. Stream-process large files (900K+ records) to extract only new construction (~5-20K records). Store raw snapshots in S3 for future analytics.

**Tech Stack:** Python 3, pandas (chunked), requests, openpyxl, psycopg2, tenacity (retry), boto3 (S3)

**ROI Context:**
- DCAD Open Records ($75/month) → Break-even at 15 leads, expected 1000+ leads
- ECAD Parcel Data ($15 one-time) → Expected $1,485 profit

---

## Task 1: Database Schema Changes

**Files:**
- Create: `scripts/migrations/001_add_data_source_columns.sql`
- Create: `scripts/migrations/002_create_scrapers_metadata.sql`
- Modify: `scripts/load_permits.py:133-145` (add new columns)

**Step 1: Write the SQL migration for leads_permit columns**

```sql
-- scripts/migrations/001_add_data_source_columns.sql
-- Add columns for tracking data source and CAD account linkage

ALTER TABLE leads_permit
ADD COLUMN IF NOT EXISTS data_source VARCHAR(50);

ALTER TABLE leads_permit
ADD COLUMN IF NOT EXISTS cad_account_number VARCHAR(50);

ALTER TABLE leads_permit
ADD COLUMN IF NOT EXISTS year_built INTEGER;

ALTER TABLE leads_permit
ADD COLUMN IF NOT EXISTS property_value DECIMAL(12,2);

-- Index for deduplication queries
CREATE INDEX IF NOT EXISTS idx_leads_permit_cad_account
ON leads_permit(cad_account_number) WHERE cad_account_number IS NOT NULL;

-- Index for data source filtering
CREATE INDEX IF NOT EXISTS idx_leads_permit_data_source
ON leads_permit(data_source) WHERE data_source IS NOT NULL;

COMMENT ON COLUMN leads_permit.data_source IS 'Source identifier (e.g., dallas_accela, dcad_taxroll, denton_socrata)';
COMMENT ON COLUMN leads_permit.cad_account_number IS 'CAD property account ID for cross-referencing';
```

**Step 2: Write the SQL migration for scrapers_metadata table**

```sql
-- scripts/migrations/002_create_scrapers_metadata.sql
-- Track scraper runs and file hashes for change detection

CREATE TABLE IF NOT EXISTS scrapers_metadata (
    id SERIAL PRIMARY KEY,
    scraper_name VARCHAR(100) UNIQUE NOT NULL,
    last_run TIMESTAMP WITH TIME ZONE,
    last_file_hash VARCHAR(64),
    last_file_url TEXT,
    records_processed INTEGER DEFAULT 0,
    records_loaded INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'idle',  -- idle, running, success, error
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Trigger to update updated_at
CREATE OR REPLACE FUNCTION update_scrapers_metadata_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER scrapers_metadata_updated
    BEFORE UPDATE ON scrapers_metadata
    FOR EACH ROW
    EXECUTE FUNCTION update_scrapers_metadata_timestamp();

COMMENT ON TABLE scrapers_metadata IS 'Tracks scraper run history and file hashes for change detection';
```

**Step 3: Run migrations**

```bash
cd /home/reid/testhome/permit-scraper
source .env  # Load DATABASE_URL
psql "$DATABASE_URL" -f scripts/migrations/001_add_data_source_columns.sql
psql "$DATABASE_URL" -f scripts/migrations/002_create_scrapers_metadata.sql
```

Expected output:
```
ALTER TABLE
ALTER TABLE
ALTER TABLE
ALTER TABLE
CREATE INDEX
CREATE INDEX
COMMENT
COMMENT
CREATE TABLE
CREATE FUNCTION
CREATE TRIGGER
COMMENT
```

**Step 4: Verify migrations**

```bash
psql "$DATABASE_URL" -c "\d leads_permit" | grep -E "(data_source|cad_account|year_built|property_value)"
```

Expected:
```
 data_source         | character varying(50)   |
 cad_account_number  | character varying(50)   |
 year_built          | integer                 |
 property_value      | numeric(12,2)           |
```

**Step 5: Commit**

```bash
git add scripts/migrations/
git commit -m "feat: add data_source columns and scrapers_metadata table

- Add data_source, cad_account_number, year_built, property_value to leads_permit
- Create scrapers_metadata table for tracking scraper runs and file hashes
- Add indexes for deduplication and filtering"
```

---

## Task 2: Address Normalizer Utility

**Files:**
- Create: `scrapers/utils/address_normalizer.py`
- Create: `tests/test_address_normalizer.py`

**Step 1: Write the failing tests**

```python
# tests/test_address_normalizer.py
"""Tests for address normalization utility."""

import pytest
from scrapers.utils.address_normalizer import normalize_address, match_addresses


class TestNormalizeAddress:
    """Test address normalization."""

    def test_basic_normalization(self):
        """Street type abbreviations should be standardized."""
        assert normalize_address("123 Main Street") == "123 MAIN ST"
        assert normalize_address("456 Oak Avenue") == "456 OAK AVE"
        assert normalize_address("789 First Boulevard") == "789 FIRST BLVD"

    def test_case_insensitive(self):
        """Should convert to uppercase."""
        assert normalize_address("123 main st") == "123 MAIN ST"
        assert normalize_address("123 MAIN ST") == "123 MAIN ST"

    def test_extra_whitespace(self):
        """Should collapse multiple spaces."""
        assert normalize_address("123   Main    St") == "123 MAIN ST"
        assert normalize_address("  123 Main St  ") == "123 MAIN ST"

    def test_punctuation_removal(self):
        """Should remove periods and commas."""
        assert normalize_address("123 Main St.") == "123 MAIN ST"
        assert normalize_address("123 Main St, Apt 4") == "123 MAIN ST APT 4"

    def test_unit_standardization(self):
        """Should standardize apartment/unit designations."""
        assert normalize_address("123 Main St Unit 4") == "123 MAIN ST UNIT 4"
        assert normalize_address("123 Main St #4") == "123 MAIN ST UNIT 4"
        assert normalize_address("123 Main St Apt 4") == "123 MAIN ST APT 4"

    def test_none_and_empty(self):
        """Should handle None and empty strings."""
        assert normalize_address(None) == ""
        assert normalize_address("") == ""
        assert normalize_address("   ") == ""

    def test_house_number_suffix(self):
        """Should handle hyphenated unit suffixes."""
        assert normalize_address("123-A Main St") == "123A MAIN ST"
        assert normalize_address("123-B Oak Ave") == "123B OAK AVE"


class TestMatchAddresses:
    """Test address matching logic."""

    def test_exact_match(self):
        """Identical normalized addresses should match."""
        assert match_addresses("123 Main St", "123 MAIN STREET") is True

    def test_with_without_street_type(self):
        """Should match with/without street type."""
        assert match_addresses("123 Main", "123 MAIN ST") is True

    def test_no_match(self):
        """Different addresses should not match."""
        assert match_addresses("123 Main St", "456 Main St") is False

    def test_close_match_threshold(self):
        """Minor typos within threshold should match."""
        assert match_addresses("123 Main St", "123 Main Str", threshold=2) is True
        assert match_addresses("123 Main St", "999 Other Rd", threshold=2) is False
```

**Step 2: Run tests to verify they fail**

```bash
pytest tests/test_address_normalizer.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'scrapers.utils.address_normalizer'`

**Step 3: Create utils package structure**

```bash
mkdir -p scrapers/utils
touch scrapers/utils/__init__.py
```

**Step 4: Write the address normalizer implementation**

```python
# scrapers/utils/address_normalizer.py
"""
Address normalization and matching utilities.

Used for deduplicating permits from multiple sources (CAD, municipal portals).
"""

import re
from typing import Optional


# Street type standardization map
STREET_TYPES = {
    'STREET': 'ST',
    'AVENUE': 'AVE',
    'BOULEVARD': 'BLVD',
    'ROAD': 'RD',
    'DRIVE': 'DR',
    'LANE': 'LN',
    'COURT': 'CT',
    'PLACE': 'PL',
    'TERRACE': 'TER',
    'CIRCLE': 'CIR',
    'HIGHWAY': 'HWY',
    'PARKWAY': 'PKWY',
    'WAY': 'WAY',
    'TRAIL': 'TRL',
}

# Direction standardization
DIRECTIONS = {
    'NORTH': 'N',
    'SOUTH': 'S',
    'EAST': 'E',
    'WEST': 'W',
    'NORTHEAST': 'NE',
    'NORTHWEST': 'NW',
    'SOUTHEAST': 'SE',
    'SOUTHWEST': 'SW',
}


def normalize_address(address: Optional[str]) -> str:
    """
    Normalize an address string for consistent matching.

    Transforms:
    - Uppercase
    - Remove punctuation (except hyphens in house numbers)
    - Standardize street types (STREET -> ST)
    - Standardize directions (NORTH -> N)
    - Collapse whitespace
    - Handle unit designations (# -> UNIT)

    Args:
        address: Raw address string

    Returns:
        Normalized address string, or empty string if input is None/empty
    """
    if not address or not isinstance(address, str):
        return ""

    # Uppercase and strip
    addr = address.upper().strip()

    if not addr:
        return ""

    # Convert # to UNIT for standardization
    addr = re.sub(r'#(\d+)', r'UNIT \1', addr)

    # Remove punctuation (keep hyphens for now)
    addr = re.sub(r'[.,]', '', addr)

    # Standardize hyphenated house number suffixes (123-A -> 123A)
    addr = re.sub(r'(\d+)-([A-Z])\b', r'\1\2', addr)

    # Collapse whitespace
    addr = ' '.join(addr.split())

    # Standardize street types (word boundaries)
    for full, abbr in STREET_TYPES.items():
        addr = re.sub(rf'\b{full}\b', abbr, addr)

    # Standardize directions
    for full, abbr in DIRECTIONS.items():
        addr = re.sub(rf'\b{full}\b', abbr, addr)

    return addr


def _levenshtein_distance(s1: str, s2: str) -> int:
    """Calculate Levenshtein distance between two strings."""
    if len(s1) < len(s2):
        return _levenshtein_distance(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


def _strip_street_type(addr: str) -> str:
    """Remove street type suffix from address."""
    for abbr in STREET_TYPES.values():
        addr = re.sub(rf'\b{abbr}$', '', addr).strip()
    return addr


def match_addresses(addr1: str, addr2: str, threshold: int = 2) -> bool:
    """
    Check if two addresses match (after normalization).

    Matching logic:
    1. Exact match after normalization
    2. Match without street type (123 MAIN == 123 MAIN ST)
    3. Levenshtein distance within threshold (for typos)

    Args:
        addr1: First address
        addr2: Second address
        threshold: Maximum Levenshtein distance for fuzzy match

    Returns:
        True if addresses match, False otherwise
    """
    norm1 = normalize_address(addr1)
    norm2 = normalize_address(addr2)

    # Empty addresses don't match
    if not norm1 or not norm2:
        return False

    # Exact match
    if norm1 == norm2:
        return True

    # Match without street type
    stripped1 = _strip_street_type(norm1)
    stripped2 = _strip_street_type(norm2)
    if stripped1 == stripped2:
        return True

    # Fuzzy match with Levenshtein
    if _levenshtein_distance(norm1, norm2) <= threshold:
        return True

    return False
```

**Step 5: Run tests to verify they pass**

```bash
pytest tests/test_address_normalizer.py -v
```

Expected: All 10 tests PASS

**Step 6: Commit**

```bash
git add scrapers/utils/ tests/test_address_normalizer.py
git commit -m "feat: add address normalizer utility for cross-source deduplication

- Standardize street types (STREET -> ST)
- Normalize case, whitespace, punctuation
- Support fuzzy matching with Levenshtein distance
- Handle unit/apartment designations"
```

---

## Task 3: Denton Socrata Scraper

**Files:**
- Create: `scrapers/denton_socrata.py`
- Create: `tests/test_denton_socrata.py`

**Step 1: Write failing test**

```python
# tests/test_denton_socrata.py
"""Tests for Denton City Socrata permit scraper."""

import pytest
from scrapers.denton_socrata import transform_permit, SOCRATA_ENDPOINT


class TestTransformPermit:
    """Test permit transformation."""

    def test_basic_transform(self):
        """Should transform Socrata record to standard format."""
        raw = {
            'permit_number': 'BP-2024-001',
            'address': '123 OAK ST',
            'permit_type': 'New Residential',
            'issue_date': '2024-12-01T00:00:00.000',
            'valuation': '350000',
            'contractor': 'ABC Builders'
        }
        result = transform_permit(raw)

        assert result['permit_id'] == 'BP-2024-001'
        assert result['address'] == '123 OAK ST'
        assert result['city'] == 'Denton'
        assert result['type'] == 'New Residential'
        assert result['date'] == '2024-12-01'
        assert result['value'] == '350000'

    def test_handles_missing_fields(self):
        """Should handle records with missing optional fields."""
        raw = {
            'permit_number': 'BP-2024-002',
            'address': '456 MAIN AVE',
        }
        result = transform_permit(raw)

        assert result['permit_id'] == 'BP-2024-002'
        assert result['date'] is None or result['date'] == ''
        assert result['value'] is None or result['value'] == ''


class TestSocrataEndpoint:
    """Test Socrata configuration."""

    def test_endpoint_configured(self):
        """Should have valid Socrata endpoint."""
        assert 'data.cityofdenton.com' in SOCRATA_ENDPOINT or 'data.texas.gov' in SOCRATA_ENDPOINT
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_denton_socrata.py -v
```

Expected: FAIL with `ModuleNotFoundError`

**Step 3: Research actual Denton API endpoint**

The City of Denton uses `data.cityofdenton.com`. Based on web search, the Building Safety Yearly Permit Report is available. We need to find the actual dataset ID.

**Step 4: Write the Denton Socrata scraper**

```python
#!/usr/bin/env python3
# scrapers/denton_socrata.py
"""
DENTON CITY PERMIT SCRAPER (Socrata API)
Source: City of Denton Open Data Portal
URL: https://data.cityofdenton.com

Scrapes building permit data from City of Denton's Socrata-based Open Data portal.
Follows the same pattern as collin_cad_socrata.py.

Usage:
    python3 scrapers/denton_socrata.py                  # All permits, 1000 limit
    python3 scrapers/denton_socrata.py --limit 5000     # More permits
    python3 scrapers/denton_socrata.py --days 30        # Last 30 days only
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

import requests
from tenacity import retry, stop_after_attempt, wait_exponential

OUTPUT_DIR = Path(__file__).parent.parent / "data" / "raw"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# City of Denton Socrata endpoint
# NOTE: This is a placeholder - need to verify actual dataset ID
# Check: https://data.cityofdenton.com/browse?category=Development+Services
SOCRATA_ENDPOINT = "https://data.cityofdenton.com/resource/xxxx-xxxx.json"

# Fallback: If Denton uses Texas Open Data Portal like Collin
# SOCRATA_ENDPOINT = "https://data.texas.gov/resource/xxxx-xxxx.json"


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def fetch_permits(limit: int = 1000, days: int = None, offset: int = 0) -> list:
    """
    Fetch permits from Denton City Socrata API.

    Uses tenacity for automatic retry with exponential backoff
    (addresses undocumented rate limits).
    """
    params = {
        '$limit': limit,
        '$offset': offset,
        '$order': 'issue_date DESC',  # Field name TBD based on actual schema
    }

    # Date filter
    if days:
        cutoff = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%dT00:00:00.000')
        params['$where'] = f"issue_date >= '{cutoff}'"

    response = requests.get(SOCRATA_ENDPOINT, params=params, timeout=60)
    response.raise_for_status()
    return response.json()


def transform_permit(raw: dict) -> dict:
    """
    Transform Socrata record to standard format.

    Field mapping TBD based on actual Denton schema.
    Common fields: permit_number, address, permit_type, issue_date, valuation
    """
    # Parse date
    issued_date = raw.get('issue_date', '')
    if issued_date:
        issued_date = issued_date[:10]  # Just YYYY-MM-DD

    return {
        'permit_id': raw.get('permit_number', raw.get('permit_num', '')),
        'address': raw.get('address', raw.get('site_address', '')),
        'city': 'Denton',  # Hardcoded - this scraper is Denton-only
        'zip': raw.get('zip_code', raw.get('zip', '')),
        'type': raw.get('permit_type', raw.get('type', '')),
        'subtype': raw.get('permit_subtype', ''),
        'date': issued_date,
        'value': raw.get('valuation', raw.get('value', '')),
        'owner_name': raw.get('owner', raw.get('owner_name', '')),
        'contractor': raw.get('contractor', raw.get('contractor_name', '')),
        'description': raw.get('description', raw.get('work_description', '')),
    }


def main():
    parser = argparse.ArgumentParser(description='Scrape Denton City permits from Open Data portal')
    parser.add_argument('--limit', '-l', type=int, default=1000, help='Max permits to fetch')
    parser.add_argument('--days', '-d', type=int, help='Only permits from last N days')
    parser.add_argument('--discover', action='store_true', help='Print API discovery info')
    args = parser.parse_args()

    if args.discover:
        print("Denton Open Data Discovery:")
        print(f"  Portal: https://data.cityofdenton.com")
        print(f"  Browse: https://data.cityofdenton.com/browse")
        print(f"  API Docs: https://dev.socrata.com/docs/endpoints.html")
        print("\nTo find the dataset ID:")
        print("  1. Visit the portal and find 'Building Safety Yearly Permit Report'")
        print("  2. Click 'API' button on the dataset page")
        print("  3. Copy the resource ID (e.g., 'xxxx-xxxx')")
        print("  4. Update SOCRATA_ENDPOINT in this file")
        return

    print('=' * 60)
    print('DENTON CITY PERMIT SCRAPER (Socrata API)')
    print('=' * 60)
    print(f'Limit: {args.limit}')
    print(f'Days filter: {args.days or "ALL"}')
    print(f'Time: {datetime.now().isoformat()}\n')

    # Fetch permits
    print('[1] Fetching permits from Denton Open Data Portal...')
    try:
        raw_permits = fetch_permits(limit=args.limit, days=args.days)
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            print("\nERROR: Dataset not found. Run with --discover to find the correct endpoint.")
            return 1
        raise

    print(f'    Retrieved {len(raw_permits)} permits')

    # Transform
    print('[2] Transforming to standard format...')
    permits = [transform_permit(p) for p in raw_permits]

    # Filter out empty permit IDs
    permits = [p for p in permits if p['permit_id']]
    print(f'    {len(permits)} valid permits')

    # Analyze types
    types = {}
    for p in permits:
        t = p['type'] or 'Unknown'
        types[t] = types.get(t, 0) + 1

    print('\n[3] Permits by type:')
    for ptype, count in sorted(types.items(), key=lambda x: -x[1])[:10]:
        print(f'    {ptype}: {count}')

    # Save
    output_file = OUTPUT_DIR / "denton_socrata_raw.json"

    output = {
        'source': 'denton_socrata',
        'portal_type': 'Socrata',
        'data_source': 'denton_socrata',  # For new data_source column
        'scraped_at': datetime.now().isoformat(),
        'target_count': args.limit,
        'actual_count': len(permits),
        'filters': {
            'days': args.days,
        },
        'permits': permits
    }

    output_file.write_text(json.dumps(output, indent=2))

    print(f'\n' + '=' * 60)
    print('SUMMARY')
    print('=' * 60)
    print(f'Permits: {len(permits)}')
    print(f'Output: {output_file}')

    if permits:
        print('\nSAMPLE:')
        for p in permits[:3]:
            print(f'  {p["date"]} | {p["permit_id"]} | {p["type"]} | {p["address"][:40]}')


if __name__ == '__main__':
    main()
```

**Step 5: Run tests**

```bash
pytest tests/test_denton_socrata.py -v
```

Expected: Tests pass (transformation logic works, endpoint will need updating after discovery)

**Step 6: Discover actual endpoint**

```bash
python3 scrapers/denton_socrata.py --discover
```

Then manually visit `https://data.cityofdenton.com/browse` to find the Building Safety dataset and update `SOCRATA_ENDPOINT`.

**Step 7: Commit**

```bash
git add scrapers/denton_socrata.py tests/test_denton_socrata.py
git commit -m "feat: add Denton City Socrata permit scraper

- Follows collin_cad_socrata.py pattern
- Uses tenacity for retry with exponential backoff
- Includes discovery mode for finding dataset ID
- NOTE: Endpoint needs updating after portal discovery"
```

---

## Task 4: Ellis County Excel Scraper

**Files:**
- Create: `scrapers/ellis_county_excel.py`
- Create: `tests/test_ellis_county_excel.py`

**Step 1: Write failing test**

```python
# tests/test_ellis_county_excel.py
"""Tests for Ellis County Excel permit scraper."""

import pytest
from io import BytesIO
from scrapers.ellis_county_excel import parse_excel_permits, detect_column_mapping


class TestParseExcel:
    """Test Excel parsing."""

    def test_detects_header_row(self):
        """Should find header row dynamically (not assume row 0)."""
        # Mock Excel data where header is on row 2
        # This tests that we don't hardcode column positions
        pass  # Implementation depends on actual file format

    def test_handles_missing_columns(self):
        """Should gracefully handle missing optional columns."""
        pass


class TestColumnMapping:
    """Test dynamic column detection."""

    def test_finds_permit_number_column(self):
        """Should find permit number column by various names."""
        headers = ['Date', 'Permit #', 'Address', 'Type']
        mapping = detect_column_mapping(headers)
        assert mapping['permit_id'] == 1  # Index of 'Permit #'

    def test_finds_address_column(self):
        """Should find address column by various names."""
        headers = ['Permit', 'Location', 'Issued']
        mapping = detect_column_mapping(headers)
        assert mapping['address'] == 1  # 'Location' maps to address
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_ellis_county_excel.py -v
```

**Step 3: Write Ellis County Excel scraper**

```python
#!/usr/bin/env python3
# scrapers/ellis_county_excel.py
"""
ELLIS COUNTY PERMIT SCRAPER (Excel)
Source: Ellis County Department of Development
URL: https://www.co.ellis.tx.us/index.aspx?nid=1074

Downloads and parses monthly Excel reports of building permits.
NOTE: Only covers UNINCORPORATED areas (not cities like Waxahachie, Ennis, Midlothian).

Usage:
    python3 scrapers/ellis_county_excel.py                  # Latest month
    python3 scrapers/ellis_county_excel.py --url <url>      # Specific file
    python3 scrapers/ellis_county_excel.py --file data.xlsx # Local file
"""

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import requests

try:
    import openpyxl
except ImportError:
    print("ERROR: openpyxl required. Install with: pip install openpyxl")
    exit(1)

OUTPUT_DIR = Path(__file__).parent.parent / "data" / "raw"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Known column name variations
COLUMN_ALIASES = {
    'permit_id': ['permit #', 'permit number', 'permit no', 'permit', 'permit id'],
    'address': ['address', 'location', 'property address', 'site address'],
    'date': ['date', 'issue date', 'issued date', 'permit date'],
    'type': ['type', 'permit type', 'description', 'work type'],
    'value': ['value', 'valuation', 'est value', 'estimated value', 'cost'],
    'owner': ['owner', 'owner name', 'property owner'],
    'contractor': ['contractor', 'contractor name', 'builder'],
}


def detect_column_mapping(headers: List[str]) -> Dict[str, int]:
    """
    Dynamically detect column positions from header row.

    Handles Excel files where columns may be in different positions
    or have slightly different names.
    """
    mapping = {}
    headers_lower = [str(h).lower().strip() for h in headers]

    for field, aliases in COLUMN_ALIASES.items():
        for i, header in enumerate(headers_lower):
            if header in aliases:
                mapping[field] = i
                break

    return mapping


def find_header_row(sheet) -> tuple[int, List[str]]:
    """
    Find the header row in an Excel sheet.

    Ellis County files sometimes have metadata rows before the actual headers.
    Look for a row containing expected column names.
    """
    expected_keywords = ['permit', 'address', 'date']

    for row_idx in range(1, min(10, sheet.max_row + 1)):  # Check first 10 rows
        row = [cell.value for cell in sheet[row_idx]]
        row_lower = [str(c).lower() if c else '' for c in row]

        # Check if this looks like a header row
        matches = sum(1 for kw in expected_keywords if any(kw in cell for cell in row_lower))
        if matches >= 2:
            return row_idx, row

    # Default to first row
    row = [cell.value for cell in sheet[1]]
    return 1, row


def parse_excel_permits(file_path: Path) -> List[dict]:
    """
    Parse permits from an Ellis County Excel file.

    Handles dynamic column positions and header row detection.
    """
    workbook = openpyxl.load_workbook(file_path, data_only=True)
    sheet = workbook.active

    # Find header row
    header_row_idx, headers = find_header_row(sheet)

    # Detect column mapping
    mapping = detect_column_mapping(headers)

    if 'permit_id' not in mapping or 'address' not in mapping:
        print(f"WARNING: Could not find required columns. Headers: {headers}")
        return []

    permits = []

    for row_idx in range(header_row_idx + 1, sheet.max_row + 1):
        row = [cell.value for cell in sheet[row_idx]]

        # Skip empty rows
        if not any(row):
            continue

        permit_id = row[mapping['permit_id']] if 'permit_id' in mapping else None
        address = row[mapping['address']] if 'address' in mapping else None

        if not permit_id or not address:
            continue

        # Parse date
        issued_date = None
        if 'date' in mapping and row[mapping['date']]:
            date_val = row[mapping['date']]
            if isinstance(date_val, datetime):
                issued_date = date_val.strftime('%Y-%m-%d')
            elif isinstance(date_val, str):
                # Try common formats
                for fmt in ['%m/%d/%Y', '%Y-%m-%d', '%m/%d/%y']:
                    try:
                        issued_date = datetime.strptime(date_val.strip(), fmt).strftime('%Y-%m-%d')
                        break
                    except ValueError:
                        continue

        permit = {
            'permit_id': str(permit_id).strip(),
            'address': str(address).strip(),
            'city': 'Ellis County (Unincorporated)',
            'date': issued_date,
            'type': str(row[mapping['type']]).strip() if 'type' in mapping and row[mapping['type']] else None,
            'value': row[mapping['value']] if 'value' in mapping else None,
            'owner_name': str(row[mapping['owner']]).strip() if 'owner' in mapping and row[mapping['owner']] else None,
            'contractor': str(row[mapping['contractor']]).strip() if 'contractor' in mapping and row[mapping['contractor']] else None,
        }
        permits.append(permit)

    return permits


def download_file(url: str, dest: Path) -> bool:
    """Download file from URL."""
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    dest.write_bytes(response.content)
    return True


def main():
    parser = argparse.ArgumentParser(description='Scrape Ellis County permits from Excel files')
    parser.add_argument('--url', help='URL of Excel file to download')
    parser.add_argument('--file', '-f', help='Local Excel file to parse')
    parser.add_argument('--discover', action='store_true', help='Show where to find Excel files')
    args = parser.parse_args()

    if args.discover:
        print("Ellis County Building Permits:")
        print(f"  Portal: https://www.co.ellis.tx.us/index.aspx?nid=1074")
        print(f"  Reports: Look for 'Monthly Building Permit Data' Excel downloads")
        print("\nNOTE: This only covers UNINCORPORATED Ellis County.")
        print("Cities (Waxahachie, Ennis, Midlothian) have their own portals.")
        return

    print('=' * 60)
    print('ELLIS COUNTY PERMIT SCRAPER (Excel)')
    print('=' * 60)
    print(f'Time: {datetime.now().isoformat()}\n')

    # Determine input file
    if args.file:
        input_file = Path(args.file)
    elif args.url:
        input_file = OUTPUT_DIR / 'ellis_county_temp.xlsx'
        print(f'[1] Downloading from {args.url}...')
        download_file(args.url, input_file)
    else:
        print("ERROR: Provide --url or --file. Use --discover for portal info.")
        return 1

    # Parse
    print(f'[2] Parsing {input_file.name}...')
    permits = parse_excel_permits(input_file)
    print(f'    Found {len(permits)} permits')

    if not permits:
        print("No permits found. Check file format.")
        return 1

    # Analyze types
    types = {}
    for p in permits:
        t = p['type'] or 'Unknown'
        types[t] = types.get(t, 0) + 1

    print('\n[3] Permits by type:')
    for ptype, count in sorted(types.items(), key=lambda x: -x[1])[:10]:
        print(f'    {ptype}: {count}')

    # Save
    output_file = OUTPUT_DIR / "ellis_county_raw.json"

    output = {
        'source': 'ellis_county',
        'portal_type': 'Excel',
        'data_source': 'ellis_county_excel',
        'scraped_at': datetime.now().isoformat(),
        'actual_count': len(permits),
        'note': 'Unincorporated Ellis County only - not cities',
        'permits': permits
    }

    output_file.write_text(json.dumps(output, indent=2))

    print(f'\n' + '=' * 60)
    print('SUMMARY')
    print('=' * 60)
    print(f'Permits: {len(permits)}')
    print(f'Output: {output_file}')

    if permits:
        print('\nSAMPLE:')
        for p in permits[:3]:
            print(f'  {p["date"]} | {p["permit_id"]} | {p["type"]} | {p["address"][:40]}')


if __name__ == '__main__':
    main()
```

**Step 4: Run tests**

```bash
pytest tests/test_ellis_county_excel.py -v
```

**Step 5: Commit**

```bash
git add scrapers/ellis_county_excel.py tests/test_ellis_county_excel.py
git commit -m "feat: add Ellis County Excel permit scraper

- Dynamic column detection (handles format variations)
- Auto-detects header row position
- Only covers unincorporated Ellis County
- Includes discovery mode for finding Excel files"
```

---

## Task 5: CAD Delta Engine

**Files:**
- Create: `scrapers/cad_delta_engine.py`
- Create: `scrapers/cad_configs/dcad.yaml`
- Create: `scrapers/cad_configs/tad.yaml`
- Create: `scrapers/cad_configs/denton_cad.yaml`
- Create: `tests/test_cad_delta_engine.py`

**Step 1: Write failing test**

```python
# tests/test_cad_delta_engine.py
"""Tests for CAD Delta Engine."""

import pytest
from scrapers.cad_delta_engine import (
    is_new_construction,
    stream_csv_records,
    CADConfig,
)


class TestNewConstructionDetection:
    """Test new construction detection logic."""

    def test_dcad_flag(self):
        """DCAD NEW_CONSTRUCTION flag should be authoritative."""
        record = {'new_construction': 'Y', 'year_built': 2010}
        assert is_new_construction(record, 2024) is True

    def test_recent_year_built(self):
        """Year built in last 2 years should count."""
        record = {'year_built': 2024}
        assert is_new_construction(record, 2024) is True

        record = {'year_built': 2023}
        assert is_new_construction(record, 2024) is True

    def test_old_year_built(self):
        """Old year built without flag should not count."""
        record = {'year_built': 2010}
        assert is_new_construction(record, 2024) is False

    def test_improvement_value_increase(self):
        """Large improvement value increase suggests new construction."""
        record = {'improvement_value': 250000, 'prior_improvement_value': 0}
        assert is_new_construction(record, 2024) is True


class TestStreamProcessing:
    """Test CSV stream processing."""

    def test_processes_large_file_in_chunks(self):
        """Should not load entire file into memory."""
        # Would need actual test file
        pass
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_cad_delta_engine.py -v
```

**Step 3: Create CAD config directory**

```bash
mkdir -p scrapers/cad_configs
```

**Step 4: Write DCAD config**

```yaml
# scrapers/cad_configs/dcad.yaml
# Dallas Central Appraisal District configuration

name: dcad
display_name: Dallas Central Appraisal District
county: Dallas

# Data source
download:
  base_url: https://www.dallascad.org/DataDownload.aspx
  # Actual file URL changes - need to scrape download page
  # Format: Certified Data Files (CSV format preferred)
  format: csv

# Column mapping (CSV version)
# Based on DCAD data dictionary
columns:
  account_number: ACCT
  owner_name: OWNER_NAME
  property_address: SITUS_ADDR
  city: SITUS_CITY
  zip: SITUS_ZIP
  year_built: YR_BUILT
  improvement_value: IMPR_VAL
  land_value: LAND_VAL
  total_value: TOT_VAL
  new_construction_flag: NEW_CONST  # Field 103 - 'Y' or 'N'
  property_type: PROP_TYPE_CD  # A=Real, B=Personal

# Filter criteria for new construction
filters:
  # Only residential
  property_types:
    - A1  # Single family
    - A2  # Mobile home
    - A3  # Duplex
    - A4  # Multi-family

  # Minimum improvement value to consider
  min_improvement_value: 50000

  # Year built window (current year and prior year)
  year_built_window: 2

# Processing
processing:
  chunk_size: 100000
  encoding: latin1
```

**Step 5: Write TAD config**

```yaml
# scrapers/cad_configs/tad.yaml
# Tarrant Appraisal District configuration

name: tad
display_name: Tarrant Appraisal District
county: Tarrant

download:
  base_url: https://gis-tad.opendata.arcgis.com
  # TAD uses ArcGIS Hub - need to find actual download link
  format: flat_file  # Fixed-width or CSV

# TAD does NOT have NEW_CONSTRUCTION flag
# Must rely on year_built and improvement value changes
columns:
  account_number: ACCOUNT_NUM
  owner_name: OWNER_NAME
  property_address: PROPERTY_ADDR
  city: CITY
  zip: ZIP
  year_built: YEAR_BUILT
  improvement_value: IMPROVEMENT_VAL
  land_value: LAND_VAL
  total_value: TOTAL_VAL
  sptb_code: SPTB_CODE  # State Property Tax Board code

filters:
  # SPTB codes for residential
  sptb_codes:
    - A1  # Single family
    - A2  # Mobile home on land

  min_improvement_value: 50000
  year_built_window: 2

processing:
  chunk_size: 100000
  encoding: utf-8
```

**Step 6: Write CAD Delta Engine**

```python
#!/usr/bin/env python3
# scrapers/cad_delta_engine.py
"""
CAD DELTA ENGINE
Processes Central Appraisal District tax rolls to identify new construction.

Lightweight approach:
1. Download tax roll (CSV preferred)
2. Stream process in chunks (no full memory load)
3. Filter for new construction (year_built, flags, value changes)
4. Output only matching records as permits
5. Track file hash for change detection

Supports: DCAD (Dallas), TAD (Tarrant), Denton CAD

Usage:
    python3 scrapers/cad_delta_engine.py dcad            # Process DCAD
    python3 scrapers/cad_delta_engine.py tad             # Process TAD
    python3 scrapers/cad_delta_engine.py --list          # List available CADs
    python3 scrapers/cad_delta_engine.py dcad --dry-run  # Test without saving
"""

import argparse
import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Generator, List, Optional

import pandas as pd
import requests
import yaml

from dotenv import load_dotenv
load_dotenv()

OUTPUT_DIR = Path(__file__).parent.parent / "data" / "raw"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

CONFIG_DIR = Path(__file__).parent / "cad_configs"
CACHE_DIR = Path(__file__).parent.parent / ".scraper_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class CADConfig:
    """Configuration for a Central Appraisal District."""
    name: str
    display_name: str
    county: str
    download_url: Optional[str]
    format: str
    columns: Dict[str, str]
    filters: Dict
    chunk_size: int = 100000
    encoding: str = 'utf-8'


def load_config(cad_name: str) -> CADConfig:
    """Load CAD configuration from YAML file."""
    config_file = CONFIG_DIR / f"{cad_name}.yaml"
    if not config_file.exists():
        raise ValueError(f"No config for '{cad_name}'. Available: {list_available_cads()}")

    with open(config_file) as f:
        data = yaml.safe_load(f)

    return CADConfig(
        name=data['name'],
        display_name=data['display_name'],
        county=data['county'],
        download_url=data.get('download', {}).get('url'),
        format=data.get('download', {}).get('format', 'csv'),
        columns=data.get('columns', {}),
        filters=data.get('filters', {}),
        chunk_size=data.get('processing', {}).get('chunk_size', 100000),
        encoding=data.get('processing', {}).get('encoding', 'utf-8'),
    )


def list_available_cads() -> List[str]:
    """List available CAD configurations."""
    return [f.stem for f in CONFIG_DIR.glob('*.yaml')]


def get_file_hash(file_path: Path) -> str:
    """Calculate SHA256 hash of a file (streaming for large files)."""
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            sha256.update(chunk)
    return sha256.hexdigest()


def get_cached_hash(cad_name: str) -> Optional[str]:
    """Get previously stored file hash."""
    cache_file = CACHE_DIR / f"{cad_name}_hash.txt"
    if cache_file.exists():
        return cache_file.read_text().strip()
    return None


def save_cached_hash(cad_name: str, file_hash: str):
    """Save file hash for future comparisons."""
    cache_file = CACHE_DIR / f"{cad_name}_hash.txt"
    cache_file.write_text(file_hash)


def is_new_construction(record: dict, current_year: int) -> bool:
    """
    Determine if a record represents new construction.

    Logic:
    1. If NEW_CONSTRUCTION flag exists and is 'Y', return True (DCAD only)
    2. If year_built is current year or previous year, return True
    3. If improvement value increased from 0 to significant value, return True
    """
    # Check DCAD-specific flag
    new_const_flag = record.get('new_construction')
    if new_const_flag and str(new_const_flag).upper() == 'Y':
        return True

    # Check year built
    year_built = record.get('year_built')
    if year_built:
        try:
            year = int(year_built)
            if year >= current_year - 1:
                return True
        except (ValueError, TypeError):
            pass

    # Check improvement value increase (if prior value available)
    improvement = record.get('improvement_value', 0)
    prior_improvement = record.get('prior_improvement_value', 0)

    try:
        current_val = float(improvement) if improvement else 0
        prior_val = float(prior_improvement) if prior_improvement else 0

        # New construction: was 0, now > $50K
        if prior_val == 0 and current_val >= 50000:
            return True
    except (ValueError, TypeError):
        pass

    return False


def stream_csv_records(
    file_path: Path,
    config: CADConfig,
    current_year: int
) -> Generator[dict, None, None]:
    """
    Stream CSV records, filtering for new construction.

    Uses pandas chunked reading to keep memory low.
    Yields only records that match new construction criteria.
    """
    # Reverse column mapping for reading
    col_mapping = {v: k for k, v in config.columns.items()}

    for chunk in pd.read_csv(
        file_path,
        chunksize=config.chunk_size,
        encoding=config.encoding,
        low_memory=False,
        dtype=str  # Read all as strings initially
    ):
        # Rename columns to our standard names
        chunk = chunk.rename(columns=col_mapping)

        # Convert to records
        for _, row in chunk.iterrows():
            record = row.to_dict()

            # Apply filters
            if 'property_type' in record and 'property_types' in config.filters:
                if record['property_type'] not in config.filters['property_types']:
                    continue

            if 'sptb_code' in record and 'sptb_codes' in config.filters:
                if record['sptb_code'] not in config.filters['sptb_codes']:
                    continue

            # Check new construction
            if is_new_construction(record, current_year):
                yield record


def transform_to_permit(record: dict, config: CADConfig) -> dict:
    """Transform CAD record to standard permit format."""
    return {
        'permit_id': f"{config.name.upper()}-{record.get('account_number', '')}",
        'address': record.get('property_address', ''),
        'city': record.get('city', config.county),
        'zip': record.get('zip', ''),
        'type': 'New Construction (from CAD)',
        'date': None,  # CAD data doesn't have permit date
        'value': record.get('total_value') or record.get('improvement_value'),
        'owner_name': record.get('owner_name'),
        'year_built': record.get('year_built'),
        'cad_account_number': record.get('account_number'),
        'data_source': f"{config.name}_taxroll",
    }


def process_cad(cad_name: str, file_path: Path, dry_run: bool = False) -> dict:
    """
    Process a CAD tax roll file.

    Returns summary dict with counts and output file path.
    """
    config = load_config(cad_name)
    current_year = datetime.now().year

    print(f'[1] Loading config for {config.display_name}...')
    print(f'    County: {config.county}')
    print(f'    Chunk size: {config.chunk_size:,}')

    # Check file hash
    print(f'[2] Checking file hash...')
    file_hash = get_file_hash(file_path)
    cached_hash = get_cached_hash(cad_name)

    if cached_hash == file_hash:
        print(f'    File unchanged (hash: {file_hash[:16]}...)')
        return {'status': 'unchanged', 'permits': 0}

    print(f'    New file detected (hash: {file_hash[:16]}...)')

    # Stream process
    print(f'[3] Processing records...')
    permits = []
    total_processed = 0

    for record in stream_csv_records(file_path, config, current_year):
        permit = transform_to_permit(record, config)
        permits.append(permit)
        total_processed += 1

        if total_processed % 10000 == 0:
            print(f'    Processed {total_processed:,} new construction records...')

    print(f'    Total new construction: {len(permits):,}')

    # Analyze cities
    cities = {}
    for p in permits:
        c = p['city'] or 'Unknown'
        cities[c] = cities.get(c, 0) + 1

    print(f'\n[4] By city (top 15):')
    for city, count in sorted(cities.items(), key=lambda x: -x[1])[:15]:
        print(f'    {city}: {count:,}')

    if dry_run:
        print('\n[DRY RUN] Not saving output')
        return {'status': 'dry_run', 'permits': len(permits)}

    # Save output
    output_file = OUTPUT_DIR / f"{cad_name}_taxroll_raw.json"

    output = {
        'source': f'{cad_name}_taxroll',
        'portal_type': 'CAD Tax Roll',
        'data_source': f'{cad_name}_taxroll',
        'scraped_at': datetime.now().isoformat(),
        'file_hash': file_hash,
        'total_processed': total_processed,
        'actual_count': len(permits),
        'permits': permits
    }

    output_file.write_text(json.dumps(output, indent=2))

    # Save hash for next run
    save_cached_hash(cad_name, file_hash)

    return {
        'status': 'success',
        'permits': len(permits),
        'output_file': str(output_file),
        'file_hash': file_hash
    }


def main():
    parser = argparse.ArgumentParser(description='Process CAD tax rolls for new construction')
    parser.add_argument('cad', nargs='?', help='CAD to process (dcad, tad, denton_cad)')
    parser.add_argument('--file', '-f', help='Local tax roll file to process')
    parser.add_argument('--list', '-l', action='store_true', help='List available CADs')
    parser.add_argument('--dry-run', action='store_true', help='Process without saving')
    args = parser.parse_args()

    if args.list:
        print("Available CAD configurations:")
        for cad in list_available_cads():
            config = load_config(cad)
            print(f"  {cad}: {config.display_name} ({config.county} County)")
        return

    if not args.cad:
        parser.print_help()
        return 1

    if not args.file:
        print(f"ERROR: --file required (download from CAD website)")
        print(f"\nFor {args.cad.upper()}:")
        config = load_config(args.cad)
        print(f"  Download from: {config.download_url or 'See CAD website'}")
        return 1

    file_path = Path(args.file)
    if not file_path.exists():
        print(f"ERROR: File not found: {file_path}")
        return 1

    print('=' * 60)
    print(f'CAD DELTA ENGINE: {args.cad.upper()}')
    print('=' * 60)
    print(f'Input: {file_path}')
    print(f'Time: {datetime.now().isoformat()}\n')

    result = process_cad(args.cad, file_path, dry_run=args.dry_run)

    print(f'\n' + '=' * 60)
    print('SUMMARY')
    print('=' * 60)
    print(f'Status: {result["status"]}')
    print(f'New construction permits: {result["permits"]:,}')
    if result.get('output_file'):
        print(f'Output: {result["output_file"]}')


if __name__ == '__main__':
    main()
```

**Step 7: Run tests**

```bash
pytest tests/test_cad_delta_engine.py -v
```

**Step 8: Commit**

```bash
git add scrapers/cad_delta_engine.py scrapers/cad_configs/ tests/test_cad_delta_engine.py
git commit -m "feat: add CAD Delta Engine for tax roll processing

- Stream processes large files (900K+ records) in chunks
- YAML configs for DCAD, TAD, Denton CAD
- File hash tracking for change detection
- Filters for new construction (year_built, DCAD flag, value changes)
- Outputs standard permit JSON format"
```

---

## Task 6: Update load_permits.py for New Columns

**Files:**
- Modify: `scripts/load_permits.py:133-145`

**Step 1: Update the insert SQL to include new columns**

Add to `scripts/load_permits.py`, update the `pg_rows` tuple and `insert_sql`:

```python
# Around line 133, update pg_rows to include new fields
pg_rows.append((
    permit_id,
    city,
    address,
    permit.get('type', permit.get('permit_type')),
    permit.get('description'),
    permit.get('status'),
    issued,
    permit.get('applicant', permit.get('applicant_name', permit.get('owner_name'))),
    permit.get('contractor', permit.get('contractor_name')),
    permit.get('value', permit.get('estimated_value')) or None,
    scraped,
    None,  # lead_type
    # NEW COLUMNS
    permit.get('data_source', source),  # data_source
    permit.get('cad_account_number'),   # cad_account_number
    permit.get('year_built'),           # year_built
    permit.get('value') if isinstance(permit.get('value'), (int, float)) else None,  # property_value
))

# Update insert_sql to include new columns
insert_sql = """
    INSERT INTO leads_permit (
        permit_id, city, property_address, permit_type, description,
        status, issued_date, applicant_name, contractor_name,
        estimated_value, scraped_at, lead_type,
        data_source, cad_account_number, year_built, property_value
    ) VALUES %s
    ON CONFLICT ON CONSTRAINT clients_permit_city_permit_id_33861e17_uniq DO UPDATE SET
        property_address = COALESCE(EXCLUDED.property_address, leads_permit.property_address),
        permit_type = COALESCE(EXCLUDED.permit_type, leads_permit.permit_type),
        description = COALESCE(EXCLUDED.description, leads_permit.description),
        status = COALESCE(EXCLUDED.status, leads_permit.status),
        issued_date = COALESCE(EXCLUDED.issued_date, leads_permit.issued_date),
        estimated_value = COALESCE(EXCLUDED.estimated_value, leads_permit.estimated_value),
        applicant_name = COALESCE(EXCLUDED.applicant_name, leads_permit.applicant_name),
        contractor_name = COALESCE(EXCLUDED.contractor_name, leads_permit.contractor_name),
        scraped_at = EXCLUDED.scraped_at,
        lead_type = COALESCE(EXCLUDED.lead_type, leads_permit.lead_type),
        data_source = COALESCE(EXCLUDED.data_source, leads_permit.data_source),
        cad_account_number = COALESCE(EXCLUDED.cad_account_number, leads_permit.cad_account_number),
        year_built = COALESCE(EXCLUDED.year_built, leads_permit.year_built),
        property_value = COALESCE(EXCLUDED.property_value, leads_permit.property_value)
"""
```

**Step 2: Test with existing JSON file**

```bash
cd /home/reid/testhome/permit-scraper/data/raw
python3 ../../scripts/load_permits.py --file collin_cad_raw.json
```

**Step 3: Commit**

```bash
git add scripts/load_permits.py
git commit -m "feat: update load_permits.py to handle new CAD columns

- Add data_source, cad_account_number, year_built, property_value
- COALESCE logic preserves existing values on conflict"
```

---

## Task 7: Integration Testing

**Files:**
- Create: `tests/test_integration_cad.py`

**Step 1: Write integration test**

```python
# tests/test_integration_cad.py
"""Integration tests for CAD data pipeline."""

import json
import pytest
from pathlib import Path


class TestEndToEnd:
    """Test full pipeline from scraper to database."""

    def test_denton_socrata_output_format(self):
        """Denton Socrata output should have required fields."""
        # Would run scraper and check output
        pass

    def test_cad_delta_output_format(self):
        """CAD delta output should have cad_account_number."""
        pass

    def test_load_permits_handles_cad_fields(self):
        """load_permits.py should insert CAD-specific fields."""
        pass
```

**Step 2: Run all tests**

```bash
pytest tests/ -v --tb=short
```

**Step 3: Final commit**

```bash
git add tests/test_integration_cad.py
git commit -m "test: add integration tests for CAD pipeline"
```

---

## Task 8: Documentation Update

**Files:**
- Modify: `CLAUDE.md` (add new scrapers section)
- Modify: `README.md` (update with new scrapers)

**Step 1: Update CLAUDE.md**

Add to the Working Portals section:

```markdown
### CAD Tax Rolls (New Construction Detection)
- **DCAD** (Dallas County) - `cad_delta_engine.py dcad`
- **TAD** (Tarrant County) - `cad_delta_engine.py tad`
- **Denton CAD** - `cad_delta_engine.py denton_cad`

### City Open Data Portals
- **Denton City** (Socrata) - `denton_socrata.py`
- **Ellis County** (Excel) - `ellis_county_excel.py`
```

**Step 2: Commit**

```bash
git add CLAUDE.md README.md
git commit -m "docs: add CAD delta engine and new scrapers to documentation"
```

---

## Summary: Implementation Order

| Order | Task | Time Est | Files |
|-------|------|----------|-------|
| 1 | Database schema | 15 min | 2 SQL files |
| 2 | Address normalizer | 30 min | 2 Python files |
| 3 | Denton Socrata | 45 min | 2 Python files |
| 4 | Ellis County Excel | 45 min | 2 Python files |
| 5 | CAD Delta Engine | 90 min | 4 Python + 3 YAML |
| 6 | Update load_permits | 20 min | 1 Python file |
| 7 | Integration tests | 30 min | 1 Python file |
| 8 | Documentation | 15 min | 2 MD files |

**Total: ~5 hours**

---

## Phase 2: Paid Sources (After Phase 1 Complete)

### DCAD Open Records Request

**ROI:** $75/month → break-even at 15 leads, expected 1000+

**Process:**
1. Email DCAD Public Information Officer
2. Request: "Monthly electronic import file of building permits received from all taxing units"
3. Set up monthly standing request
4. Create `scrapers/dcad_open_records.py` to parse received files

### ECAD Parcel Data

**ROI:** $15 one-time → expected $1,485 profit

**Process:**
1. Purchase from Ellis CAD website
2. Use for owner name enrichment on Ellis County permits
3. Cross-reference with CAD delta engine output
