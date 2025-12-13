# Session Notes - Permit Scraper

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
