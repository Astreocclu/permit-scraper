# City Prioritization Ranking for Permit Scraping

**Created:** 2025-12-18
**Confidence:** Claude 95% | Gemini 95%
**Status:** REVISED - Updated with Dec 17 browser-use results

---

## Executive Summary

This plan ranks DFW cities for permit scraper development based on:
1. **Scraper status** (prioritize cities WITHOUT working scrapers)
2. **Quality/income/development potential**
3. **Population**

**CORRECTION:** MyGov platform IS WORKING - browser-use was testing wrong URLs.
- WRONG: `mansfield.tx.mygov.us` (redirects to marketing)
- RIGHT: `public.mygov.us/mansfield_tx/module?module=pi` (working permit portal)

---

## Priority Tier 1: MyGov CITIES - ❌ TESTED & BLOCKED (Dec 18)

**Browser-use tested all 4 cities - NONE have working public permit search.**

| Rank | City | Population | URL Tested | Result |
|------|------|-----------|------------|--------|
| 1 | **Mansfield** | 75,000 | `public.mygov.us/mansfield_tx/module?module=pi` | ❌ Search returns 0 results, no Reports module |
| 2 | **Little Elm** | 55,000 | `public.mygov.us/little_elm_tx/module?module=pi` | ⚠️ Found "All Issued Permits" report but navigation broken |
| 3 | **Celina** | 30,000 | `public.mygov.us/celina_tx/module?module=pi` | ❌ Redirects to homepage, module=pi disabled |
| 4 | **Fate** | 25,000 | `public.mygov.us/fate_tx/module?module=pi` | ❌ Reports only shows contractor registration |

**Conclusion:** The `module?module=pi` URL pattern does NOT provide public permit search for these cities.

**Little Elm potential:** Has pre-generated PDF report "All Issued Permits - Commercial, Residential, and Pools (Within One Month)" - could manually download like Grapevine.

---

## Priority Tier 2: PARTIAL IMPLEMENTATION

Existing code that needs completion.

| Rank | City | Population | Platform | Status | Work Needed |
|------|------|-----------|----------|--------|-------------|
| 5 | **Irving** | 240,000 | MGO Connect | ⚠️ Partial | Finish PDF extraction in `mgo_connect.py` |

**Irving Details:**
- Scraper exists: `scrapers/mgo_connect.py`
- Login works, downloads PDFs
- Missing: PDF parsing to extract permit data
- CAD enrichment: Dallas County (working)

---

## Priority Tier 3: NEEDS RESEARCH (Unknown Platform)

High-population cities with unknown permit portals.

| Rank | City | Population | Platform | CAD County | Status |
|------|------|-----------|----------|------------|--------|
| 6 | **Garland** | 240,000 | Unknown | Dallas | Jurisdiction not in dropdown (Dec 17) |
| 7 | **Richardson** | 120,000 | Unknown | Dallas/Collin | Not yet tested |
| 8 | **Lewisville** | 110,000 | MGO Connect | Denton | ⚠️ Works but 0 permits returned (Dec 18) |
| 9 | **Euless** | 60,000 | Unknown | Tarrant | ❌ Access Denied + CAPTCHA (Dec 18) |

**Combined population: 530,000** (only 360K realistically accessible)

### MOVED TO WORKING (Dec 17):
- **Grapevine** (55K) - MyGov PDF export, 126 permits loaded via `parse_grapevine_pdf.py`

### MOVED TO LIMITED (Dec 17):
- **Bedford** (50K) - OpenGov with keyword-only search, no date filtering

---

## Priority Tier 4: SCRAPABLE - IMPLEMENT

Platform known and scrapable.

| Rank | City | Population | Platform | CAD Status |
|------|------|-----------|----------|------------|
| 12 | **Weatherford** | 35,000 | GovBuilt | Parker County (no API - permits only) |

**Weatherford Details:**
- URL: https://permits.weatherfordtx.gov/
- Platform is modern, scrapable
- CAD enrichment can be added later when Parker County API found

---

## BLOCKED - Login Required (Confirmed Dec 17)

| City | Population | Platform | Status | Notes |
|------|-----------|----------|--------|-------|
| Forney | 35,000 | MyGov Collaborator | ❌ LOGIN REQUIRED | All public URLs redirect to marketing pages |

**Browser-use confirmed:** Forney uses MyGov Collaborator Portal which requires authentication. Cannot scrape without credentials.

---

## Cities ALREADY WORKING (Not Targets)

These have functioning scrapers - do NOT prioritize.

| City | Population | Platform | Scraper |
|------|-----------|----------|---------|
| Dallas | 1,300,000 | Accela | `accela_fast.py` |
| Fort Worth | 950,000 | Accela | `accela_fast.py` |
| Arlington | 400,000 | Socrata | `dfw_big4_socrata.py` |
| Plano | 285,000 | eTRAKiT | `etrakit.py` |
| Frisco | 200,000 | eTRAKiT | `etrakit_fast.py` |
| McKinney | 195,000 | EnerGov | `citizen_self_service.py` |
| Grand Prairie | 195,000 | Accela | `accela_fast.py` |
| Denton | 160,000 | eTRAKiT | `etrakit_fast.py` |
| Mesquite | 145,000 | Accela | `accela_fast.py` |
| Carrollton | 135,000 | CityView | `cityview.py` |
| Allen | 105,000 | EnerGov | `citizen_self_service.py` |
| Flower Mound | 75,000 | eTRAKiT | `etrakit_fast.py` |
| Waxahachie | 45,000 | EnerGov | `citizen_self_service.py` |
| Coppell | 42,000 | EnerGov | `citizen_self_service.py` |
| Hurst | 40,000 | EnerGov | `citizen_self_service.py` |
| Southlake | 32,000 | EnerGov | `citizen_self_service.py` |
| Sachse | 30,000 | SmartGov | `smartgov_sachse.py` |
| Grapevine | 55,000 | MyGov | `parse_grapevine_pdf.py` |
| Colleyville | 27,000 | EnerGov | `citizen_self_service.py` |
| Trophy Club | 12,000 | EnerGov | `citizen_self_service.py` |
| Westlake | 1,500 | MyGov | `mygov_westlake.py` |

---

## Recommended Action Plan

### ~~IMMEDIATE: Browser-Use MyGov Sprint~~ ❌ COMPLETED - ALL BLOCKED

All 4 MyGov cities tested Dec 18 - none have working public permit search:
- Mansfield: Zero results from search
- Celina: module=pi redirects to homepage
- Fate: Only contractor reports available
- **Little Elm: Has PDF report - try manual download like Grapevine**

### NEXT: Unknown Platform Research + Browser-Use
For each unknown city, browser-use can discover and scrape:
1. Garland (240K) - Jurisdiction not in dropdown, needs alternative research
2. Richardson (120K) - Not yet tested

**COMPLETED (Dec 17-18):**
- ✅ Grapevine (55K) - 126 permits loaded
- ⚠️ Bedford (50K) - LIMITED (keyword-only search)
- ✅ Weatherford (35K) - 203 permits found, PUBLIC access
- ❌ Forney (35K) - LOGIN REQUIRED
- ⚠️ Lewisville (110K) - MGO Connect works but returned 0 permits for Nov-Dec 2025
- ❌ Euless (60K) - "Access Denied" on all URLs, CAPTCHA blocking

### PARALLEL: Irving PDF Completion
- Fix `mgo_connect.py` PDF extraction while browser-use handles MyGov

---

## Success Criteria

**Goal: DOUBLE current coverage using browser-use**

Current working: 21 cities (~4.6M population) - includes Grapevine added Dec 17
Target: 40+ cities

- [x] ~~4 MyGov cities online~~ = ❌ ALL BLOCKED (tested Dec 18) - Little Elm has PDF potential
- [x] ~~4 Unknown platform cities~~ = Lewisville ⚠️ (0 permits), Euless ❌ (blocked), Garland/Richardson pending
- [x] ~~Weatherford online~~ = +35K pop (CONFIRMED SCRAPABLE Dec 17)
- [x] ~~Grapevine online~~ = +55K pop (DONE Dec 17 - 126 permits)
- [ ] Irving PDF extraction complete = +240K pop
- [x] ~~Forney platform identified~~ = LOGIN REQUIRED (Dec 17)

**Remaining new coverage potential: ~955K population**
**Already added Dec 17: Grapevine (55K)**

---

## Data Sources

- `SCRAPER_STATUS.md` - Current scraper status
- `permit.md` - Strategic market analysis
- `123456.txt` - Session logs showing platform failures
- `CLAUDE.md` - Project documentation

---

## Appendix: Platform Summary

| Platform | Status | Cities |
|----------|--------|--------|
| Accela | ✅ Working | Dallas, Fort Worth, Grand Prairie, Mesquite |
| eTRAKiT | ✅ Working | Frisco, Flower Mound, Denton, Plano |
| EnerGov CSS | ✅ Working | 10+ cities |
| CityView | ✅ Working | Carrollton |
| Socrata | ✅ Working | Arlington |
| SmartGov | ✅ Working | Sachse |
| MGO Connect | ⚠️ Partial | Irving (needs PDF work) |
| GovBuilt | 🔬 Scrapable | Weatherford (PUBLIC, no CAD) |
| MyGov | ✅/❌ Mixed | Grapevine ✅ (PDF), Westlake ✅, Forney ❌ (login), Mansfield ❌, Little Elm ⚠️ (PDF?), Celina ❌, Fate ❌ |
| OpenGov | ⚠️ Limited | Bedford (keyword-only search) |
| MGO Connect | ⚠️ Limited | Lewisville (0 permits returned) |
| Unknown | ❓ Research | Garland, Richardson |
| Blocked | ❌ Access Denied | Euless (CAPTCHA) |
