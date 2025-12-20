# Easy DFW Municipalities Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add 5 easy/already-configured DFW municipalities to the permit scraping system.

**Architecture:** Add configurations to existing scrapers (eTRAKiT, EnerGov CSS, MyGov) and verify they work. No new scrapers needed.

**Tech Stack:** Python, Playwright, existing scraper modules

---

## Summary of Municipalities

| City | Pop | Platform | Status | Effort |
|------|-----|----------|--------|--------|
| Burleson | 50K | eTRAKiT | NEW - add config | 15 min |
| DeSoto | 55K | EnerGov CSS | Already configured | 10 min (verify) |
| Little Elm | 57K | MyGov | Already configured | 10 min (verify) |
| Rowlett | 65K | MyGov | Already configured | 10 min (verify) |
| Mansfield | 75K | MyGov | Already configured | 10 min (verify) |

---

## Task 1: Add Burleson to eTRAKiT Scraper

**Files:**
- Modify: `scrapers/etrakit.py:19-96` (ETRAKIT_CITIES dict)
- Test: Manual test run

**Step 1: Add Burleson config to ETRAKIT_CITIES**

Add this entry to the `ETRAKIT_CITIES` dict in `scrapers/etrakit.py` after the `the_colony` entry (around line 95):

```python
    'burleson': {
        'name': 'Burleson',
        'base_url': 'https://etrakit.burlesontx.com',
        'search_path': '/Search/permit.aspx',
        # Burleson uses standard B-prefix format like Frisco: B25-NNNNN
        'prefixes': ['B25', 'B24', 'B23', 'B22', 'B21', 'B20'],
        'permit_regex': r'^[A-Z]\d{2}-\d{5}$',
    },
```

**Step 2: Verify the scraper runs**

Run:
```bash
cd /home/reid/testhome/permit-scraper && python3 scrapers/etrakit.py burleson 50
```

Expected: Should scrape ~50 permits and save to `data/raw/burleson_raw.json`

**Step 3: Check output file**

Run:
```bash
cat data/raw/burleson_raw.json | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'Permits: {len(d[\"permits\"])}')"
```

Expected: `Permits: 50` (or close to it)

**Step 4: Commit**

```bash
git add scrapers/etrakit.py
git commit -m "feat: add Burleson to eTRAKiT scraper

- Population: 50K
- URL: https://etrakit.burlesontx.com
- Uses standard B-prefix permit format"
```

---

## Task 2: Verify DeSoto EnerGov CSS Works

DeSoto is already configured in `CSS_CITIES` at line 81-84.

**Files:**
- Verify: `scrapers/citizen_self_service.py:81-84`

**Step 1: Check existing config**

The config should be:
```python
    'desoto': {
        'name': 'DeSoto',
        'base_url': 'https://cityofdesototx-energovweb.tylerhost.net/apps/selfservice',
    },
```

**Step 2: Run test scrape**

Run:
```bash
cd /home/reid/testhome/permit-scraper && python3 scrapers/citizen_self_service.py desoto 100
```

Expected: Should scrape ~100 permits and save to `data/raw/desoto_raw.json`

**Step 3: Verify output**

Run:
```bash
ls -la data/raw/desoto* && cat data/raw/desoto_raw.json | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'Permits: {len(d[\"permits\"])}')"
```

Expected: File exists with permits

**Step 4: If successful, update SCRAPER_STATUS.md**

Add DeSoto to the working cities list in SCRAPER_STATUS.md.

---

## Task 3: Verify Little Elm MyGov Works

Little Elm is already configured in `MYGOV_CITIES` at line 37.

**Files:**
- Verify: `scrapers/mygov_multi.py:37`

**Step 1: Check existing config**

The config should be:
```python
    'little_elm': {'name': 'Little Elm', 'slug': 'little_elm_tx', 'pop': 50000},
```

**Step 2: Run test scrape**

Run:
```bash
cd /home/reid/testhome/permit-scraper && python3 scrapers/mygov_multi.py little_elm 100
```

Expected: Should scrape permits using street name searches

**Step 3: Verify output**

Run:
```bash
ls -la data/raw/little_elm*
```

Expected: File exists with permits

---

## Task 4: Verify Rowlett MyGov Works

Rowlett is already configured in `MYGOV_CITIES` at line 34.

**Files:**
- Verify: `scrapers/mygov_multi.py:34`

**Step 1: Check existing config**

The config should be:
```python
    'rowlett': {'name': 'Rowlett', 'slug': 'rowlett_tx', 'pop': 67000},
```

**Step 2: Run test scrape**

Run:
```bash
cd /home/reid/testhome/permit-scraper && python3 scrapers/mygov_multi.py rowlett 100
```

Expected: Should scrape permits using street name searches

**Step 3: Verify output**

Run:
```bash
ls -la data/raw/rowlett*
```

Expected: File exists with permits

---

## Task 5: Verify Mansfield MyGov Works

Mansfield is already configured in `MYGOV_CITIES` at line 33.

**Files:**
- Verify: `scrapers/mygov_multi.py:33`

**Step 1: Check existing config**

The config should be:
```python
    'mansfield': {'name': 'Mansfield', 'slug': 'mansfield_tx', 'pop': 75000},
```

**Step 2: Run test scrape**

Run:
```bash
cd /home/reid/testhome/permit-scraper && python3 scrapers/mygov_multi.py mansfield 100
```

Expected: Should scrape permits using street name searches

**Step 3: Verify output**

Run:
```bash
ls -la data/raw/mansfield*
```

Expected: File exists with permits

---

## Task 6: Update Documentation

**Files:**
- Modify: `SCRAPER_STATUS.md`
- Modify: `TODO.md`

**Step 1: Update SCRAPER_STATUS.md**

Add new municipalities to the table and update counts based on verification results.

**Step 2: Commit documentation**

```bash
git add SCRAPER_STATUS.md TODO.md
git commit -m "docs: update status for new municipalities

Added/verified:
- Burleson (eTRAKiT) - NEW
- DeSoto (EnerGov CSS) - verified
- Little Elm (MyGov) - verified
- Rowlett (MyGov) - verified
- Mansfield (MyGov) - verified"
```

---

## Notes

### Keller (Excluded)
Keller was researched but excluded because:
- Uses "Enterprise Permitting & Licensing" (EPL), NOT standard EnerGov CSS
- Would require new scraper implementation
- Moved to "hard" category for future implementation

### Population Priority
Cities sorted by fruitfulness (population):
1. Mansfield (75K) - highest priority
2. Rowlett (65K)
3. Little Elm (57K)
4. DeSoto (55K)
5. Burleson (50K)

### CAD Enrichment
All cities have CAD enrichment available:
- Burleson → Johnson County (may need new CAD integration)
- DeSoto → Dallas County (existing)
- Little Elm → Denton County (existing)
- Rowlett → Dallas/Rockwall County (existing)
- Mansfield → Tarrant/Johnson County (partial)
