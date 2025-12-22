# University Park Portal Analysis

**Date:** 2025-12-22
**City:** University Park, TX
**Platform:** MyGov Public Portal
**Status:** ❌ PORTAL DOES NOT EXIST

---

## Investigation Summary

The University Park MyGov portal at `https://public.mygov.us/university_park_tx` **does not exist**.

### Evidence

```bash
# HTTP response headers
$ curl -sI "https://public.mygov.us/university_park_tx"
HTTP/2 302
location: https://public.mygov.us/notfound/
```

The server returns a **302 redirect to `/notfound/`**, confirming the portal is not configured.

### Comparison with Working Portals

For reference, working MyGov portals return 200 OK:

```bash
$ curl -sI "https://public.mygov.us/mansfield_tx"
HTTP/2 200

$ curl -sI "https://public.mygov.us/rowlett_tx"
HTTP/2 200
```

---

## Why 0 Permits?

The scraper configuration in `scrapers/mygov_multi.py` includes:

```python
'university_park': {'name': 'University Park', 'slug': 'university_park_tx', 'pop': 25000},
```

However, University Park **never set up a MyGov public portal**, so the scraper searches a non-existent site and correctly returns 0 results.

---

## City Background

- **Population:** ~25,000
- **Location:** Enclave city between Dallas and Highland Park (affluent area)
- **Notable:** Home to Southern Methodist University (SMU)

Given the city's size and location in an affluent area, it likely has building permits, but they're not accessible via MyGov.

---

## Alternate Data Sources

### Option 1: Official City Portal
Check if University Park has a different permit portal:
- City website: https://www.uptexas.org/
- Look for "Building Permits", "Development", or "City Services" sections
- May use a different platform (Accela, CityView, etc.)

### Option 2: Dallas CAD
University Park properties may be in Dallas CAD's jurisdiction:
- Dallas CAD (DCAD) property data might include University Park permits
- Worth checking if DCAD covers this enclave city

### Option 3: Manual Contact
- City Building Department phone/email
- Request bulk permit data or API access
- May require formal data request

---

## Recommendations

### Immediate Action
**Remove University Park from `mygov_multi.py` MYGOV_CITIES dict** to prevent wasted scraping attempts.

```python
# Remove this line:
# 'university_park': {'name': 'University Park', 'slug': 'university_park_tx', 'pop': 25000},
```

### Future Exploration (Low Priority)
If University Park becomes a priority for coverage:
1. Visit city website to find official permit portal
2. Check if Dallas CAD includes University Park data
3. Contact city to ask about public permit access

### Priority Assessment
**Low priority** - University Park is a small enclave city. Focus scraping efforts on:
- Large cities with working portals (Dallas, Fort Worth, etc.)
- MyGov cities that actually have portals (Mansfield, Rowlett, Grapevine, etc.)
- High-population cities without coverage yet

---

## Related Files

- `/home/reid/testhome/permit-scraper/scrapers/mygov_multi.py` - Remove university_park entry
- `/home/reid/testhome/permit-scraper/docs/plans/2025-12-22-five-city-scrapers.md` - Task 4 (this investigation)

---

## Conclusion

University Park MyGov portal **does not exist** (302 → /notfound/). This is why the scraper returns 0 permits - there's nothing to scrape. The city either:
- Never set up a MyGov portal
- Uses a different permit platform
- Doesn't offer public online permit access

**Recommended action:** Remove from `mygov_multi.py` and deprioritize unless alternate portal is found.
