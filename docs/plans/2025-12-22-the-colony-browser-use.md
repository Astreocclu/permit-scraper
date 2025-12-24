# The Colony Browser-Use Detail Extraction Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create a Browser-Use task that extracts full addresses from The Colony permit detail pages, solving the incomplete address data issue.

**Architecture:** Add a new `THE_COLONY_DETAIL_TASK` template to `permit_tasks.py` that instructs the AI agent to click into each permit's detail page to extract the full address. Update `CITY_TASKS` to use this new template for The Colony.

**Tech Stack:** Python 3.11, Browser-Use 0.11.1, DeepSeek API, Playwright

---

## Task 1: Write Test for The Colony Detail Task

**Files:**
- Modify: `tests/browser_scraper/test_permit_tasks.py`

**Step 1: Write the failing test**

Add to `tests/browser_scraper/test_permit_tasks.py`:

```python
def test_the_colony_has_detail_extraction():
    """The Colony task must click into detail pages to get full addresses."""
    from services.browser_scraper.permit_tasks import CITY_TASKS

    task = CITY_TASKS.get('the_colony')
    assert task is not None, "the_colony not in CITY_TASKS"

    # Must instruct to click into detail pages
    assert 'detail' in task.lower() or 'click' in task.lower(), \
        "The Colony task must instruct agent to click into detail pages"

    # Must extract full address
    assert 'full address' in task.lower() or 'street number' in task.lower(), \
        "The Colony task must extract full address from detail page"


def test_the_colony_bulk_extracts_multiple_permits():
    """The Colony bulk task must handle multiple permits with detail extraction."""
    from services.browser_scraper.permit_tasks import get_task_for_city

    task = get_task_for_city("the_colony", mode="bulk", start_date="01/01/2025", end_date="12/22/2025")

    # Must handle multiple permits
    assert 'each' in task.lower() or 'all' in task.lower() or 'multiple' in task.lower(), \
        "Bulk task must handle multiple permits"

    # Must return JSON array
    assert 'json' in task.lower(), \
        "Task must return JSON"
```

**Step 2: Run test to verify it fails**

Run: `cd /home/reid/testhome/permit-scraper && pytest tests/browser_scraper/test_permit_tasks.py::test_the_colony_has_detail_extraction -v`

Expected: FAIL with "The Colony task must instruct agent to click into detail pages"

**Step 3: Commit test**

```bash
cd /home/reid/testhome/permit-scraper
git add tests/browser_scraper/test_permit_tasks.py
git commit -m "test(the_colony): add tests for detail page extraction"
```

---

## Task 2: Create The Colony Detail Task Template

**Files:**
- Modify: `services/browser_scraper/permit_tasks.py:85-110` (add new template after SOUTHLAKE_BULK_TASK)

**Step 1: Add THE_COLONY_DETAIL_TASK template**

Add after line ~145 (after `SOUTHLAKE_BULK_TASK`):

```python
THE_COLONY_DETAIL_TASK = EFFICIENCY_DIRECTIVE + """
Go to The Colony eTRAKiT portal at https://tcol-trk.aspgov.com/etrakit/Search/permit.aspx

1. SEARCH FOR PERMITS:
   - In the "Search By" dropdown, select "Permit Number"
   - In the search field, enter "{prefix}" (just the letter prefix)
   - Click "Search" button
   - Wait for results to load

2. FOR EACH PERMIT IN RESULTS (up to 50):
   - Note the permit number from the table (format: MMYY-NNNN like 0701-4211)
   - Click on the permit number link to open detail page

3. ON DETAIL PAGE - Extract these fields:
   - permit_number: The permit ID (e.g., "0701-4211")
   - full_address: Look for "Site Address", "Property Address", or "Location" field
     - MUST include street NUMBER and street NAME (e.g., "123 BAKER DR")
   - permit_type: Type/Category of permit
   - status: Current status (Issued, Closed, etc.)
   - issue_date: Date permit was issued
   - description: Work description if available
   - valuation: Dollar value if shown

4. NAVIGATE BACK:
   - Click browser Back button or "Return to Search" link
   - Continue to next permit

5. RETURN FORMAT:
Return a JSON array of permit objects:
```json
[
  {{
    "permit_number": "0701-4211",
    "address": "123 BAKER DR",
    "permit_type": "Building",
    "status": "Closed",
    "issue_date": "07/01/2007",
    "description": "New single family residence",
    "valuation": "250000"
  }}
]
```

IMPORTANT: The search results table only shows street NAMES. You MUST click into detail page to get full address with street NUMBER.
"""

THE_COLONY_BULK_TASK = EFFICIENCY_DIRECTIVE + """
Go to The Colony eTRAKiT portal at https://tcol-trk.aspgov.com/etrakit/Search/permit.aspx

1. SEARCH SETUP:
   - In "Search By" dropdown, select "Issue Date" or "Date Range"
   - Set start date: {start_date}
   - Set end date: {end_date}
   - Click "Search"

2. FOR EACH PERMIT IN RESULTS (handle pagination, up to 100 total):
   - Click on the permit number link to open detail page

3. ON DETAIL PAGE - Extract:
   - permit_number
   - full_address (MUST have street number + name, e.g., "123 BAKER DR")
   - permit_type
   - status
   - issue_date
   - description
   - valuation

4. Navigate back and continue to next permit

5. If pagination exists, click "Next" and repeat

Return JSON array of all permits with full addresses.
"""
```

**Step 2: Run test to verify still fails (template not wired up)**

Run: `cd /home/reid/testhome/permit-scraper && pytest tests/browser_scraper/test_permit_tasks.py::test_the_colony_has_detail_extraction -v`

Expected: Still FAIL (template exists but not in CITY_TASKS yet)

**Step 3: Commit template**

```bash
cd /home/reid/testhome/permit-scraper
git add services/browser_scraper/permit_tasks.py
git commit -m "feat(the_colony): add detail extraction task template"
```

---

## Task 3: Wire Up The Colony to Use New Template

**Files:**
- Modify: `services/browser_scraper/permit_tasks.py:389` (CITY_TASKS dict)

**Step 1: Update CITY_TASKS entry for the_colony**

Find line ~389 and change:

```python
# FROM:
"the_colony": ETRAKIT_TEMPLATE.format(city_name="The Colony", url="https://tcol-trk.aspgov.com/eTrakit/"),

# TO:
"the_colony": THE_COLONY_DETAIL_TASK.format(prefix="B"),
```

**Step 2: Run test to verify it passes**

Run: `cd /home/reid/testhome/permit-scraper && pytest tests/browser_scraper/test_permit_tasks.py::test_the_colony_has_detail_extraction -v`

Expected: PASS

**Step 3: Run second test**

Run: `cd /home/reid/testhome/permit-scraper && pytest tests/browser_scraper/test_permit_tasks.py::test_the_colony_bulk_extracts_multiple_permits -v`

Expected: PASS

**Step 4: Commit wiring**

```bash
cd /home/reid/testhome/permit-scraper
git add services/browser_scraper/permit_tasks.py
git commit -m "feat(the_colony): wire up detail extraction template"
```

---

## Task 4: Add Bulk Mode Handling for The Colony

**Files:**
- Modify: `services/browser_scraper/permit_tasks.py:620-650` (get_task_for_city function)

**Step 1: Add The Colony bulk mode handling**

Find the `get_task_for_city` function (around line 610) and add The Colony handling in the bulk mode section:

```python
# Add after line ~626 (after Southlake handling):
        if normalized_city == "the_colony":
            return THE_COLONY_BULK_TASK.format(start_date=start_date, end_date=end_date)
```

**Step 2: Write test for bulk mode**

Add to `tests/browser_scraper/test_permit_tasks.py`:

```python
def test_the_colony_bulk_mode_uses_bulk_template():
    """The Colony bulk mode should use THE_COLONY_BULK_TASK."""
    from services.browser_scraper.permit_tasks import get_task_for_city

    task = get_task_for_city("the_colony", mode="bulk", start_date="01/01/2025", end_date="12/22/2025")

    # Should have date range
    assert "01/01/2025" in task or "start_date" in task.lower(), \
        "Bulk task should include start date"
    assert "12/22/2025" in task or "end_date" in task.lower(), \
        "Bulk task should include end date"
```

**Step 3: Run all The Colony tests**

Run: `cd /home/reid/testhome/permit-scraper && pytest tests/browser_scraper/test_permit_tasks.py -k "the_colony" -v`

Expected: All tests PASS

**Step 4: Commit bulk handling**

```bash
cd /home/reid/testhome/permit-scraper
git add services/browser_scraper/permit_tasks.py tests/browser_scraper/test_permit_tasks.py
git commit -m "feat(the_colony): add bulk mode with date range support"
```

---

## Task 5: Integration Test - Run Browser-Use on The Colony

**Files:**
- None to modify (execution test)

**Step 1: Verify Browser-Use runner imports**

Run: `cd /home/reid/testhome/permit-scraper && python3.11 -c "from services.browser_scraper.runner import PermitScraperRunner; print('OK')"`

Expected: `OK`

**Step 2: Run single permit test (headless)**

Run:
```bash
cd /home/reid/testhome/permit-scraper
python3.11 -m services.browser_scraper.runner --city the_colony --mode single --address "123 Main St"
```

Expected: Browser-Use navigates to portal, clicks into detail page, extracts permit with full address

**Step 3: Check output**

Run: `cat data/raw/the_colony_raw.json | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'Permits: {len(d.get(\"permits\", d)) if isinstance(d,dict) else len(d)}')"`

Expected: Shows permit count > 0

**Step 4: Verify address has street number**

Run: `cat data/raw/the_colony_raw.json | python3 -c "import json,sys; d=json.load(sys.stdin); permits=d.get('permits',d) if isinstance(d,dict) else d; print(permits[0].get('address','NO ADDRESS') if permits else 'EMPTY')"`

Expected: Full address like "123 BAKER DR" (not just "BAKER DR")

---

## Task 6: Run Bulk Scrape and Load to Database

**Files:**
- None to modify (execution)

**Step 1: Run bulk scrape for 2025**

Run:
```bash
cd /home/reid/testhome/permit-scraper
python3.11 -m services.browser_scraper.runner --city the_colony --mode bulk --start-date "01/01/2025" --end-date "12/22/2025"
```

Expected: Extracts multiple permits with full addresses

**Step 2: Verify output has full addresses**

Run:
```bash
cd /home/reid/testhome/permit-scraper
cat data/raw/the_colony_raw.json | python3 -c "
import json, sys, re
d = json.load(sys.stdin)
permits = d.get('permits', d) if isinstance(d, dict) else d
full_addr = 0
for p in permits[:10]:
    addr = p.get('address', '')
    if re.match(r'^\d+\s+\w+', addr):  # Starts with number
        full_addr += 1
        print(f'FULL: {addr}')
    else:
        print(f'PARTIAL: {addr}')
print(f'\n{full_addr}/10 have full addresses')
"
```

Expected: Most addresses start with a number (full address)

**Step 3: Load to database**

Run: `cd /home/reid/testhome/permit-scraper && python3 scripts/load_permits.py --city the_colony`

Expected: Permits loaded successfully (not skipped due to missing address)

**Step 4: Final commit**

```bash
cd /home/reid/testhome/permit-scraper
git add -A
git commit -m "feat(the_colony): Browser-Use detail extraction working

- Added THE_COLONY_DETAIL_TASK template for single permit extraction
- Added THE_COLONY_BULK_TASK template for date range bulk extraction
- Both templates click into detail pages to get full addresses
- Successfully extracts permits with complete address data
"
```

---

## Summary

| Task | Description | Files |
|------|-------------|-------|
| 1 | Write failing tests | `tests/browser_scraper/test_permit_tasks.py` |
| 2 | Create detail task template | `services/browser_scraper/permit_tasks.py` |
| 3 | Wire up CITY_TASKS | `services/browser_scraper/permit_tasks.py` |
| 4 | Add bulk mode handling | `services/browser_scraper/permit_tasks.py` |
| 5 | Integration test | (execution only) |
| 6 | Bulk scrape and load | (execution only) |

**Success Criteria:**
- The Colony permits have full addresses (street number + name)
- Permits successfully load to database
- All tests pass
