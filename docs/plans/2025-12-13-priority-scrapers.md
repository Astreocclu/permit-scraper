# Priority Scrapers Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix broken scrapers and expand coverage for 5 priority items: Frisco eTRAKiT, EnerGov McKinney/Allen, Property Images, CAD Enrichment, and MGO Connect.

**Architecture:** Refactor existing scrapers to use faster DOM extraction (vs LLM), fix navigation timing issues caused by Tyler Portico Identity, and add new county support to CAD enrichment pipeline.

**Tech Stack:** Python 3, Playwright (async), pypdf, BeautifulSoup, tenacity, PostgreSQL

---

## Task 1: Refactor eTRAKiT Scrapers (Frisco)

**Context:** Two eTRAKiT scrapers exist - `etrakit.py` (has Plano login logic, uses DeepSeek LLM) and `etrakit_fast.py` (DOM extraction, faster, no login). We need to preserve login capability for Plano while making fast DOM extraction the default.

**Files:**
- Rename: `scrapers/etrakit.py` → `scrapers/etrakit_auth.py`
- Rename: `scrapers/etrakit_fast.py` → `scrapers/etrakit.py`
- Modify: `CLAUDE.md` (update docs)

### Step 1: Backup and rename legacy scraper

```bash
cd /home/reid/testhome/permit-scraper
git mv scrapers/etrakit.py scrapers/etrakit_auth.py
```

### Step 2: Promote fast scraper to default

```bash
git mv scrapers/etrakit_fast.py scrapers/etrakit.py
```

### Step 3: Update CLAUDE.md documentation

Change the eTRAKiT section to reflect new file names:

```markdown
### eTRAKiT
- Frisco, Flower Mound, Denton - `etrakit.py` (fast DOM)
- Plano - `etrakit_auth.py` (requires login)
```

### Step 4: Verify fast scraper runs

Run: `python3 scrapers/etrakit.py frisco 10`
Expected: Scrapes ~10 permits from Frisco, outputs to `data/raw/frisco_raw.json`

### Step 5: Commit

```bash
git add scrapers/etrakit.py scrapers/etrakit_auth.py CLAUDE.md
git commit -m "refactor: rename eTRAKiT scrapers - fast DOM is now default

- etrakit.py (was etrakit_fast.py): Fast DOM extraction for Frisco/Flower Mound/Denton
- etrakit_auth.py (was etrakit.py): Login-capable version for Plano"
```

---

## Task 2: Fix EnerGov McKinney/Allen Timeouts

**Context:** McKinney and Allen use EnerGov Citizen Self Service (same as working Southlake), but have Tyler Portico Identity enabled which creates continuous background network traffic. This prevents `networkidle` from ever being satisfied, causing 60s timeouts.

**Root Cause:** `globals.tylerIdEnabled = true` loads `oidc-client.min.js` which creates token refresh pings that never stop.

**Solution:** Change `wait_until='networkidle'` to `wait_until='domcontentloaded'` and add explicit selector wait.

**Files:**
- Modify: `scrapers/citizen_self_service.py`
- Test: Manual run against McKinney

### Step 1: Find the navigation call

Open `scrapers/citizen_self_service.py` and locate the `page.goto()` call that uses `wait_until='networkidle'`.

### Step 2: Change navigation wait strategy

Replace:
```python
await page.goto(url, wait_until='networkidle')
```

With:
```python
await page.goto(url, wait_until='domcontentloaded')
# Wait for Angular app to hydrate - Tyler Portico Identity creates
# background traffic that prevents networkidle from ever completing
await page.wait_for_selector('#SearchModule', timeout=30000)
```

### Step 3: Add fallback selector for non-SearchModule portals

Some CSS portals may not have `#SearchModule`. Add a fallback:

```python
await page.goto(url, wait_until='domcontentloaded')
# Wait for app to be interactive - handle both Angular and legacy variants
try:
    await page.wait_for_selector('#SearchModule', timeout=15000)
except:
    # Fallback for legacy WebForms portals
    await page.wait_for_selector('input[type="text"]', timeout=15000)
```

### Step 4: Test against McKinney

Run: `python3 scrapers/citizen_self_service.py mckinney 10`
Expected: Successfully scrapes permits without 60s timeout

### Step 5: Test against working city (regression check)

Run: `python3 scrapers/citizen_self_service.py southlake 10`
Expected: Still works (no regression)

### Step 6: Commit

```bash
git add scrapers/citizen_self_service.py
git commit -m "fix: EnerGov McKinney/Allen timeouts caused by Tyler Portico Identity

Root cause: Tyler Portico Identity (globals.tylerIdEnabled) creates continuous
background network traffic for token refresh, preventing networkidle.

Solution: Use domcontentloaded + explicit selector wait instead."
```

---

## Task 3: Add Rockwall County CAD Enrichment

**Context:** CAD enrichment currently supports Tarrant, Dallas, Denton, Collin, and Kaufman. Rockwall has an ArcGIS endpoint we can add. Ellis, Parker, and other counties are deferred (no public API).

**Files:**
- Modify: `scripts/enrich_cad.py` (add Rockwall to mappings)
- Modify: `services/property_images/cad_lookup.py` (add Rockwall endpoint)

### Step 1: Add Rockwall to ZIP_TO_COUNTY mapping

In `scripts/enrich_cad.py`, find `ZIP_TO_COUNTY` dict and add Rockwall ZIP codes:

```python
# Rockwall County ZIPs
'75032': 'rockwall',  # Rockwall
'75087': 'rockwall',  # Rockwall
'75189': 'rockwall',  # Royse City
```

### Step 2: Add Rockwall to CITY_TO_COUNTY mapping

```python
'rockwall': 'rockwall',
'royse city': 'rockwall',
'heath': 'rockwall',
'fate': 'rockwall',
```

### Step 3: Add Rockwall ArcGIS endpoint to cad_lookup.py

In `services/property_images/cad_lookup.py`, add to the county config:

```python
'rockwall': {
    'type': 'arcgis',
    'base_url': 'https://gis.rockwallcad.com/arcgis/rest/services',
    'layer': 'Parcels/MapServer/0',
    'address_field': 'SITUS_ADDRESS',
    'account_field': 'ACCOUNT_NUM',
}
```

### Step 4: Test Rockwall lookup

```python
# Quick test in Python REPL
from services.property_images.cad_lookup import lookup_property
result = lookup_property('123 Main St', 'Rockwall', 'TX')
print(result)
```

Expected: Returns property data dict or None (if address not found)

### Step 5: Commit

```bash
git add scripts/enrich_cad.py services/property_images/cad_lookup.py
git commit -m "feat: add Rockwall County to CAD enrichment

- Added ZIP code mappings (75032, 75087, 75189)
- Added city mappings (Rockwall, Royse City, Heath, Fate)
- Added ArcGIS endpoint for property lookups

Deferred: Ellis, Parker, Kaufman (no public API)"
```

---

## Task 4: Property Image Scraper - DCAD Implementation

**Context:** Property images are currently supported for Tarrant (TAD) and Redfin. We need to add Dallas County (DCAD). Existing scrapers have throttling (3-5s delays) which we'll replicate.

**Files:**
- Create: `services/property_images/dcad_scraper.py`
- Modify: `services/property_images/image_fetcher.py` (add DCAD routing)

### Step 1: Create DCAD scraper skeleton

Create `services/property_images/dcad_scraper.py`:

```python
"""
Dallas County Appraisal District (DCAD) property image scraper.

Images are served from files.dcad.org with predictable URLs based on account number.
"""
import asyncio
import random
from pathlib import Path
from playwright.async_api import async_playwright

MIN_DELAY_SECONDS = 3.0
MAX_DELAY_SECONDS = 5.0
IMAGE_DIR = Path('media/property_images')

async def fetch_dcad_image(account_number: str) -> str | None:
    """
    Fetch property image from DCAD.

    Args:
        account_number: DCAD account number (e.g., '00000123456')

    Returns:
        Path to saved image file, or None if not found
    """
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    output_path = IMAGE_DIR / f'{account_number}_dcad.jpg'

    if output_path.exists():
        return str(output_path)

    # DCAD image URL pattern
    url = f'https://files.dcad.org/propertyimages/{account_number}.jpg'

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            response = await page.goto(url, wait_until='load')
            if response and response.status == 200:
                # Download image
                content = await response.body()
                output_path.write_bytes(content)
                return str(output_path)
            return None
        except Exception as e:
            print(f'DCAD image fetch failed for {account_number}: {e}')
            return None
        finally:
            await browser.close()
            # Throttle to avoid rate limiting
            await asyncio.sleep(random.uniform(MIN_DELAY_SECONDS, MAX_DELAY_SECONDS))
```

### Step 2: Add DCAD routing to image_fetcher.py

In `services/property_images/image_fetcher.py`, add DCAD to the county routing:

```python
from .dcad_scraper import fetch_dcad_image

async def fetch_property_image(account_number: str, county: str) -> str | None:
    """Route to appropriate county scraper."""
    county = county.lower()

    if county == 'tarrant':
        return await fetch_tad_image(account_number)
    elif county == 'dallas':
        return await fetch_dcad_image(account_number)
    # ... other counties
    else:
        return None
```

### Step 3: Test DCAD scraper

```bash
python3 -c "
import asyncio
from services.property_images.dcad_scraper import fetch_dcad_image

async def test():
    # Use a known DCAD account number
    result = await fetch_dcad_image('00000123456')
    print(f'Result: {result}')

asyncio.run(test())
"
```

Expected: Either saves image to `media/property_images/` or returns None

### Step 4: Commit

```bash
git add services/property_images/dcad_scraper.py services/property_images/image_fetcher.py
git commit -m "feat: add DCAD property image scraper

- Fetches images from files.dcad.org
- 3-5s random delay between requests (throttling)
- Saves to media/property_images/{account}_dcad.jpg"
```

---

## Task 5: MGO Connect - Irving PDF Support

**Context:** Irving's MGO portal exports to PDF only. We need to parse these PDFs to extract permit data. Other MGO cities (Denton, Lewisville, Cedar Hill) are working but Irving is skipped.

**Approach:** Use pypdf for text extraction. If extraction fails (image-only PDF), save to manual review folder.

**Files:**
- Modify: `scrapers/mgo_connect.py` (add Irving PDF parsing)
- Modify: `requirements.txt` (add pypdf if missing)

### Step 1: Check/add pypdf dependency

```bash
grep pypdf requirements.txt || echo "pypdf>=4.0.0" >> requirements.txt
pip install pypdf
```

### Step 2: Add PDF parsing function to mgo_connect.py

Add this function to `scrapers/mgo_connect.py`:

```python
from pypdf import PdfReader
from pathlib import Path
import re

MANUAL_REVIEW_DIR = Path('data/downloads/manual_review')

def parse_irving_pdf(pdf_path: str) -> list[dict] | None:
    """
    Parse Irving PDF export to extract permit data.

    Returns list of permit dicts, or None if parsing fails.
    """
    try:
        reader = PdfReader(pdf_path)
        text = ''
        for page in reader.pages:
            text += page.extract_text() or ''

        # Check if extraction worked (image-only PDFs return empty/garbage)
        if len(text.strip()) < 50:
            # Move to manual review
            MANUAL_REVIEW_DIR.mkdir(parents=True, exist_ok=True)
            dest = MANUAL_REVIEW_DIR / Path(pdf_path).name
            Path(pdf_path).rename(dest)
            print(f'PDF moved to manual review: {dest}')
            return None

        # Parse table rows from text
        # Irving PDF format: PERMIT_NUM | ADDRESS | TYPE | STATUS | DATE
        permits = []
        lines = text.split('\n')
        for line in lines:
            # Match permit number pattern (e.g., BP-2024-12345)
            match = re.match(r'(BP-\d{4}-\d+)\s+(.+)', line)
            if match:
                permits.append({
                    'permit_number': match.group(1),
                    'raw_text': match.group(2),
                    'source': 'irving_pdf',
                    'review_required': False
                })

        return permits if permits else None

    except Exception as e:
        print(f'PDF parsing error: {e}')
        return None
```

### Step 3: Integrate PDF parsing into Irving scraper flow

In the Irving-specific section of `mgo_connect.py`, after downloading the PDF:

```python
# After PDF download completes
if city == 'irving' and pdf_path:
    permits = parse_irving_pdf(pdf_path)
    if permits:
        # Add to output
        all_permits.extend(permits)
    else:
        print(f'Irving PDF parsing failed, moved to manual review')
```

### Step 4: Test Irving scraper

Run: `python3 scrapers/mgo_connect.py irving 10`
Expected: Downloads PDF, parses it, extracts permits (or moves to manual review)

### Step 5: Commit

```bash
git add scrapers/mgo_connect.py requirements.txt
git commit -m "feat: add Irving PDF parsing to MGO Connect scraper

- Uses pypdf to extract text from Irving PDF exports
- Fallback: moves image-only PDFs to data/downloads/manual_review/
- Parses permit number and raw text from table format"
```

---

## Deferred Items (Out of Scope)

The following items are explicitly deferred:

1. **Ellis County CAD** - Uses BisConsulting, different scraper architecture needed
2. **Parker County CAD** - No public API available
3. **Kaufman County CAD** - BisConsulting variant, deferred
4. **MGO cities with unknown JIDs** - Lancaster, Sachse need JID research
5. **Denton/Collin CAD image scrapers** - Lower priority than DCAD

---

## Verification Checklist

After completing all tasks:

- [ ] `python3 scrapers/etrakit.py frisco 10` - Works
- [ ] `python3 scrapers/etrakit_auth.py plano 10` - Works (if login configured)
- [ ] `python3 scrapers/citizen_self_service.py mckinney 10` - No timeout
- [ ] `python3 scrapers/citizen_self_service.py southlake 10` - Still works
- [ ] `python3 scrapers/mgo_connect.py irving 10` - Parses PDF
- [ ] CAD enrichment includes Rockwall addresses
- [ ] DCAD images save to `media/property_images/`

---

## Estimated Effort

| Task | Complexity | Risk |
|------|------------|------|
| 1. eTRAKiT refactor | Low | Low - just file renames |
| 2. EnerGov fix | Medium | Medium - need to test multiple cities |
| 3. CAD Rockwall | Low | Low - standard ArcGIS |
| 4. DCAD images | Medium | Medium - URL pattern may vary |
| 5. Irving PDF | High | High - PDF structure unknown |
