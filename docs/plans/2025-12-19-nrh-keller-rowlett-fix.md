# NRH, Keller, and Rowlett Scraper Fix Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix three failed scrapers (NRH, Keller, Rowlett) that each failed for different reasons during the 12/19 batch run.

**Architecture:** Each city uses a different portal type, so fixes are independent:
- NRH: EnerGov CSS with newer Angular selectors
- Keller: Wrong URL - need to find actual EnerGov CSS instance
- Rowlett: MyGov accordion stall - rate limiting or lazy load issues

**Tech Stack:** Python 3, Playwright, Stealth mode, existing scraper framework

---

## Failure Analysis

| City | Portal | Error | Root Cause |
|------|--------|-------|------------|
| NRH | EnerGov CSS | Timeout on `input[type="text"]` | Newer EnerGov 2024 uses different selectors |
| Keller | EnerGov CSS | 403 Forbidden | URL `https://www.cityofkeller.com/css` is wrong |
| Rowlett | MyGov | Stalled indefinitely | Accordion expansion timeout/rate limit |

---

## Task 1: Fix Keller URL Configuration

**Files:**
- Modify: `scrapers/citizen_self_service.py:122-126`

**Step 1: Research correct Keller EnerGov URL**

Keller migrated from eTRAKiT to EnerGov CSS. The current URL `https://www.cityofkeller.com/css` is a redirect/proxy that returns 403.

Check these candidate URLs:
- `https://energovweb.cityofkeller.com/EnerGov_Prod/SelfService`
- `https://kellertx-energovweb.tylerhost.net/apps/selfservice`
- `https://css.kellertx.gov/EnerGov_Prod/SelfService`

Use WebFetch to find which one works and has permit search.

**Step 2: Update configuration**

Once correct URL is found, update `citizen_self_service.py`:

```python
'keller': {
    'name': 'Keller',
    'base_url': '<CORRECT_URL>',
    # Note: Keller migrated from eTRAKiT to EnerGov CSS (Dec 2024)
},
```

**Step 3: Test scraper**

Run: `python3 scrapers/citizen_self_service.py keller 100`
Expected: Should navigate to portal and start extracting permits

**Step 4: Commit**

```bash
git add scrapers/citizen_self_service.py
git commit -m "fix(keller): update EnerGov CSS URL for migrated portal"
```

---

## Task 2: Fix NRH EnerGov CSS Selectors

**Files:**
- Modify: `scrapers/citizen_self_service.py:370-376`

**Problem:** NRH uses EnerGov version 2024.4.3.19 with newer Angular/Okta integration. The scraper waits for `input[type="text"]` but the newer portal may:
- Use a different search input selector
- Require waiting for Okta auth redirect to complete
- Have lazy-loaded search module

**Step 1: Debug portal load sequence**

Add diagnostic screenshot at each stage:
1. After initial navigation
2. After waiting for Angular hydration
3. After any Okta redirect completes

Save to `debug_html/nrh_*.png` for analysis.

**Step 2: Identify correct selector**

Visit `https://selfservice.nrhtx.com/energov_prod/selfservice#/search` manually or via WebFetch to identify:
- Actual search input ID/class
- Module selector dropdown
- Any auth/splash screens

**Step 3: Add NRH-specific selector handling**

If NRH needs different selectors, add to config:

```python
'north_richland_hills': {
    'name': 'North Richland Hills',
    'base_url': 'https://selfservice.nrhtx.com/energov_prod/selfservice',
    'selector_variant': 'energov_2024',  # Flag for newer selectors
},
```

Then add conditional logic in scraper:

```python
if city_config.get('selector_variant') == 'energov_2024':
    # Wait for newer EnerGov selectors
    await page.wait_for_selector('#SearchModule, [data-testid="search-input"], input.search-input', timeout=30000)
else:
    # Default selector
    await page.wait_for_selector('input[type="text"]', timeout=15000)
```

**Step 4: Test scraper**

Run: `python3 scrapers/citizen_self_service.py north_richland_hills 100`
Expected: Should wait for correct selector and proceed with search

**Step 5: Commit**

```bash
git add scrapers/citizen_self_service.py
git commit -m "fix(nrh): add selector variant for EnerGov 2024 portals"
```

---

## Task 3: Fix Rowlett MyGov Stall

**Files:**
- Modify: `scrapers/mygov_multi.py:71-156`

**Problem:** The MyGov scraper stalls when expanding address accordions. This is likely caused by:
1. **Rate limiting** - Too many requests too fast
2. **Lazy loading timeout** - Accordion content loads slowly
3. **DOM mutation wait** - Click doesn't trigger expansion

**Step 1: Add accordion expansion timeout**

The current code has no timeout on accordion expansion. Add explicit timeout:

```python
async def search_address(page, city_slug: str, search_term: str, timeout_per_accordion: int = 5000) -> list:
    # ... existing code ...

    for accordion in accordions[:20]:
        try:
            await accordion.scroll_into_view_if_needed()

            # Add timeout wrapper for accordion click and expansion
            try:
                async with asyncio.timeout(timeout_per_accordion / 1000):
                    await accordion.click()
                    await asyncio.sleep(0.8)
                    # ... rest of expansion logic ...
            except asyncio.TimeoutError:
                logger.warning(f"Accordion expansion timeout for '{search_term}'")
                continue
```

**Step 2: Add rate limiting between searches**

Add delay between search terms to avoid rate limiting:

```python
for term in SEARCH_TERMS:
    if len(all_permits) >= target_count:
        break

    logger.info(f"Searching '{term}'...")
    permits = await search_address(page, city['slug'], term)

    # Rate limit: wait 2s between searches
    await asyncio.sleep(2)
```

**Step 3: Add global scrape timeout**

Add overall timeout to prevent infinite stalls:

```python
async def scrape_city(city_key: str, target_count: int, max_runtime: int = 300) -> list:
    start_time = datetime.now()

    # ... existing code ...

    for term in SEARCH_TERMS:
        # Check runtime limit
        elapsed = (datetime.now() - start_time).total_seconds()
        if elapsed > max_runtime:
            logger.warning(f"Max runtime ({max_runtime}s) exceeded, stopping")
            break
```

**Step 4: Test scraper**

Run: `python3 scrapers/mygov_multi.py rowlett 100`
Expected: Should complete within 5 minutes with graceful timeout handling

**Step 5: Commit**

```bash
git add scrapers/mygov_multi.py
git commit -m "fix(mygov): add timeouts and rate limiting to prevent stalls"
```

---

## Task 4: Verify All Fixes Work Together

**Step 1: Run all three scrapers**

```bash
# Run sequentially to verify each works
python3 scrapers/citizen_self_service.py keller 100
python3 scrapers/citizen_self_service.py north_richland_hills 100
python3 scrapers/mygov_multi.py rowlett 100
```

**Step 2: Check output files**

Verify each created non-empty JSON:
- `data/raw/keller_raw.json` - should have permits
- `data/raw/north_richland_hills_raw.json` - should have permits
- `data/raw/rowlett_raw.json` - should have permits

**Step 3: Load to database**

```bash
python3 scripts/load_permits.py
```

**Step 4: Commit final verification**

```bash
git add data/raw/*.json
git commit -m "feat: verify NRH, Keller, Rowlett scrapers working"
```

---

## Task 5: Document Findings

**Files:**
- Create: `docs/plans/2025-12-19-research-findings.md` (update existing)

**Step 1: Update research findings document**

Add section documenting:
- Keller: Final working URL and migration notes
- NRH: EnerGov 2024 variant details
- Rowlett: Rate limiting findings

**Step 2: Update CLAUDE.md if needed**

If any scraper required significant changes, update the city listing in CLAUDE.md.

---

## Success Criteria

| City | Target | Minimum Acceptable |
|------|--------|-------------------|
| Keller | 500+ permits | 100+ permits |
| NRH | 500+ permits | 100+ permits |
| Rowlett | 200+ permits | 50+ permits |

All three cities should produce permit data that can be loaded to the database.
