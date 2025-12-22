# Codebase Maintenance Plan - 2025-12-21

## Audit Summary

**Codebase:** permit-scraper (DFW Signal Engine)
**Audit Date:** December 21, 2025
**Audit Tools:** Claude Code + Gemini analysis

---

## Priority Matrix

| Priority | Risk | Batch | Category |
|----------|------|-------|----------|
| CRITICAL | HIGH | 1 | Secrets exposure, failing health |
| HIGH | MEDIUM | 2 | Git hygiene, uncommitted work |
| MEDIUM | LOW | 3 | File cleanup, pycache, temp files |
| LOW | LOW | 4 | Documentation updates |
| NICE-TO-HAVE | LOW | 5 | Dependency updates, code cleanup |

---

## Batch 1: CRITICAL - Git Hygiene & Uncommitted Changes (HIGH PRIORITY)

### 1.1 Uncommitted Changes
**Status:** 30 commits ahead of origin, 4 modified/untracked files

```
Modified: scripts/load_permits.py
Untracked:
  - dfw_big4_contractor_leads.csv (1.8MB - should be in data/exports/)
  - docs/plans/2025-12-21-browseruse-burleson-southlake.md
  - scrapers/collin_cad_socrata.py
  - whatthe.txt (30KB - temp debug file?)
```

**Actions:**
- [ ] Review `scripts/load_permits.py` changes - stage if intentional
- [ ] Move `dfw_big4_contractor_leads.csv` to `data/exports/` (duplicate exists there)
- [ ] Stage `docs/plans/2025-12-21-browseruse-burleson-southlake.md`
- [ ] Stage `scrapers/collin_cad_socrata.py` (new scraper)
- [ ] Review and delete `whatthe.txt` if temp file
- [ ] Push 30 commits to origin

### 1.2 Secrets Scan
**Status:** CLEAN - No hardcoded secrets found

The grep scan found references to `api_key`, `mgo_password` but they're parameter names, not values:
- `services/browser_scraper/agent.py:26` - uses `self.api_key` (loaded from env)
- `services/browser_scraper/permit_tasks.py` - template placeholders for MGO credentials

**No action needed** - secrets are properly externalized to `.env`

---

## Batch 2: File Cleanup (MEDIUM PRIORITY)

### 2.1 Python Cache Directories
**Found:** 9 `__pycache__` directories

```
./scrapers/__pycache__
./services/browser_scraper/__pycache__
./services/__pycache__
./services/property_images/__pycache__
./tests/browser_scraper/__pycache__
./tests/__pycache__
./tests/services/__pycache__
./tests/services/property_images/__pycache__
./scripts/__pycache__
```

**Action:**
```bash
find . -type d -name "__pycache__" -not -path "./venv/*" -exec rm -rf {} + 2>/dev/null
find . -type f -name "*.pyc" -not -path "./venv/*" -delete 2>/dev/null
```

### 2.2 Log Files
**Found:** 1 log file in root

```
./browser_usage.log (8.2KB)
```

**Action:**
- [ ] Move `browser_usage.log` to `data/logs/` or delete
- [ ] Add `*.log` to root `.gitignore` if not present

### 2.3 Empty/Tiny Raw JSON Files
**Found:** 3 essentially empty files

```
data/raw/university_park_mygov_raw.json (empty)
data/raw/burleson_mygov_raw.json (2 bytes - just "[]")
data/raw/forney_mygov_raw.json (2 bytes - just "[]")
```

**Context:** These are from failed scraping attempts for cities where:
- University Park: Low permit activity
- Burleson: Portal blocked (no permit search module)
- Forney: May need different search config

**Action:**
- [ ] Keep files (they document failed attempts)
- [ ] Add comments in CLAUDE.md about blocked cities

### 2.4 Misplaced Files in Root
**Found:**

```
dfw_big4_contractor_leads.csv (1.8MB) - duplicate of data/exports/ version
whatthe.txt (30KB) - appears to be temp debug output
```

**Action:**
- [ ] Delete `dfw_big4_contractor_leads.csv` from root (keep data/exports version)
- [ ] Delete `whatthe.txt` after review

---

## Batch 3: Data Directory Cleanup (MEDIUM PRIORITY)

### 3.1 Stale Data Files (>7 days old)
**Found:** 20 files >7 days old

Key stale files:
- `data/permits.db` - Legacy SQLite (3.2MB) - migrated to PostgreSQL
- `data/raw/dallas_enriched.json` - Old enrichment format
- `data/raw/dallas_residential.json` - Old filtered data

**Action:**
- [ ] Archive or delete `data/permits.db` if fully migrated
- [ ] Keep `data/raw/*.json` files (valid historical data)

### 3.2 Review Queue
**Found:** 2 pending reviews (3.8MB total)

```
data/review_queue/pending/20251221_104231_southlake.json (1MB)
data/review_queue/pending/20251221_105429_burleson.json (2.8MB)
```

**Action:**
- [ ] Run `python3 -m services.browser_scraper.review_cli --list` to process

### 3.3 Screenshots
**Size:** 2.8MB in `data/screenshots/`

**Action:** No cleanup needed - reasonable size

### 3.4 Exports Directory
**Files:** 8 export files (3.3MB total)

Some are dated (Dec 8-9):
- `arlington_filtered_6wk.csv`
- `arlington_filtered.csv`
- `permits.csv`

**Action:**
- [ ] Archive old exports if no longer needed
- [ ] Keep recent exports

---

## Batch 4: Documentation Updates (LOW PRIORITY)

### 4.1 TODO.md Sync
**Issues:**
- Some completed items still unchecked
- Recent work not reflected

**Action:**
- [ ] Mark EnerGov Expansion as done (McKinney, Allen working)
- [ ] Update "Recently Added" section with Dec 21 work
- [ ] Add Collin CAD Socrata scraper to working list

### 4.2 CLAUDE.md Updates
**Issues:**
- Working portals list may be stale
- Add new Collin CAD scraper

**Action:**
- [ ] Add `collin_cad_socrata.py` to working scrapers list
- [ ] Update blocked cities section

### 4.3 Old Plan Files
**Found:** 20 plan files in `docs/plans/`

Oldest: `IMPLEMENTATION_PLAN_2025-12-09.md`

**Action:**
- [ ] Review if any can be archived (move to `docs/plans/archive/`)
- [ ] Keep recent and in-progress plans

---

## Batch 5: Code Hygiene (NICE-TO-HAVE)

### 5.1 TODO/FIXME Comments
**Found:** 8 TODO comments in code

```
./scrapers/etrakit_auth.py:44 - login required
./scrapers/mgo_connect.py:52-57 - Find JIDs for cities
./services/property_images/image_fetcher.py:72-154 - Add Denton/Collin CAD
```

**Action:**
- [ ] Create issues for unresolved TODOs
- [ ] Remove obsolete TODOs

### 5.2 Duplicate Code
Gemini identified potential duplication in `permit_tasks.py`:
- Duplicate `get_task_for_city` function
- Redundant `CITY_TASKS` entries

**Action:**
- [ ] Review and consolidate if confirmed

### 5.3 Outdated Dependencies
**Outdated packages (pip list --outdated):**

| Package | Current | Latest | Priority |
|---------|---------|--------|----------|
| aiohttp | 3.12.15 | 3.13.2 | LOW |
| browser-use | 0.11.1 | 0.11.2 | MEDIUM |
| groq | 0.37.1 | 1.0.0 | LOW |
| cryptography | 3.4.8 | 46.0.3 | SECURITY |

**Action:**
- [ ] Update `cryptography` (security fix)
- [ ] Update `browser-use` (minor bump)
- [ ] Other packages can wait

---

## Batch 6: Test Coverage (NICE-TO-HAVE)

### Current Coverage
**Tests:** 90 test items collected

Gemini analysis identified gaps:
- No mocking for DeepSeekScorer
- Database tests missing
- Address normalization untested
- Categorization untested
- Export logic untested

**Action:**
- [ ] Add mocks for external services
- [ ] Add unit tests for address normalization
- [ ] Add tests for categorization logic

---

## Execution Checklist

### Quick Wins (5 minutes)
```bash
# Delete pycache
find . -type d -name "__pycache__" -not -path "./venv/*" -exec rm -rf {} + 2>/dev/null

# Move log file
mv browser_usage.log data/logs/ 2>/dev/null

# Delete duplicate CSV
rm dfw_big4_contractor_leads.csv 2>/dev/null

# Delete temp file (after review)
# rm whatthe.txt
```

### Git Cleanup (10 minutes)
```bash
git status
git add scrapers/collin_cad_socrata.py
git add docs/plans/2025-12-21-browseruse-burleson-southlake.md
git add scripts/load_permits.py  # if changes are intentional
git push origin main
```

### Security Updates (5 minutes)
```bash
pip install --upgrade cryptography
pip install --upgrade browser-use
```

---

## Risk Assessment

| Action | Risk | Mitigation |
|--------|------|------------|
| Delete pycache | NONE | Auto-regenerated |
| Delete root CSV | LOW | Backup exists in data/exports/ |
| Delete whatthe.txt | LOW | Review first |
| Push 30 commits | LOW | Already tested locally |
| Upgrade cryptography | MEDIUM | Test after upgrade |
| Delete permits.db | MEDIUM | Verify PostgreSQL migration complete |

---

## Verification Commands

After cleanup, run:
```bash
# Verify tests still pass
pytest

# Check no new issues
git status

# Verify DB connectivity
python3 -c "from scripts.load_permits import get_db_connection; get_db_connection()"
```

---

## Confidence Assessment

**Claude confidence:** 90%
- Comprehensive diagnostics run
- Low-risk changes identified
- Clear prioritization

**Concerns:**
- Should verify `permits.db` is fully deprecated before deleting
- `whatthe.txt` contents unknown - need manual review
- 30 unpushed commits is a lot - consider squashing if appropriate
