# 10 New DFW Municipalities Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add 10 new DFW municipalities to the permit scraping system, enabling lead generation from high-wealth suburbs.

**Architecture:** Config-driven scraper expansion - add city configurations to existing `citizen_self_service.py`, `etrakit.py`, `mygov_multi.py`, and `accela_fast.py` scrapers. Fix Angular timeout issues in McKinney/Allen.

**Tech Stack:** Python 3, Playwright, existing scraper framework

---

## Summary of Changes

| City | Platform | Scraper File | Action |
|------|----------|--------------|--------|
| The Colony | eTRAKiT | `scrapers/etrakit.py` | Add config |
| University Park | MyGov | `scrapers/mygov_multi.py` | Add config |
| Hurst | EnerGov CSS | `scrapers/citizen_self_service.py` | Add config |
| Farmers Branch | EnerGov CSS | `scrapers/citizen_self_service.py` | Add config |
| Coppell | EnerGov CSS | `scrapers/citizen_self_service.py` | Add config |
| Forney | MyGov | `scrapers/mygov_multi.py` | Add config |
| North Richland Hills | EnerGov CSS | `scrapers/citizen_self_service.py` | Add config |
| Duncanville | Accela | `scrapers/accela_fast.py` | Add config |
| McKinney | EnerGov CSS | `scrapers/citizen_self_service.py` | Fix timeout |
| Allen | EnerGov CSS | `scrapers/citizen_self_service.py` | Fix timeout |

---

## Task 1: Add The Colony to eTRAKiT Scraper

**Files:**
- Modify: `scrapers/etrakit.py:19-88` (ETRAKIT_CITIES dict)
- Test: Manual test via CLI

**Step 1: Add The Colony configuration to ETRAKIT_CITIES**

In `scrapers/etrakit.py`, add this entry to `ETRAKIT_CITIES` dict after the `prosper` entry:

```python
    'the_colony': {
        'name': 'The Colony',
        'base_url': 'https://tcol-trk.aspgov.com',
        'search_path': '/etrakit3/Search/permit.aspx',
        # The Colony uses standard B-prefix format: B25-NNNNN
        'prefixes': ['B25', 'B24', 'B23', 'B22', 'B21', 'B20'],
        'permit_regex': r'^[A-Z]\d{2}-\d{5}$',
    },
```

**Step 2: Test The Colony scraper**

Run: `cd /home/reid/testhome/permit-scraper && python3 scrapers/etrakit.py the_colony 10`

Expected: Should scrape 5-10 permits successfully without errors.

**Step 3: Commit**

```bash
cd /home/reid/testhome/permit-scraper && git add scrapers/etrakit.py && git commit -m "feat: add The Colony to eTRAKiT scraper"
```

---

## Task 2: Add University Park and Forney to MyGov Scraper

**Files:**
- Modify: `scrapers/mygov_multi.py:32-43` (MYGOV_CITIES dict)
- Test: Manual test via CLI

**Step 1: Add University Park and Forney to MYGOV_CITIES**

In `scrapers/mygov_multi.py`, add these entries to `MYGOV_CITIES` dict:

```python
    'university_park': {'name': 'University Park', 'slug': 'university_park_tx', 'pop': 25000},
    'forney': {'name': 'Forney', 'slug': 'forney_tx', 'pop': 25000},
```

**Step 2: Test University Park scraper**

Run: `cd /home/reid/testhome/permit-scraper && python3 scrapers/mygov_multi.py university_park 10`

Expected: Should find addresses and extract permits (may get 0-10 depending on recent activity).

**Step 3: Test Forney scraper**

Run: `cd /home/reid/testhome/permit-scraper && python3 scrapers/mygov_multi.py forney 10`

Expected: Should find addresses and extract permits.

Note: If Forney requires login, mark as BLOCKED in commit message.

**Step 4: Commit**

```bash
cd /home/reid/testhome/permit-scraper && git add scrapers/mygov_multi.py && git commit -m "feat: add University Park and Forney to MyGov scraper"
```

---

## Task 3: Add EnerGov CSS Cities (Hurst, Farmers Branch, Coppell, NRH)

**Files:**
- Modify: `scrapers/citizen_self_service.py:52-91` (CSS_CITIES dict)
- Test: Manual test via CLI

**Step 1: Add four new cities to CSS_CITIES**

In `scrapers/citizen_self_service.py`, add these entries to `CSS_CITIES` dict after `mesquite`:

```python
    'hurst': {
        'name': 'Hurst',
        'base_url': 'https://energov.hursttx.gov/EnerGov_Prod/SelfService',
    },
    'farmers_branch': {
        'name': 'Farmers Branch',
        'base_url': 'https://egselfservice.farmersbranchtx.gov/EnerGov_Prod/SelfService',
    },
    'coppell': {
        'name': 'Coppell',
        'base_url': 'https://muniselfservice.coppelltx.gov/css',
        # Coppell uses newer Tyler Civic Access - may need skip_permit_type_filter
        'skip_permit_type_filter': True,
    },
    'north_richland_hills': {
        'name': 'North Richland Hills',
        'base_url': 'https://selfservice.nrhtx.com/energov_prod/selfservice',
    },
```

**Step 2: Test Hurst scraper**

Run: `cd /home/reid/testhome/permit-scraper && python3 scrapers/citizen_self_service.py hurst 10`

Expected: Should navigate to portal and extract permits. Watch for Angular timeout errors.

**Step 3: Test Farmers Branch scraper**

Run: `cd /home/reid/testhome/permit-scraper && python3 scrapers/citizen_self_service.py farmers_branch 10`

Expected: Should work similarly to Southlake.

**Step 4: Test North Richland Hills scraper**

Run: `cd /home/reid/testhome/permit-scraper && python3 scrapers/citizen_self_service.py north_richland_hills 10`

Expected: Should work with standard EnerGov CSS interface.

**Step 5: Test Coppell scraper (HIGH RISK)**

Run: `cd /home/reid/testhome/permit-scraper && python3 scrapers/citizen_self_service.py coppell 10`

Expected: May fail due to newer Tyler Civic Access interface. If fails, note URL redirect patterns.

**Step 6: Commit working cities**

```bash
cd /home/reid/testhome/permit-scraper && git add scrapers/citizen_self_service.py && git commit -m "feat: add Hurst, Farmers Branch, NRH, Coppell to EnerGov CSS scraper"
```

---

## Task 4: Add Duncanville to Accela Scraper

**Files:**
- Modify: `scrapers/accela_fast.py:21-37` (ACCELA_CITIES dict)
- Test: Manual test via CLI

**Step 1: Research Duncanville Accela URL**

First, verify the Duncanville Citizen Access Portal URL:

Run: `curl -sI "https://www.duncanvilletx.gov/residents/household_services/permit_and_inspection_services/permits_and_applications" | grep -i location`

The portal may redirect to an Accela-hosted URL like `aca-prod.accela.com/DUNCANVILLE` or similar.

**Step 2: Add Duncanville configuration to ACCELA_CITIES**

In `scrapers/accela_fast.py`, add this entry to `ACCELA_CITIES` dict:

```python
    'duncanville': {
        'name': 'Duncanville',
        # URL needs verification - typical Accela pattern
        'base_url': 'https://aca-prod.accela.com/DUNCANVILLE',
        'search_path': '/Cap/CapHome.aspx?module=Building&TabName=Building',
    },
```

Note: The exact URL path may differ. If the standard Accela pattern doesn't work, the city may use a self-hosted instance.

**Step 3: Test Duncanville scraper**

Run: `cd /home/reid/testhome/permit-scraper && python3 scrapers/accela_fast.py duncanville 10`

Expected: If URL is correct, should extract permits. If not, note actual URL from browser inspection.

**Step 4: Commit**

```bash
cd /home/reid/testhome/permit-scraper && git add scrapers/accela_fast.py && git commit -m "feat: add Duncanville to Accela scraper"
```

---

## Task 5: Fix McKinney and Allen Angular Timeouts

**Files:**
- Modify: `scrapers/citizen_self_service.py` (add wait logic)
- Test: Manual test via CLI

**Step 1: Identify the timeout issue**

McKinney and Allen use Angular-heavy EnerGov portals that timeout. The issue is typically:
1. Angular takes longer to render results
2. Bot detection (Cloudflare) delays responses

**Step 2: Add extended wait configuration for McKinney/Allen**

Modify the `mckinney` and `allen` entries in `CSS_CITIES` to include timeout settings:

```python
    'mckinney': {
        'name': 'McKinney',
        'base_url': 'https://egov.mckinneytexas.org/EnerGov_Prod/SelfService',
        'extended_wait': True,  # Flag for longer timeouts
        'wait_for_angular': True,
    },
    'allen': {
        'name': 'Allen',
        'base_url': 'https://energovweb.cityofallen.org/EnerGov/SelfService',
        'extended_wait': True,
        'wait_for_angular': True,
    },
```

**Step 3: Add Angular wait logic to scraper**

Find the page navigation/wait code and add conditional logic:

```python
# After navigating to search results page, before extracting:
city_config = CSS_CITIES.get(city_key, {})
if city_config.get('wait_for_angular'):
    # Wait for Angular to finish rendering
    await page.wait_for_function(
        '''() => {
            // Check if Angular is done loading
            const ng = window.getAllAngularTestabilities && window.getAllAngularTestabilities();
            if (!ng || ng.length === 0) return true;  // Not Angular
            return ng.every(t => t.isStable());
        }''',
        timeout=30000
    )
    await asyncio.sleep(2)  # Extra buffer for DOM updates
```

**Step 4: Test McKinney with extended waits**

Run: `cd /home/reid/testhome/permit-scraper && python3 scrapers/citizen_self_service.py mckinney 10`

Expected: Should complete without timeout errors. May take 30-60 seconds.

**Step 5: Test Allen with extended waits**

Run: `cd /home/reid/testhome/permit-scraper && python3 scrapers/citizen_self_service.py allen 10`

Expected: Should complete without timeout errors.

**Step 6: Commit fix**

```bash
cd /home/reid/testhome/permit-scraper && git add scrapers/citizen_self_service.py && git commit -m "fix: add Angular wait logic for McKinney and Allen scrapers"
```

---

## Task 6: Update TODO.md with New Cities

**Files:**
- Modify: `TODO.md`

**Step 1: Update working cities list**

Add the new cities to the appropriate sections in TODO.md.

**Step 2: Commit**

```bash
cd /home/reid/testhome/permit-scraper && git add TODO.md && git commit -m "docs: update TODO with new city coverage"
```

---

## Task 7: Verification - Run Full Test Suite

**Step 1: Run pytest**

Run: `cd /home/reid/testhome/permit-scraper && pytest -v`

Expected: All existing tests should pass.

**Step 2: Test each new city (quick 5-permit check)**

```bash
cd /home/reid/testhome/permit-scraper

# eTRAKiT
python3 scrapers/etrakit.py the_colony 5

# MyGov
python3 scrapers/mygov_multi.py university_park 5
python3 scrapers/mygov_multi.py forney 5

# EnerGov CSS
python3 scrapers/citizen_self_service.py hurst 5
python3 scrapers/citizen_self_service.py farmers_branch 5
python3 scrapers/citizen_self_service.py north_richland_hills 5
python3 scrapers/citizen_self_service.py coppell 5

# Accela
python3 scrapers/accela_fast.py duncanville 5

# Fixed cities
python3 scrapers/citizen_self_service.py mckinney 5
python3 scrapers/citizen_self_service.py allen 5
```

Expected: Most should return permits. Note any that fail for follow-up.

---

## Risk Summary

| City | Risk | Mitigation |
|------|------|------------|
| The Colony | Low | Standard eTRAKiT |
| University Park | Low | Standard MyGov |
| Forney | Medium | May require login - test first |
| Hurst | Medium | Standard EnerGov, may have WAF |
| Farmers Branch | Low | Standard EnerGov |
| Coppell | High | Newer Tyler Civic Access UI |
| North Richland Hills | Low | Standard EnerGov |
| Duncanville | Medium | URL needs verification |
| McKinney | Medium | Angular timeout fix |
| Allen | Medium | Angular timeout fix |

---

## Rollback Plan

If any city causes issues:
1. Comment out the problematic city config
2. Add `# BLOCKED: <reason>` comment
3. Commit with explanatory message

Example:
```python
    # BLOCKED: Requires contractor login for permit search
    # 'forney': {'name': 'Forney', 'slug': 'forney_tx', 'pop': 25000},
```
