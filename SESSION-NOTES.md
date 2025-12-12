# Permit Scraper Session Notes

---

## Session: 2025-12-12 - Residential Permit Filtering & Westlake Harvester

### Context
- User wanted to fix Southlake/Westlake scrapers which were returning commercial permits instead of residential
- Goal: Filter for residential-only permits at the portal level, not just post-processing
- Also needed to fix Westlake scraper which was guessing addresses instead of using verified data

### Work Completed

1. **Gemini Collaborative Planning** (3 rounds)
   - Analyzed Southlake CSS portal and Westlake MyGov portal
   - Discovered Southlake needs portal-level permit type filtering
   - Discovered Westlake has API endpoint for address harvesting (not autocomplete)

2. **Southlake Post-Processing Filter** (`scrapers/filters.py`)
   - Created `filter_residential_permits()` function with TDD (4 tests)
   - Keywords: residential, pool, spa, roof, foundation, accessory, patio, remodel, addition
   - Excludes: commercial, business, sign, fire, certificate of occupancy
   - Commit: `db8caf1`

3. **Integrated Filter into CSS Scraper** (`scrapers/citizen_self_service.py`)
   - Added import and filter call for Southlake
   - Filter runs after Excel export, before save
   - Commit: `ec35787`

4. **Westlake API Discovery** (Spike)
   - Discovered API endpoint: `https://public.mygov.us/westlake_tx/getLookupResults`
   - POST with `address_search` param returns `[{address, location_id}, ...]`
   - Much better than guessing addresses!
   - Commit: `a283d7d`

5. **Westlake Address Harvester** (`scrapers/westlake_harvester.py`)
   - Uses discovered API to harvest real addresses
   - 367 addresses harvested from 16 residential streets
   - Streets: Cedar Elm, Post Oak, Vaquero, Paigebrooke, Dove Rd, etc.
   - Saved to `data/westlake_addresses.json`
   - 6 TDD tests
   - Commit: `463d4e7`

6. **Updated Westlake Scraper** (`scrapers/mygov_westlake.py`)
   - Now loads harvested addresses instead of guessing
   - Falls back to brute force if harvested file missing
   - Commit: `14aad97`

7. **Added Permit Type Filtering to CSS Scraper** (`scrapers/citizen_self_service.py`)
   - New `--permit-type` / `-t` argument
   - Selects permit type in Advanced Search dropdown
   - Uses "Export Current View" when filtering (gets filtered results only)
   - Includes permit type in export filename
   - Commit: `e58b183`

8. **Created Batch Residential Scraper** (`scrapers/southlake_residential_batch.py`)
   - Iterates through 14 residential permit types
   - Downloads each type separately
   - Partial success: 90 permits from 8 types (some timing issues)

### Current State

**Southlake Permit Types Found (54 residential):**
- High-value: `Residential New Building (Single Family Home)`, `Residential Remodel`, `Pool (Residential)`, etc.
- Full list discovered programmatically from portal

**Batch Scraper Results (partial run):**
| Type | Permits |
|------|---------|
| Residential Remodel | 17 |
| Residential Addition Conditioned & Uncond | 31 |
| Pool (Residential) | 10 |
| Mechanical Permit (Residential) | 10 |
| Residential Reroof | 11 |
| Solar Panel - Residential | 10 |
| Residential New Building (Duplex) | 1 |
| **TOTAL** | **90** |

**Westlake:**
- 367 harvested addresses ready to use
- Scraper updated to use harvested addresses
- Full scrape not yet run (would take time with 367 addresses)

### Next Steps

1. **Complete Southlake batch scrape** - Run `southlake_residential_batch.py` with better error recovery to get all types
2. **Run Westlake scraper** - Use harvested addresses to get residential permits
3. **Score new permits** - Load, enrich, and score the residential permits
4. **Consider expanding date range** - Current results are limited; older permits may have more data

### Notes

**Southlake CSS Portal Structure:**
- Permit Type dropdown: Select element with `--Select Permit Type--` first option
- Has 136 permit types total, 54 residential
- "Export Current View" exports filtered results only
- "Export first 500 Results" exports unfiltered

**Westlake MyGov API:**
- Endpoint: `POST https://public.mygov.us/westlake_tx/getLookupResults`
- Body: `address_search=<search_term>` (form-encoded)
- Returns: `[{"address": "...", "location_id": 123}, ...]`
- Works with partial street names (e.g., "Vaquero" returns all Vaquero addresses)

**Timing Issues:**
- CSS scraper has timing issues in headless mode
- Batch scraper works better with `headless=False`
- Some permit types fail to find dropdown on retry (need page refresh between types)

### Key Files

**New/Modified:**
- `scrapers/filters.py` - Residential permit filter (NEW)
- `scrapers/westlake_harvester.py` - Address harvester using API (NEW)
- `scrapers/southlake_residential_batch.py` - Batch scraper for all residential types (NEW)
- `scrapers/westlake_spike.py` - API discovery spike (MODIFIED)
- `scrapers/citizen_self_service.py` - Added `--permit-type` arg (MODIFIED)
- `scrapers/mygov_westlake.py` - Uses harvested addresses (MODIFIED)

**Test Files:**
- `tests/test_filters.py` - 4 tests for residential filter
- `tests/test_westlake_harvester.py` - 6 tests for harvester

**Data Files:**
- `data/westlake_addresses.json` - 367 harvested addresses
- `data/downloads/southlake_*.xlsx` - Downloaded residential permits

**Plans:**
- `docs/plans/2025-12-11-residential-permit-filtering.md` - Implementation plan

---

## Session: 2025-12-11 (Late PM) - CSS Scraper Fixes & High-Value Suburbs

### Context
- User wanted to scrape Westlake, Southlake, and Colleyville (affluent DFW suburbs)
- CSS (Citizen Self Service / EnerGov) scraper was broken - pagination not working, date filter not applying
- Goal: Get 1000+ leads from each city, enrich with CAD data, score with AI

### Work Completed

1. **Fixed CSS Scraper Module Selection** (`scrapers/citizen_self_service.py`)
   - **Problem**: JavaScript DOM manipulation wasn't selecting "Permit" module correctly
   - **Fix**: Changed to Playwright's native `select_option()` with Angular value `'number:2'` (lines 213-231)
   - Key selector: `#SearchModule` with value `'number:2'`

2. **Fixed CSS Date Filter** (`scrapers/citizen_self_service.py`)
   - **Problem**: Date inputs not being found - complex DOM traversal failing
   - **Fix**: Use direct input IDs `#ApplyDateFrom` and `#ApplyDateTo` (lines 259-281)
   - Now correctly fills 60-day date range

3. **Fixed Export Modal Handling** (`scrapers/citizen_self_service.py`)
   - **Problem**: Export button opens modal asking for filename, not direct download
   - **Fix**: Added modal detection, filename input, and "Ok" button click (lines 130-185)
   - Modal fields: filename input, "Export first 1000 Results" radio, Ok/Cancel buttons

4. **Fixed CSV/Excel Parsing** (`scrapers/utils.py`)
   - **Problem**: Export is CSV despite `.xlsx` extension, `pd.read_excel()` failed
   - **Fix**: Try CSV first, fall back to Excel (lines 576-587)
   - Added column mappings: `'case number'` → `permit_id`, `'project name'` → `description`

5. **Fixed load_permits.py**
   - Added `dotenv` loading for DATABASE_URL
   - Added skip for permits without addresses (NOT NULL constraint)

6. **Scraped 3 Cities:**
   | City | Permits | Notes |
   |------|---------|-------|
   | Westlake | 180 | MyGov platform, all commercial |
   | Colleyville | 1,000 | CSS platform, mixed residential |
   | Southlake | 500 | CSS platform, mostly commercial |

7. **Loaded, Enriched, and Scored:**
   - Loaded 1,138 permits to database
   - CAD enrichment: 7,050 properties enriched total
   - Scored permits and exported to CSV

### Current State

**Scraping Results:**
- Colleyville: 1,000 permits (468 with addresses loaded)
- Southlake: 500 permits (498 loaded) - BUT mostly commercial electrical/antenna
- Westlake: 180 permits (172 loaded) - BUT mostly commercial (Solana office campus)

**High-Value Leads Found (Colleyville only - Tier A):**
| Owner | Property Value | Project | Score |
|-------|---------------|---------|-------|
| JACKSON, JAMES L | $970,729 | Patio cover + grill area | 92 |
| SINUNU, STEPHEN | $961,390 | Masonry fireplace | 88 |
| SHATTO, BRIAN | $1,375,520 | Custom patio door | 85 |
| CALVERT, MICHAEL J | $867,105 | Attached patio cover | 85 |
| LATORRE FAMILY TRUST | $3,920,391 | (enriched, not scored yet) | - |

**Issue Discovered:**
- Southlake scraped 223 Commercial Electrical + 191 Commercial New Building = almost ALL commercial
- Westlake scraped mostly Solana Blvd office permits - commercial, not residential
- Only Colleyville had good residential outdoor living permits

### Next Steps

1. **Re-scrape Southlake with residential filter** - the CSS portal may have a permit type filter, or need to search for specific residential types
2. **Find Westlake residential portal** - MyGov may have separate residential module, or permits may be filed under different search criteria
3. **Run more Colleyville scoring** - only scored 37 permits, have 468 loaded
4. **Consider expanding date range** - 60 days may be too narrow for smaller cities

### Notes

**CSS Portal Structure (EnerGov):**
- Module dropdown: `#SearchModule` with values like `'number:2'` (Permit), `'number:3'` (Plan)
- Date inputs: `#ApplyDateFrom`, `#ApplyDateTo`, `#IssueDateFrom`, `#IssueDateTo`
- Export opens modal with filename input and radio buttons
- Export is CSV format despite `.xlsx` extension
- Results limited to 1000 per export

**Westlake/Southlake Issue:**
The scrapers worked correctly, but the portals returned commercial permits:
- Southlake: Commercial electrical permits (antenna installations, etc.)
- Westlake: Solana Blvd office complex permits (Wells Fargo, Glenstar, etc.)
- These cities may have low residential permit volume, or residential permits are filed differently

**Colleyville Success:**
- Only city with good residential leads
- Outdoor living projects: patio covers, fireplaces, door replacements
- Property values $500K-$3.9M - very affluent
- 10 Tier A leads found, 6 in luxury outdoor living category

### Key Files

- `scrapers/citizen_self_service.py` - Fixed CSS scraper (lines 213-231, 259-281, 130-185)
- `scrapers/utils.py` - CSV parsing fix (lines 576-587), column mappings (lines 521-527)
- `scripts/load_permits.py` - Added dotenv, address validation
- `scripts/enrich_cad.py` - Added dotenv
- `scripts/score_leads.py` - Added dotenv
- `westlake_raw.json` - 180 permits (commercial)
- `colleyville_raw.json` - 1000 permits (mixed, good residential)
- `southlake_raw.json` - 500 permits (commercial)
- `exports/luxury_outdoor/outdoor_living/tier_a.csv` - 6 high-value Colleyville leads

---

## Session: 2025-12-11 (PM) - Flower Mound & Carrollton Scraper Expansion

### Context
- User wanted to expand scraper coverage to new DFW cities
- Started with `/startuppermit` and `/geminiplan all of them` to plan fixes for:
  1. Research unknown portals (Garland, Carrollton, Flower Mound)
  2. Fix MGO Connect scrapers (Irving, Denton, Lewisville) - anti-bot blocked
  3. Fix MyGov scrapers (Rowlett, Grapevine) - URL 404s
- Gemini quota was exhausted, proceeded with Claude-based planning

### Work Completed

1. **Portal Research Results:**
   - **Flower Mound**: eTRAKiT platform (same as Frisco) - https://etrakit.flower-mound.com
   - **Carrollton**: CityView platform - https://cityserve.cityofcarrollton.com/CityViewPortal/Permit/Locator
   - **Garland**: No online portal (in-person only) - NOT SCRAPEABLE
   - **Rowlett/Grapevine (MyGov)**: Require contractor login / .exe client - NOT SCRAPEABLE

2. **Fixed Flower Mound Scraper** (`scrapers/etrakit_fast.py`)
   - **Problem**: Wrong prefixes (`BP25`, `25-`) - only found 179 permits
   - **Root cause**: Flower Mound uses type-based prefixes (`BP`, `EL`, `PL`, `ME`, `RO`, etc.) not year-based
   - **Fix**: Updated config with 23 correct prefixes (lines 27-58)
   - **Fix**: Improved permit ID extraction to use link text first (more reliable)
   - **Result**: 897 permits (was 179) - 5x improvement

3. **Created Carrollton CityView Scraper** (`scrapers/cityview.py`)
   - New scraper for CityView platform
   - Portal limits to 20 results per search (hard limit)
   - Implemented multi-search strategy with 114 granular search terms
   - Added periodic saves and crash recovery
   - **Result**: 258 permits collected

4. **Archived Dead Scrapers:**
   - Moved `scrapers/mygov.py` to `_archive/2025-12-11/`
   - MyGov requires login/desktop client - not scrapeable

5. **Updated Documentation:**
   - `SCRAPER_STATUS.md` updated with new coverage
   - `docs/plans/2025-12-11-expand-scraper-coverage.md` created

6. **Loaded, Enriched, and Scored New Permits:**
   - Loaded 897 Flower Mound + 258 Carrollton permits to PostgreSQL
   - CAD enrichment running (80%+ complete when scoring started)
   - Scored all new permits:
     - Flower Mound: 193 scored (27 Tier A, 63 Tier B, 103 Tier C)
     - Carrollton: 54 scored (4 Tier A, 11 Tier B, 39 Tier C)

### Current State

**New scrapers working:**
| City | Platform | Scraper | Permits |
|------|----------|---------|---------|
| Flower Mound | eTRAKiT | `etrakit_fast.py` | 897 |
| Carrollton | CityView | `cityview.py` | 258 |

**Total working scrapers: 9** (was 7)
- Dallas, Fort Worth, Grand Prairie (Accela)
- Frisco, Flower Mound, Plano (eTRAKiT)
- Arlington (Socrata API)
- Carrollton (CityView)

**Scored leads exported to:**
- `exports/home_systems/hvac/tier_a.csv` - 13 HVAC leads ($500K-$2.6M properties)
- `exports/luxury_outdoor/pool/tier_a.csv` - 3 pool leads
- `exports/home_systems/plumbing/tier_a.csv` - plumbing leads
- Plus Tier B/C across categories

### Next Steps

1. **Carrollton scraping could be improved** - currently gets ~258 permits due to portal limitations. Could run multiple times with different search strategies to accumulate more.

2. **MGO Connect remains blocked** - Irving, Denton, Lewisville, Cedar Hill, Duncanville all blocked by anti-bot. Would need playwright-stealth + residential proxies to attempt.

3. **Consider adding more eTRAKiT cities** - Flower Mound fix pattern could apply to other eTRAKiT cities with wrong prefix configs.

### Notes

**Flower Mound Prefix Discovery:**
The key insight was that Flower Mound uses COMPLETELY different permit formats than Frisco:
- Frisco: `B25-00001` (year-based)
- Flower Mound: `EL-00-0026`, `BP13-01542`, `RER-11-3040` (type-based)

Working prefixes for Flower Mound: `BP`, `EL`, `PL`, `ME`, `RO`, `RF`, `AC`, `HV`, `RE`, `RER`, `CO`, `DE`, `PO`, `FE`, `IR`, `FR`, `SW`, `DR`, `GR`, `SI`, `PC`, `COM`, `AD`

**CityView Portal Limitations:**
- Hard limit of 20 results per search
- No pagination beyond first page
- Must do many granular searches and deduplicate
- Playwright crashes on long runs (EPIPE errors) - added periodic saves

**Closed as Not Scrapeable:**
- Garland (240K pop) - No online portal
- Rowlett (68K) - Requires contractor login
- Grapevine (55K) - Requires desktop .exe client

### Key Files

- `scrapers/etrakit_fast.py` - Fixed Flower Mound config (lines 27-58, 63-130)
- `scrapers/cityview.py` - NEW Carrollton scraper
- `SCRAPER_STATUS.md` - Updated coverage documentation
- `docs/plans/2025-12-11-expand-scraper-coverage.md` - Implementation plan
- `_archive/2025-12-11/mygov.py` - Archived dead scraper
- `flower_mound_raw.json` - 897 permits
- `carrollton_raw.json` - 258 permits
- `exports/` - Scored leads by category/tier

---

## Session: 2025-12-11 - Lead Scoring & Pre-Filter Pipeline Analysis

### Context
- User wanted to score unscored enriched permit records
- Initial DeepSeek API key was expired, user topped up credits
- After scoring, discovered 75% of permits were being discarded AFTER enrichment (wasted effort)

### Work Completed

1. **Ran lead scoring on enriched permits**
   - Scored 1,163 permits via DeepSeek AI
   - Results: 107 Tier A, 103 Tier B, 953 Tier C
   - Saved to `clients_scoredlead` table
   - Exported to `exports/` directory by trade_group/category/tier

2. **Fixed FK constraint bug in `scripts/score_leads.py`**
   - Line 549-616: `save_scored_leads()` function
   - Issue: `cad_property_id` was set to address even if property didn't exist in `leads_property`
   - Fix: Added lookup to check if property exists first, set NULL if not found
   - Added per-record commits with rollback on failure

3. **Analyzed pipeline inefficiency**
   - 75% of permits discarded by pre-filter in scoring step
   - Discard reasons: no data (50%), too old >90 days (36%), junk projects (10%), production builders (4%)
   - Problem: Enrichment happens BEFORE filtering, wasting CAD API calls

4. **Investigated "would_score" permits (1,087)**
   - Found filter gaps: "ashton dallas" not in production builder list, "sewer line repair" not caught by "sewer repair"
   - Fort Worth description field is chaotic - no consistent pattern for contractor names

5. **Started Gemini planning for pre-filter solution** (incomplete)
   - Proposed: Add DeepSeek classification BEFORE enrichment
   - Architecture: New `permit_classifications` sidecar table (avoids Django schema issues)
   - Gemini got stuck in tool-calling loop, planning incomplete

### Current State

**Database counts:**
| Table | Count |
|-------|-------|
| leads_permit | 7,598 |
| leads_property | 7,705 |
| clients_scoredlead | 3,127 |
| Enriched (success) | 6,186 |
| Enriched (failed) | 1,516 |
| Unscored but enriched | 2,619 |

**Scored leads by tier:**
- Tier A: 209
- Tier B: 336
- Tier C: 2,582

**Top cities:** Arlington (3,274), Dallas (2,257), Fort Worth (751)

### Next Steps

1. **PRIORITY: Implement pre-filter classification**
   - Create `scripts/classify_leads.py`
   - Add `permit_classifications` sidecar table
   - Call DeepSeek to classify permits BEFORE enrichment
   - Modify `enrich_cad.py` to skip discarded permits

2. **Fix filter gaps in scoring**
   - Add "ashton dallas" to production builders list
   - Add "sewer line" to junk projects
   - Consider: Should classification replace regex filtering entirely?

3. **Re-run scoring** on the 1,087 "would_score" permits that slipped through

### Notes

**DeepSeek API:**
- Key in `.env`: `DEEPSEEK_API_KEY`
- Same key used in contractor-auditor project
- Cost: ~$0.14/1M input tokens (very cheap)

**Pre-filter prompt design (from Gemini planning):**
- KEEP: Pool, patio, addition, remodel, kitchen, bath, roof replacement, fence, deck, pergola, ADU
- DISCARD: Production builders (DR Horton, Lennar, M/I Homes, etc.), sewer, water heater, gas line, demo, fire sprinkler, electrical panel, shed, irrigation, Habitat for Humanity, City of, ISD, church

**Architecture decision:** Use sidecar table `permit_classifications` instead of modifying `leads_permit` to avoid breaking Django ORM in contractor-auditor.

**Data quality issue:** Fort Worth descriptions are a dumping ground - contractor names, addresses, person names, project descriptions all mixed in. Can't reliably parse.

### Key Files

- `scripts/score_leads.py` - Lead scoring with DeepSeek (modified this session)
- `scripts/enrich_cad.py` - CAD enrichment (needs modification for pre-filter)
- `scripts/load_permits.py` - Permit loading
- `.env` - Contains DEEPSEEK_API_KEY, DATABASE_URL
- `exports/` - CSV exports by trade_group/category/tier
