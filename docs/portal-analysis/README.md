# Portal Analysis Reports

This directory contains detailed technical investigations of city permit portals, especially those that are blocked or require special handling.

## Available Reports

### North Richland Hills
**File:** `north_richland_hills.md`
**Status:** ❌ BLOCKED - Tyler SSO required
**Summary:** Portal enforces Tyler Identity authentication with no anonymous fallback. Canceling SSO results in internal error and empty page.

---

### University Park
**File:** `university_park.md`
**Status:** ❌ NO PORTAL - skip city
**Summary:** MyGov endpoint returns /notfound; city never enabled a public portal.

---

## Report Format

Each portal analysis includes:
1. **Executive Summary** - Quick verdict on scrapability
2. **Technical Findings** - Step-by-step portal behavior
3. **Test Scripts** - How findings were validated
4. **Scraperability Assessment** - Can we scrape? Why/why not?
5. **Workarounds** - Possible solutions (if any)
6. **Recommendations** - Next steps

---

## When to Create a Portal Analysis

Create a new analysis when:
- Portal returns authentication errors
- Scraper consistently gets 0 permits
- Portal behavior is unclear or inconsistent
- Need to document why a city is blocked

---

## Related Documentation

- `/AUTH_REQUIRED.md` - List of cities needing authentication
- `/docs/archive/plans/` - Implementation plans referencing these analyses
- `/docs/archive/portal-analysis/university_park_summary.txt` - Archived short summary (2026-02-05)
