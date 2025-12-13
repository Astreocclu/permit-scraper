# Session Notes - Permit Scraper

---

## Session: 2025-12-12 (Evening) - DFW Municipality Expansion + Pipeline Run

### Context
- User wanted to expand permit scraping to new DFW municipalities
- Two cities already researched (Sachse SmartGov, Forney MyGov) needed implementation
- Goal: Research best municipalities not currently in system, implement scrapers, run full pipeline

### Work Completed

1. **Research & Analysis**
   - Identified 13 new municipalities with public permit portals
   - Tested MyGov URLs for 9 cities (all confirmed working)
   - Tested eTRAKiT for Keller (complicated - skipped)
   - Confirmed EnerGov CSS URLs for Cedar Hill and DeSoto

2. **New Scrapers Created**
   - `scrapers/mygov_multi.py` - Multi-city MyGov scraper (9 cities)
     - Mansfield, Rowlett, Burleson, Little Elm, Lancaster, Midlothian, Celina, Fate, Venus
     - Uses street-name iteration (address-only search, no wildcards/date filters)
   - `scrapers/smartgov_sachse.py` - Sachse SmartGov scraper (new platform)
     - Angular SPA with pagination via `ApplicationSearchResults.gotoPage()`
     - Fixed pagination: clicks page links instead of JS call (scroll error)

3. **EnerGov CSS Config Updates**
   - Added Cedar Hill and DeSoto to `scrapers/citizen_self_service.py`

4. **Pipeline Run**
   - Loaded 2,478 permits (Cedar Hill 999, DeSoto 499, Sachse 980)
   - Enriched with CAD data (Sachse working well - Collin/Dallas County)
   - Scored 917 leads total

5. **Commits Made**
   - `7bfcdee` - fix(sachse): add pagination support for SmartGov scraper
   - `c7a5199` - docs: add Sachse SmartGov to CLAUDE.md
   - `a96cccc` - feat: add Sachse SmartGov scraper
   - `692866d` - docs: update CLAUDE.md with new cities and scrapers
   - `d025c4d` - feat: add multi-city MyGov scraper for 9 DFW cities
   - `d8c37c2` - feat: add Cedar Hill and DeSoto to EnerGov CSS scraper

### Current State

**Scoring Results:**
| Tier | Count | Best Categories |
|------|-------|-----------------|
| A | 8 | 3 fence, 1 pool, 1 foundation, 1 roof, 1 commercial pool |
| B | 37 | 8 plumbing, 6 electrical, 5 fence, 4 outdoor living, 3 roof |
| C | 251 | 75 roof, 51 plumbing, 23 electrical |
| U | 621 | Unverified (mostly "other" category) |

**Top Leads Found (Sachse):**
- Pool: $473K home (1 day old), $667K home (24 days old)
- Foundation: $775K home (24 days old), $472K home (22 days old)

**Data Quality Issue Discovered:**
- Cedar Hill EnerGov CSS Excel export ignores date filters
- Exported all historical data back to 2008 instead of recent permits
- Cleaned up: deleted 976 old permits, kept 23 recent ones

### Next Steps

1. **Fix EnerGov CSS Scraper** (Priority)
   - Add DOM-only scraping mode for portals where Excel export ignores filters
   - Cedar Hill confirmed to have this bug
   - Test if DeSoto/other EnerGov portals have same issue

2. **Cedar Hill/DeSoto CAD Enrichment**
   - Dallas County CAD API not finding addresses for these cities
   - Need to debug address normalization or API query format

3. **MyGov Optimization** (Low priority)
   - Current street-name iteration is slow (~290 permits in 5 min)
   - No optimization path available (portal has no date filters, wildcards, or export)
   - Can run in background overnight

4. **Keller eTRAKiT** (Deferred)
   - Permit search doesn't support prefix wildcards
   - Different permit format than other eTRAKiT cities
   - Needs more research

### Notes

**Bugs Discovered:**
- EnerGov CSS Excel export ignores search filters (date range, sort order)
- SmartGov `gotoPage()` JS function throws scroll error - use click instead
- MyGov portals have no bulk export, date filters, or wildcard search

**Pre-filter Statistics (from 6,290 permits):**
- Too old (>90 days): 4,652 (74%)
- Junk project: 433 (7%)
- Production builder: 279 (4%)
- Actually scored: 917 (15%)

**Yield Analysis:**
- MyGov: ~3,480 permits/hour (slow, street iteration)
- EnerGov CSS: ~16,760 permits/hour (fast, Excel export)
- SmartGov: ~600 permits/hour (pagination required)

### Key Files

```
scrapers/
├── mygov_multi.py              # NEW - 9 MyGov cities
├── smartgov_sachse.py          # NEW - Sachse SmartGov
├── citizen_self_service.py     # UPDATED - Added Cedar Hill, DeSoto
└── etrakit_fast.py             # Keller config exists but skipped

scripts/
├── load_permits.py             # Load raw JSON to PostgreSQL
├── enrich_cad.py               # CAD enrichment (Tarrant, Denton, Dallas, Collin, Kaufman)
└── score_leads.py              # AI scoring with DeepSeek

exports/                        # Scored leads by category/tier
├── luxury_outdoor/pool/tier_a.csv
├── structural/foundation/tier_b.csv
├── home_exterior/roof/tier_a.csv
└── ...

docs/plans/
└── 2025-12-12-dfw-municipality-expansion.md  # Implementation plan
```

### Database State

```
Total permits: 33,083
Properties: 11,852
Scored leads: 6,804

Recent permits by city:
  Cedar Hill: 23 (after cleanup)
  DeSoto: 478
  Sachse: 457
```

---

## Session: 2025-12-12 - Property Image Scraper Implementation

### Context
- User wanted to build a service to fetch property images for a pool visualizer pipeline
- Primary source: CAD (County Appraisal District) portals
- Backup source: Redfin real estate listings
- Starting state: Permit scraper codebase with working scrapers for DFW municipalities

### Work Completed
1. **Full implementation of property image scraper service** (7 tasks, all completed)
   - Task 1: Module structure and PropertyImage dataclass
   - Task 2: CAD account lookup utility (ArcGIS APIs for 4 DFW counties)
   - Task 3: TAD image scraper (Playwright-based)
   - Task 4: Redfin backup scraper (Playwright with rate limiting)
   - Task 5: Main orchestrator (fetch_property_image)
   - Task 6: Media directory and integration tests
   - Task 7: CLI verification

2. **Files created:**
   - `services/property_images/__init__.py`
   - `services/property_images/models.py` - PropertyImage dataclass
   - `services/property_images/cad_lookup.py` - ArcGIS API wrapper (4 counties)
   - `services/property_images/tad_scraper.py` - TAD.org Playwright scraper
   - `services/property_images/redfin_scraper.py` - Redfin backup scraper
   - `services/property_images/image_fetcher.py` - Main orchestrator + CLI
   - `tests/services/property_images/` - 5 test files, 11 unit tests
   - `media/property_images/.gitkeep` - Image storage directory
   - `docs/plans/2025-12-12-property-image-scraper.md` - Implementation plan

3. **Merged to main branch** from `fix/scraper-hardening`

### Current State
- **CAD lookup works perfectly** - API-based, no browser needed, returns account numbers
- **TAD scraper has issues:**
  - TAD.org uses Cloudflare and blocks after 2-3 requests
  - Even when TAD loads, it doesn't show property photos (only data + Google Map)
  - TAD is NOT a viable source for property images
- **Redfin scraper has issues:**
  - Timeouts on homepage/search
  - Uses `networkidle` which is slow/unreliable
  - Standard Playwright detected by anti-bot measures
  - No stealth measures implemented

### Next Steps
1. **Fix Redfin scraper** (highest priority for backyard photos):
   - Replace `wait_until="networkidle"` with `domcontentloaded`
   - Add `playwright-stealth` for anti-detection
   - Use direct URL construction instead of search
   - Implement retry with exponential backoff
   - Navigate photo gallery to find backyard images

2. **Alternative approaches to consider:**
   - Have homeowners upload their own backyard photos (most reliable)
   - Mapbox Static API (50k free/month, includes satellite)
   - Accept partial success rate from Redfin

3. **Not viable (discovered during session):**
   - TAD.org - Cloudflare blocks + no photos available
   - Google Maps API - User banned due to $300 overcharge
   - Nearmap/Bing Maps - $2-3k/year subscriptions

### Notes
- **Gemini CLI quota exhausted** - resets in ~21 hours. Uses Google AI Studio free tier (oauth-personal). Can switch to API key from aistudio.google.com for 1500 req/day.
- **Google API Key:** [REDACTED - leaked, regenerate in GCP console] (rate limit: 30 seconds between requests)
- **SQL injection fix applied** to CAD lookup WHERE clauses (escaping single quotes)
- **Rate limiting in place:** TAD 2s delay, Redfin 3-5s random delay
- All 11 unit tests pass; integration tests pass but slow (~5 min)
- **Redfin scraper hardened (2025-12-12):**
  - Added playwright-stealth for anti-detection
  - Replaced networkidle with domcontentloaded + explicit waits
  - Added retry with exponential backoff (3 attempts: 2s, 4s, 8s)

### Key Files
```
services/property_images/
├── __init__.py              # Exports: PropertyImage, fetch_property_image
├── models.py                # PropertyImage dataclass
├── cad_lookup.py            # lookup_cad_account() - WORKING
├── tad_scraper.py           # fetch_tad_image() - BLOCKED BY CLOUDFLARE
├── redfin_scraper.py        # fetch_redfin_image() - NEEDS FIXES
└── image_fetcher.py         # fetch_property_image() + CLI

tests/services/property_images/
├── test_cad_lookup.py       # 4 tests
├── test_tad_scraper.py      # 3 tests
├── test_redfin_scraper.py   # 2 tests
├── test_image_fetcher.py    # 2 tests
└── test_integration.py      # 2 integration tests
```

### Usage
```python
from services.property_images import fetch_property_image, PropertyImage

result = await fetch_property_image(
    address="3705 DESERT RIDGE DR, Fort Worth TX 76116",
    city="Fort Worth",
    permit_id="PP25-21334"
)
# result.success, result.image_path, result.source, result.image_type
```

CLI:
```bash
python -m services.property_images.image_fetcher "ADDRESS" "CITY" "PERMIT_ID"
```
