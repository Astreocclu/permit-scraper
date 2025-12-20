# Codebase Refactoring Plan

**Created:** 2025-12-14
**Confidence:** Claude 95%, Gemini 98%
**Risk Level:** Low-Medium

## Executive Summary

Clean up the permit-scraper codebase by:
1. Deleting 76+ dead files (screenshots, logs, research scripts)
2. Standardizing scraper output to `data/raw/`
3. Consolidating duplicate southlake batch scraper
4. Fixing import inconsistencies

## Phase 1: Safe Deletions (No Dependencies)

### Task 1.1: Delete Root Screenshots (24 files)
```bash
cd /home/reid/testhome/permit-scraper
rm -f *.png
```
**Verify:** `ls *.png 2>/dev/null | wc -l` should return 0

### Task 1.2: Delete Root Log Files (9 files)
```bash
rm -f *.log
```
**Verify:** `ls *.log 2>/dev/null | wc -l` should return 0

### Task 1.3: Delete Root TXT Files (7 files)
```bash
rm -f *.txt
```
**Verify:** `ls *.txt 2>/dev/null | wc -l` should return 0

### Task 1.4: Delete Research Scripts (6 files)
```bash
rm -f explore_sachse_portal.py
rm -f research_sachse_alternate.py
rm -f research_sachse_correct.py
rm -f research_sachse_smartgov.py
rm -f kaufman_endpoint_test.py
rm -f ryan_robinson_cheatsheet.py
```

### Task 1.5: Delete Research JSON/HTML Files
```bash
rm -f sachse_complete_research.json
rm -f sachse_research_findings.json
rm -f url_variations_test.json
rm -f network_log.json
rm -f opengov_search.html
rm -f weatherford_search.html
rm -f debug_keller_page.html
```

### Task 1.6: Delete Misc Cruft
```bash
rm -f "=4.0.0"  # npm artifact
rm -f ryan_robinson_cheatsheet.pdf
```

### Task 1.7: Clean debug_html/ folder
```bash
rm -rf debug_html/
```

## Phase 2: Scraper Output Standardization

### Task 2.1: Update accela_fast.py Output Path
**File:** `scrapers/accela_fast.py`
**Line:** ~344

**Before:**
```python
output_file = f'{city_key}_raw.json'
```

**After:**
```python
from pathlib import Path
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "raw"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
# ... in save_results():
output_file = OUTPUT_DIR / f'{city_key}_raw.json'
```

### Task 2.2: Update citizen_self_service.py Output Path
**File:** `scrapers/citizen_self_service.py`
**Line:** ~1115

Same pattern as Task 2.1.

### Task 2.3: Update cityview.py Output Path
**File:** `scrapers/cityview.py`
**Lines:** 229, 256, 273

Same pattern. Multiple write locations to update.

### Task 2.4: Update etrakit.py Output Path
**File:** `scrapers/etrakit.py`
**Line:** ~319

Same pattern.

### Task 2.5: Update etrakit_auth.py Output Path
**File:** `scrapers/etrakit_auth.py`
**Line:** ~626

Same pattern.

### Task 2.6: Update mygov_westlake.py Output Path
**File:** `scrapers/mygov_westlake.py`
**Line:** ~353-354

**Before:**
```python
Path('westlake_raw.json').write_text(json.dumps(output, indent=2))
print(f"\nSaved to: {Path('westlake_raw.json').absolute()}")
```

**After:**
```python
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "raw"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
output_file = OUTPUT_DIR / 'westlake_raw.json'
output_file.write_text(json.dumps(output, indent=2))
print(f"\nSaved to: {output_file.absolute()}")
```

### Task 2.7: Move Existing Root JSON Files
```bash
mv /home/reid/testhome/permit-scraper/*_raw.json /home/reid/testhome/permit-scraper/data/raw/ 2>/dev/null || true
```

## Phase 3: Code Consolidation

### Task 3.1: Merge RESIDENTIAL_TYPES into filters.py
**File:** `scrapers/filters.py`

Add to the file:
```python
# Southlake-specific residential permit types for batch scraping
SOUTHLAKE_RESIDENTIAL_TYPES = [
    "Residential New Building (Single Family Home)",
    "Residential New Building (Duplex)",
    "Residential New Building (Townhome)",
    "Residential Remodel",
    "Residential Addition Conditioned Space",
    "Residential Addition Conditioned & Uncond",
    "Pool & Spa (Residential)",
    "Pool (Residential)",
    "Electrical Permit (Residential)",
    "Mechanical Permit (Residential)",
    "Plumbing Permit (Residential)",
    "Residential Reroof",
    "Fence (Residential)",
    "Solar Panel - Residential",
]
```

### Task 3.2: Delete southlake_residential_batch.py
```bash
rm scrapers/southlake_residential_batch.py
```

### Task 3.3: Fix Import Issues in citizen_self_service.py
**File:** `scrapers/citizen_self_service.py`

Find and replace the try/except import fallback pattern with consistent relative imports:
```python
from .utils import parse_excel_permits
from .filters import filter_residential_permits
```

Or if running as script:
```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from scrapers.utils import parse_excel_permits
from scrapers.filters import filter_residential_permits
```

## Phase 4: Optional Cleanup

### Task 4.1: Clean data/downloads/ (Manual Decision)
The folder contains many duplicate xlsx files from scraper runs. These are safe to delete if not needed for debugging.
```bash
# Review first
ls -la data/downloads/ | head -20
# Then delete if confirmed
# rm -rf data/downloads/*.xlsx
```

### Task 4.2: Refactor dfw_big4_socrata.py (Low Priority)
This file is standalone and mostly obsolete. Only Arlington works.
- Option A: Delete entirely, create dedicated `arlington_arcgis.py`
- Option B: Leave as-is with clear comments

## Verification Commands

After all phases:
```bash
# Check root is clean
ls *.png *.log *.txt *.json *.html 2>/dev/null | wc -l  # Should be 0 or near 0

# Check scrapers output correctly
python3 scrapers/accela_fast.py dallas 5  # Should write to data/raw/

# Run tests
pytest tests/

# Git status
git status
```

## Rollback Plan

All changes are on local files. If something breaks:
```bash
git checkout -- .
git clean -fd
```

## Files NOT to Touch

- `CLAUDE.md` - Must stay in root (Claude Code convention)
- `README.md`, `TODO.md` - Project documentation
- `.env`, `.env.example` - Configuration
- `requirements.txt`, `package.json` - Dependencies
- `pytest.ini` - Test configuration
