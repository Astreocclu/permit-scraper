# DFW Permit Scraper - Status Documentation

**Last Updated:** December 20, 2024 (afternoon)

---

## Overview

This document tracks the status of all permit scrapers across DFW municipalities, including platform types, scraper implementations, CAD enrichment capabilities, and blocking issues.

**Total Coverage:** 30 municipalities tracked
**Working Scrapers:** 21 (Sachse added Dec 19)
**Partial/In Progress:** 1 (Weatherford)
**Blocked/Not Implemented:** 8

---

## DFW Metro - All 30 Municipalities

| # | City | Population | Platform | Scraper | CAD County | Status | Notes |
|---|------|-----------|----------|---------|-----------|--------|-------|
| 1 | **Dallas** | 1.3M | Accela | `accela_fast.py` | Dallas | ✅ Working | Fast DOM extraction |
| 2 | **Fort Worth** | 950K | Accela | `accela_fast.py` | Tarrant | ✅ Working | Fast DOM extraction |
| 3 | **Arlington** | 400K | Socrata API | `dfw_big4_socrata.py` | Tarrant | ✅ Working | API-based bulk CSV |
| 4 | **Plano** | 285K | eTRAKiT | `etrakit.py` | Collin | ✅ Working | Public login required |
| 5 | **Irving** | 240K | MGO Connect | `mgo_connect.py` | Dallas | ❌ Blocked | PDF export opens about:blank, never loads |
| 6 | **Garland** | 240K | None (311 only) | — | Dallas | ❌ Blocked | No public permit portal exists |
| 7 | **Frisco** | 200K | eTRAKiT | `etrakit_fast.py` | Collin/Denton | ✅ Working | Fast DOM extraction |
| 8 | **Denton** | 160K | eTRAKiT | `etrakit_fast.py` | Denton | ✅ Working | YYMM-#### format |
| 9 | **McKinney** | 195K | EnerGov CSS | `citizen_self_service.py` | Collin | ✅ Working | 1,001 permits (Dec 13) |
| 10 | **Grand Prairie** | 195K | Accela | `accela_fast.py` | Dallas/Tarrant | ✅ Working | Fast DOM extraction |
| 11 | **Mesquite** | 145K | Accela | `accela_fast.py` | Dallas | ✅ Working | Fast DOM extraction |
| 12 | **Carrollton** | 135K | CityView | `cityview.py` | Dallas/Denton | ✅ Working | Limited to 20 results/search |
| 13 | **Richardson** | 120K | Unknown | — | Dallas/Collin | ❌ Blocked | cor.net returns 403, needs proxy |
| 14 | **Lewisville** | 110K | Tyler eSuite | `tyler_esuite_parcel.py` | Denton | ❌ Blocked | Portal requires authentication, no public search |
| 15 | **Flower Mound** | 75K | eTRAKiT | `etrakit_fast.py` | Denton | ✅ Working | Fast DOM extraction |
| 16 | **Allen** | 105K | EnerGov CSS | `citizen_self_service.py` | Collin | ✅ Working | 1,070 permits (Dec 13) |
| 17 | **Grapevine** | 55K | MyGov | `parse_grapevine_pdf.py` | Tarrant | ✅ Working | PDF export + manual parse |
| 18 | **Waxahachie** | 45K | EnerGov CSS | `citizen_self_service.py` | Ellis | ✅ Working | No CAD enrichment (firewalled) |
| 19 | **Coppell** | 42K | EnerGov CSS | `citizen_self_service.py` | Dallas | ✅ Working | 1,096 permits (Dec 13) |
| 20 | **Euless** | 60K | Cityworks PLL | — | Tarrant | ❌ Blocked | Login + reCAPTCHA required |
| 21 | **Bedford** | 50K | Unknown | — | Tarrant | ❌ Not Implemented | Research needed |
| 22 | **Hurst** | 40K | EnerGov CSS | `citizen_self_service.py` | Tarrant | ✅ Working | 1,000 permits (Dec 13) |
| 23 | **Forney** | 35K | MyGov | — | Kaufman | ❌ Blocked | Login required (confirmed Dec 17) |
| 24 | **Weatherford** | 35K | GovBuilt | — | Parker | 🔬 Scrapable | No CAD API (Parker County) |
| 25 | **Sachse** | 30K | SmartGov | `smartgov_sachse.py` | Dallas/Collin | ✅ Working | 500 permits (Dec 19) |
| 26 | **Southlake** | 32K | EnerGov CSS | `citizen_self_service.py` | Tarrant | ✅ Working | Residential filtering |
| 27 | **Colleyville** | 27K | EnerGov CSS | `citizen_self_service.py` | Tarrant | ✅ Working | Residential filtering |
| 28 | **Trophy Club** | 12K | EnerGov CSS | `citizen_self_service.py` | Denton | ✅ Working | Fast DOM extraction |
| 29 | **Westlake** | 1.5K | MyGov | `mygov_westlake.py` | Tarrant | ✅ Working | Address-based lookup |
| 30 | **Aledo** | 6K | Unknown | — | Parker | ❌ Blocked | No portal found + No CAD API |

---

## Platform Summary

| Platform | # Cities | Working | Blocked | Notes |
|----------|----------|---------|---------|-------|
| **Accela** | 5 | 5 | 0 | Dallas, Fort Worth, Grand Prairie, Mesquite (+ others) |
| **eTRAKiT** | 4 | 4 | 0 | Frisco, Flower Mound, Plano, Denton |
| **EnerGov CSS** | 10 | 8 | 2 | Southlake, Colleyville, Trophy Club, Waxahachie, McKinney, Allen, Hurst, Coppell, Farmers Branch (NRH needs work) |
| **MyGov** | 2 | 1 | 1 | Westlake works, Forney blocked |
| **CityView** | 1 | 1 | 0 | Carrollton |
| **Socrata API** | 1 | 1 | 0 | Arlington |
| **MGO Connect** | 1 | 0 | 1 | Irving - PDF export broken (about:blank) |
| **SmartGov** | 1 | 1 | 0 | Sachse - working (500 permits Dec 19) |
| **GovBuilt** | 1 | 0 | 1 | Weatherford (scrapable but no CAD) |
| **Tyler eSuite** | 1 | 0 | 1 | Lewisville - requires authentication |
| **Cityworks PLL** | 1 | 0 | 1 | Euless - Login + reCAPTCHA required |
| **No Portal** | 1 | 0 | 1 | Garland - Uses 311 only, no public permit search |
| **Unknown** | 4 | 0 | 4 | Richardson (403 blocked), Bedford, + 2 others |

---

## CAD County Coverage

| County | API Status | Cities Covered | Notes |
|--------|-----------|----------------|-------|
| **Dallas** | ✅ Working | Dallas, Irving, Grand Prairie, Mesquite, Carrollton, Coppell, Richardson, Sachse | Full enrichment available |
| **Tarrant** | ✅ Working | Fort Worth, Arlington, Southlake, Colleyville, Westlake, Grapevine, Euless, Bedford, Hurst | Full enrichment available |
| **Collin** | ✅ Working | Plano, Frisco, McKinney, Allen, Richardson, Sachse | Full enrichment available |
| **Denton** | ✅ Working | Denton, Flower Mound, Lewisville, Carrollton, Trophy Club, Frisco | Full enrichment available |
| **Kaufman** | ⚠️ Partial | Forney | Working API but missing year_built, square_feet |
| **Ellis** | ❌ Blocked | Waxahachie | GIS server firewalled (internal access only) |
| **Parker** | ❌ No API | Weatherford, Aledo | No public CAD API available |
| **Johnson** | ❌ Not Used | — | No cities in current scope |

---

## Session Notes - December 20, 2024 (Afternoon)

### Irving & Lewisville Deep Investigation

**Attempted to implement scrapers for both cities. Both are now confirmed BLOCKED.**

#### Irving MGO Connect - BLOCKED
- Tested existing Advanced Reporting code path
- **Finding:** PDF export opens new browser tab but stays at `about:blank`
- PDF never loads, 20-second timeout expires
- Root cause: Unknown - possibly anti-bot, possibly broken PDF endpoint
- **Status:** ❌ BLOCKED - would need city contact or API access

#### Lewisville Tyler eSuite - BLOCKED
- Created infrastructure: `scrapers/cad_parcel_fetcher.py`, `scripts/extract_parcel_ids.py`
- Fetched all 24,755 Lewisville parcels from Denton CAD
- Created `scrapers/tyler_esuite_parcel.py` for parcel-based lookup
- **Finding:** Portal has NO public search interface
  - Home page: No visible search inputs
  - All search endpoints (Search.aspx, PermitSearch.aspx, PublicSearch.aspx) return auth errors
- **Status:** ❌ BLOCKED - requires login credentials or different access method

#### New Infrastructure Created (Useful for Other Cities)
- `scrapers/cad_parcel_fetcher.py` - Bulk parcel download from Denton/Tarrant/Dallas CAD
- `scripts/extract_parcel_ids.py` - Format parcel IDs for Tyler eSuite
- `data/parcels/lewisville_denton_parcels.json` - 24,755 parcels (example dataset)

**Commits:**
- `694fad7` feat: add CAD parcel fetcher with Denton/Tarrant/Dallas support
- `29d50da` feat: add parcel ID extractor for Tyler eSuite format
- `2a8647f` feat: add Tyler eSuite parcel-based scraper for Lewisville

---

## Session Notes - December 20, 2024 (Morning)

### City Research Results

Researched 4 unknown cities using parallel subagents. All research complete.

| City | Population | Platform | Status | Notes |
|------|-----------|----------|--------|-------|
| **Garland** | 240K | None | ❌ Blocked | No public permit portal. Uses Accela CRM (E-Assist) for 311 only. Open data portal exists but no permit dataset. |
| **Richardson** | 120K | Unknown | ❌ Blocked | cor.net returns 403 Access Denied. Has Citizenserve portal but blocked. Needs residential proxy. |
| **Lewisville** | 110K | Tyler eSuite | 🔬 Scrapable | **NOT MGO Connect!** Uses Tyler eSuite (NewWorld) at https://etools.cityoflewisville.com/esuite.permits/ - PUBLIC access. Needs new scraper. |
| **Euless** | 60K | Cityworks PLL | ❌ Blocked | Trimble Cityworks via NewEdge Services. Login + reCAPTCHA required. LOW priority. |

### Irving MGO Connect Investigation

Investigated why Irving MGO Connect returns 0 permits despite login working.

**Root Cause Found:**
- `scrape_orchestrator()` only calls `run_scraper_session()`
- Irving requires "Advanced Reporting → PDF export" workflow
- This logic exists in unused `scrape()` function (lines 700+)
- Standard search returns 0 results; sidebar shows "New in 30d: 761"

**Fix Required:**
- Architectural refactor needed to call `scrape()` for Irving instead of `run_scraper_session()`
- Blocked until MGO Connect redesign

### Key Discoveries

1. **Lewisville Misidentified:** Was listed as "MGO Connect" in previous notes but uses completely different Tyler eSuite platform
2. **Garland Has No Portal:** Despite 240K population, no public online permit search exists
3. **Richardson Actively Blocked:** Server returns 403, likely IP-based blocking
4. **Euless Has CAPTCHA:** reCAPTCHA on login makes automated scraping impractical

### Action Items

1. **HIGH VALUE:** Create Tyler eSuite scraper for Lewisville (110K pop, public access)
2. **MEDIUM:** Refactor MGO Connect to use Advanced Reporting for Irving (240K pop)
3. **LOW:** Try Richardson with residential proxy
4. **SKIP:** Euless (CAPTCHA), Garland (no portal)

---

## Session Notes - December 17, 2024

### Browser-Use Scraper Testing

Tested 4 cities using browser-use LLM agent for portal exploration.

**Weatherford (GovBuilt):** ✅ SUCCESS
- Portal: https://permits.weatherfordtx.gov/
- Access: PUBLIC (no login)
- Results: 203 permits found (samples extracted)
- Issue: No valuation field in public view
- CAD: Parker County has NO public API

**Grapevine (MyGov):** ✅ SUCCESS
- Portal: MyGov with PDF export capability
- Access: PUBLIC
- Method: Downloaded "All Permits - last month (PP).pdf" (50 pages)
- Results: **126 permits loaded to database**
- Data quality: Excellent - includes contractor names, phones, emails
- Scraper: `scripts/parse_grapevine_pdf.py` (manual PDF parse)
- Categories: 40 plumbing, 27 roofing, 12 electrical, 12 addition/remodel, 9 HVAC, etc.

**Forney (MyGov):** ❌ BLOCKED
- Portal: MyGov Collaborator Portal
- **Login URL:** `https://mygov.us/collaborator/forneytx`
- Access: **LOGIN REQUIRED** (confirmed via browser-use)
- Issue: All public URLs redirect to marketing page (empower.tylertech.com/mygov)
- Tested URLs: `mygov.us/collaborator/forneytx`, `web.mygov.us/collaborator/forneytx`, `public.mygov.us/forney` - all failed
- Status: Cannot scrape without credentials

**Bedford (OpenGov):** ⚠️ LIMITED
- Portal: OpenGov with keyword search only
- Access: PUBLIC but limited
- Issue: No date filtering, keyword-only search
- Results: Few matches for general permit searches
- Status: Scrapable but low value without better filtering

**Garland:** ❌ NOT AVAILABLE
- Attempted to access citizen portal
- Issue: Jurisdiction not found in dropdown
- Status: Requires further research

---

## Session Notes - December 18, 2024

### MyGov Cities Testing (All Failed)

Tested all 4 MyGov cities with `public.mygov.us/{city}_tx/module?module=pi` URL pattern.

| City | Population | Result | Notes |
|------|-----------|--------|-------|
| Mansfield | 75K | ❌ BLOCKED | Search returns 0 results, no Reports module |
| Little Elm | 55K | ✅ WORKING | 2,729 permits via Excel export - `parse_littleelm_excel.py` |
| Celina | 30K | ❌ BLOCKED | module=pi redirects to homepage |
| Fate | 25K | ❌ BLOCKED | Reports only shows contractor registration |

**Conclusion:** MyGov `module?module=pi` URL pattern does NOT work for permit search.

### Additional Cities Tested

| City | Platform | Result | Notes |
|------|----------|--------|-------|
| Lewisville | MGO Connect | ⚠️ 0 PERMITS | Login works, searched Nov-Dec 2025, returned empty |
| Euless | Unknown | ❌ ACCESS DENIED | All URLs blocked, CAPTCHA on search engines |

### Summary of Dec 17-18 Testing

**Working (added to DB):**
- Grapevine: 126 permits via PDF parse

**Confirmed Scrapable:**
- Weatherford: 203 permits, PUBLIC access (no CAD)

**Blocked:**
- Forney: LOGIN REQUIRED
- Mansfield, Celina, Fate: MyGov module disabled
- Euless: Access Denied + CAPTCHA

**Limited/Partial:**
- Little Elm: Has PDF report (like Grapevine)
- Bedford: OpenGov keyword-only search
- Lewisville: MGO Connect works but 0 permits returned

**Resolved Dec 19:**
- ✅ Little Elm: 2,729 permits loaded via Excel export from MyGov Reports
  - Created `scripts/parse_littleelm_excel.py` for automated parsing
  - Parser extracts 82.4% contractor names (vs 4.8% ad-hoc)
  - Finds latest Excel in `/tmp/browser-use-downloads-*/`
  - Manual workflow: Download Excel from MyGov Reports → Run parser
- ❌ Richardson: cor.net blocked (Access Denied), Citizenserve portal at `https://www.citizenserve.com/Portal/PortalController?Action=showPermit&ctzPagePrefix=Portal_&installationID=343`
- ❌ Garland: No public permit portal found (PDF forms + email only)

---

## Session Notes - December 13, 2024

### Production Run Results

**Permits Loaded to Database:**
| City | Platform | Permits |
|------|----------|---------|
| McKinney | EnerGov CSS | 1,001 |
| Allen | EnerGov CSS | 1,070 |
| Hurst | EnerGov CSS | 1,000 |
| Coppell | EnerGov CSS | 1,096 |
| Farmers Branch | EnerGov CSS | 276 |
| **Total** | | **4,443** |

**CAD Enrichment Results:**
- Properties enriched: 2,351 (52% hit rate)
- Absentee owners identified: 574
- By county: Collin 1,124, Dallas 795, Tarrant 383, Denton 47, Kaufman 2
- Top property values: $14M, $10.8M, $8M, $7.7M

**AI Scoring Results:**
- Tier A (80+): 17 leads
- Tier B (50-79): 33 leads
- Tier C (<50): 65 leads
- Tier U (unverified): 238 leads
- Exports: `exports/{category}/tier_{a,b,c}.csv`

**Key Fixes Applied:**
- Fixed McKinney/Allen Angular timeout issues
- Updated Hurst URL: `css.hursttx.gov`
- Updated Coppell URL: `energovcss.coppelltx.gov`
- Changed date range from 60 to 365 days for more results
- Changed export mode from "current view" to bulk export

---

## Session Notes - December 12, 2024

### New Municipalities Expansion (Tasks 1-11 Complete)

**New Working Scrapers Added:**
1. **Denton** (160K pop)
   - Platform: eTRAKiT
   - Scraper: `etrakit_fast.py`
   - URL: https://dntn-trk.aspgov.com/eTRAKiT
   - Format: YYMM-#### (e.g., 2501-0001 for Jan 2025)
   - CAD: Denton County (existing, working)
   - Status: ✅ Working

2. **Trophy Club** (12K pop)
   - Platform: EnerGov CSS (Citizen Self Service)
   - Scraper: `citizen_self_service.py`
   - URL: https://energovweb.trophyclub.org/energovprod/selfservice
   - CAD: Denton County (existing, working)
   - Status: ✅ Working

3. **Waxahachie** (45K pop)
   - Platform: EnerGov CSS (Citizen Self Service)
   - Scraper: `citizen_self_service.py`
   - URL: https://waxahachietx-energovpub.tylerhost.net/Apps/SelfService
   - CAD: Ellis County (no public API - firewalled)
   - Status: ✅ Working scraper, ❌ No CAD enrichment
   - Note: Ellis County GIS server (ecgis.co.ellis.tx.us) exists but blocks all external connections

**New CAD County Integration:**
- **Kaufman County** (for Forney area)
  - API URL: https://services9.arcgis.com/26s7bQ5Q51Gt4J2Q/arcgis/rest/services/KaufmanCADWebService/FeatureServer/0/query
  - Status: ✅ Working API endpoint found
  - Limitations: Missing `year_built` and `square_feet` fields
  - Available: owner_name, situs_address, market_value, land_value, improvement_value, acreage
  - Documentation: `/docs/kaufman-county-endpoint-research.md`

**Research Completed:**

4. **Sachse** (30K pop) - SmartGov Platform
   - **Status:** 🔬 Scrapable (needs new scraper implementation)
   - Correct URL: https://ci-sachse-tx.smartgovcommunity.com (NOT pl-sachse-tx)
   - Framework: Angular SPA
   - Public access: YES (no login required)
   - Search endpoint: /ApplicationPublic/ApplicationSearch
   - Requirements: Playwright with JavaScript rendering
   - CAD: Dallas/Collin County (existing, working)
   - Documentation: `/SACHSE_RESEARCH_REPORT.md`
   - Next Steps: Create `scrapers/smartgov.py` using Playwright

5. **Weatherford** (35K pop) - GovBuilt Platform
   - **Status:** 🔬 Scrapable but limited value
   - URL: https://permits.weatherfordtx.gov/
   - Platform: GovBuilt (public JSON API available)
   - Blocking Issue: Parker County has NO public CAD API
   - Impact: Can scrape permits but cannot enrich with property data
   - Recommendation: Low priority until CAD source found
   - Alternative: Use commercial data provider (Regrid, TaxNetUSA)

**Blocked Municipalities:**

6. **Forney** (35K pop) - MyGov
   - **Status:** ❌ BLOCKED (no public access)
   - Tested URLs: All variations of public.mygov.us/forney* returned 404
   - Comparison: Westlake MyGov works at public.mygov.us/westlake_tx/lookup
   - Conclusion: Forney either doesn't use MyGov or has public access disabled
   - Documentation: `/FORNEY_MYGOV_FINDINGS.md`
   - Next Steps: Research alternative permit portal on cityofforney.com

7. **Aledo** (6K pop)
   - **Status:** ❌ BLOCKED (no portal + no CAD)
   - No online permit portal found
   - Parker County has no public CAD API
   - Recommendation: Skip unless manual process established

8. **Ellis County CAD**
   - **Status:** ❌ BLOCKED (firewalled)
   - Server: ecgis.co.ellis.tx.us (IP: 12.44.249.11)
   - Issue: 100% packet loss, connection timeouts
   - Diagnosis: Behind firewall, requires VPN/internal network access
   - Impact: Waxahachie permits can be scraped but not enriched
   - Documentation: `/docs/research/ellis_county_cad_api_research.md`
   - Alternatives: Contact Ellis County GIS, use commercial provider, or download static shapefiles

---

## Working Scraper Details

### Accela Platform (5 cities)
**Scraper:** `scrapers/accela_fast.py`
**Method:** Fast DOM extraction
**Cities:**
- Dallas (1.3M) - Dallas County CAD
- Fort Worth (950K) - Tarrant County CAD
- Grand Prairie (195K) - Dallas/Tarrant County CAD
- Mesquite (145K) - Dallas County CAD

**Usage:**
```bash
python3 scrapers/accela_fast.py dallas 1000
python3 scrapers/accela_fast.py fort_worth 1000
python3 scrapers/accela_fast.py grand_prairie 1000
```

### eTRAKiT Platform (4 cities)
**Scrapers:** `scrapers/etrakit_fast.py`, `scrapers/etrakit.py`
**Method:** Fast DOM extraction (or login-based for Plano)
**Cities:**
- Frisco (200K) - Collin/Denton County CAD - No login required
- Flower Mound (75K) - Denton County CAD - No login required
- Denton (160K) - Denton County CAD - No login required
- Plano (285K) - Collin County CAD - **Requires public login**

**Usage:**
```bash
python3 scrapers/etrakit_fast.py frisco 1000
python3 scrapers/etrakit_fast.py flower_mound 1000
python3 scrapers/etrakit_fast.py denton 1000
python3 scrapers/etrakit.py plano 1000  # Login required
```

### EnerGov CSS Platform (8 working, 2 in progress)
**Scraper:** `scrapers/citizen_self_service.py`
**Method:** Playwright browser automation with Excel export
**Working Cities:**
- McKinney (195K) - Collin County CAD - 1,001 permits (Dec 13)
- Allen (105K) - Collin County CAD - 1,070 permits (Dec 13)
- Hurst (40K) - Tarrant County CAD - 1,000 permits (Dec 13)
- Coppell (42K) - Dallas County CAD - 1,096 permits (Dec 13)
- Farmers Branch (30K) - Dallas County CAD - 276 permits (Dec 13)
- Southlake (32K) - Tarrant County CAD - Residential filtering available
- Colleyville (27K) - Tarrant County CAD - Residential filtering available
- Trophy Club (12K) - Denton County CAD
- Waxahachie (45K) - NO CAD (Ellis County firewalled)

**In Progress:**
- North Richland Hills - Different page structure, needs custom selectors

**Usage:**
```bash
python3 scrapers/citizen_self_service.py southlake 500 --permit-type "Residential Remodel"
python3 scrapers/citizen_self_service.py colleyville 500
python3 scrapers/citizen_self_service.py trophy_club 500
python3 scrapers/citizen_self_service.py waxahachie 500
```

### Other Platforms
**CityView (Carrollton):**
```bash
python3 scrapers/cityview.py carrollton 500  # Limited to 20 results per search
```

**Socrata API (Arlington):**
```bash
python3 scrapers/dfw_big4_socrata.py  # Bulk CSV download
```

**MyGov (Westlake):**
```bash
python3 scrapers/westlake_harvester.py  # First: harvest addresses
python3 scrapers/mygov_westlake.py       # Then: scrape permits
```

**MGO Connect (Irving - Partial):**
```bash
python3 scrapers/mgo_connect.py irving 100  # Login works, PDF extraction in progress
```

---

## Blocking Issues

### Technical Blocks

**McKinney & Allen (EnerGov CSS):** ✅ RESOLVED (Dec 13, 2024)
- Issue was Angular loading timeouts
- Solution: Increased wait times, changed to bulk Excel export mode
- McKinney: 1,001 permits loaded
- Allen: 1,070 permits loaded

**Irving (MGO Connect Anti-Bot):**
- Platform: MGO Connect
- Issue: Anti-bot detection triggers on automated access
- Status: Login works, but permit data extraction blocked
- Potential Solution: Stealth mode, human-like delays, session rotation

### Access Blocks

**Forney (No Public MyGov):**
- Platform: MyGov (expected)
- Issue: No public lookup portal exists
- Tested: All URL variations return 404
- Next Steps: Research cityofforney.com for alternative portal

**Ellis County CAD (Firewalled GIS Server):**
- Server: ecgis.co.ellis.tx.us
- Issue: All connections timeout (firewall/VPN-only access)
- Impact: Waxahachie permits scrapable but cannot be enriched
- Next Steps: Contact Ellis County GIS, use commercial provider, or static shapefile downloads

**Parker County (No CAD API):**
- Counties: Weatherford, Aledo
- Issue: No public CAD API available
- Impact: Permits scrapable but no enrichment possible
- Next Steps: Contact Parker County CAD, use commercial provider

### Not Yet Researched

The following cities require platform research:
- Bedford (50K) - Unknown platform

**Resolved (Dec 20):**
- Garland (240K) - No public permit portal (311/E-Assist only)
- Richardson (120K) - cor.net blocked with 403, needs residential proxy
- Lewisville (110K) - Tyler eSuite platform at etools.cityoflewisville.com
- Euless (60K) - Cityworks PLL, requires login + reCAPTCHA

**Resolved (Dec 17):** Grapevine (55K) - MyGov with PDF export
**Resolved (Dec 13):** Coppell (42K) and Hurst (40K) - now working with EnerGov CSS

---

## Next Steps

### Immediate Priorities (High Value)

1. **Implement Sachse SmartGov scraper** (30K pop, working CAD)
   - Create `scrapers/smartgov.py` using Playwright
   - Use correct URL: https://ci-sachse-tx.smartgovcommunity.com
   - Handle Angular SPA rendering
   - Target: ApplicationPublic/ApplicationSearch endpoint
   - **STATUS:** Ready to implement - PUBLIC access confirmed

2. **Check other Denton County cities** for public parcel-based portals
   - CAD infrastructure ready (`cad_parcel_fetcher.py`)
   - Flower Mound, Highland Village, The Colony, etc.
   - Look for cities with public Tyler eSuite or similar

### Blocked (Require External Action)

3. ~~**Irving MGO Connect**~~ ❌ BLOCKED (240K pop)
   - PDF export opens about:blank, never loads
   - Would need city API access or different approach

4. ~~**Lewisville Tyler eSuite**~~ ❌ BLOCKED (110K pop)
   - Portal requires authentication
   - Scraper framework ready but useless without access

5. ~~**Richardson**~~ ❌ BLOCKED (120K pop)
   - cor.net returns 403
   - Residential proxy might work but unconfirmed

### Medium Priorities

6. **Research Forney alternatives** (35K pop)
   - Check cityofforney.com for permit portal
   - Contact building department for public records access
   - Note: Kaufman County CAD ready (partial fields)

7. **Try Richardson with residential proxy** (120K pop)
   - cor.net returns 403 from datacenter IPs
   - May work with residential proxy
   - Has Citizenserve portal if accessible

### Long-term Considerations

7. **Resolve Ellis County CAD access** (for Waxahachie)
   - Contact Ellis County GIS for public endpoint
   - Evaluate commercial providers (Regrid, TaxNetUSA)
   - Consider static shapefile integration

8. **Evaluate Parker County options** (for Weatherford, Aledo)
   - Contact Parker County CAD for API access
   - Evaluate commercial providers
   - Determine if non-enriched permits are valuable

9. **Research Bedford** (50K pop) - Only remaining unknown city
   - Platform research required
   - Tarrant County CAD (already working)

---

## Success Metrics

### Current Coverage
- **Working Scrapers:** 19 municipalities (+5 added Dec 13)
- **Combined Population:** ~4.5M (approx 65% of DFW metro)
- **Working CAD Counties:** 4 (Dallas, Tarrant, Collin, Denton)
- **Partial CAD Counties:** 1 (Kaufman - missing building details)
- **Latest Run (Dec 13):** 4,443 permits loaded, 2,351 enriched, 50 quality leads

### Target Coverage (If All Implemented)
- **Total Municipalities:** 30
- **Total Population:** ~7M+ (full DFW metro coverage)
- **Total CAD Counties:** 7 (+ Ellis, Parker, Kaufman with limitations)

### High-Value Targets Still Blocked
- Garland (240K) - ❌ No public permit portal exists
- Irving (240K) - ❌ PDF export broken (about:blank)
- Richardson (120K) - ❌ 403 Blocked (needs residential proxy)
- Lewisville (110K) - ❌ Tyler eSuite requires authentication

**Combined blocked high-value population:** ~670K (all confirmed blocked Dec 20)

**Resolved Dec 20:** All 4 cities researched (Garland, Richardson, Lewisville, Euless)
**Resolved Dec 13:** McKinney (195K) and Allen (105K) - now working!

---

## Technical Notes

### Scraper Types
- **Fast DOM:** Accela, eTRAKiT (no login)
- **Browser Automation:** EnerGov CSS, MyGov, CityView, SmartGov
- **API-based:** Socrata (Arlington), GovBuilt (Weatherford)
- **Login Required:** eTRAKiT (Plano), MGO Connect (Irving)

### CAD Integration
All CAD enrichment uses ArcGIS REST API endpoints:
- Dallas County: Working, full fields
- Tarrant County: Working, full fields
- Collin County: Working, full fields
- Denton County: Working, full fields
- Kaufman County: Working, missing year_built/square_feet
- Ellis County: Endpoint exists but firewalled
- Parker County: No public API

### Output Files
- `{city}_raw.json` - Raw scraped permits
- `exports/{trade_group}/{category}/tier_{a,b,c}.csv` - Scored leads
- Database: `leads_permit` - All permits
- Database: `leads_property` - CAD enrichment
- Database: `clients_scoredlead` - AI-scored leads

---

## Documentation References

- **Main README:** `/README.md`
- **Sachse Research:** `/SACHSE_RESEARCH_REPORT.md`
- **Forney Research:** `/FORNEY_MYGOV_FINDINGS.md`
- **Kaufman County CAD:** `/docs/kaufman-county-endpoint-research.md`
- **Ellis County CAD:** `/docs/research/ellis_county_cad_api_research.md`
- **Expansion Plan:** `/docs/plans/2025-12-12-new-municipalities-expansion.md`

---

**Status Legend:**
- ✅ Working - Fully functional scraper with CAD enrichment
- ⚠️ Partial - Working but incomplete/limited functionality
- 🔬 Scrapable - Researched and scrapable but not yet implemented
- ❌ Blocked - Cannot scrape due to technical or access issues
- ❌ Not Implemented - No research or implementation yet
