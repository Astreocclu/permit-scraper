# Sachse SmartGov Platform Research Report

**Date:** December 12, 2025
**Researcher:** AI Assistant
**Project:** Permit Scraper - Sachse, TX

---

## Executive Summary

The Sachse, TX SmartGov permit portal **IS SCRAPABLE** with public access to permit/application data.

**Scrapability Rating:** Easy-Medium
**Recommendation:** Proceed with scraper development using Playwright

---

## Critical Finding: URL Correction

**IMPORTANT:** The originally provided URL was incorrect and returns a 404 error.

- **INCORRECT URL (404):** `https://pl-sachse-tx.smartgovcommunity.com/Public/Home`
- **CORRECT URL (200):** `https://ci-sachse-tx.smartgovcommunity.com`

The correct domain pattern uses `ci-sachse-tx` instead of `pl-sachse-tx`.

---

## Key Findings

### 1. Public Access: YES
- No login required to access the portal
- Public permit/application search is available
- Direct URL for application search: `https://ci-sachse-tx.smartgovcommunity.com/ApplicationPublic/ApplicationSearch`

### 2. Framework: Angular
- The site is built with Angular (Single Page Application)
- Requires JavaScript rendering
- Must use Playwright or similar browser automation tool
- Standard HTML parsing (BeautifulSoup) will NOT work

### 3. Permit Search Functionality: YES
- Search page found at `/ApplicationPublic/ApplicationSearch`
- Search interface allows queries by permit/license number, address, or name
- Requires at least 2 characters minimum for search
- "Advanced Search" link is also available

### 4. API Endpoints Discovered
The following key JavaScript files were detected:
- `ApplicationSearchHelper.js` - Likely contains search-related API logic
- `parcel.js` - Parcel search functionality

Total API-like requests captured: 66 during exploration

### 5. Network Infrastructure
- Hosted on AWS (Elastic Load Balancer in us-west-2)
- Powered by ASP.NET backend
- Uses Granicus SmartGov platform (version 2025.20)

---

## Portal Structure

### Main Sections
1. **My Portal** - View applications and inspection results (public access, no login required for search)
2. **Public Notices** - Find and review public notice announcements
3. **Parcel Search** - Find and review parcel information
4. **Reports** - Additional reporting features
5. **Documents** - Document access

### Application Search Interface
- **URL:** `https://ci-sachse-tx.smartgovcommunity.com/ApplicationPublic/ApplicationSearch`
- **Search Field:** "Enter a permit or license number, address, or name"
- **Minimum Length:** 2 characters
- **Advanced Search:** Available via link in top-right

---

## Scrapability Assessment

### Difficulty Level: Easy-Medium

**Easy Aspects:**
- Public access (no authentication required)
- Clean URL structure
- Direct search endpoint available
- No obvious rate limiting or bot detection (during testing)

**Medium Complexity:**
- Angular SPA requires JavaScript rendering
- Must use Playwright/Selenium (not simple HTTP requests)
- May need to reverse-engineer search API calls for efficiency
- Dynamic content loading

### Technical Requirements
1. **Playwright** (already available in project)
2. **Python 3** with async/await support
3. **Headless browser** for production scraping
4. **Wait strategies** for Angular content loading

---

## Recommended Scraping Strategy

### Option 1: Browser Automation (Recommended for MVP)
**Approach:** Use Playwright to interact with the search interface
- Navigate to application search page
- Fill search field with query
- Wait for results to load
- Extract data from rendered HTML
- Pagination handling if needed

**Pros:**
- Works exactly like a user
- Handles all Angular rendering automatically
- Less likely to break on minor updates

**Cons:**
- Slower than direct API calls
- More resource-intensive (requires full browser)

### Option 2: API Reverse Engineering (Future Optimization)
**Approach:** Monitor network traffic to find direct API endpoints
- Capture search API requests
- Replicate request headers/parameters
- Make direct HTTP calls instead of browser automation

**Pros:**
- Much faster
- Less resource usage
- Can scale better

**Cons:**
- Requires reverse engineering
- May break if API changes
- Might need to handle authentication tokens/headers

---

## Testing Results

### Successful URLs
- Main Portal: `https://ci-sachse-tx.smartgovcommunity.com` - **200 OK**
- Public Home: `https://ci-sachse-tx.smartgovcommunity.com/Public/Home` - **200 OK**
- Application Search: `https://ci-sachse-tx.smartgovcommunity.com/ApplicationPublic/ApplicationSearch` - **200 OK**
- Training Portal: `https://ci-sachse-tx.training.smartgovcommunity.com` - **200 OK** (test environment)

### Failed URLs
- Original URL: `https://pl-sachse-tx.smartgovcommunity.com/Public/Home` - **404 Not Found**
- All `pl-sachse-tx` variations - **404 Not Found**

---

## Screenshots

The following screenshots were captured during research:
1. `ci-sachse-tx.smartgovcommunity.com.png` - Home page with main navigation
2. `ApplicationSearch.png` - Application search interface
3. `explore_2_my_portal.png` - My Portal section
4. `explore_3_public_notices.png` - Public Notices section
5. `explore_4_parcel_search.png` - Parcel Search section

---

## Research Artifacts

### Files Created
- `/home/reid/testhome/permit-scraper/research_sachse_smartgov.py` - Initial research script
- `/home/reid/testhome/permit-scraper/research_sachse_alternate.py` - URL variation testing
- `/home/reid/testhome/permit-scraper/research_sachse_correct.py` - Correct URL testing
- `/home/reid/testhome/permit-scraper/explore_sachse_portal.py` - Detailed portal exploration
- `/home/reid/testhome/permit-scraper/sachse_complete_research.json` - Complete findings data
- `/home/reid/testhome/permit-scraper/network_log.json` - Network traffic log
- `/home/reid/testhome/permit-scraper/sachse_research_findings.json` - Initial findings

---

## Next Steps

### Immediate Actions
1. Update any documentation/configuration with correct URL
2. Develop initial scraper using Playwright browser automation
3. Test search functionality with various query types
4. Implement pagination handling if search results are paginated
5. Add error handling and retry logic

### Future Enhancements
1. Reverse-engineer API calls for direct data access (performance optimization)
2. Implement rate limiting/throttling to be respectful of server resources
3. Add data validation and normalization
4. Set up scheduled scraping (if needed)
5. Monitor for site changes/updates

---

## Conclusion

**Status: PROCEED WITH SCRAPER DEVELOPMENT**

The Sachse SmartGov platform is scrapable with public access. The main challenge is handling the Angular-based SPA, which requires JavaScript rendering via Playwright. The correct production URL is `https://ci-sachse-tx.smartgovcommunity.com` and the application search is available at `/ApplicationPublic/ApplicationSearch`.

**No blockers identified** - scraper development can proceed.

---

## Additional Notes

- Contact: devservices@cityofsachse.com
- Support: 469-429-4781
- Platform: SmartGov by Granicus (2011-2025)
- Version: 2025.20
- Framework: ASP.NET + Angular

---

## Sources

Research was conducted using web search and browser automation tools:
- [City of Sachse, TX Public Portal](https://ci-sachse-tx.smartgovcommunity.com/)
- [City of Sachse, TX Training Portal](https://ci-sachse-tx.training.smartgovcommunity.com/)
