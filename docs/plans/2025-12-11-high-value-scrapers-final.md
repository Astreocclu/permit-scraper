# High-Value City Scrapers Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Expand permit data collection from Westlake (adaptive scanning), Southlake/Colleyville (Excel export), and Irving (PDF sample download).

**Architecture:** Three parallel improvements to existing scrapers: (1) Westlake gets "Expanding Ripple" adaptive scanning that focuses on active blocks, (2) CSS scrapers get proper Excel download handling with flexible column mapping, (3) Irving gets PDF download-only (parsing deferred until sample exists).

**Tech Stack:** Playwright, pandas, openpyxl, tenacity (retry), Python 3.10+

---

## Prerequisites

### Task 0: Update Dependencies

**Files:**
- Modify: `requirements.txt`

**Step 1: Add new dependencies**

```txt
# Add to requirements.txt:
pandas>=2.0.0,<3.0.0
openpyxl>=3.1.0
tenacity>=8.2.0
```

**Step 2: Install dependencies**

Run: `cd /home/reid/testhome/permit-scraper && pip install -r requirements.txt`
Expected: Successfully installed pandas, openpyxl, tenacity

**Step 3: Commit**

```bash
cd /home/reid/testhome/permit-scraper
git add requirements.txt
git commit -m "chore: add pandas, openpyxl, tenacity dependencies"
```

---

## Part 1: Westlake Adaptive Scanning

### Task 1: Add Retry Decorator to Westlake Scraper

**Files:**
- Modify: `scrapers/mygov_westlake.py`

**Step 1: Add tenacity import and retry decorator**

At top of `scrapers/mygov_westlake.py`, add:

```python
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from playwright.async_api import TimeoutError as PlaywrightTimeout

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=2, max=8),
    retry=retry_if_exception_type((PlaywrightTimeout, Exception)),
    reraise=True
)
async def fetch_address_permits(page, address: str) -> list:
    """Fetch permits for a single address with retry logic."""
    # ... existing address lookup logic moved here
```

**Step 2: Run scraper to verify import works**

Run: `cd /home/reid/testhome/permit-scraper && python3 -c "from scrapers.mygov_westlake import *; print('OK')"`
Expected: OK

**Step 3: Commit**

```bash
git add scrapers/mygov_westlake.py
git commit -m "feat(westlake): add retry decorator for network resilience"
```

---

### Task 2: Implement Expanding Ripple Adaptive Scanning

**Files:**
- Modify: `scrapers/mygov_westlake.py`

**Step 1: Add adaptive scanning function**

Add this function to `scrapers/mygov_westlake.py`:

```python
async def scan_neighborhood(page, center_address: str, center_num: int, street_name: str, permits_found: list) -> list:
    """
    Expanding Ripple scan: when a permit is found at center_num, scan ±50 addresses.

    Logic:
    - Range: center_num - 50 to center_num + 50
    - Step: 2 (preserve street parity - even/odd)
    - Stop conditions (any):
      1. Reached ±50 boundary
      2. 5 consecutive "No Results"
      3. 15 total failures in this neighborhood
    """
    consecutive_failures = 0
    total_failures = 0
    MAX_CONSECUTIVE = 5
    MAX_TOTAL_FAILURES = 15
    RANGE = 50
    STEP = 2

    start_num = max(1, center_num - RANGE)
    end_num = center_num + RANGE

    # Determine parity from center (even addresses vs odd)
    start_parity = center_num % 2
    if start_num % 2 != start_parity:
        start_num += 1

    logger.info(f"Deep dive: scanning {start_num}-{end_num} on {street_name}")

    neighborhood_permits = []

    for num in range(start_num, end_num + 1, STEP):
        if num == center_num:
            continue  # Already scanned

        if consecutive_failures >= MAX_CONSECUTIVE:
            logger.info(f"Stopping deep dive: {MAX_CONSECUTIVE} consecutive failures")
            break

        if total_failures >= MAX_TOTAL_FAILURES:
            logger.info(f"Stopping deep dive: {MAX_TOTAL_FAILURES} total failures")
            break

        address = f"{num} {street_name}"
        try:
            results = await fetch_address_permits(page, address)
            if results:
                neighborhood_permits.extend(results)
                consecutive_failures = 0
                logger.info(f"Found {len(results)} permits at {address}")
            else:
                consecutive_failures += 1
                total_failures += 1
        except Exception as e:
            logger.warning(f"Error scanning {address}: {e}")
            consecutive_failures += 1
            total_failures += 1

    return neighborhood_permits
```

**Step 2: Integrate adaptive scanning into main loop**

Find the main scanning loop in `scrapers/mygov_westlake.py` and modify:

```python
# In the main scraping function, after finding permits at an address:
MAX_GLOBAL_REQUESTS = 2000
global_request_count = 0

for street in STREETS:
    for base_num in range(1000, 3500, 100):
        if global_request_count >= MAX_GLOBAL_REQUESTS:
            logger.warning(f"Hit global request limit: {MAX_GLOBAL_REQUESTS}")
            break

        address = f"{base_num} {street}"
        global_request_count += 1

        results = await fetch_address_permits(page, address)
        if results:
            all_permits.extend(results)
            # ADAPTIVE: Deep dive into this neighborhood
            neighborhood = await scan_neighborhood(
                page, address, base_num, street, results
            )
            all_permits.extend(neighborhood)
            global_request_count += len(neighborhood) // 2  # Approximate
```

**Step 3: Run a quick test**

Run: `cd /home/reid/testhome/permit-scraper && timeout 60 python3 scrapers/mygov_westlake.py --test 2>&1 | head -30`
Expected: Logs showing address scanning (may not have --test flag, adjust accordingly)

**Step 4: Commit**

```bash
git add scrapers/mygov_westlake.py
git commit -m "feat(westlake): add Expanding Ripple adaptive scanning for active blocks"
```

---

## Part 2: CSS Excel Export (Southlake/Colleyville)

### Task 3: Add Excel Parsing Utility

**Files:**
- Create: `scrapers/utils.py` (or modify if exists)

**Step 1: Create/update utils.py with Excel parsing**

```python
"""Shared utilities for permit scrapers."""
import os
import logging
from pathlib import Path
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)

# Flexible column mapping - handles variations across cities
COLUMN_MAP = {
    # Permit ID variations
    'permitnumber': 'permit_id',
    'permitno': 'permit_id',
    'permit number': 'permit_id',
    'permit_number': 'permit_id',
    'projectnumber': 'permit_id',

    # Description variations
    'projectname': 'description',
    'description': 'description',
    'work description': 'description',
    'project description': 'description',

    # Date variations
    'applieddate': 'date',
    'issuedate': 'date',
    'date': 'date',
    'applied date': 'date',
    'issued date': 'date',

    # Address variations
    'address': 'address',
    'siteaddress': 'address',
    'site address': 'address',
    'project location': 'address',
    'projectaddress': 'address',

    # Type variations
    'permittype': 'type',
    'permit type': 'type',
    'type': 'type',
    'workclass': 'type',

    # Status variations
    'status': 'status',
    'permitstatus': 'status',
    'permit status': 'status',
}


def parse_excel_permits(filepath: str, city: str) -> list[dict]:
    """
    Parse Excel export from CSS/EnerGov portal with flexible column mapping.

    Args:
        filepath: Path to downloaded .xlsx file
        city: City name for logging

    Returns:
        List of permit dicts with standardized keys
    """
    # Check file exists and has content
    if not os.path.exists(filepath):
        logger.error(f"Excel file not found: {filepath}")
        return []

    file_size = os.path.getsize(filepath)
    if file_size < 1024:  # Less than 1KB = likely empty/corrupted
        logger.warning(f"Excel file too small ({file_size} bytes), likely empty: {filepath}")
        return []

    try:
        df = pd.read_excel(filepath, engine='openpyxl')
    except Exception as e:
        logger.error(f"Failed to read Excel file: {e}")
        return []

    if df.empty:
        logger.info(f"Excel file has no data rows: {filepath}")
        return []

    # Log original columns for debugging
    original_cols = list(df.columns)
    logger.info(f"[{city}] Excel columns found: {original_cols}")

    # Normalize column names: lowercase, strip whitespace
    df.columns = [str(c).lower().strip() for c in df.columns]

    # Map columns to standard schema
    mapped_cols = {}
    unmapped_cols = []

    for col in df.columns:
        if col in COLUMN_MAP:
            mapped_cols[col] = COLUMN_MAP[col]
        else:
            unmapped_cols.append(col)

    if unmapped_cols:
        logger.debug(f"[{city}] Unmapped columns (ignored): {unmapped_cols}")

    # Rename mapped columns
    df = df.rename(columns=mapped_cols)

    # Keep only standard columns that exist
    standard_cols = ['permit_id', 'address', 'type', 'status', 'date', 'description']
    keep_cols = [c for c in standard_cols if c in df.columns]

    if 'permit_id' not in keep_cols:
        logger.error(f"[{city}] No permit ID column found! Available: {list(df.columns)}")
        # Save debug info
        debug_path = filepath.replace('.xlsx', '_columns_debug.txt')
        with open(debug_path, 'w') as f:
            f.write(f"Original columns: {original_cols}\n")
            f.write(f"After normalization: {list(df.columns)}\n")
        logger.info(f"Saved column debug info to {debug_path}")
        return []

    df = df[keep_cols]

    # Convert to list of dicts
    permits = df.to_dict('records')

    # Clean up values
    for permit in permits:
        for key, val in permit.items():
            if pd.isna(val):
                permit[key] = None
            elif isinstance(val, str):
                permit[key] = val.strip()

    logger.info(f"[{city}] Parsed {len(permits)} permits from Excel")
    return permits
```

**Step 2: Verify module imports**

Run: `cd /home/reid/testhome/permit-scraper && python3 -c "from scrapers.utils import parse_excel_permits; print('OK')"`
Expected: OK

**Step 3: Commit**

```bash
git add scrapers/utils.py
git commit -m "feat(utils): add flexible Excel parsing with column mapping"
```

---

### Task 4: Add Download Handling to CSS Scraper

**Files:**
- Modify: `scrapers/citizen_self_service.py`

**Step 1: Add imports and download directory setup**

At top of `scrapers/citizen_self_service.py`, add/update:

```python
import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path

from scrapers.utils import parse_excel_permits

# Download directory
DOWNLOAD_DIR = Path(__file__).parent.parent / "data" / "downloads"
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
```

**Step 2: Fix date filter to use 60-day window**

Find the date filter setup code (around lines 187-210) and ensure:

```python
# Calculate date range: last 60 days
end_date = datetime.now()
start_date = end_date - timedelta(days=60)

# Format for the portal (adjust format as needed per portal)
start_date_str = start_date.strftime("%m/%d/%Y")
end_date_str = end_date.strftime("%m/%d/%Y")

logger.info(f"Date filter: {start_date_str} to {end_date_str}")
```

**Step 3: Add download handling function**

Add this function:

```python
async def download_excel_export(page, city: str, timeout_ms: int = 60000) -> Optional[str]:
    """
    Click Export button and wait for download.

    Args:
        page: Playwright page
        city: City name for filename
        timeout_ms: Max wait time for download (default 60s)

    Returns:
        Path to downloaded file, or None if failed
    """
    try:
        # Find and click the Export button
        export_btn = page.locator("button:has-text('Export'), a:has-text('Export')")

        if not await export_btn.count():
            logger.warning(f"[{city}] Export button not found")
            return None

        # Wait for download event
        async with page.expect_download(timeout=timeout_ms) as download_info:
            await export_btn.first.click()
            logger.info(f"[{city}] Clicked Export, waiting for download...")

        download = await download_info.value

        # Save to our download directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{city.lower()}_{timestamp}.xlsx"
        dest_path = DOWNLOAD_DIR / filename

        await download.save_as(str(dest_path))

        logger.info(f"[{city}] Downloaded: {dest_path}")
        return str(dest_path)

    except Exception as e:
        logger.error(f"[{city}] Download failed: {e}")
        return None
```

**Step 4: Integrate into main scraping flow**

In the main scraping function, after setting up filters:

```python
# After applying date filters and search...

# Try Excel export first (more reliable than DOM scraping)
excel_path = await download_excel_export(page, city)

if excel_path:
    permits = parse_excel_permits(excel_path, city)
    if permits:
        logger.info(f"[{city}] Got {len(permits)} permits from Excel export")
        all_permits.extend(permits)
    else:
        logger.warning(f"[{city}] Excel export empty, falling back to DOM scraping")
        # ... existing DOM scraping logic as fallback
else:
    logger.warning(f"[{city}] Excel download failed, using DOM scraping")
    # ... existing DOM scraping logic
```

**Step 5: Test import**

Run: `cd /home/reid/testhome/permit-scraper && python3 -c "from scrapers.citizen_self_service import *; print('OK')"`
Expected: OK (or specific import errors to fix)

**Step 6: Commit**

```bash
git add scrapers/citizen_self_service.py
git commit -m "feat(css): add Excel export download with 60-day filter and flexible parsing"
```

---

## Part 3: Irving PDF Download (Sample Only)

### Task 5: Create Irving PDF Sampler

**Files:**
- Create: `scrapers/irving_pdf_sampler.py`

**Step 1: Create PDF download-only script**

```python
"""
Irving (MGO Connect) PDF Sampler

Goal: Download ONE sample PDF to analyze structure before writing parser.
This is a discovery script, not a production scraper.

Usage:
    python scrapers/irving_pdf_sampler.py

Requires:
    MGO_EMAIL and MGO_PASSWORD in .env
"""
import os
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from playwright.async_api import async_playwright

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Output directory
SAMPLE_DIR = Path(__file__).parent.parent / "data" / "samples"
SAMPLE_DIR.mkdir(parents=True, exist_ok=True)

MGO_EMAIL = os.getenv("MGO_EMAIL")
MGO_PASSWORD = os.getenv("MGO_PASSWORD")

if not MGO_EMAIL or not MGO_PASSWORD:
    raise ValueError("MGO_EMAIL and MGO_PASSWORD must be set in .env")


async def download_irving_pdf_sample():
    """
    Login to Irving MGO Connect and download ONE PDF sample.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # Visible for debugging
        context = await browser.new_context(accept_downloads=True)
        page = await context.new_page()

        try:
            # Navigate to Irving MGO Connect
            logger.info("Navigating to Irving MGO Connect...")
            await page.goto("https://irving.mgoconnect.com/", timeout=30000)
            await page.wait_for_load_state("networkidle")

            # Login
            logger.info("Logging in...")
            await page.fill('input[type="email"], input[name="email"]', MGO_EMAIL)
            await page.fill('input[type="password"], input[name="password"]', MGO_PASSWORD)
            await page.click('button[type="submit"], input[type="submit"]')
            await page.wait_for_load_state("networkidle")

            # Check if login succeeded
            if "login" in page.url.lower():
                logger.error("Login failed - still on login page")
                await page.screenshot(path=str(SAMPLE_DIR / "login_failed.png"))
                return None

            logger.info("Login successful")

            # Navigate to permits/search
            # (Adjust selectors based on actual portal structure)
            await page.wait_for_timeout(2000)

            # Look for a View/Download/Report button
            download_btn = page.locator("button:has-text('View Report'), button:has-text('Download'), button:has-text('Export'), a:has-text('PDF')")

            if not await download_btn.count():
                logger.warning("No download button found, taking screenshot for analysis")
                await page.screenshot(path=str(SAMPLE_DIR / "irving_no_download_btn.png"))

                # Log page content for debugging
                content = await page.content()
                with open(SAMPLE_DIR / "irving_page_content.html", "w") as f:
                    f.write(content)

                return None

            # Attempt download
            logger.info("Found download button, attempting PDF download...")

            async with page.expect_download(timeout=60000) as download_info:
                await download_btn.first.click()

            download = await download_info.value

            # Save sample
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            sample_path = SAMPLE_DIR / f"irving_sample_{timestamp}.pdf"
            await download.save_as(str(sample_path))

            file_size = os.path.getsize(sample_path)
            logger.info(f"Downloaded: {sample_path} ({file_size} bytes)")

            if file_size < 1000:
                logger.warning("File very small - may be empty or error page")

            return str(sample_path)

        except Exception as e:
            logger.error(f"Error: {e}")
            await page.screenshot(path=str(SAMPLE_DIR / "irving_error.png"))
            return None

        finally:
            await browser.close()


if __name__ == "__main__":
    result = asyncio.run(download_irving_pdf_sample())

    if result:
        print(f"\n{'='*50}")
        print(f"SUCCESS: Sample PDF downloaded to {result}")
        print(f"{'='*50}")
        print("\nNext steps:")
        print("1. Open the PDF manually and analyze structure")
        print("2. Check if it's text-based or image-based")
        print("3. Identify table columns and layout")
        print("4. Then implement parser in scrapers/mgo_connect.py")
    else:
        print(f"\n{'='*50}")
        print("FAILED: Could not download PDF sample")
        print(f"{'='*50}")
        print(f"\nCheck {SAMPLE_DIR} for screenshots and debug info")
```

**Step 2: Verify script syntax**

Run: `cd /home/reid/testhome/permit-scraper && python3 -m py_compile scrapers/irving_pdf_sampler.py && echo "Syntax OK"`
Expected: Syntax OK

**Step 3: Commit**

```bash
git add scrapers/irving_pdf_sampler.py
git commit -m "feat(irving): add PDF sampler script for structure discovery"
```

---

### Task 6: Document Irving PDF Status

**Files:**
- Modify: `SCRAPER_STATUS.md` (or create if doesn't exist)

**Step 1: Update status documentation**

Add/update Irving section:

```markdown
## Irving (MGO Connect)

**Status:** BLOCKED - PDF Only

**Portal:** https://irving.mgoconnect.com/

**Auth:** Requires login (MGO_EMAIL, MGO_PASSWORD in .env)

**Issue:** Portal only exports to PDF format. No HTML tables or API data available.

**Current State:**
- `scrapers/irving_pdf_sampler.py` - Downloads sample PDF for analysis
- `scrapers/mgo_connect.py` - Has login/navigation, PDF parsing NOT implemented

**Next Steps:**
1. Run `python scrapers/irving_pdf_sampler.py` to get sample PDF
2. Analyze PDF structure (text vs image, table layout)
3. If text-based: implement pdfplumber parser
4. If image-based: requires OCR (pytesseract) - more complex

**Sample Location:** `data/samples/irving_sample_*.pdf`
```

**Step 2: Commit**

```bash
git add SCRAPER_STATUS.md
git commit -m "docs: update Irving status with PDF discovery workflow"
```

---

## Verification Checklist

After completing all tasks, run these verification steps:

### 1. Dependencies Check
```bash
cd /home/reid/testhome/permit-scraper
pip list | grep -E "pandas|openpyxl|tenacity"
```
Expected: All three packages installed with correct versions

### 2. Import Check
```bash
python3 -c "
from scrapers.utils import parse_excel_permits
from scrapers.mygov_westlake import scan_neighborhood
from scrapers.irving_pdf_sampler import download_irving_pdf_sample
print('All imports OK')
"
```
Expected: All imports OK

### 3. Final Commit Summary
```bash
git log --oneline -10
```
Should show commits for:
- Dependencies update
- Westlake retry decorator
- Westlake adaptive scanning
- Utils Excel parsing
- CSS Excel download
- Irving PDF sampler
- Status documentation

---

## Summary

| Task | Files | Status |
|------|-------|--------|
| Dependencies | `requirements.txt` | Ready |
| Westlake Retry | `scrapers/mygov_westlake.py` | Ready |
| Westlake Adaptive | `scrapers/mygov_westlake.py` | Ready |
| Excel Utils | `scrapers/utils.py` | Ready |
| CSS Download | `scrapers/citizen_self_service.py` | Ready |
| Irving Sampler | `scrapers/irving_pdf_sampler.py` | Ready |
| Documentation | `SCRAPER_STATUS.md` | Ready |

**Total commits:** 7
**Estimated implementation time:** Engineer-dependent (bite-sized tasks)
