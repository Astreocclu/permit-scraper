# North Richland Hills Portal Analysis

**Date:** 2025-12-22
**Portal:** https://selfservice.nrhtx.com/energov_prod/selfservice
**Portal Type:** EnerGov Citizen Self Service with Tyler Identity SSO
**Status:** ❌ BLOCKED - Requires authentication, no anonymous access

---

## Executive Summary

North Richland Hills portal **cannot be scraped without authentication credentials**. The portal enforces Tyler SSO (Single Sign-On) and displays an internal error when SSO is cancelled. There is no guest or public search option.

---

## Technical Findings

### 1. Portal Loads Successfully

The portal HTML loads and serves the EnerGov CSS Angular application. Key indicators:
- ✅ HTML loads at base URL
- ✅ `<meta id="isTylerIdEnabled" value="true">` present
- ✅ Angular app initializes

### 2. SSO Redirect Triggered Immediately

When navigating to the search page (`#/search`), the portal:
1. Redirects to `#/sso.html?redirectUrl=%2Fsearch`
2. Shows a dialog: "You are being redirected to Tyler Identity login page for authorization purposes"
3. Offers two buttons: **Continue** (to Tyler SSO) or **Cancel**

### 3. Cancel Results in Internal Error

When clicking **Cancel** on the SSO dialog:
1. Returns to `#/search` URL
2. Displays error dialog: "An internal error occurred. Please contact your system administrator."
3. After closing error dialog, page is **completely empty**:
   - ❌ No search module (`#SearchModule`)
   - ❌ No text inputs
   - ❌ No permit search functionality
   - ❌ Only shows header/footer with "Login or Register"

### 4. No Guest Access Options

Home page analysis:
- ❌ No "Guest Search" link
- ❌ No "Public Records" option
- ❌ Only available actions: "Log In", "Register", "Login or Register"
- All menu items require authentication

---

## Test Scripts Used

```bash
# Quick diagnostic (headless)
python3 test_nrh_quick.py

# Test canceling SSO
python3 test_nrh_cancel_sso.py
```

### Test Results Summary

| Test | Result |
|------|--------|
| Portal loads | ✅ SUCCESS |
| SSO dialog appears | ✅ YES (blocks access) |
| Cancel SSO | ❌ Internal error shown |
| Guest access after error | ❌ NONE (empty page) |
| Public search option | ❌ NOT FOUND |
| Search module without auth | ❌ NOT PRESENT |

---

## Scraperability Assessment

### Can We Scrape This Portal?

**NO** - Not without authentication credentials.

### Why Not?

1. **Tyler SSO Required:** Portal enforces Tyler Identity authentication
2. **No Anonymous Fallback:** Canceling SSO leaves empty page
3. **No Public Search:** No guest or public records search option
4. **Portal Design:** Intentionally restricts all search functionality to authenticated users

### Compared to Other Cities

| City | Portal Type | Guest Access? | Scrapeable? |
|------|-------------|---------------|-------------|
| Southlake | EnerGov CSS | ✅ Yes | ✅ Yes (works) |
| McKinney | EnerGov CSS | ✅ Yes | ✅ Yes (works) |
| Colleyville | EnerGov CSS | ✅ Yes | ✅ Yes (works) |
| **North Richland Hills** | **EnerGov CSS + Tyler SSO** | **❌ No** | **❌ No** |

---

## Possible Workarounds

### 1. ❌ Bypass SSO Dialog
**Tried:** Clicking Cancel
**Result:** Internal error, empty page
**Viable:** No

### 2. ❓ Register for Account
**Approach:** Create a free account via "Register" link
**Considerations:**
- May require verification (email, phone)
- Unknown if free accounts get search access
- Would need to store credentials in `.env`
- Still requires session management

**Next Step:** Would need Reid to test registration process

### 3. ❓ Contact City for API/Data Access
**Approach:** Request permit data directly from city
**Considerations:**
- May have open records request process
- Might provide CSV/Excel exports
- Could take days/weeks to fulfill

### 4. ❌ Attempt to Reverse Engineer API
**Approach:** Capture authenticated API calls
**Viable:** No - still requires auth tokens

---

## Recommendations

### Option A: Request Credentials from Reid
If Reid has (or can create) a NRH account, we can:
1. Store credentials in `.env`
2. Modify `citizen_self_service.py` to handle Tyler SSO login
3. Scrape as authenticated user

**Required:**
- `NRH_USERNAME=...`
- `NRH_PASSWORD=...`
- SSO login flow in scraper

### Option B: Skip This City
Mark NRH as permanently blocked and focus on other cities.

**Impact:** ~50-200 potential leads lost (estimate based on city size)

### Option C: Alternative Data Sources
Check if NRH publishes permit data elsewhere:
- ❓ Texas Open Data portal (like Collin CAD)
- ❓ City website "Recent Permits" page
- ❓ Tarrant CAD property records

---

## Files Created

- `test_nrh_quick.py` - Quick headless diagnostic
- `test_nrh_cancel_sso.py` - Test SSO cancel behavior
- `nrh_portal.png` - Screenshot of SSO dialog
- `nrh_before_cancel.png` - Before canceling SSO
- `nrh_after_cancel.png` - After canceling (error dialog)
- `nrh_error_closed.png` - After closing error (empty page)

---

## Next Steps

**Immediate:**
1. ✅ Document findings (this file)
2. ⏭️ Ask Reid if he has or can create NRH account
3. ⏭️ Update `AUTH_REQUIRED.md` with NRH status

**If credentials available:**
1. Add NRH Tyler SSO login flow to `citizen_self_service.py`
2. Store credentials in `.env`
3. Test authenticated scraping

**If no credentials:**
1. Mark NRH as `status: 'blocked_auth_required'` in config
2. Move to other cities (University Park, Forney)

---

## Code Reference

Current NRH config in `scrapers/citizen_self_service.py:109-114`:

```python
'north_richland_hills': {
    'name': 'North Richland Hills',
    'base_url': 'https://selfservice.nrhtx.com/energov_prod/selfservice',
    'requires_sso_bypass': True,  # BROKEN: Tyler SSO required, no anonymous access
    'status': 'broken',  # Portal shows "internal error" when SSO is cancelled
},
```

**Accuracy:** ✅ 100% correct. Config accurately reflects portal behavior.

---

## Conclusion

North Richland Hills portal is **not scrapeable without authentication credentials**. The portal enforces Tyler Identity SSO with no anonymous fallback. Recommended action: Ask Reid for credentials or skip this city.
