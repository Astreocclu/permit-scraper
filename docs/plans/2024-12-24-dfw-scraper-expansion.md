# DFW Scraper Expansion Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Test and scrape 12 cities already configured in CITY_TASKS but missing raw data, then run full pipeline.

**Architecture:** All cities already have Browser-Use tasks in `permit_tasks.py`. Just need to run Browser-Use bulk mode and handle failures. Some cities are known blocked (Garland, Irving, Richardson).

**Tech Stack:** Browser-Use (DeepSeek), existing scraper infrastructure, PostgreSQL

---

## Cities to Test (Configured but No Data)

| City | Expected Platform | Known Status | CAD County |
|------|------------------|--------------|------------|
| Anna | SmartGov | Unknown | Collin ✅ |
| Arlington | Accela/Socrata | Should work | Tarrant ✅ |
| Azle | Unknown | Unknown | Tarrant ✅ |
| Cleburne | Unknown | Unknown | Johnson ❌ |
| Garland | MGO Connect | BLOCKED (no portal) | Dallas ✅ |
| Haltom City | Unknown | Unknown | Tarrant ✅ |
| Irving | MGO Connect | BLOCKED (PDF bug) | Dallas ✅ |
| Melissa | Unknown | Unknown | Collin ✅ |
| Richardson | Unknown | BLOCKED (403) | Dallas/Collin ✅ |
| Rockwall | Cityworks | Unknown | Rockwall ❌ |
| Saginaw | Unknown | Unknown | Tarrant ✅ |
| Wylie | Citizenserve | Unknown | Collin ✅ |

---

## Phase 1: Test Working Cities

### Task 1: Test Anna (SmartGov)

**Step 1: Run Browser-Use**

```bash
source venv/bin/activate
python3 -m services.browser_scraper.runner --city anna --mode bulk --start-date 2024-01-01 --end-date 2024-12-24
```

**Step 2: Check results**

```bash
ls -la data/raw/anna*.json
cat data/raw/anna_raw.json | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'{len(d)} permits')"
```

**Step 3: If fails, try SmartGov scraper directly**

```bash
python3 scrapers/smartgov_sachse.py anna 100
```

**Step 4: Document result**

---

### Task 2: Test Arlington (Socrata API)

Arlington has a Socrata API - should work with existing scraper.

**Step 1: Run Socrata scraper**

```bash
python3 scrapers/dfw_big4_socrata.py --city arlington --limit 500
```

**Step 2: Check results**

```bash
ls -la data/raw/arlington*.json
```

---

### Task 3: Test Wylie (Citizenserve)

**Step 1: Run Browser-Use**

```bash
python3 -m services.browser_scraper.runner --city wylie --mode bulk --start-date 2024-01-01 --end-date 2024-12-24
```

**Step 2: Check results**

```bash
ls -la data/raw/wylie*.json
```

**Step 3: If fails, check review queue**

```bash
python3 -m services.browser_scraper.review_cli --show wylie
```

---

### Task 4: Test Rockwall (Cityworks)

**Note:** No CAD enrichment available (Rockwall County)

**Step 1: Run Browser-Use**

```bash
python3 -m services.browser_scraper.runner --city rockwall --mode bulk --start-date 2024-01-01 --end-date 2024-12-24
```

**Step 2: Check results**

```bash
ls -la data/raw/rockwall*.json
```

---

### Task 5: Test Saginaw

**Step 1: Run Browser-Use**

```bash
python3 -m services.browser_scraper.runner --city saginaw --mode bulk --start-date 2024-01-01 --end-date 2024-12-24
```

---

### Task 6: Test Melissa

**Step 1: Run Browser-Use**

```bash
python3 -m services.browser_scraper.runner --city melissa --mode bulk --start-date 2024-01-01 --end-date 2024-12-24
```

---

### Task 7: Test Haltom City

**Step 1: Run Browser-Use**

```bash
python3 -m services.browser_scraper.runner --city haltom_city --mode bulk --start-date 2024-01-01 --end-date 2024-12-24
```

---

### Task 8: Test Azle

**Step 1: Run Browser-Use**

```bash
python3 -m services.browser_scraper.runner --city azle --mode bulk --start-date 2024-01-01 --end-date 2024-12-24
```

---

### Task 9: Test Cleburne

**Note:** No CAD enrichment (Johnson County)

**Step 1: Run Browser-Use**

```bash
python3 -m services.browser_scraper.runner --city cleburne --mode bulk --start-date 2024-01-01 --end-date 2024-12-24
```

---

## Phase 2: Attempt Blocked Cities

### Task 10: Retry Irving (MGO Connect)

Known issue: PDF export opens about:blank

**Step 1: Try Browser-Use with fresh approach**

```bash
python3 -m services.browser_scraper.runner --city irving --mode bulk --start-date 2024-10-01 --end-date 2024-12-24
```

**Step 2: Review failure context**

```bash
python3 -m services.browser_scraper.review_cli --show irving
```

**Step 3: Document blockers**

---

### Task 11: Retry Richardson

Known issue: 403 Forbidden

**Step 1: Try Browser-Use**

```bash
python3 -m services.browser_scraper.runner --city richardson --mode bulk --start-date 2024-10-01 --end-date 2024-12-24
```

---

### Task 12: Skip Garland

Garland has NO public permit portal - only 311 system. Mark as permanently blocked.

---

## Phase 3: Pipeline Integration

### Task 13: Load New Data to Database

**Step 1: Load all raw JSON**

```bash
python3 scripts/load_permits.py
```

**Step 2: Verify counts**

```bash
source .env && psql $DATABASE_URL -c "SELECT city, COUNT(*) FROM leads_permit WHERE city IN ('anna','arlington','wylie','rockwall','saginaw','melissa','haltom_city','azle','cleburne') GROUP BY city ORDER BY COUNT(*) DESC;"
```

---

### Task 14: CAD Enrichment

**Step 1: Run enrichment**

```bash
python3 scripts/enrich_cad.py
```

**Step 2: Verify (skip Rockwall, Cleburne - no CAD)**

```bash
source .env && psql $DATABASE_URL -c "SELECT p.city, COUNT(*) as permits, COUNT(pr.id) as enriched FROM leads_permit p LEFT JOIN leads_property pr ON p.id = pr.permit_id WHERE p.city IN ('anna','arlington','wylie','saginaw','melissa','haltom_city','azle') GROUP BY p.city;"
```

---

### Task 15: Score Leads

**Step 1: Run scoring**

```bash
python3 scripts/score_leads.py
```

**Step 2: Verify**

```bash
source .env && psql $DATABASE_URL -c "SELECT city, tier, COUNT(*) FROM clients_scoredlead WHERE city IN ('anna','arlington','wylie','rockwall','saginaw','melissa','haltom_city','azle','cleburne') GROUP BY city, tier ORDER BY city, tier;"
```

---

### Task 16: Update Documentation

**Step 1: Update SCRAPER_STATUS.md**

Add results for each city tested.

**Step 2: Commit all changes**

```bash
git add SCRAPER_STATUS.md data/raw/*.json
git commit -m "feat: expand DFW coverage - tested 12 new cities"
```

---

## Summary

| Phase | Cities | Expected Time |
|-------|--------|---------------|
| 1 (Working) | Anna, Arlington, Wylie, Rockwall, Saginaw, Melissa, Haltom City, Azle, Cleburne | 2-3 hours |
| 2 (Blocked) | Irving, Richardson, (skip Garland) | 1 hour |
| 3 (Pipeline) | Load, Enrich, Score | 1 hour |

**Total: ~4-5 hours for 12 cities**

**Expected Results:**
- 6-8 new working cities
- 3-4 blocked (already known)
- Full pipeline for working cities in CAD-covered counties
