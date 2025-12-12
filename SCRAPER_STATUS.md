# Permit Scraper Status Summary
**Last Updated**: December 12, 2025
**Archive**: See `_archive/` for historical session logs.

## Working Scrapers

| City | Scraper | Command | Notes |
|------|---------|---------|-------|
| **Dallas** | `accela_fast.py` | `python3 scrapers/accela_fast.py dallas 1000` | ⚡ Fast DOM extraction (no LLM) - VERIFIED 12/09/25 |
| **Fort Worth** | `accela_fast.py` | `python3 scrapers/accela_fast.py fort_worth 1000` | ⚡ Fast DOM extraction (migrated from LLM) |
| **Frisco** | `etrakit_fast.py` | `python3 scrapers/etrakit_fast.py frisco 1000` | ⚡ Fast DOM extraction, no LLM |
| **Arlington** | `dfw_big4_socrata.py` | `python3 scrapers/dfw_big4_socrata.py` | API-based, bulk CSV |
| **Grand Prairie** | `accela_fast.py` | `python3 scrapers/accela_fast.py grand_prairie 1000` | ⚡ Fast DOM extraction |
| **Plano** | `etrakit.py` | `python3 scrapers/etrakit.py plano 1000` | Working (Public Login) |
| **Flower Mound** | `etrakit_fast.py` | `python3 scrapers/etrakit_fast.py flower_mound 1000` | ⚡ Fast DOM extraction (eTRAKiT) |
| **Carrollton** | `cityview.py` | `python3 scrapers/cityview.py carrollton 500` | CityView portal (limits to ~20 results per search) |

## Data Inventory (Verified 12/09/25)

| File | Rows | Description |
|------|------|-------------|
| `dallas_leads.csv` | 988 | Enriched & scored Dallas leads |
| `dfw_big4_contractor_leads.csv` | 19,478 | Raw Arlington/Socrata data |
| `arlington_filtered.csv` | 8,009 | Filtered Arlington permits |
| `frisco_raw.json` | ~1000 | Raw Frisco permits |
| `fort_worth_raw.json` | 1000 | Raw Fort Worth permits |
| `plano_raw.json` | 54 | Raw Plano permits |

---

## DFW Metro - All 30 Municipalities

| # | City | Pop (est) | Platform | Scraper | Status |
|---|------|-----------|----------|---------|--------|
| 1 | **Dallas** | 1.3M | Accela | `accela_fast.py` | ✅ Working (Fast DOM) |
| 2 | **Fort Worth** | 950K | Accela | `accela_fast.py` | ✅ Working (Fast DOM) |
| 3 | **Arlington** | 400K | Socrata API | `dfw_big4_socrata.py` | ✅ Working |
| 4 | **Plano** | 290K | eTRAKiT | `etrakit.py` | ✅ Working |
| 5 | **Frisco** | 220K | eTRAKiT | `etrakit_fast.py` | ✅ Working (Fast DOM) |
| 6 | **Grand Prairie** | 200K | Accela | `accela_fast.py` | ✅ Working (Fast DOM) |
| 7 | **Irving** | 250K | MGO Connect | `mgo_connect.py` | ⚠️ Partial (login works, extraction I/O error) |
| 8 | **McKinney** | 200K | EnerGov CSS | `citizen_self_service.py` | ❌ Angular timeouts |
| 9 | **Garland** | 240K | None | — | ❌ No unified portal |
| 10 | **Denton** | 150K | MGO Connect | `mgo_connect.py` | ❌ Anti-bot blocked |
| 11 | **Lewisville** | 115K | MGO Connect | `mgo_connect.py` | ❌ Anti-bot blocked |
| 12 | **Carrollton** | 140K | CityView | `cityview.py` | ✅ Working |
| 13 | **Richardson** | 120K | Custom (cor.net) | — | ❌ Not Accela (404) |
| 14 | **Allen** | 110K | EnerGov CSS | `citizen_self_service.py` | ❌ Angular timeouts |
| 15 | **Flower Mound** | 80K | eTRAKiT | `etrakit_fast.py` | ✅ Working |
| 16 | **Cedar Hill** | 50K | MGO Connect | `mgo_connect.py` | ❌ Anti-bot blocked |
| 17 | **Mesquite** | 150K | EnerGov CSS | `energov.py` | ❌ Angular timeouts (tested 12/09) |
| 18 | **Southlake** | 32K | EnerGov CSS | `citizen_self_service.py` | ✅ Working (140K permits, residential filter added 12/12) |
| 19 | **Colleyville** | 27K | EnerGov CSS | `citizen_self_service.py` | ✅ Working (5,817 permits available) |
| 20 | **Rowlett** | 68K | MyGov | — | ❌ Requires contractor login |
| 21 | **Westlake** | 4K | MyGov | `mygov_westlake.py` | ✅ Working (367 addresses harvested via API 12/12) |
| 22 | **Grapevine** | 55K | MyGov (.exe) | — | ❌ Requires desktop client |
| 23 | **Duncanville** | 40K | MGO Connect | `mgo_connect.py` | ❌ Anti-bot blocked |
| 24 | **Keller** | 50K | EnerGov CSS | — | 🔍 Migrated from eTRAKiT |
| 25 | **DeSoto** | 55K | Unknown | — | 🔍 Not researched |
| 26 | **Lancaster** | 42K | MyGov | `mygov.py` | 🔍 Not tested |
| 27 | **Euless** | 58K | Unknown | — | 🔍 Not researched |
| 28 | **Bedford** | 50K | Unknown | — | 🔍 Not researched |
| 29 | **Hurst** | 40K | Unknown | — | 🔍 Not researched |
| 30 | **Coppell** | 45K | Unknown | — | 🔍 Not researched |
| 31 | **Watauga** | 25K | MyGov | `mygov.py` | 🔍 Not tested |
| 32 | **The Colony** | 45K | Unknown | — | 🔍 Not researched |

### Legend
- ✅ **Working** - Scraper runs, data extracted
- ❌ **Blocked** - Technical barrier (anti-bot, timeouts, broken)
- ⚠️ **Partial** - Works but limited/old data
- 🔍 **Not researched** - Need to identify portal platform
- 🔻 **TBD** - Low priority / difficult access (Grapevine requires .exe)

---

## Platform Summary

| Platform | Working | Partial | Blocked | Not Scrapeable |
|----------|---------|---------|---------|----------------|
| Accela | 4 | 0 | 0 | 0 |
| eTRAKiT | 3 | 0 | 0 | 0 |
| CityView | 1 | 0 | 0 | 0 |
| Socrata API | 1 | 0 | 0 | 0 |
| MGO Connect | 0 | 1 | 4 | 0 |
| EnerGov CSS | 2 | 0 | 2 | 0 |
| MyGov | 1 | 0 | 0 | 2 |
| None | 0 | 0 | 0 | 1 |
| Unknown | 0 | 0 | 0 | 9 |

**Total: 12 working / 1 partial / 6 blocked / 13 not scrapeable or not researched**

---

## Quick Reference

- **Credentials**: Stored in `.env` file
- **Raw Output**: `{city}_raw.json` in repo root
- **Processed Output**: `{city}_leads.csv` or `exports/` directory
- **Debug**: Screenshots saved to `debug_html/`

## Scraper File Inventory

| File | Type | Description |
|------|------|-------------|
| `scrapers/accela_fast.py` | ⚡ Production | Fast DOM extraction for Accela portals (Dallas, Fort Worth, Grand Prairie) |
| `scrapers/etrakit_fast.py` | ⚡ Production | Fast DOM extraction for eTRAKiT (Frisco, Flower Mound) - GOLD STANDARD |
| `scrapers/cityview.py` | Production | CityView portal scraper (Carrollton) |
| `scrapers/dfw_big4_socrata.py` | ⚡ Production | API-based bulk extraction (Arlington) |
| `scrapers/etrakit.py` | Production | eTRAKiT with login support (Plano) |
| `scrapers/accela.py` | Legacy | LLM-based Accela scraper (slow, expensive) - DEPRECATED |
| `scrapers/mgo_connect.py` | ❌ Blocked | MGO Connect scraper - anti-bot detection |
| `scrapers/citizen_self_service.py` | ⚡ Production | EnerGov CSS scraper (Southlake, Colleyville) - Fixed 12/11/25 |
| `scrapers/energov.py` | ❌ Broken | EnerGov scraper - Angular timeouts (same as citizen_self_service) |
| `scrapers/mygov.py` | ❌ Broken | MyGov scraper - URLs 404 |
| `scrapers/mygov_westlake.py` | ⚡ Production | Address-based MyGov scraper for Westlake (367 harvested addresses) |
| `scrapers/westlake_harvester.py` | ⚡ Production | API-based address harvester for Westlake MyGov |
| `scrapers/filters.py` | Utility | Residential permit post-processing filter |
| `scrapers/southlake_residential_batch.py` | Production | Batch scraper for Southlake residential permit types |
| `scrapers/deepseek.py` | Utility | LLM structured extraction helper |
| `scrapers/mgo_test.py` | Debug | MGO Connect debugging tool |

## Session Notes - December 12, 2025

### Scraper Hardening (Evening Session)

**Branch:** `fix/scraper-hardening`

**MGO Connect Anti-Bot Fix:**
- Added phased fallback strategy: headless → headed → fail gracefully
- Integrated `playwright-stealth` (graceful fallback if not installed)
- New functions: `run_scraper_session()`, `scrape_orchestrator()`, `save_results()`
- **Status:** Ready for testing against Irving/Denton/Lewisville
- **Command:** `python3 scrapers/mgo_connect.py Irving 10`

**EnerGov Diagnosis Script:**
- Created `scripts/diagnose_energov.py` to capture HTML/screenshots from McKinney/Allen
- Also captures Southlake/Colleyville for comparison
- Analyzes selectors, detects Cloudflare/anti-bot mechanisms
- **Status:** Diagnosis needed before implementing fixes (30% confidence)
- **Command:** `python3 scripts/diagnose_energov.py`
- **Output:** `debug_html/energov_{city}_diag.{png,html}`

**Westlake Recursive Harvester:**
- Replaced hardcoded street list with recursive A-Z prefix discovery
- Added urllib3 Retry with exponential backoff (1s, 2s, 4s, 8s, 16s)
- Checkpointing for resumability (saves after each top-level prefix)
- Drills down when results hit 50-limit (up to depth 3)
- **Status:** Ready for full harvest
- **Command:** `python3 scrapers/westlake_harvester.py`

**Tests Added:**
- `tests/test_mgo_connect.py` - 3 tests for phased fallback
- `tests/test_westlake_harvester.py` - 5 tests for recursive search, retry, checkpointing
- **All 8 tests passing**

---

### Residential Permit Filtering & Westlake Harvester

**Southlake Residential Filter:**
- Created `scrapers/filters.py` with `filter_residential_permits()` function (TDD: 4 tests)
- Added `--permit-type` arg to CSS scraper for portal-level filtering
- Created `southlake_residential_batch.py` for iterating through 14+ residential permit types
- **Result:** 90 residential permits from 8 types (pool, remodel, addition, reroof, etc.)

**Westlake Address Harvester:**
- Discovered MyGov API endpoint: `POST https://public.mygov.us/westlake_tx/getLookupResults`
- Created `scrapers/westlake_harvester.py` to harvest addresses from API (TDD: 6 tests)
- **Result:** 367 addresses harvested from 16 residential streets (Cedar Elm, Vaquero, etc.)
- Updated `mygov_westlake.py` to use harvested addresses instead of guessing

**Lead Scoring Tier U System:**
- Fixed missing date bug in `score_leads.py` - now uses `days_old = -1` sentinel
- Added Tier U (Unverified) for leads with unknown freshness
- **Result:** 1,243 leads now properly marked as Tier U instead of incorrectly scored

---

## Session Notes - December 11, 2025

### High-Value Cities Investigation

**Southlake (EnerGov CSS)** - ✅ FIXED
- **Status**: WORKING
- **Permits Available**: 140,390
- **Test Results**: Successfully scraped 10 permits
- **Fix Applied**: Added explicit wait for results table, relaxed permit ID regex to handle format variations
- **Command**: `python3 scrapers/citizen_self_service.py southlake 10`
- **Notes**: Previously marked as broken due to Angular timeouts. Now working reliably with proper waits.

**Colleyville (EnerGov CSS)** - ✅ NEW
- **Status**: WORKING
- **Permits Available**: 5,817
- **Test Results**: Successfully scraped 10 permits
- **Configuration**: Added to CSS_CITIES with URL https://selfservice.colleyville.com/energov_prod/selfservice
- **Command**: `python3 scrapers/citizen_self_service.py colleyville 10`
- **Notes**: Uses same platform as Southlake. Working with same fixes.

**Irving (MGO Connect)** - ⚠️ BLOCKED - PDF Only
- **Status**: Portal only exports to PDF format. No HTML tables or API data available.
- **Portal**: https://irving.mgoconnect.com/
- **Auth**: Requires login (MGO_EMAIL, MGO_PASSWORD in .env)
- **Current State**:
  - `scrapers/irving_pdf_sampler.py` - Downloads sample PDF for analysis (created 12/11/25)
  - `scrapers/mgo_connect.py` - Has login/navigation, PDF parsing NOT implemented
- **Next Steps**:
  1. Run `python scrapers/irving_pdf_sampler.py` to get sample PDF
  2. Analyze PDF structure (text vs image, table layout)
  3. If text-based: implement pdfplumber parser
  4. If image-based: requires OCR (pytesseract) - more complex
- **Sample Location**: `data/samples/irving_sample_*.pdf`

**Westlake (MyGov)** - 🔍 SCRAPEABLE (Different Approach Required)
- **Status**: Public access confirmed, requires address-based scraping
- **Public URL**: https://public.mygov.us/westlake_tx/lookup
- **Access Method**: No login required - public address lookup
- **Limitation**: Must search by address (not by permit number or date range)
- **Test Result**: Found 3 permits at test address "1301 Solana Blvd"
- **Next Step**: Need comprehensive address list to scrape systematically
- **Scraper Created**: `scrapers/mygov_westlake.py` (proof of concept)

### Impact Summary
- **New Working Cities**: +2 (Southlake, Colleyville) = 146,207 permits accessible
- **EnerGov CSS Platform**: Breakthrough - 2 working, 2 still blocked (McKinney, Allen)
- **MGO Connect Platform**: Progress on Irving but not fully resolved
- **MyGov Platform**: New approach identified (address-based vs. permit-based)

---

## Next Steps

1. ~~**Optimize Fort Worth**~~ ✅ DONE - Migrated to `accela_fast.py`
2. ~~**Research unknown cities**~~ ✅ DONE - Flower Mound (eTRAKiT), Carrollton (CityView), Garland (no portal)
3. ~~**EnerGov CSS - Southlake/Colleyville**~~ ✅ DONE - Fixed with explicit waits (12/11/25)
4. **MGO Connect - Irving I/O Error** - Debug playwright I/O blocking error in data extraction
5. **EnerGov CSS - McKinney/Allen** - Apply Southlake fixes to remaining EnerGov cities
6. **Westlake Address List** - Obtain comprehensive address list for MyGov address-based scraping
7. **MGO Decision** - Lewisville/Denton still blocked by anti-automation (consider playwright-stealth + proxies)
8. ~~**Grapevine/Rowlett**~~ ❌ CLOSED - MyGov requires login/desktop client, not scrapeable
