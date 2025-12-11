# Permit Scraper Session Notes

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
