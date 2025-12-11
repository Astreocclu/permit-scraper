
## Pending Tasks

### Frisco Trade Permits - Re-scrape for Dates
**Added:** 2025-12-10 16:15 UTC
**Priority:** Medium
**Estimated Time:** ~1 hour

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
