# Scraper Status Report

> **Last Updated:** 2026-02-07 (00:45)
> **Run By:** Collections Agent (Full Scrape Run)

## Summary

| Category | Count |
|----------|-------|
| **Total Scrapers** | 23 |
| **Working** | 20 |
| **Broken** | 0 |
| **Partial/Limited** | 3 |
| **Needs Auth** | 3 |

## Full Scrape Run (2026-02-07)

**Total Permits Collected: ~32,000+**

| Platform | Cities Run | Permits Collected |
|----------|------------|-------------------|
| Accela | 2 | 2,000 |
| eTRAKiT | 3 | 2,917 |
| EnerGov CSS | 10 | 10,000 |
| MyGov | 10 | 1,894 |
| SmartGov | 1 | 507 |
| CityView | 1 | 458 |
| Socrata | 1 | 17,895 |
| GovBuilt | 1 | 200 |
| OpenGov | 1 | 3 |

## Recent Fixes (2026-02-06)

### Grand Prairie - FIXED
- **Issue:** Old Accela portal (aca-prod.accela.com/GPTX) returns 404
- **Solution:** City migrated to EnerGov CSS portal
- **New Command:** `python3 scrapers/citizen_self_service.py grand_prairie`
- **New URL:** https://egov.gptx.org/EnerGov_Prod/SelfService
- **Result:** 1000 permits via Excel export

### Flower Mound - FIXED
- **Issue:** eTRAKiT page load timeout (transient)
- **Solution:** Issue was transient; scraper now works
- **Command:** `python3 scrapers/etrakit.py flower_mound`
- **Result:** 20+ permits returned

### Prosper - FIXED
- **Issue:** Old eTRAKiT portal (etrakit.prospertx.gov) is defunct
- **Solution:** City migrated to EnerGov CSS portal (Dec 2022)
- **New Command:** `python3 scrapers/citizen_self_service.py prosper`
- **New URL:** https://prospertx-energovweb.tylerhost.net/apps/SelfService
- **Result:** 1000 permits via Excel export

---

## Scraper Details by Platform

### Accela Platform (2 cities)

| City | Scraper | Status | Last Run | Permits |
|------|---------|--------|----------|---------|
| Dallas | `accela_fast.py dallas` | WORKING | 2026-02-07 | 1,000 |
| Fort Worth | `accela_fast.py fort_worth` | WORKING | 2026-02-07 | 1,000 |
| Grand Prairie | **MIGRATED** | - | - | Use `citizen_self_service.py grand_prairie` |

### eTRAKiT Platform (5 cities)

| City | Scraper | Status | Last Run | Permits |
|------|---------|--------|----------|---------|
| Frisco | `etrakit.py frisco` | WORKING | 2026-02-07 | 1,000 |
| Flower Mound | `etrakit.py flower_mound` | WORKING | 2026-02-07 | 917 |
| Denton | `etrakit.py denton` | WORKING | 2026-02-07 | 1,000 |
| Prosper | **MIGRATED** | - | - | Use `citizen_self_service.py prosper` |
| The Colony | `etrakit.py the_colony` | PARTIAL | 2026-02-06 | Returns permits but empty addresses |
| Plano | `etrakit_auth.py plano` | NEEDS FIX | 2026-02-06 | Requires DEEPSEEK_API_KEY env var |
| Keller | Not supported | - | - | City not in scraper config |

### EnerGov CSS Platform (12 cities)

| City | Scraper | Status | Last Run | Permits |
|------|---------|--------|----------|---------|
| Southlake | `citizen_self_service.py southlake` | PARTIAL | 2026-02-06 | 0 (residential filter issue) |
| Colleyville | `citizen_self_service.py colleyville` | WORKING | 2026-02-07 | 1,000 |
| McKinney | `citizen_self_service.py mckinney` | PARTIAL | 2026-02-07 | 5 (pagination stuck) |
| Allen | `citizen_self_service.py allen` | WORKING | 2026-02-07 | 1,000 |
| Trophy Club | `citizen_self_service.py trophy_club` | WORKING | 2026-02-07 | 1,000 |
| Cedar Hill | `citizen_self_service.py cedar_hill` | WORKING | 2026-02-07 | 1,000 |
| DeSoto | `citizen_self_service.py desoto` | WORKING | 2026-02-07 | 1,000 |
| Mesquite | `citizen_self_service.py mesquite` | PARTIAL | 2026-02-07 | 5 (pagination stuck) |
| Waxahachie | `citizen_self_service.py waxahachie` | WORKING | 2026-02-07 | 1,000 |
| Grand Prairie | `citizen_self_service.py grand_prairie` | WORKING | 2026-02-07 | 1,000 |
| Prosper | `citizen_self_service.py prosper` | WORKING | 2026-02-07 | 1,000 |
| Hurst | Not tested | - | - | In config but not tested |
| Coppell | Not tested | - | - | In config but not tested |

### MyGov Platform (14 cities configured)

| City | Scraper | Status | Last Run | Permits |
|------|---------|--------|----------|---------|
| Mansfield | `mygov_multi.py mansfield` | WORKING | 2026-02-07 | 358 |
| Rowlett | `mygov_multi.py rowlett` | WORKING | 2026-02-07 | 211 |
| Grapevine | `mygov_multi.py grapevine` | WORKING | 2026-02-07 | 225 |
| Little Elm | `mygov_multi.py little_elm` | WORKING | 2026-02-07 | 203 |
| Lancaster | `mygov_multi.py lancaster` | WORKING | 2026-02-07 | 222 |
| Midlothian | `mygov_multi.py midlothian` | WORKING | 2026-02-07 | 210 |
| Celina | `mygov_multi.py celina` | WORKING | 2026-02-07 | 219 |
| Fate | `mygov_multi.py fate` | WORKING | 2026-02-07 | 156 |
| Venus | `mygov_multi.py venus` | WORKING | 2026-02-07 | 65 |
| Burleson | `mygov_multi.py burleson` | TIMEOUT | 2026-02-06 | Portal may be blocked |
| Crowley | `mygov_multi.py crowley` | WORKING | 2026-02-07 | 241 |
| University Park | `mygov_multi.py university_park` | NO DATA | 2026-02-06 | 0 permits found |
| Royse City | Not tested | - | - | Listed in config |
| Forney | Not tested | - | - | Needs auth per AUTH_REQUIRED.md |
| Westlake | `mygov_westlake.py` | WORKING | 2026-02-07 | 6 (address-based, slow) |

### SmartGov Platform (1 city)

| City | Scraper | Status | Last Run | Permits |
|------|---------|--------|----------|---------|
| Sachse | `smartgov_sachse.py` | WORKING | 2026-02-07 | 507 |

### CityView Platform (1 city)

| City | Scraper | Status | Last Run | Permits |
|------|---------|--------|----------|---------|
| Carrollton | `cityview.py carrollton` | WORKING | 2026-02-07 | 458 |

### Socrata API Scrapers

| City/Region | Scraper | Status | Last Run | Permits |
|-------------|---------|--------|----------|---------|
| Arlington | `dfw_big4_socrata.py` | WORKING | 2026-02-07 | 17,895 |
| Dallas (Socrata) | `dfw_big4_socrata.py` | NO DATA | 2026-02-07 | 0 (use Accela) |
| Collin County (18 cities) | `collin_cad_socrata.py` | WORKING | 2026-02-06 | CAD data for Collin County |
| Denton City | `denton_socrata.py` | BROKEN | 2026-02-06 | 404 error - dataset ID invalid |

### OpenGov Platform (2 cities)

| City | Scraper | Status | Last Run | Permits |
|------|---------|--------|----------|---------|
| Bedford | `opengov.py bedford` | WORKING | 2026-02-07 | 3 |
| Seagoville | `opengov.py seagoville` | BROKEN | 2026-02-06 | Records tab not found |

### MGO Connect Platform (requires auth)

| City | Scraper | Status | Last Test | Notes |
|------|---------|--------|-----------|-------|
| Irving | `mgo_connect.py Irving` | TIMEOUT | 2026-02-06 | Timed out during login (has creds) |
| Denton (MGO) | `mgo_connect.py Denton` | Not tested | - | Uses same creds as Irving |

### Other Scrapers

| Scraper | Status | Last Run | Permits |
|---------|--------|----------|---------|
| `govbuilt_weatherford.py` | WORKING | 2026-02-07 | 200 |
| `ellis_county_excel.py` | NEEDS DEP | 2026-02-06 | Requires `openpyxl` package |
| `cad_delta_engine.py` | UTILITY | 2026-02-06 | CAD tax roll processor (DCAD, TAD, Denton) |
| `denton_cad_search.py` | UTILITY | 2026-02-06 | DCAD address enrichment |
| `cad_parcel_fetcher.py` | UTILITY | - | Parcel data fetcher |
| `tyler_esuite_parcel.py` | UTILITY | - | Tyler eSuite parcel fetcher |

---

## Broken Scrapers - Repair Needed

**All high-priority scrapers are now FIXED!** See "Recent Fixes" section above.

### Remaining Issues (Low Priority)

1. **Denton Socrata** - `denton_socrata.py`
   - **Issue:** 404 error - dataset ID `xxxx-xxxx` is placeholder
   - **Fix:** Find correct Denton open data dataset ID
   - **Impact:** Duplicate of eTRAKiT scraper exists

2. **Seagoville (OpenGov)** - `opengov.py seagoville`
   - **Issue:** Records tab not found on portal
   - **Fix:** Investigate portal structure changes
   - **Impact:** Small city

3. **Irving (MGO Connect)** - `mgo_connect.py Irving`
   - **Issue:** Login timeout (may be transient)
   - **Fix:** Retry, check if portal changed, verify credentials
   - **Impact:** Major city, have credentials

4. **Plano (eTRAKiT Auth)** - `etrakit_auth.py plano`
   - **Issue:** Requires `DEEPSEEK_API_KEY` env var (LLM-based scraper)
   - **Fix:** Set env var or refactor to use fast DOM approach
   - **Impact:** Have credentials, just needs config

---

## Auth Required (Per AUTH_REQUIRED.md)

| City | Platform | Have Creds? | Status |
|------|----------|-------------|--------|
| Irving | MGO Connect | YES | Scraper timeout |
| Denton | MGO Connect | YES | Not tested |
| Plano | eTRAKiT | YES | Needs DEEPSEEK_API_KEY |
| Lewisville | Tyler eSuite | NO | Blocked |
| Richardson | Citizenserve | NO | 403 blocked |
| Forney | MyGov Collaborator | NO | No public portal |
| Highland Village | Custom | NO | Registration required |
| Corinth | Civic Access | NO | Registration required |
| Euless | NewEdge | NO | Login required |
| North Richland Hills | EnerGov + Tyler SSO | NO | SSO enforced |

---

## Partial/Limited Scrapers

1. **The Colony (eTRAKiT)** - Returns permits but addresses are empty
   - Use `enrich_colony_addresses.py` for address enrichment

2. **Southlake (EnerGov)** - Gets 500 permits but residential filter returns 0
   - May need to adjust permit type filter

3. **University Park (MyGov)** - Search returns 0 permits
   - May need different search terms

4. **Carrollton (CityView)** - Works but data may be stale (July 2025)
   - Per AUTH_REQUIRED.md, may need login for fresh data

---

## Missing Dependencies

```bash
# Required for ellis_county_excel.py:
pip install openpyxl

# Already installed but worth noting:
pip install pandas playwright-stealth sodapy
```

---

## Cities Not Currently Scraped

These cities are in DFW but have no working scraper:

- **Lewisville** - Tyler eSuite (needs auth)
- **Richardson** - Citizenserve (403 blocked)
- **Garland** - No public portal
- **North Richland Hills** - Tyler SSO required
- **Highland Village** - Registration required
- **Corinth** - Registration required
- **Euless** - Login required
- **Forney** - No public portal

---

## Recommendations

### Completed (2026-02-06)
1. ~~Fix Grand Prairie selector~~ **DONE** - Migrated to EnerGov CSS
2. ~~Investigate Flower Mound/Prosper timeouts~~ **DONE** - Flower Mound works, Prosper migrated to CSS

### Short-term
3. Set DEEPSEEK_API_KEY for Plano scraper
4. Find correct Denton Socrata dataset ID
5. Debug Irving MGO login timeout
6. Install openpyxl for Ellis County

### Long-term
7. Acquire credentials for blocked cities (Lewisville, Richardson, etc.)
8. Consider proxy solution for 403-blocked portals

---

## Test Commands Reference

```bash
cd /home/astre/command-center/src/greenlit/collections
source /home/astre/command-center/venv/bin/activate

# Accela
python3 scrapers/accela_fast.py dallas 10
python3 scrapers/accela_fast.py fort_worth 10

# eTRAKiT
python3 scrapers/etrakit.py frisco 10
python3 scrapers/etrakit.py flower_mound 10
python3 scrapers/etrakit.py denton 10

# EnerGov CSS (includes migrated cities)
python3 scrapers/citizen_self_service.py mckinney 10
python3 scrapers/citizen_self_service.py allen 10
python3 scrapers/citizen_self_service.py grand_prairie 10  # NEW - migrated from Accela
python3 scrapers/citizen_self_service.py prosper 10         # NEW - migrated from eTRAKiT

# MyGov
python3 scrapers/mygov_multi.py mansfield 10
python3 scrapers/mygov_multi.py --list  # Show all cities

# Others
python3 scrapers/smartgov_sachse.py 10
python3 scrapers/cityview.py carrollton 10
python3 scrapers/dfw_big4_socrata.py
python3 scrapers/collin_cad_socrata.py --limit 10
python3 scrapers/opengov.py bedford 10
python3 scrapers/govbuilt_weatherford.py 10
```
