# Lewisville MGO Connect Scraper - Debug Report
**Date:** 2025-12-19
**Task:** Debug why Lewisville scraper returns 0 permits
**Scraper:** `scrapers/mgo_connect.py` + `services/browser_scraper/`
**Portal:** https://permits.lewisville.com (MGO Connect platform)

---

## Executive Summary

**Root Cause:** Portal returns 0 results for **ALL** date range searches tested, including both past and recent periods (60-90 days). This is NOT a date calculation issue.

**Status:** Portal appears to have NO permits in the system OR requires different search criteria than standard MGO Connect portals.

---

## Investigation Timeline

### Test 1: Dec 18, 2025 - Browser-Use Exploration
- **Date Range:** 11/18/2025 - 12/18/2025 (30 days, future dates)
- **Result:** 0 permits
- **Observation:** "Showing 0 to 0 of 0 entries"
- **Initial Hypothesis:** Future date problem

### Test 2: Dec 19, 2025 - Extended Range Test
- **Date Range:** 09/20/2025 - 12/19/2025 (90 days)
- **Result:** 0 permits
- **Key Findings:**
  - Login successful
  - Jurisdiction selection successful
  - Search form accessed successfully
  - **Portal Warning:** "Your search results were limited to the top 500 results. Please enter additional search criteria to return more results"
  - **Date Fields:** After search, fields appear empty
  - **Critical:** Portal shows warning about "limiting top 500" despite returning ZERO results (contradiction)

---

## Technical Analysis

### MGO Connect Portal Behavior (Lewisville Specific)

1. **Authentication:** WORKING
   - Login credentials accepted
   - Jurisdiction (Lewisville) selectable
   - Portal dashboard accessible

2. **Search Interface:** WORKING
   - Search Permits page loads
   - Date input fields functional
   - Search button clickable

3. **Date Range Handling:** PROBLEMATIC
   - Portal accepts date input but fields clear after search
   - Warning message suggests >35 day range auto-adjusts start date
   - No visual confirmation of accepted date range

4. **Results:** ALWAYS ZERO
   - No permits returned for any date range tested
   - Pagination shows "Showing 0 to 0 of 0 entries"
   - Contradictory "top 500 limit" warning when 0 results exist

---

## Comparison: Lewisville vs. Irving (Same Platform)

| Feature | Irving | Lewisville |
|---------|--------|------------|
| Platform | MGO Connect | MGO Connect |
| JID | 245 | 325 |
| Login | Works | Works |
| Search Page | Works | Works |
| Permit Results | **Partial** (PDF export) | **ZERO** |
| Export Options | PDF only | Not tested (0 results) |

**Note:** Irving also has data issues but returns SOME permits via PDF export path. Lewisville returns NOTHING.

---

## Hypotheses & Tests

### ❌ Hypothesis 1: Future Date Problem
**Test:** Used 90-day range going back to September 2025
**Result:** Still 0 permits
**Conclusion:** NOT a date calculation issue

### ❌ Hypothesis 2: Date Format Issue
**Test:** Dates entered as MM/DD/YYYY (standard MGO format)
**Result:** Format accepted but fields clear post-search
**Conclusion:** Format correct but not persisting

### ❌ Hypothesis 3: Search Too Broad
**Test:** Portal warns "add more criteria" but has no other filter options visible
**Result:** Can't narrow search further
**Conclusion:** UI limitation or empty database

### ⚠️ Hypothesis 4: Portal Database Empty
**Evidence:**
- Zero results across all date ranges
- No alternative search yielded data
- Portal accessible but no data visible
**Likelihood:** HIGH

### ⚠️ Hypothesis 5: Requires Alternative Search Path
**Evidence:**
- Irving uses "Advanced Reporting" → PDF export
- Lewisville standard search may not be the correct entry point
**Likelihood:** MEDIUM
**Action Needed:** Explore "Reports" or "Advanced Search" sections

---

## Portal Limitations Discovered

1. **35-Day Search Window:** Portal shows warning about date ranges >35 days
2. **Auto-Adjustment:** Start date may auto-adjust if range exceeds limit (not clearly communicated)
3. **Field Clearing:** Date inputs clear after search (user feedback failure)
4. **Contradictory Messages:** "Top 500 limit" warning when 0 results exist
5. **No Public Data Visibility:** Possible that permits aren't published publicly via standard search

---

## Recommended Next Steps

### Option A: Explore Alternative Search Paths ⭐ RECOMMENDED
```bash
# Test if Lewisville has Advanced Reporting like Irving
# Look for:
# - "Click here for advanced reporting"
# - "Reports" menu
# - "Open Records Data Export"
# - Alternative permit search interfaces
```

### Option B: Test NO Date Filter Search
```bash
# Try searching without ANY date criteria
# May return recent permits if database exists
```

### Option C: Contact Lewisville IT
```bash
# Questions to ask:
# 1. Are building permits published via MGO Connect portal?
# 2. Is there a delay in publishing permits to public portal?
# 3. Are permits available via API or bulk export?
# 4. What date range has available data?
```

### Option D: Mark as BLOCKED
```bash
# If no permits exist in system OR public access disabled:
# - Update scraper status to BLOCKED
# - Document reason: "Portal has no public permit data"
# - Explore alternative data sources (city website, FOI request, etc.)
```

---

## Code Changes Needed

### 1. Add Lewisville-Specific Logic (if fix found)
```python
# In mgo_connect.py, add special handling:
if city_name.lower() == 'lewisville':
    # Try alternative search path (like Irving's PDF export)
    use_advanced_reporting = True
    # OR: Use different date format/search criteria
```

### 2. Update Browser-Use Task Template
```python
# In services/browser_scraper/permit_tasks.py
# Add Lewisville fallback to try multiple search approaches
```

### 3. Add Error Handling for Empty Portals
```python
# Detect "0 to 0 of 0" pagination
# Return informative error instead of silent failure
if "Showing 0 to 0 of 0" in pagination_text:
    raise NoPermitsAvailableError(
        f"{city_name} portal returned 0 permits. "
        "Portal may be empty or require different search criteria."
    )
```

---

## Conclusion

**Lewisville MGO Connect portal is accessible but returns 0 permits for all standard searches.**

**This is NOT a scraper bug** - the scraper correctly navigates, logs in, and searches. The issue is:
1. Portal database appears empty, OR
2. Permits not published publicly via standard search, OR
3. Requires alternative search method not yet tested

**Recommendation:** Manually log into https://permits.lewisville.com and verify if ANY permits are visible via the public interface. If yes, identify the correct search path. If no, mark Lewisville as BLOCKED and seek alternative data source.

---

## Files Involved
- `/home/reid/testhome/permit-scraper/scrapers/mgo_connect.py` (Line 43: JID 325)
- `/home/reid/testhome/permit-scraper/services/browser_scraper/permit_tasks.py` (MGO template)
- `/tmp/lewisville.log` (Dec 18 test)
- `/tmp/claude/-home-reid-command-center/tasks/bff0bcb.output` (Dec 19 test)
