# BrowserUse Scrapers for Burleson & Southlake Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix Burleson and Southlake scrapers that return 0 permits by using BrowserUse AI-driven scraping instead of broken Playwright scrapers.

**Architecture:** Update `services/browser_scraper/permit_tasks.py` to add a Southlake-specific bulk task (handles portal's date-sort quirks) and fix Burleson's incorrect portal config. Modify `runner.py` to output both jsonl (for review) and `{city}_raw.json` (for pipeline compatibility).

**Tech Stack:** Python 3.11, BrowserUse 0.11.1, DeepSeek API, Playwright (via BrowserUse)

---

## Task 1: Fix Burleson City Config

**Files:**
- Modify: `services/browser_scraper/permit_tasks.py:355`

**Step 1: Write the failing test**

```python
# tests/browser_scraper/test_permit_tasks.py
def test_burleson_uses_mygov_template():
    """Burleson should use MyGov, not eTRAKiT (which 404s)."""
    from services.browser_scraper.permit_tasks import CITY_TASKS

    task = CITY_TASKS.get('burleson')
    assert task is not None, "burleson not in CITY_TASKS"
    assert 'mygov' in task.lower() or 'public.mygov.us/burleson_tx' in task, \
        f"Burleson should use MyGov portal, got: {task[:100]}"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/browser_scraper/test_permit_tasks.py::test_burleson_uses_mygov_template -v`
Expected: FAIL - currently uses eTRAKiT template

**Step 3: Update CITY_TASKS for Burleson**

In `services/browser_scraper/permit_tasks.py`, find line ~355:
```python
# CHANGE FROM:
"burleson": ETRAKIT_TEMPLATE.format(city_name="Burleson", url="https://etrakit.burlesontx.com/eTRAKiT"),

# CHANGE TO:
"burleson": MYGOV_TEMPLATE.format(city_name="Burleson", url="https://public.mygov.us/burleson_tx"),
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/browser_scraper/test_permit_tasks.py::test_burleson_uses_mygov_template -v`
Expected: PASS

**Step 5: Commit**

```bash
git add services/browser_scraper/permit_tasks.py tests/browser_scraper/test_permit_tasks.py
git commit -m "fix(burleson): use MyGov portal instead of 404ing eTRAKiT URL"
```

---

## Task 2: Create Southlake-Specific Bulk Task

**Files:**
- Modify: `services/browser_scraper/permit_tasks.py` (add template near line 90, update CITY_TASKS)

**Step 1: Write the failing test**

```python
# tests/browser_scraper/test_permit_tasks.py
def test_southlake_has_date_sort_instruction():
    """Southlake task must include date sorting to work around portal bug."""
    from services.browser_scraper.permit_tasks import get_task_for_city

    task = get_task_for_city("southlake", mode="bulk", start_date="01/01/2025", end_date="12/21/2025")

    assert 'Issued Date' in task or 'sort' in task.lower(), \
        "Southlake bulk task must instruct agent to sort by date"
    assert 'descending' in task.lower() or 'newest' in task.lower(), \
        "Southlake must sort newest first"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/browser_scraper/test_permit_tasks.py::test_southlake_has_date_sort_instruction -v`
Expected: FAIL - current template doesn't have date sort instructions

**Step 3: Add SOUTHLAKE_BULK_TASK template**

Add after `BULK_ENERGOV_TEMPLATE` (around line 112):

```python
SOUTHLAKE_BULK_TASK = EFFICIENCY_DIRECTIVE + """
Go to the Southlake EnerGov portal at https://energov.cityofsouthlake.com/EnerGov_Prod/SelfService#/search

1. Select "Permit" from the Module dropdown.

2. Click "Advanced" to open advanced search.

3. Set date filters:
   - Find "Issued Date" fields
   - Set start date: {start_date}
   - Set end date: {end_date}

4. Click "Search" button.

5. CRITICAL: After results load, the portal may show old permits despite date filter.
   - Find the "Issued Date" column header in the results table
   - Click it TWICE to sort DESCENDING (newest first)
   - Verify the top results show dates within your search range

6. If "Export" button is available, click it to download Excel file.
   Otherwise, scrape the first page of results.

7. Extract up to 50 permits with these fields:
   - permit_number (Case Number column)
   - issue_date (Issued Date column)
   - permit_type (Type column)
   - status (Status column)
   - address (Address column)
   - description (Description column if available)

Return the data as a valid JSON list of objects.
"""
```

**Step 4: Update CITY_TASKS for Southlake bulk mode**

Find the `get_task_for_city` function (around line 575) and add special handling for Southlake before the generic EnerGov handling:

```python
# Inside get_task_for_city(), add after mode == "bulk" check, before other template swapping:
if mode == "bulk":
    # Special handling for Southlake (portal ignores date filters)
    if normalized_city == "southlake":
        return SOUTHLAKE_BULK_TASK.format(start_date=start_date, end_date=end_date)

    # ... rest of existing bulk logic
```

**Step 5: Run test to verify it passes**

Run: `pytest tests/browser_scraper/test_permit_tasks.py::test_southlake_has_date_sort_instruction -v`
Expected: PASS

**Step 6: Commit**

```bash
git add services/browser_scraper/permit_tasks.py tests/browser_scraper/test_permit_tasks.py
git commit -m "feat(southlake): add custom bulk task with date sorting workaround"
```

---

## Task 3: Add Dual Output to Runner

**Files:**
- Modify: `services/browser_scraper/runner.py:168-183`
- Create: `data/raw/` directory (if not exists)

**Step 1: Write the failing test**

```python
# tests/browser_scraper/test_runner.py
import json
import os
from pathlib import Path
from unittest.mock import patch, AsyncMock

def test_batch_runner_creates_city_raw_json(tmp_path):
    """BatchRunner should create {city}_raw.json alongside jsonl."""
    import asyncio
    from services.browser_scraper.runner import BatchRunner

    # Mock the scraper to return fake data
    mock_result = {
        "success": True,
        "data": [{"permit_number": "TEST-001", "address": "123 Main St"}],
        "error": None,
        "context": None
    }

    runner = BatchRunner(concurrency=1)

    # Patch the raw data directory
    raw_dir = tmp_path / "data" / "raw"
    raw_dir.mkdir(parents=True)

    with patch.object(runner, '_get_raw_dir', return_value=raw_dir):
        with patch('services.browser_scraper.runner.PermitScraperRunner.scrape_permit',
                   new_callable=AsyncMock, return_value=mock_result):
            asyncio.run(runner.run_batch(["TestCity"], mode="bulk"))

    # Check that city_raw.json was created
    expected_file = raw_dir / "testcity_raw.json"
    assert expected_file.exists(), f"Expected {expected_file} to exist"

    data = json.loads(expected_file.read_text())
    assert len(data) > 0
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/browser_scraper/test_runner.py::test_batch_runner_creates_city_raw_json -v`
Expected: FAIL - no `_get_raw_dir` method, no city json output

**Step 3: Add dual output to BatchRunner**

In `services/browser_scraper/runner.py`, add these methods to `BatchRunner` class:

```python
def _get_raw_dir(self) -> Path:
    """Get the raw data output directory."""
    raw_dir = Path("data/raw")
    raw_dir.mkdir(parents=True, exist_ok=True)
    return raw_dir

def _save_city_raw_json(self, city: str, data: Any):
    """Save permits to {city}_raw.json for pipeline compatibility."""
    if not data:
        return

    raw_dir = self._get_raw_dir()
    normalized_city = city.lower().replace(" ", "_")
    output_file = raw_dir / f"{normalized_city}_raw.json"

    # Wrap in standard format if it's a list
    if isinstance(data, list):
        output = {
            "source": normalized_city,
            "portal_type": "browser_use",
            "scraped_at": datetime.datetime.now().isoformat(),
            "target_count": len(data),
            "actual_count": len(data),
            "errors": [],
            "permits": data
        }
    else:
        output = data

    with open(output_file, 'w') as f:
        json.dump(output, f, indent=2)

    logger.info(f"Saved {len(data) if isinstance(data, list) else 1} permits to {output_file}")
```

Then modify `_scrape_safe` method to call `_save_city_raw_json`:

```python
# In _scrape_safe, after creating result_payload (around line 147):
# Add this line before the incremental save:
if result["success"] and result.get("data"):
    self._save_city_raw_json(city, result["data"])
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/browser_scraper/test_runner.py::test_batch_runner_creates_city_raw_json -v`
Expected: PASS

**Step 5: Commit**

```bash
git add services/browser_scraper/runner.py tests/browser_scraper/test_runner.py
git commit -m "feat(runner): add dual output - jsonl for review + city_raw.json for pipeline"
```

---

## Task 4: Create Test Cities File

**Files:**
- Create: `data/target_cities_fix.json`

**Step 1: Create the test cities file**

```bash
echo '["southlake", "burleson"]' > data/target_cities_fix.json
```

**Step 2: Verify file exists**

Run: `cat data/target_cities_fix.json`
Expected: `["southlake", "burleson"]`

**Step 3: Commit**

```bash
git add data/target_cities_fix.json
git commit -m "chore: add target cities file for Southlake/Burleson fix testing"
```

---

## Task 5: Integration Test (Manual)

**Files:** None (manual testing)

**Step 1: Run BrowserUse scraper for both cities**

```bash
cd /home/reid/testhome/permit-scraper
source ../.venv/bin/activate 2>/dev/null || true
export DEEPSEEK_API_KEY=$(grep DEEPSEEK_API_KEY .env | cut -d'=' -f2)

python3 -m services.browser_scraper.runner \
    --batch \
    --cities_file data/target_cities_fix.json \
    --mode bulk \
    --days 30 \
    --concurrency 1
```

**Step 2: Verify outputs exist**

```bash
ls -la data/raw/southlake_raw.json data/raw/burleson_raw.json
cat data/raw/southlake_raw.json | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'Southlake: {d[\"actual_count\"]} permits')"
cat data/raw/burleson_raw.json | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'Burleson: {d[\"actual_count\"]} permits')"
```

Expected: Both files exist with actual_count > 0

**Step 3: Check for recent dates in Southlake**

```bash
cat data/raw/southlake_raw.json | python3 -c "
import json,sys
d=json.load(sys.stdin)
for p in d['permits'][:5]:
    print(f\"{p.get('permit_number', 'N/A')}: {p.get('issue_date', 'N/A')}\")"
```

Expected: Dates should be from 2025, not 2000-2002

**Step 4: If tests pass, commit verification**

```bash
git add -A
git commit -m "test: verify BrowserUse scrapers work for Southlake and Burleson"
```

---

## Task 6: Update Documentation

**Files:**
- Modify: `CLAUDE.md` (already has Browser-Use section, just verify it's accurate)

**Step 1: Verify CLAUDE.md has Browser-Use docs**

Run: `grep -A5 "Browser-Use" CLAUDE.md | head -20`
Expected: Should show Browser-Use section exists

**Step 2: If needed, add note about Southlake/Burleson fixes**

Add to the "When to Use Browser-Use" table:
```markdown
| Southlake/Burleson | Yes - portal quirks require AI navigation |
```

**Step 3: Commit if changed**

```bash
git add CLAUDE.md
git commit -m "docs: note Southlake/Burleson require Browser-Use"
```

---

## Verification Checklist

After all tasks complete:

- [ ] `pytest tests/browser_scraper/ -v` - All tests pass
- [ ] `data/raw/southlake_raw.json` exists with recent permits
- [ ] `data/raw/burleson_raw.json` exists with permits
- [ ] `data/incremental_batch_results.jsonl` has entries for both cities
- [ ] Southlake permits have 2025 dates (not 2000-2002)
