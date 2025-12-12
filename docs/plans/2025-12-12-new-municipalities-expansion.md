# New DFW Municipalities Expansion Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add permit scrapers and CAD enrichment for 7 new high-value DFW municipalities: Denton, Trophy Club, Waxahachie, Forney, Weatherford, Sachse, and Aledo.

**Architecture:** Leverage existing scraper patterns (eTRAKiT, EnerGov CSS, MyGov) for cities using known platforms. Add new county CAD configurations (Ellis, Kaufman) to enrichment pipeline. Research new platforms (GovBuilt, SmartGov) via spikes.

**Tech Stack:** Python 3, Playwright, requests, PostgreSQL, ArcGIS REST APIs

---

## Research Summary

| Priority | City | Pop | Platform | Scraper Pattern | CAD County | Risk |
|----------|------|-----|----------|-----------------|------------|------|
| 1 | **Denton** | 160K | eTRAKiT | `etrakit_fast.py` (existing) | Denton (existing) | LOW |
| 2 | **Trophy Club** | 12K | EnerGov CSS | `citizen_self_service.py` (existing) | Denton (existing) | LOW |
| 3 | **Waxahachie** | 45K | EnerGov CSS | `citizen_self_service.py` (existing) | Ellis (NEW) | MEDIUM |
| 4 | **Forney** | 35K | MyGov | `mygov_westlake.py` pattern | Kaufman (NEW) | MEDIUM |
| 5 | **Sachse** | 30K | SmartGov | NEW spike required | Dallas/Collin (existing) | HIGH |
| 6 | **Weatherford** | 35K | GovBuilt | NEW spike required | Parker (NO API) | HIGH |
| 7 | **Aledo** | 6K | Unknown/Manual | Skip | Parker (NO API) | BLOCKED |

---

## Phase 1: Quick Wins (Existing Patterns + Existing CAD)

### Task 1: Add Denton to eTRAKiT Scraper

**Files:**
- Modify: `scrapers/etrakit_fast.py` (lines 19-60)
- Test: Manual verification via `python3 scrapers/etrakit_fast.py denton 10`

**Step 1: Add Denton configuration to ETRAKIT_CITIES**

Open `scrapers/etrakit_fast.py` and add after line 59 (after `flower_mound` config):

```python
    'denton': {
        'name': 'Denton',
        'base_url': 'https://etrakit.cityofdenton.com',
        'search_path': '/etrakit/Search/permit.aspx',
        # Denton uses B-prefixed permits like Frisco: B25-00001
        'prefixes': ['B25', 'B24', 'B23', 'B22', 'B21', 'B20', 'B19'],
        'permit_regex': r'^[A-Z]\d{2}-\d{5}$',
    },
```

**Step 2: Verify scraper works**

Run: `python3 scrapers/etrakit_fast.py denton 10`

Expected output:
```
============================================================
DENTON FAST PERMIT SCRAPER
============================================================
Target: 10 permits
...
Total collected: 10+
```

**Step 3: Commit**

```bash
git add scrapers/etrakit_fast.py
git commit -m "feat: add Denton to eTRAKiT scraper"
```

---

### Task 2: Add Trophy Club to EnerGov CSS Scraper

**Files:**
- Modify: `scrapers/citizen_self_service.py` (lines 43-60)
- Test: Manual verification via `python3 scrapers/citizen_self_service.py trophy_club 10`

**Step 1: Add Trophy Club configuration to CSS_CITIES**

Open `scrapers/citizen_self_service.py` and add after line 58 (after `allen` config):

```python
    'trophy_club': {
        'name': 'Trophy Club',
        'base_url': 'https://energovweb.trophyclub.org/energovprod/selfservice',
    },
```

**Step 2: Verify scraper works**

Run: `python3 scrapers/citizen_self_service.py trophy_club 10`

Expected output:
```
============================================================
TROPHY CLUB PERMIT SCRAPER (Citizen Self Service)
============================================================
Target: 10 permits
...
Permits scraped: 10+
```

**Step 3: Commit**

```bash
git add scrapers/citizen_self_service.py
git commit -m "feat: add Trophy Club to EnerGov CSS scraper"
```

---

## Phase 2: New CAD County Integration

### Task 3: Research Ellis County ArcGIS Endpoint

**Files:**
- Create: `scripts/test_ellis_cad.py` (spike script)

**Step 1: Create spike script to find working endpoint**

```python
#!/usr/bin/env python3
"""Spike: Find Ellis County CAD ArcGIS endpoint."""

import requests

# Candidate endpoints to test (from web research)
CANDIDATE_URLS = [
    # ArcGIS Online hosted
    'https://services.arcgis.com/NAnnb4W7JLztFw9i/arcgis/rest/services/Ellis_County_Parcel_Ownership/FeatureServer/0/query',
    'https://services7.arcgis.com/NAnnb4W7JLztFw9i/arcgis/rest/services/Ellis_County_Parcel_Ownership/FeatureServer/0/query',
    # Self-hosted possibilities
    'https://ecgis.co.ellis.tx.us/gis/rest/services/Public/Parcels/MapServer/0/query',
    'https://gis.co.ellis.tx.us/arcgis/rest/services/Parcels/MapServer/0/query',
]

TEST_PARAMS = {
    'where': '1=1',
    'outFields': '*',
    'resultRecordCount': 1,
    'f': 'json'
}

def test_endpoint(url):
    """Test if endpoint returns valid parcel data."""
    try:
        resp = requests.get(url, params=TEST_PARAMS, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if 'features' in data and len(data['features']) > 0:
                fields = list(data['features'][0].get('attributes', {}).keys())
                print(f"SUCCESS: {url}")
                print(f"  Fields: {fields[:10]}...")
                return True, fields
            elif 'error' in data:
                print(f"ERROR: {url} - {data['error']}")
        else:
            print(f"HTTP {resp.status_code}: {url}")
    except Exception as e:
        print(f"FAILED: {url} - {e}")
    return False, []

if __name__ == '__main__':
    print("=== Testing Ellis County CAD Endpoints ===\n")
    for url in CANDIDATE_URLS:
        success, fields = test_endpoint(url)
        if success:
            print(f"\nWORKING ENDPOINT FOUND!")
            print(f"URL: {url}")
            print(f"Available fields: {fields}")
            break
    else:
        print("\nNo working endpoint found. Manual research required.")
```

**Step 2: Run spike to find working endpoint**

Run: `python3 scripts/test_ellis_cad.py`

Expected: One endpoint returns success with field names. Document the working URL and field mapping.

**Step 3: Clean up spike**

```bash
rm scripts/test_ellis_cad.py  # Remove after documenting results
```

---

### Task 4: Research Kaufman County ArcGIS Endpoint

**Files:**
- Create: `scripts/test_kaufman_cad.py` (spike script)

**Step 1: Create spike script**

```python
#!/usr/bin/env python3
"""Spike: Find Kaufman County CAD ArcGIS endpoint."""

import requests

CANDIDATE_URLS = [
    # Pape-Dawson hosted (from Gemini research)
    'https://services.arcgis.com/f9Y1T9P58f25zDlm/arcgis/rest/services/PD_GIS_WebMap__DFW_External/MapServer/475/query',
    'https://gis.pape-dawson.com/arcgis/rest/services/PD_GIS_WebMap__DFW_External/MapServer/475/query',
    # Self-hosted possibilities
    'https://gis.kaufman-cad.org/arcgis/rest/services/Parcels/MapServer/0/query',
    'https://kaufmancad.org/arcgis/rest/services/Parcels/MapServer/0/query',
]

TEST_PARAMS = {
    'where': '1=1',
    'outFields': '*',
    'resultRecordCount': 1,
    'f': 'json'
}

def test_endpoint(url):
    try:
        resp = requests.get(url, params=TEST_PARAMS, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            if 'features' in data and len(data['features']) > 0:
                fields = list(data['features'][0].get('attributes', {}).keys())
                print(f"SUCCESS: {url}")
                print(f"  Fields: {fields[:10]}...")
                return True, fields
            elif 'error' in data:
                print(f"ERROR: {url} - {data['error']}")
        else:
            print(f"HTTP {resp.status_code}: {url}")
    except Exception as e:
        print(f"FAILED: {url} - {e}")
    return False, []

if __name__ == '__main__':
    print("=== Testing Kaufman County CAD Endpoints ===\n")
    for url in CANDIDATE_URLS:
        success, fields = test_endpoint(url)
        if success:
            print(f"\nWORKING ENDPOINT FOUND!")
            print(f"URL: {url}")
            print(f"Available fields: {fields}")
            break
    else:
        print("\nNo working endpoint found. Manual research required.")
```

**Step 2: Run spike**

Run: `python3 scripts/test_kaufman_cad.py`

**Step 3: Clean up**

```bash
rm scripts/test_kaufman_cad.py
```

---

### Task 5: Add Ellis County to CAD Enrichment

**Prerequisites:** Task 3 must complete successfully with a working endpoint.

**Files:**
- Modify: `scripts/enrich_cad.py` (COUNTY_CONFIGS around line 54, ZIP_TO_COUNTY around line 168)

**Step 1: Add Ellis County configuration**

After finding the working endpoint and field names from Task 3, add to `COUNTY_CONFIGS` dict (after `collin` config around line 160):

```python
    'ellis': {
        'name': 'Ellis',
        'url': 'WORKING_URL_FROM_SPIKE',  # Replace with actual URL
        'address_field': 'FIELD_NAME',     # Replace with actual field
        'fields': [
            # Replace with actual field names from spike
            "owner_name_field", "address_field", "value_field", ...
        ],
        'field_map': {
            'owner_name': 'OWNER_NAME_FIELD',
            'situs_addr': 'ADDRESS_FIELD',
            'owner_addr': 'MAILING_ADDR_FIELD',
            'owner_city': 'MAILING_CITY_FIELD',
            'owner_zip': 'MAILING_ZIP_FIELD',
            'market_value': 'VALUE_FIELD',
            'year_built': 'YEAR_FIELD',
            'square_feet': 'SQFT_FIELD',
            'account_num': 'ACCOUNT_FIELD',
        }
    },
```

**Step 2: Add Ellis County ZIP codes to ZIP_TO_COUNTY**

Add after line 249 (after Johnson County zips):

```python
    # Ellis County (Waxahachie, Ennis, Midlothian)
    '75119': 'ellis',  # Ennis
    '75154': 'ellis',  # Red Oak
    '75165': 'ellis',  # Waxahachie
    '75167': 'ellis',  # Waxahachie
    '76065': 'ellis',  # Midlothian (split with Johnson)
```

**Step 3: Add Waxahachie to CITY_TO_COUNTY**

Add to CITY_TO_COUNTY dict around line 320:

```python
    # Ellis County cities
    'waxahachie': 'ellis',
    'ennis': 'ellis',
    'midlothian': 'ellis',
    'red oak': 'ellis',
```

**Step 4: Test enrichment with a Waxahachie address**

Run: `python3 scripts/enrich_cad.py --limit 1`

(After scraping some Waxahachie permits)

**Step 5: Commit**

```bash
git add scripts/enrich_cad.py
git commit -m "feat: add Ellis County CAD enrichment for Waxahachie"
```

---

### Task 6: Add Kaufman County to CAD Enrichment

**Prerequisites:** Task 4 must complete successfully.

**Files:**
- Modify: `scripts/enrich_cad.py`

**Step 1: Add Kaufman County configuration**

Similar to Task 5, add to `COUNTY_CONFIGS`:

```python
    'kaufman': {
        'name': 'Kaufman',
        'url': 'WORKING_URL_FROM_SPIKE',
        'address_field': 'FIELD_NAME',
        'fields': [...],
        'field_map': {...}
    },
```

**Step 2: Add Kaufman County ZIP codes**

```python
    # Kaufman County (Forney, Terrell, Kaufman)
    '75126': 'kaufman',  # Forney
    '75142': 'kaufman',  # Kaufman
    '75160': 'kaufman',  # Terrell
    '75161': 'kaufman',  # Terrell
```

**Step 3: Add Forney to CITY_TO_COUNTY**

```python
    # Kaufman County cities
    'forney': 'kaufman',
    'terrell': 'kaufman',
    'kaufman': 'kaufman',
```

**Step 4: Commit**

```bash
git add scripts/enrich_cad.py
git commit -m "feat: add Kaufman County CAD enrichment for Forney"
```

---

### Task 7: Add Waxahachie to EnerGov CSS Scraper

**Files:**
- Modify: `scrapers/citizen_self_service.py`

**Step 1: Add Waxahachie configuration**

```python
    'waxahachie': {
        'name': 'Waxahachie',
        'base_url': 'https://waxahachietx-energovpub.tylerhost.net/Apps/SelfService',
    },
```

**Step 2: Test scraper**

Run: `python3 scrapers/citizen_self_service.py waxahachie 10`

**Step 3: Commit**

```bash
git add scrapers/citizen_self_service.py
git commit -m "feat: add Waxahachie to EnerGov CSS scraper"
```

---

### Task 8: Create Forney MyGov Scraper

**Files:**
- Create: `scrapers/mygov_forney.py` (based on `mygov_westlake.py` pattern)

**Step 1: Research Forney MyGov portal**

First verify the public URL works:
- Try: `https://public.mygov.us/forney_tx/lookup`
- If 404, search for alternate URL

**Step 2: Create spike to test access**

```python
#!/usr/bin/env python3
"""Spike: Test Forney MyGov public access."""

import requests

# Test if public lookup exists
urls = [
    'https://public.mygov.us/forney_tx/lookup',
    'https://public.mygov.us/forneytx/lookup',
    'https://public.mygov.us/forney/lookup',
]

for url in urls:
    try:
        resp = requests.get(url, timeout=10, allow_redirects=True)
        print(f"{url}: {resp.status_code}")
        if resp.status_code == 200:
            print("  -> PUBLIC ACCESS AVAILABLE")
            break
    except Exception as e:
        print(f"{url}: {e}")
else:
    print("\nNo public MyGov access found for Forney")
```

**Step 3: If public access exists, copy mygov_westlake.py pattern**

If Forney has public access, create `scrapers/mygov_forney.py` based on `mygov_westlake.py`.

**Step 4: Commit**

```bash
git add scrapers/mygov_forney.py
git commit -m "feat: add Forney MyGov scraper"
```

---

## Phase 3: New Platform Research (Spikes)

### Task 9: Research Sachse SmartGov Platform

**Files:**
- Create: `scrapers/smartgov_spike.py`

**Step 1: Create investigation spike**

```python
#!/usr/bin/env python3
"""Spike: Investigate Sachse SmartGov platform for scrapability."""

import asyncio
from playwright.async_api import async_playwright

async def investigate():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # Visual debugging
        page = await browser.new_page()

        # Navigate to SmartGov
        url = 'https://pl-sachse-tx.smartgovcommunity.com/Public/Home'
        print(f"Loading: {url}")
        await page.goto(url, wait_until='networkidle', timeout=60000)

        # Check for login requirement
        login_required = await page.evaluate('''() => {
            return document.body.innerText.toLowerCase().includes('login') ||
                   document.body.innerText.toLowerCase().includes('sign in');
        }''')
        print(f"Login required: {login_required}")

        # Look for permit search
        await page.screenshot(path='debug_html/sachse_smartgov.png')

        # Check if there's a public search
        links = await page.evaluate('''() => {
            return Array.from(document.querySelectorAll('a')).map(a => ({
                text: a.innerText.trim(),
                href: a.href
            })).filter(l => l.text.length > 0);
        }''')

        print("\nAvailable links:")
        for link in links[:20]:
            print(f"  {link['text']}: {link['href']}")

        await browser.close()

asyncio.run(investigate())
```

**Step 2: Run spike and document findings**

Run: `python3 scrapers/smartgov_spike.py`

Document whether:
- Public access available
- Login required
- API endpoints discoverable
- Scrapable via DOM or requires different approach

**Step 3: Decision point**

If scrapable: Create `scrapers/smartgov.py`
If blocked: Mark Sachse as "Blocked - requires login" in SCRAPER_STATUS.md

---

### Task 10: Research Weatherford GovBuilt Platform

**Files:**
- Create: `scrapers/govbuilt_spike.py`

**Step 1: Create investigation spike**

```python
#!/usr/bin/env python3
"""Spike: Investigate Weatherford GovBuilt platform."""

import asyncio
from playwright.async_api import async_playwright

async def investigate():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        url = 'https://weatherfordtx.govbuilt.com/'
        print(f"Loading: {url}")

        # Enable network logging to find API calls
        api_calls = []
        page.on('request', lambda req: api_calls.append(req.url) if 'api' in req.url.lower() else None)

        await page.goto(url, wait_until='networkidle', timeout=60000)
        await page.screenshot(path='debug_html/weatherford_govbuilt.png')

        # Check page structure
        is_angular = await page.evaluate('() => typeof window.ng !== "undefined"')
        is_react = await page.evaluate('() => typeof window.React !== "undefined" || document.querySelector("[data-reactroot]") !== null')

        print(f"Angular: {is_angular}, React: {is_react}")
        print(f"\nAPI calls detected: {api_calls[:10]}")

        # Look for search functionality
        search_elements = await page.evaluate('''() => {
            const inputs = document.querySelectorAll('input[type="text"], input[type="search"]');
            const buttons = document.querySelectorAll('button');
            return {
                inputs: inputs.length,
                buttons: Array.from(buttons).map(b => b.innerText.trim()).slice(0, 10)
            };
        }''')
        print(f"\nSearch elements: {search_elements}")

        await browser.close()

asyncio.run(investigate())
```

**Step 2: Run spike**

Run: `python3 scrapers/govbuilt_spike.py`

**Step 3: Decision point**

Note: Even if Weatherford is scrapable, Parker County has NO CAD API, so enrichment is impossible. Mark as:
- "Scrapable but no enrichment" or
- "Blocked - no CAD API for Parker County"

---

## Phase 4: Update Status Documentation

### Task 11: Update SCRAPER_STATUS.md

**Files:**
- Modify: `SCRAPER_STATUS.md`

**Step 1: Add new cities to main table**

Add rows for each new city with their status:

```markdown
| 33 | **Denton** | 160K | eTRAKiT | `etrakit_fast.py` | ✅ Working |
| 34 | **Trophy Club** | 12K | EnerGov CSS | `citizen_self_service.py` | ✅ Working |
| 35 | **Waxahachie** | 45K | EnerGov CSS | `citizen_self_service.py` | ✅ Working |
| 36 | **Forney** | 35K | MyGov | `mygov_forney.py` | [STATUS] |
| 37 | **Sachse** | 30K | SmartGov | — | [STATUS] |
| 38 | **Weatherford** | 35K | GovBuilt | — | ❌ No CAD API |
| 39 | **Aledo** | 6K | Unknown | — | ❌ No portal + No CAD |
```

**Step 2: Update platform summary**

Update the platform count table.

**Step 3: Add session notes**

```markdown
## Session Notes - [DATE]

### New Municipalities Expansion

**New Working Scrapers:**
- Denton (eTRAKiT) - 160K pop
- Trophy Club (EnerGov CSS) - 12K pop
- Waxahachie (EnerGov CSS) - 45K pop

**New CAD Counties:**
- Ellis County (for Waxahachie)
- Kaufman County (for Forney)

**Research Results:**
- Sachse: [RESULT]
- Weatherford: GovBuilt platform, but Parker County has no CAD API
- Aledo: No online portal found, Parker County has no CAD API
```

**Step 4: Commit**

```bash
git add SCRAPER_STATUS.md
git commit -m "docs: update status for new municipality expansion"
```

---

## Verification Checklist

After completing all tasks:

- [ ] `python3 scrapers/etrakit_fast.py denton 10` returns 10+ permits
- [ ] `python3 scrapers/citizen_self_service.py trophy_club 10` returns 10+ permits
- [ ] `python3 scrapers/citizen_self_service.py waxahachie 10` returns 10+ permits
- [ ] Ellis County CAD endpoint documented and integrated
- [ ] Kaufman County CAD endpoint documented (if found)
- [ ] Forney MyGov access tested
- [ ] Sachse SmartGov researched
- [ ] Weatherford GovBuilt researched
- [ ] SCRAPER_STATUS.md updated with all findings
- [ ] All commits pushed

---

## Risk Register

| Risk | Mitigation |
|------|------------|
| EnerGov URLs may be incorrect | Verify by loading in browser first |
| CAD ArcGIS endpoints may not exist | Spike scripts test multiple candidates |
| Tyler-hosted EnerGov may have bot detection | Use same stealth settings as Southlake |
| Forney MyGov may require login | Check public URL first, mark blocked if required |
| Parker County has no CAD API | Skip Weatherford/Aledo enrichment, document limitation |

---

## Summary of Changes

| File | Change Type |
|------|-------------|
| `scrapers/etrakit_fast.py` | Add Denton config |
| `scrapers/citizen_self_service.py` | Add Trophy Club, Waxahachie configs |
| `scripts/enrich_cad.py` | Add Ellis, Kaufman counties |
| `scrapers/mygov_forney.py` | New file (if public access) |
| `SCRAPER_STATUS.md` | Update with all findings |
