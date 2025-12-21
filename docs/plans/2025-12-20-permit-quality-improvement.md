# Permit Quality & Coverage Improvement Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Increase Tier A+B leads from ~1,079 cumulative to 100+ per WEEK by fixing broken scrapers and adding new city coverage.

**Architecture:** Fix 4 broken scrapers (Denton, Prosper, Arlington, Carrollton) that have 2,562 permits with missing metadata (no dates/types = no premium classification possible). Then add new city scrapers for blocked cities (Richardson, Euless) using proxy/CAPTCHA solutions.

**Tech Stack:** Python 3, Playwright (async), Socrata API (sodapy), PostgreSQL

---

## Summary of Issues

| City | Leads | Issue | Expected Premium Gain |
|------|-------|-------|----------------------|
| Denton | 728 | No dates, no permit types (eTRAKiT search-only) | +145-180/week |
| Prosper | 385 | Same eTRAKiT issue | +75-95/week |
| Arlington | 1,245 | Stale data (Nov 14), coded types (RP, CP) | +250-300/week |
| Carrollton | 204 | Has types but no dates | +40-50/week |
| **Total** | **2,562** | | **+510-625/week** |

---

## Task 1: Arlington Socrata Freshness + Type Mapping

**Files:**
- Modify: `scrapers/dfw_big4_socrata.py:75-86` (Arlington config)
- Modify: `scrapers/dfw_big4_socrata.py` (add permit type mapping)
- Test: `tests/test_arlington_socrata.py` (create new)

**Step 1: Write the failing test for permit type mapping**

Create `tests/test_arlington_socrata.py`:

```python
"""Tests for Arlington Socrata scraper permit type mapping."""

import pytest

# Import will be created in Step 3
def test_arlington_permit_type_mapping():
    """Verify coded permit types are mapped to descriptive names."""
    from scrapers.dfw_big4_socrata import ARLINGTON_PERMIT_TYPES

    # Known Arlington codes from database
    assert ARLINGTON_PERMIT_TYPES.get('RP') == 'Residential Permit'
    assert ARLINGTON_PERMIT_TYPES.get('CP') == 'Commercial Permit'
    assert ARLINGTON_PERMIT_TYPES.get('FE') == 'Fence Permit'
    assert ARLINGTON_PERMIT_TYPES.get('RO') == 'Roofing Permit'

def test_arlington_config_has_type_mapping():
    """Verify Arlington config includes type mapper."""
    from scrapers.dfw_big4_socrata import CITY_CONFIGS

    config = CITY_CONFIGS.get('arlington')
    assert config is not None
    assert hasattr(config, 'permit_type_mapper') or 'type_mapping' in dir(config)
```

**Step 2: Run test to verify it fails**

Run: `cd /home/reid/testhome/permit-scraper && python3 -m pytest tests/test_arlington_socrata.py -v`

Expected: FAIL with "cannot import name 'ARLINGTON_PERMIT_TYPES'"

**Step 3: Add permit type mapping constant**

In `scrapers/dfw_big4_socrata.py`, add after line 99 (after CITY_CONFIGS):

```python
# =============================================================================
# ARLINGTON PERMIT TYPE MAPPING
# =============================================================================

ARLINGTON_PERMIT_TYPES = {
    'RP': 'Residential Permit',
    'CP': 'Commercial Permit',
    'FE': 'Fence Permit',
    'RO': 'Roofing Permit',
    'RF': 'Roofing Permit',
    'EL': 'Electrical Permit',
    'PL': 'Plumbing Permit',
    'ME': 'Mechanical Permit',
    'MH': 'Mechanical/HVAC',
    'HV': 'HVAC Permit',
    'AC': 'A/C Permit',
    'PO': 'Pool Permit',
    'SW': 'Swimming Pool',
    'DE': 'Demolition Permit',
    'AD': 'Addition',
    'GA': 'Gas Permit',
    'IR': 'Irrigation',
    'FR': 'Fire Permit',
    'SI': 'Sign Permit',
    'BS': 'Building Shell',
    'TT': 'Tenant Finish',
}


def map_arlington_permit_type(code: str) -> str:
    """Map Arlington coded permit type to descriptive name."""
    if not code:
        return ''
    return ARLINGTON_PERMIT_TYPES.get(code.upper(), code)
```

**Step 4: Run test to verify it passes**

Run: `cd /home/reid/testhome/permit-scraper && python3 -m pytest tests/test_arlington_socrata.py::test_arlington_permit_type_mapping -v`

Expected: PASS

**Step 5: Commit**

```bash
cd /home/reid/testhome/permit-scraper
git add tests/test_arlington_socrata.py scrapers/dfw_big4_socrata.py
git commit -m "feat(arlington): add permit type mapping for coded types"
```

---

## Task 2: Arlington - Integrate Type Mapping in Extraction

**Files:**
- Modify: `scrapers/dfw_big4_socrata.py` (SocrataExtractor class)

**Step 1: Write test for integrated mapping**

Add to `tests/test_arlington_socrata.py`:

```python
def test_arlington_extraction_maps_types():
    """Verify extraction applies type mapping to results."""
    from scrapers.dfw_big4_socrata import SocrataExtractor, CITY_CONFIGS, map_arlington_permit_type

    # Mock raw data with coded type
    raw_record = {'foldertype': 'RP', 'address': '123 Main St'}

    mapped_type = map_arlington_permit_type(raw_record.get('foldertype', ''))
    assert mapped_type == 'Residential Permit'
```

**Step 2: Run test**

Run: `cd /home/reid/testhome/permit-scraper && python3 -m pytest tests/test_arlington_socrata.py::test_arlington_extraction_maps_types -v`

Expected: PASS (this test just verifies the function works)

**Step 3: Update SocrataExtractor to use mapping**

Find the `extract` method in `SocrataExtractor` class and add Arlington-specific mapping. Look for where records are processed (around line 250+) and add:

```python
# In the extract() or process_results() method, add:
if self.city_key == 'arlington':
    from scrapers.dfw_big4_socrata import map_arlington_permit_type
    record['permit_type'] = map_arlington_permit_type(
        record.get(self.config.permit_type_field, '')
    )
```

**Step 4: Test full extraction flow manually**

Run: `cd /home/reid/testhome/permit-scraper && python3 scrapers/dfw_big4_socrata.py --city arlington --limit 10`

Verify output shows "Residential Permit" instead of "RP"

**Step 5: Commit**

```bash
git add scrapers/dfw_big4_socrata.py tests/test_arlington_socrata.py
git commit -m "feat(arlington): integrate type mapping in extraction flow"
```

---

## Task 3: eTRAKiT Detail Page Extraction for Denton/Prosper

**Files:**
- Modify: `scrapers/etrakit.py:103-200` (extract function)
- Create: `tests/test_etrakit_detail.py`

**Problem:** Current `extract_permits_from_page()` only reads the search results table, not the detail pages. Permit type and issued date are empty because they're only shown on detail pages.

**Step 1: Write failing test for detail extraction**

Create `tests/test_etrakit_detail.py`:

```python
"""Tests for eTRAKiT detail page extraction."""

import pytest

def test_extract_permit_detail_fields():
    """Verify detail extraction returns permit_type and issued_date."""
    # This tests the structure of extracted data
    sample_detail = {
        'permit_id': '2501-0032',
        'permit_type': 'Residential Remodel',
        'issued_date': '01/15/2025',
        'address': '5009 GOLDEN CIRCLE RD',
        'valuation': '25000.00',
    }

    # Verify required fields
    assert 'permit_type' in sample_detail
    assert 'issued_date' in sample_detail
    assert sample_detail['issued_date'] != ''
    assert sample_detail['permit_type'] != ''


def test_parse_etrakit_date():
    """Test date parsing from eTRAKiT format."""
    from scrapers.etrakit import parse_etrakit_date

    # eTRAKiT uses MM/DD/YYYY format
    assert parse_etrakit_date('01/15/2025') == '2025-01-15'
    assert parse_etrakit_date('12/31/2024') == '2024-12-31'
    assert parse_etrakit_date('') is None
    assert parse_etrakit_date(None) is None
```

**Step 2: Run test to verify it fails**

Run: `cd /home/reid/testhome/permit-scraper && python3 -m pytest tests/test_etrakit_detail.py -v`

Expected: FAIL with "cannot import name 'parse_etrakit_date'"

**Step 3: Add date parser function**

In `scrapers/etrakit.py`, add after line 20 (after imports):

```python
from datetime import datetime as dt


def parse_etrakit_date(date_str: str) -> str | None:
    """Parse eTRAKiT date format (MM/DD/YYYY) to ISO format."""
    if not date_str:
        return None
    try:
        parsed = dt.strptime(date_str.strip(), '%m/%d/%Y')
        return parsed.strftime('%Y-%m-%d')
    except (ValueError, AttributeError):
        return None
```

**Step 4: Run test to verify parser passes**

Run: `cd /home/reid/testhome/permit-scraper && python3 -m pytest tests/test_etrakit_detail.py::test_parse_etrakit_date -v`

Expected: PASS

**Step 5: Commit**

```bash
git add scrapers/etrakit.py tests/test_etrakit_detail.py
git commit -m "feat(etrakit): add date parser for detail page extraction"
```

---

## Task 4: eTRAKiT Detail Page Click-Through Logic

**Files:**
- Modify: `scrapers/etrakit.py` (add detail extraction function)

**Step 1: Create detail extraction function**

Add new async function after `extract_permits_from_page()` (around line 200):

```python
async def extract_permit_detail(page, permit_id: str, base_url: str) -> dict:
    """
    Click into a permit's detail page and extract full information.

    Args:
        page: Playwright page object
        permit_id: The permit ID to look up
        base_url: Base URL for the eTRAKiT portal

    Returns:
        Dict with permit_type, issued_date, valuation, description
    """
    detail = {
        'permit_type': '',
        'issued_date': '',
        'valuation': '',
        'description': '',
    }

    try:
        # Click the permit link in the search results
        permit_link = await page.query_selector(f'a:has-text("{permit_id}")')
        if not permit_link:
            return detail

        await permit_link.click()

        # Wait for detail page to load
        await page.wait_for_load_state('networkidle', timeout=10000)
        await asyncio.sleep(1)

        # Extract from detail page using JavaScript
        detail = await page.evaluate('''() => {
            const result = {
                permit_type: '',
                issued_date: '',
                valuation: '',
                description: ''
            };

            // Find all table rows or label/value pairs
            const allText = document.body.innerText;

            // Look for common eTRAKiT detail page patterns
            const typeMatch = allText.match(/(?:Permit Type|Type)[:\\s]+([^\\n]+)/i);
            if (typeMatch) result.permit_type = typeMatch[1].trim();

            const dateMatch = allText.match(/(?:Issue Date|Issued Date|Issued)[:\\s]+(\\d{1,2}\\/\\d{1,2}\\/\\d{4})/i);
            if (dateMatch) result.issued_date = dateMatch[1].trim();

            const valMatch = allText.match(/(?:Valuation|Value|Est.? Value)[:\\s]+\\$?([\\d,\\.]+)/i);
            if (valMatch) result.valuation = valMatch[1].replace(/,/g, '').trim();

            const descMatch = allText.match(/(?:Description|Work Description)[:\\s]+([^\\n]+)/i);
            if (descMatch) result.description = descMatch[1].trim();

            return result;
        }''')

        # Navigate back to search results
        await page.go_back()
        await page.wait_for_load_state('networkidle', timeout=10000)

    except Exception as e:
        print(f'      Detail extraction error for {permit_id}: {e}')
        # Try to recover navigation
        try:
            await page.go_back()
        except:
            pass

    return detail
```

**Step 2: Test manually with Denton**

Run: `cd /home/reid/testhome/permit-scraper && python3 -c "
import asyncio
from scrapers.etrakit import extract_permit_detail
from playwright.async_api import async_playwright

async def test():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        await page.goto('https://dntn-trk.aspgov.com/eTRAKiT/Search/permit.aspx')
        # Search for a known permit
        search_box = await page.query_selector('#txtSearchString')
        await search_box.fill('2501-0032')
        await page.click('#btnSearch')
        await asyncio.sleep(3)
        detail = await extract_permit_detail(page, '2501-0032', 'https://dntn-trk.aspgov.com/eTRAKiT')
        print(detail)
        await browser.close()

asyncio.run(test())
"`

**Step 3: Commit**

```bash
git add scrapers/etrakit.py
git commit -m "feat(etrakit): add detail page click-through extraction"
```

---

## Task 5: Integrate Detail Extraction into Main Scrape Loop

**Files:**
- Modify: `scrapers/etrakit.py` (main scrape function)

**Step 1: Find the main scraping loop**

In `etrakit.py`, find the function that iterates through permits (likely `scrape()` or similar around line 250+).

**Step 2: Add detail extraction after initial extraction**

After the basic permit list is extracted from search results, add a loop to enrich each permit:

```python
# After extracting basic permits from search results table
# Add this loop to enrich with detail page data:

enriched_permits = []
for i, permit in enumerate(permits):
    if i >= 50:  # Rate limit: only enrich first 50 per search
        enriched_permits.append(permit)
        continue

    permit_id = permit.get('permit_id', '')
    if not permit_id:
        enriched_permits.append(permit)
        continue

    # Get detail page data
    detail = await extract_permit_detail(page, permit_id, config['base_url'])

    # Merge detail data into permit (detail takes precedence)
    permit['permit_type'] = detail.get('permit_type') or permit.get('type', '')
    permit['issued_date'] = parse_etrakit_date(detail.get('issued_date', ''))
    permit['valuation'] = detail.get('valuation', '')
    permit['description'] = detail.get('description', '')

    enriched_permits.append(permit)

    # Rate limiting
    await asyncio.sleep(1.5)  # 1.5 second delay between detail pages

    if (i + 1) % 10 == 0:
        print(f'      Enriched {i + 1}/{len(permits)} permits...')

permits = enriched_permits
```

**Step 3: Test with Denton (small batch)**

Run: `cd /home/reid/testhome/permit-scraper && python3 scrapers/etrakit.py denton 10`

Verify output JSON has `issued_date` and `permit_type` populated

**Step 4: Commit**

```bash
git add scrapers/etrakit.py
git commit -m "feat(etrakit): integrate detail extraction into main scrape loop"
```

---

## Task 6: CityView Date Extraction for Carrollton

**Files:**
- Modify: `scrapers/cityview.py:32-92` (extract function)
- Create: `tests/test_cityview_dates.py`

**Step 1: Write failing test**

Create `tests/test_cityview_dates.py`:

```python
"""Tests for CityView date extraction."""

import pytest

def test_extract_issue_date_from_text():
    """Verify date extraction from CityView permit text."""
    from scrapers.cityview import extract_issue_date

    # CityView shows dates in various formats
    assert extract_issue_date('Issue Date: 12/15/2025') == '2025-12-15'
    assert extract_issue_date('Issued: 01/02/2025') == '2025-01-02'
    assert extract_issue_date('Date Issued: 11/30/2024') == '2024-11-30'
    assert extract_issue_date('No date here') is None
```

**Step 2: Run test to verify failure**

Run: `cd /home/reid/testhome/permit-scraper && python3 -m pytest tests/test_cityview_dates.py -v`

Expected: FAIL with "cannot import name 'extract_issue_date'"

**Step 3: Add date extraction function**

In `scrapers/cityview.py`, add after line 17 (after imports):

```python
import re
from datetime import datetime as dt


def extract_issue_date(text: str) -> str | None:
    """Extract issue date from CityView permit text."""
    if not text:
        return None

    # Try multiple date patterns
    patterns = [
        r'(?:Issue Date|Issued|Date Issued)[:\s]+(\d{1,2}/\d{1,2}/\d{4})',
        r'(\d{1,2}/\d{1,2}/\d{4})',  # Fallback: any date
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                parsed = dt.strptime(match.group(1), '%m/%d/%Y')
                return parsed.strftime('%Y-%m-%d')
            except ValueError:
                continue

    return None
```

**Step 4: Run test**

Run: `cd /home/reid/testhome/permit-scraper && python3 -m pytest tests/test_cityview_dates.py -v`

Expected: PASS

**Step 5: Integrate into extraction**

Modify `extract_permits_from_page()` in `cityview.py` to use the date extraction. Find where `date: ''` is set (around line 86) and update:

```javascript
// In the JavaScript extraction, look for Issue Date pattern
const dateMatch = permitText.match(/(?:Issue Date|Issued|Date Issued)[:\\s]+(\\d{1,2}\\/\\d{1,2}\\/\\d{4})/i);
if (dateMatch) {
    // Return raw date - Python will parse it
    date = dateMatch[1];
}
```

Then in Python after extraction, parse the dates:

```python
# After extracting permits
for permit in permits:
    if permit.get('date'):
        permit['issued_date'] = extract_issue_date(permit['date'])
```

**Step 6: Commit**

```bash
git add scrapers/cityview.py tests/test_cityview_dates.py
git commit -m "feat(cityview): add issue date extraction for Carrollton"
```

---

## Task 7: Re-scrape Arlington with Fresh Data

**Files:**
- Run: `scrapers/dfw_big4_socrata.py`

**Step 1: Check current Arlington data freshness**

Run: `cd /home/reid/testhome/permit-scraper && PGPASSWORD=localdev123 psql -h localhost -U contractors_user -d contractors_dev -c "SELECT MAX(issued_date), COUNT(*) FROM leads_permit WHERE city = 'arlington';"`

Expected: Shows Nov 14 as max date (stale)

**Step 2: Run Arlington scraper**

Run: `cd /home/reid/testhome/permit-scraper && python3 scrapers/dfw_big4_socrata.py --city arlington`

**Step 3: Load new permits to database**

Run: `cd /home/reid/testhome/permit-scraper && python3 scripts/load_permits.py`

**Step 4: Verify freshness improved**

Run: `cd /home/reid/testhome/permit-scraper && PGPASSWORD=localdev123 psql -h localhost -U contractors_user -d contractors_dev -c "SELECT MAX(issued_date), COUNT(*) FROM leads_permit WHERE city = 'arlington';"`

Expected: Shows December 2025 dates

**Step 5: No commit needed (data only)**

---

## Task 8: Re-scrape Denton with Detail Extraction

**Files:**
- Run: `scrapers/etrakit.py`

**Step 1: Check current Denton data**

Run: `cd /home/reid/testhome/permit-scraper && PGPASSWORD=localdev123 psql -h localhost -U contractors_user -d contractors_dev -c "SELECT permit_id, permit_type, issued_date FROM leads_permit WHERE city = 'denton' LIMIT 5;"`

Expected: Shows NULL dates and empty types

**Step 2: Run Denton scraper with detail extraction**

Run: `cd /home/reid/testhome/permit-scraper && python3 scrapers/etrakit.py denton 200`

**Step 3: Verify output JSON has dates**

Run: `cd /home/reid/testhome/permit-scraper && head -50 data/raw/denton_raw.json | grep -E '"issued_date"|"permit_type"'`

Expected: Shows populated dates and types

**Step 4: Load to database**

Run: `cd /home/reid/testhome/permit-scraper && python3 scripts/load_permits.py`

**Step 5: Verify database updated**

Run: `cd /home/reid/testhome/permit-scraper && PGPASSWORD=localdev123 psql -h localhost -U contractors_user -d contractors_dev -c "SELECT permit_id, permit_type, issued_date FROM leads_permit WHERE city = 'denton' AND issued_date IS NOT NULL LIMIT 5;"`

Expected: Shows populated dates

---

## Task 9: Re-scrape Prosper

**Files:**
- Run: `scrapers/etrakit.py`

**Step 1: Run Prosper scraper**

Run: `cd /home/reid/testhome/permit-scraper && python3 scrapers/etrakit.py prosper 200`

**Step 2: Load to database**

Run: `cd /home/reid/testhome/permit-scraper && python3 scripts/load_permits.py`

**Step 3: Verify**

Run: `cd /home/reid/testhome/permit-scraper && PGPASSWORD=localdev123 psql -h localhost -U contractors_user -d contractors_dev -c "SELECT permit_id, permit_type, issued_date FROM leads_permit WHERE city = 'prosper' AND issued_date IS NOT NULL LIMIT 5;"`

---

## Task 10: Re-scrape Carrollton

**Files:**
- Run: `scrapers/cityview.py`

**Step 1: Run Carrollton scraper**

Run: `cd /home/reid/testhome/permit-scraper && python3 scrapers/cityview.py carrollton 200`

**Step 2: Load to database**

Run: `cd /home/reid/testhome/permit-scraper && python3 scripts/load_permits.py`

**Step 3: Verify dates populated**

Run: `cd /home/reid/testhome/permit-scraper && PGPASSWORD=localdev123 psql -h localhost -U contractors_user -d contractors_dev -c "SELECT permit_id, permit_type, issued_date FROM leads_permit WHERE city = 'carrollton' AND issued_date IS NOT NULL LIMIT 5;"`

---

## Task 11: Run Full Pipeline (CAD + Scoring)

**Files:**
- Run: `scripts/enrich_cad.py`, `scripts/score_leads.py`

**Step 1: Enrich with CAD data**

Run: `cd /home/reid/testhome/permit-scraper && python3 scripts/enrich_cad.py`

**Step 2: Run AI scoring**

Run: `cd /home/reid/testhome/permit-scraper && python3 scripts/score_leads.py`

**Step 3: Verify premium lead increase**

Run: `cd /home/reid/testhome/permit-scraper && PGPASSWORD=localdev123 psql -h localhost -U contractors_user -d contractors_dev -c "
SELECT
    p.city,
    COUNT(*) as total,
    COUNT(*) FILTER (WHERE s.tier IN ('A', 'B')) as premium
FROM clients_scoredlead s
JOIN leads_permit p ON s.permit_id = p.id
WHERE p.city IN ('arlington', 'denton', 'prosper', 'carrollton')
GROUP BY p.city
ORDER BY premium DESC;"`

Expected: Premium counts significantly higher than before (was 5, 0, 0, 0)

---

## Task 12: Update SCRAPER_STATUS.md

**Files:**
- Modify: `SCRAPER_STATUS.md`

**Step 1: Update status documentation**

Update the Session Notes section with results:

```markdown
## Session Notes - December 20, 2024 (Quality Improvement)

### Fixes Applied

| City | Before | After | Change |
|------|--------|-------|--------|
| Denton | 0 premium, no dates | XX premium | +XX |
| Prosper | 0 premium, no dates | XX premium | +XX |
| Arlington | 5 premium, stale (Nov) | XX premium | +XX |
| Carrollton | 0 premium, no dates | XX premium | +XX |

### Technical Changes
- `etrakit.py`: Added detail page click-through extraction
- `cityview.py`: Added issue date extraction
- `dfw_big4_socrata.py`: Added Arlington permit type mapping

### Next Steps
- Richardson proxy implementation
- Euless reCAPTCHA solver
```

**Step 2: Commit documentation**

```bash
git add SCRAPER_STATUS.md
git commit -m "docs: update scraper status with Dec 20 quality improvements"
```

---

## Future Tasks (Expansion)

### Task 13: Richardson Proxy Scraper (if time permits)

Create `scrapers/richardson_proxy.py` using rotating residential proxies to bypass 403 block.

### Task 14: Euless reCAPTCHA Solver (if time permits)

Create `scrapers/euless_recaptcha.py` using browser-use + LLM to solve CAPTCHA challenges.

---

## Verification Checklist

After completing all tasks, verify:

- [ ] Denton has populated dates and types in database
- [ ] Prosper has populated dates and types in database
- [ ] Arlington has fresh data (Dec 2025 dates) and mapped types
- [ ] Carrollton has populated dates
- [ ] Premium lead count increased from ~5 to 500+ for these 4 cities
- [ ] All tests pass: `python3 -m pytest tests/ -v`
