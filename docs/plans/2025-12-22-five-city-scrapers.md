# Five City Scrapers Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Get production-ready scrapers for 5 DFW cities currently returning 0 permits: The Colony, Southlake, North Richland Hills, University Park, and Forney.

**Architecture:** Fix The Colony's regex (uses `AEC#####` not `B25-#####`), run Southlake batch scrape with Browser-Use, run Browser-Use diagnostic mode on NRH/University Park to understand portal behavior, defer Forney (requires Collaborator login we don't have).

**Tech Stack:** Python 3.11, Playwright, Browser-Use 0.11.1, DeepSeek API, PostgreSQL

---

## Task 1: Fix The Colony eTRAKiT Regex

**Files:**
- Modify: `scrapers/etrakit.py:92-99`
- Test: `tests/test_etrakit_config.py` (create)

**Step 1: Write the failing test**

Create `tests/test_etrakit_config.py`:

```python
"""Tests for eTRAKiT city configurations."""
import re
import pytest

def test_the_colony_permit_format():
    """The Colony uses AEC##### format, not B25-#####."""
    from scrapers.etrakit import ETRAKIT_CITIES

    config = ETRAKIT_CITIES.get('the_colony')
    assert config is not None, "the_colony not in ETRAKIT_CITIES"

    # Real permit numbers from The Colony portal
    real_permits = ['AEC10007', 'AEC10008', 'AEC10023', 'AEC11108']

    pattern = re.compile(config['permit_regex'])
    for permit in real_permits:
        assert pattern.match(permit), f"Regex should match {permit}"

    # Should NOT match old B25 format
    assert not pattern.match('B25-00001'), "Should not match B25 format"

def test_the_colony_has_aec_prefix():
    """The Colony should search for AEC prefix, not B25."""
    from scrapers.etrakit import ETRAKIT_CITIES

    config = ETRAKIT_CITIES.get('the_colony')
    assert 'AEC' in config['prefixes'], "The Colony must have AEC prefix"
    assert 'B25' not in config['prefixes'], "The Colony should NOT have B25 prefix"
```

**Step 2: Run test to verify it fails**

Run: `cd /home/reid/testhome/permit-scraper && pytest tests/test_etrakit_config.py -v`

Expected: FAIL with "Regex should match AEC10007" or "The Colony must have AEC prefix"

**Step 3: Fix The Colony config in etrakit.py**

In `scrapers/etrakit.py`, replace lines 92-99:

```python
    'the_colony': {
        'name': 'The Colony',
        'base_url': 'https://tcol-trk.aspgov.com',
        'search_path': '/etrakit/Search/permit.aspx',
        # The Colony uses AEC format: AEC10007, AEC11108, etc.
        'prefixes': ['AEC'],
        'permit_regex': r'^AEC\d{4,6}$',
    },
```

**Step 4: Run test to verify it passes**

Run: `cd /home/reid/testhome/permit-scraper && pytest tests/test_etrakit_config.py -v`

Expected: PASS

**Step 5: Integration test - scrape The Colony**

Run: `cd /home/reid/testhome/permit-scraper && python3 scrapers/etrakit.py the_colony 20`

Expected: Should find >0 permits with AEC format

**Step 6: Commit**

```bash
cd /home/reid/testhome/permit-scraper
git add scrapers/etrakit.py tests/test_etrakit_config.py
git commit -m "fix(the_colony): use AEC permit format instead of B25"
```

---

## Task 2: Southlake Batch Scrape

**Files:**
- None to modify (existing SOUTHLAKE_BULK_TASK at `services/browser_scraper/permit_tasks.py:114`)
- Output: `data/raw/southlake_raw.json`

**Step 1: Verify Browser-Use runner works**

Run: `cd /home/reid/testhome/permit-scraper && python3 -c "from services.browser_scraper.runner import PermitScraperRunner; print('Runner imports OK')"`

Expected: "Runner imports OK"

**Step 2: Run Southlake bulk scrape for 2025**

Run:
```bash
cd /home/reid/testhome/permit-scraper
python3 -m services.browser_scraper.runner --city southlake --mode bulk --start-date "01/01/2025" --end-date "12/22/2025"
```

Expected: Browser opens, navigates to Southlake EnerGov, sorts by date descending, extracts permits

**Step 3: Verify output file**

Run: `cat data/raw/southlake_raw.json | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'Southlake: {len(d) if isinstance(d,list) else len(d.get(\"permits\",[]))} permits')"`

Expected: `Southlake: >10 permits` (more than the 4 we had before)

**Step 4: If successful, load to database**

Run: `cd /home/reid/testhome/permit-scraper && python3 scripts/load_permits.py --city southlake`

Expected: Permits loaded to `leads_permit` table

**Step 5: Document result in TODO.md**

If successful, mark Southlake batch scrape as complete in TODO.md.

---

## Task 3: NRH Diagnostic - Investigate Auth Boundary

**Files:**
- Output: `data/screenshots/north_richland_hills/` (screenshots)
- Output: `data/raw/north_richland_hills_diagnostic.json`

**Step 1: Run Browser-Use single mode to observe**

Run:
```bash
cd /home/reid/testhome/permit-scraper
BROWSER_USE_HEADLESS=false python3 -m services.browser_scraper.runner --city north_richland_hills --mode single --address "123 Main St"
```

Expected: Browser opens visibly. Watch what happens - note where "requires auth" error occurs.

**Step 2: Capture observations**

While browser is open, note:
- Does the portal load?
- Can you click "Permit" module?
- At what step does auth block appear?
- Is there a "Guest" or "Public Search" option?

**Step 3: Document findings**

Create `docs/portal-analysis/north_richland_hills.md`:

```markdown
# North Richland Hills Portal Analysis

**Date:** 2025-12-22
**Portal:** https://selfservice.nrhtx.com/energov_prod/selfservice

## Observations

[Fill in from Step 2]

## Auth Boundary

- Public access to: [list what's accessible]
- Auth required for: [list what needs login]

## Recommended Approach

[Based on findings]
```

**Step 4: Commit analysis**

```bash
cd /home/reid/testhome/permit-scraper
git add docs/portal-analysis/north_richland_hills.md
git commit -m "docs(nrh): document portal auth boundaries"
```

---

## Task 4: University Park Diagnostic - Verify Portal Has Permits

**Files:**
- Output: `data/raw/university_park_diagnostic.json`

**Step 1: Check if MyGov public portal exposes permits**

Run:
```bash
cd /home/reid/testhome/permit-scraper
curl -s "https://public.mygov.us/university_park_tx" | grep -iE "permit|application|building" | head -10
```

Expected: Should see permit-related links if portal has them

**Step 2: Run Browser-Use to observe portal**

Run:
```bash
cd /home/reid/testhome/permit-scraper
BROWSER_USE_HEADLESS=false python3 -m services.browser_scraper.runner --city university_park --mode single --address "3700 University Blvd"
```

Expected: Observe what modules are available

**Step 3: Document findings**

Create `docs/portal-analysis/university_park.md`:

```markdown
# University Park Portal Analysis

**Date:** 2025-12-22
**Portal:** https://public.mygov.us/university_park_tx

## Available Modules

[List what's visible in portal]

## Permit Search

- Available: [yes/no]
- Method: [keyword search? address lookup? permit number?]

## Recommended Approach

[Based on findings - may need to skip city if no permits exposed]
```

**Step 4: Commit analysis**

```bash
cd /home/reid/testhome/permit-scraper
git add docs/portal-analysis/university_park.md
git commit -m "docs(university_park): document portal capabilities"
```

---

## Task 5: Forney - Document Blocker

**Files:**
- Modify: `AUTH_REQUIRED.md`

**Step 1: Confirm Forney requires Collaborator login**

Run:
```bash
curl -s "https://mygov.us/collaborator/forneytx" -o /dev/null -w "%{http_code}"
```

Expected: `302` (redirect to login) or `401`

**Step 2: Update AUTH_REQUIRED.md**

Add to the "Need Credentials From Reid" section:

```markdown
### Forney (MyGov Collaborator)
- **Portal:** https://mygov.us/collaborator/forneytx
- **Type:** MyGov Collaborator (requires contractor/city login)
- **Status:** BLOCKED - need to register or request access
- **Alternative:** Check if city publishes permit data elsewhere
```

**Step 3: Commit**

```bash
cd /home/reid/testhome/permit-scraper
git add AUTH_REQUIRED.md
git commit -m "docs(forney): document MyGov Collaborator login requirement"
```

---

## Task 6: Full Integration Test & Pipeline Run

**Files:**
- None to modify

**Step 1: Run all working scrapers**

```bash
cd /home/reid/testhome/permit-scraper

# The Colony (should work now)
python3 scrapers/etrakit.py the_colony 100

# Southlake (Browser-Use bulk)
python3 -m services.browser_scraper.runner --city southlake --mode bulk --start-date "01/01/2025" --end-date "12/22/2025"
```

**Step 2: Load permits to database**

```bash
python3 scripts/load_permits.py
```

**Step 3: Verify counts**

```bash
source .env
psql "$DATABASE_URL" -c "SELECT city, COUNT(*) FROM leads_permit WHERE city IN ('The Colony', 'Southlake') GROUP BY city;"
```

Expected: Both cities should have >0 permits

**Step 4: Update LEADS_INVENTORY.md**

Document new permit counts for The Colony and Southlake.

**Step 5: Final commit**

```bash
git add LEADS_INVENTORY.md
git commit -m "docs: update lead inventory with The Colony and Southlake counts"
```

---

## Summary

| City | Task | Status |
|------|------|--------|
| The Colony | Fix regex `AEC\d{4,6}` | Task 1 |
| Southlake | Browser-Use bulk scrape | Task 2 |
| North Richland Hills | Diagnostic - understand auth | Task 3 |
| University Park | Diagnostic - verify permits exist | Task 4 |
| Forney | Document blocker | Task 5 |

**Success Criteria:**
- The Colony: 50+ permits scraped
- Southlake: 50+ permits scraped (up from 4)
- NRH/University Park: Clear documentation of what's possible
- Forney: Documented blocker with next steps
