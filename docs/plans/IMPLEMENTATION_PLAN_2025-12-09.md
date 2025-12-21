# Implementation Plan: Garland, Carrollton, Flower Mound Scrapers

**Created**: December 9, 2025
**Status**: Ready for Implementation
**Confidence**: Claude 95% | Gemini 99%

---

## Summary

Research completed for three DFW municipalities. One is ready to implement immediately using existing scraper, one requires a new scraper, and one needs further investigation.

---

## 1. Flower Mound (QUICK WIN)

| Field | Value |
|-------|-------|
| Population | 80,000 |
| Platform | **eTRAKiT** |
| Portal URL | https://etrakit.flower-mound.com/ |
| Search Page | https://etrakit.flower-mound.com/Search/permit.aspx |
| Login Required | No (public search available) |
| Existing Scraper | `scrapers/etrakit_fast.py` |

### Implementation Steps

1. Open `scrapers/etrakit_fast.py`
2. Add Flower Mound to the city configuration (similar to Frisco)
3. Configuration needed:
   ```python
   "flower_mound": {
       "base_url": "https://etrakit.flower-mound.com",
       "search_path": "/Search/permit.aspx",
       # ... copy structure from frisco config
   }
   ```
4. Test: `python3 scrapers/etrakit_fast.py flower_mound 100`
5. Verify output in `flower_mound_raw.json`

### Notes
- Same platform as Frisco and Plano
- Town adopted 2024 I-Codes effective October 1, 2025
- Inspections can be scheduled same-day if requested before 7:30 AM

---

## 2. Carrollton (NEW SCRAPER)

| Field | Value |
|-------|-------|
| Population | 140,000 |
| Platform | **CityView** (by Municipal Software) |
| Portal URL | https://cityserve.cityofcarrollton.com/CityViewPortal |
| Search Page | https://cityserve.cityofcarrollton.com/CityViewPortal/Permit/Locator |
| Login Required | No (public search available) |
| Existing Scraper | None - NEW |

### Search Fields Available
- Application number
- Address
- Parcel number
- Contact name/address
- Jurisdiction filter (dropdown)
- Category filter (dropdown)
- Geographic search (map-based)

### Implementation Steps

1. Create new file: `scrapers/cityview.py`
2. Analyze the CityView portal:
   - Open browser DevTools on search page
   - Submit a test search and capture network requests
   - Identify API endpoints (likely REST or form POST)
3. Determine pagination method
4. Build scraper following existing patterns:
   ```python
   # Template structure
   CITIES = {
       "carrollton": {
           "base_url": "https://cityserve.cityofcarrollton.com",
           "search_endpoint": "/CityViewPortal/Permit/Locator",
           # ...
       }
   }
   ```
5. Test with small batch first
6. Output to `carrollton_raw.json`

### Technical Notes
- CityView is a commercial platform by municipalsoftware.com
- Should be scrapeable via standard DOM/API methods
- May need to handle autocomplete/typeahead functionality

---

## 3. Garland (NEEDS INVESTIGATION)

| Field | Value |
|-------|-------|
| Population | 240,000 |
| Platform | **PublicStuff / E-Assist** (unclear) |
| Portal URL | https://iframe.publicstuff.com/?client_id=417 |
| Login Required | Unknown |
| Existing Scraper | None |

### Issue
PublicStuff is typically a 311/service request platform, NOT a building permit system. Garland may:
- Use a different internal system for building permits
- Not have a public permit search portal
- Have permits embedded in a different city system

### Investigation Steps

1. Navigate to https://www.garlandtx.gov/2152/Building-Permit
2. Look for any "Permit Search" or "Permit Status" links
3. Check if permits are filed through the PublicStuff iframe or elsewhere
4. Contact options if no portal found:
   - Email: permits@garlandtx.gov
   - Phone: 972-205-2300
5. Check if Garland uses MyGov or another platform not yet identified

### Recommendation
**Defer until Flower Mound and Carrollton are complete.** This may require manual research or may not be scrapeable at all.

---

## Update SCRAPER_STATUS.md

After implementation, update the status table:

```markdown
| 9 | **Garland** | 240K | PublicStuff? | — | 🔍 Under investigation |
| 12 | **Carrollton** | 140K | CityView | `cityview.py` | ✅ Working (once implemented) |
| 15 | **Flower Mound** | 80K | eTRAKiT | `etrakit_fast.py` | ✅ Working (once implemented) |
```

---

## Priority Order

1. **Flower Mound** - 30 min estimate (config change only)
2. **Carrollton** - 2-4 hours estimate (new scraper, known platform)
3. **Garland** - Unknown (research spike needed)

---

## Sources

- Flower Mound eTRAKiT: https://etrakit.flower-mound.com/
- Carrollton CityView: https://cityserve.cityofcarrollton.com/CityViewPortal/Permit/Locator
- Garland Permits Page: https://www.garlandtx.gov/2152/Building-Permit
- Garland E-Assist: https://iframe.publicstuff.com/?client_id=417
