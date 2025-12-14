# Permit Scraper TODO

## Priority Tasks

- [ ] **Southlake Batch Scrape**: Complete execution of `southlake_residential_batch.py` to capture all 14 residential permit types
- [ ] **Westlake Full Harvest**: Run `mygov_westlake.py` using the 367 addresses in `data/westlake_addresses.json`
- [ ] **MGO Connect Fixes**: Debug Playwright I/O blocking error for Irving; implement PDF parsing
- [x] **EnerGov Expansion**: McKinney and Allen already working (tested Dec 2024)
- [ ] **Pre-filter Classification**: Implement `scripts/classify_leads.py` to filter permits using DeepSeek *before* expensive CAD enrichment

## Pending Tasks

### Frisco Trade Permits - Re-scrape for Dates
**Priority:** Medium

1,368 Frisco trade permits (electrical, mechanical, building alterations) need dates.
These are B25-* permits that aren't in the residential PDF reports.

**Approach:** Scrape eTRAKiT detail pages one-by-one:
```bash
# For each permit_id without date:
# 1. Load https://etrakit.friscotexas.gov/etrakit/Search/permit.aspx
# 2. Search for permit_id
# 3. Click into detail page
# 4. Extract issued_date
# 5. Update database
```

**Permits affected:** ~1,368 (B25-00001 through B25-00820 range, trade permits)

**Why deferred:** Time-intensive; residential permits prioritized for now.

---

## Recently Added (Dec 2024)

### Working
- **Hurst** (EnerGov CSS) - 100 permits tested
- **Farmers Branch** (EnerGov CSS) - 100 permits tested
- **Coppell** (EnerGov CSS) - 57 permits tested
- **University Park** (MyGov) - Config added, 0 permits found (low activity)
- **Forney** (MyGov) - Config added, 0 permits found (may need different search)

### Needs Investigation
- **The Colony** (eTRAKiT) - Config added but portal has different interface (Search By dropdown)
- **North Richland Hills** (EnerGov CSS) - URL works but different page structure, needs custom selectors

### Blocked
- **Duncanville** - Accela URL not found, may use different platform or require login

---

## Backlog

- [ ] **Carrollton scraping improvements** - Currently gets ~258 permits due to portal 20-result limit. Could run multiple times with different search strategies.
- [ ] **MGO Connect anti-bot** - Irving, Denton, Lewisville, Cedar Hill, Duncanville all blocked. Would need playwright-stealth + residential proxies.
- [ ] **More eTRAKiT cities** - Flower Mound fix pattern could apply to other eTRAKiT cities with wrong prefix configs.
- [ ] **Database cleanup** - Drop dead `leads_lead` table (legacy Django model)
