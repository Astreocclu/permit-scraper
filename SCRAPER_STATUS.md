# DFW Permit Scraper - Status Documentation

**Last Updated:** December 12, 2025

---

## Overview

This document tracks the status of all permit scrapers across DFW municipalities, including platform types, scraper implementations, CAD enrichment capabilities, and blocking issues.

**Total Coverage:** 30 municipalities tracked
**Working Scrapers:** 14
**Partial/In Progress:** 1
**Blocked/Not Implemented:** 15

---

## DFW Metro - All 30 Municipalities

| # | City | Population | Platform | Scraper | CAD County | Status | Notes |
|---|------|-----------|----------|---------|-----------|--------|-------|
| 1 | **Dallas** | 1.3M | Accela | `accela_fast.py` | Dallas | ✅ Working | Fast DOM extraction |
| 2 | **Fort Worth** | 950K | Accela | `accela_fast.py` | Tarrant | ✅ Working | Fast DOM extraction |
| 3 | **Arlington** | 400K | Socrata API | `dfw_big4_socrata.py` | Tarrant | ✅ Working | API-based bulk CSV |
| 4 | **Plano** | 285K | eTRAKiT | `etrakit.py` | Collin | ✅ Working | Public login required |
| 5 | **Irving** | 240K | MGO Connect | `mgo_connect.py` | Dallas | ⚠️ Partial | Login works, PDF extraction needed |
| 6 | **Garland** | 240K | Unknown | — | Dallas | ❌ Not Implemented | Research needed |
| 7 | **Frisco** | 200K | eTRAKiT | `etrakit_fast.py` | Collin/Denton | ✅ Working | Fast DOM extraction |
| 8 | **Denton** | 160K | eTRAKiT | `etrakit_fast.py` | Denton | ✅ Working | YYMM-#### format |
| 9 | **McKinney** | 195K | EnerGov CSS | `citizen_self_service.py` | Collin | ❌ Blocked | Angular timeouts |
| 10 | **Grand Prairie** | 195K | Accela | `accela_fast.py` | Dallas/Tarrant | ✅ Working | Fast DOM extraction |
| 11 | **Mesquite** | 145K | Accela | `accela_fast.py` | Dallas | ✅ Working | Fast DOM extraction |
| 12 | **Carrollton** | 135K | CityView | `cityview.py` | Dallas/Denton | ✅ Working | Limited to 20 results/search |
| 13 | **Richardson** | 120K | Unknown | — | Dallas/Collin | ❌ Not Implemented | Research needed |
| 14 | **Lewisville** | 110K | Unknown | — | Denton | ❌ Not Implemented | Research needed |
| 15 | **Flower Mound** | 75K | eTRAKiT | `etrakit_fast.py` | Denton | ✅ Working | Fast DOM extraction |
| 16 | **Allen** | 105K | EnerGov CSS | `citizen_self_service.py` | Collin | ❌ Blocked | Angular timeouts |
| 17 | **Grapevine** | 55K | Unknown | — | Tarrant | ❌ Not Implemented | Research needed |
| 18 | **Waxahachie** | 45K | EnerGov CSS | `citizen_self_service.py` | Ellis | ✅ Working | No CAD enrichment (firewalled) |
| 19 | **Coppell** | 42K | Unknown | — | Dallas | ❌ Not Implemented | Research needed |
| 20 | **Euless** | 60K | Unknown | — | Tarrant | ❌ Not Implemented | Research needed |
| 21 | **Bedford** | 50K | Unknown | — | Tarrant | ❌ Not Implemented | Research needed |
| 22 | **Hurst** | 40K | Unknown | — | Tarrant | ❌ Not Implemented | Research needed |
| 23 | **Forney** | 35K | MyGov | — | Kaufman | ❌ Blocked | No public MyGov access |
| 24 | **Weatherford** | 35K | GovBuilt | — | Parker | 🔬 Scrapable | No CAD API (Parker County) |
| 25 | **Sachse** | 30K | SmartGov | — | Dallas/Collin | 🔬 Scrapable | Needs new scraper (Angular SPA) |
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
| **EnerGov CSS** | 6 | 3 | 3 | Southlake, Colleyville, Trophy Club, Waxahachie (McKinney/Allen blocked) |
| **MyGov** | 2 | 1 | 1 | Westlake works, Forney blocked |
| **CityView** | 1 | 1 | 0 | Carrollton |
| **Socrata API** | 1 | 1 | 0 | Arlington |
| **MGO Connect** | 1 | 0 | 1 | Irving partial (anti-bot issues) |
| **SmartGov** | 1 | 0 | 1 | Sachse (scrapable but needs implementation) |
| **GovBuilt** | 1 | 0 | 1 | Weatherford (scrapable but no CAD) |
| **Unknown** | 8 | 0 | 8 | Requires research |

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

## Session Notes - December 12, 2025

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

### EnerGov CSS Platform (3 working, 3 blocked)
**Scraper:** `scrapers/citizen_self_service.py`
**Method:** Playwright browser automation
**Working Cities:**
- Southlake (32K) - Tarrant County CAD - Residential filtering available
- Colleyville (27K) - Tarrant County CAD - Residential filtering available
- Trophy Club (12K) - Denton County CAD
- Waxahachie (45K) - NO CAD (Ellis County firewalled)

**Blocked Cities:**
- McKinney (195K) - Angular timeouts
- Allen (105K) - Angular timeouts

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

**McKinney & Allen (EnerGov CSS Angular Timeouts):**
- Platform: Tyler EnerGov Citizen Self Service
- Issue: Angular app loading timeouts, inconsistent page rendering
- Status: Under investigation
- Potential Solution: Increase wait times, use different Playwright configuration

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
- Garland (240K)
- Richardson (120K)
- Lewisville (110K)
- Grapevine (55K)
- Coppell (42K)
- Euless (60K)
- Bedford (50K)
- Hurst (40K)

---

## Next Steps

### Immediate Priorities (High Value)

1. **Implement Sachse SmartGov scraper** (30K pop, working CAD)
   - Create `scrapers/smartgov.py` using Playwright
   - Use correct URL: https://ci-sachse-tx.smartgovcommunity.com
   - Handle Angular SPA rendering
   - Target: ApplicationPublic/ApplicationSearch endpoint

2. **Research remaining high-population cities**
   - Garland (240K) - Likely Accela or similar platform
   - Richardson (120K) - Unknown platform
   - Lewisville (110K) - Unknown platform

3. **Fix McKinney & Allen EnerGov timeouts** (300K+ combined pop)
   - Debug Angular loading issues
   - Increase wait times or adjust Playwright settings
   - High value if solvable (195K + 105K population)

### Medium Priorities

4. **Complete Irving MGO Connect** (240K pop)
   - Finish PDF extraction logic
   - Handle anti-bot detection
   - Implement stealth mode or human-like behavior

5. **Research Forney alternatives** (35K pop)
   - Check cityofforney.com for permit portal
   - Contact building department for public records access
   - Note: Kaufman County CAD ready (partial fields)

6. **Evaluate Weatherford** (35K pop)
   - GovBuilt portal is scrapable
   - Decide if permit data alone (no CAD) is valuable
   - Consider commercial CAD provider for Parker County

### Long-term Considerations

7. **Resolve Ellis County CAD access** (for Waxahachie)
   - Contact Ellis County GIS for public endpoint
   - Evaluate commercial providers (Regrid, TaxNetUSA)
   - Consider static shapefile integration

8. **Evaluate Parker County options** (for Weatherford, Aledo)
   - Contact Parker County CAD for API access
   - Evaluate commercial providers
   - Determine if non-enriched permits are valuable

9. **Expand to remaining cities** (Grapevine, Coppell, Euless, Bedford, Hurst)
   - Platform research required
   - Total population: ~250K combined
   - Likely mix of existing platforms

---

## Success Metrics

### Current Coverage
- **Working Scrapers:** 14 municipalities
- **Combined Population:** ~4.2M (approx 60% of DFW metro)
- **Working CAD Counties:** 4 (Dallas, Tarrant, Collin, Denton)
- **Partial CAD Counties:** 1 (Kaufman - missing building details)

### Target Coverage (If All Implemented)
- **Total Municipalities:** 30
- **Total Population:** ~7M+ (full DFW metro coverage)
- **Total CAD Counties:** 7 (+ Ellis, Parker, Kaufman with limitations)

### High-Value Targets Still Blocked
- Garland (240K) - Not researched
- Irving (240K) - Partial (anti-bot)
- McKinney (195K) - Angular timeout
- Allen (105K) - Angular timeout
- Richardson (120K) - Not researched
- Lewisville (110K) - Not researched

**Combined blocked high-value population:** ~1M+

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
