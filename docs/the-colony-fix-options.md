# The Colony Address Data Fix Options

## Problem Summary

The Colony scraper successfully extracts **106 permits** but with incomplete address data:
- Only street names (e.g., "BAKER DR")
- No street numbers
- Cannot load to database (requires full address)

**Root cause:** The Colony's eTRAKiT portal only displays street names in search results, not full addresses.

---

## Option 1: Click into Detail Pages (Recommended)

The search results only show street names, but clicking each permit likely reveals the full address on the detail page.

### Approach
1. Extract permit numbers from search results
2. Click into each permit detail page
3. Scrape full address from detail view
4. Return to search, repeat

### Pros
- Gets complete, accurate data
- One-time fix to scraper
- No external dependencies

### Cons
- Slower scraping (one HTTP request per permit)
- Need to understand detail page structure

### Effort
**Medium** - Add detail page navigation to `scrapers/etrakit.py`

### Implementation Notes
```python
# Pseudocode for detail page extraction
for permit_link in search_results:
    await page.click(permit_link)
    full_address = await page.query_selector('.address-field').text_content()
    permit_data['address'] = full_address
    await page.go_back()
```

---

## Option 2: CAD Enrichment (Use Existing Infrastructure)

Use Collin County CAD data to match street names to full addresses.

### Approach
1. Load permits with partial addresses (street name only)
2. Query CAD by street name + city to find matching parcels
3. Enrich with full address from CAD

### Pros
- Already have `collin_cad_socrata.py` scraper
- CAD enrichment pipeline exists (`scripts/enrich_cad.py`)
- No changes to permit scraper needed

### Cons
- The Colony is in **Denton County**, not Collin County
- Would need Denton County CAD access (may not be available via Socrata)
- Matching by street name alone is ambiguous

### Effort
**Low** if Denton CAD available, **High** if not

### Implementation Notes
- Check if Denton County has Socrata API
- Alternative: Use Google Maps Geocoding API to complete addresses

---

## Option 3: Browser-Use for Detail Extraction

Use AI-driven Browser-Use to handle the complex navigation.

### Approach
1. Create Browser-Use task that searches for permits
2. For each result, clicks to view details
3. Extracts full permit data including address
4. Returns structured JSON

### Pros
- Browser-Use handles dynamic navigation well
- Already have Browser-Use infrastructure
- Can handle JavaScript-heavy pages

### Cons
- Slower than DOM scraping
- Uses DeepSeek API credits
- May be overkill for simple click-through

### Effort
**Medium** - Create new task in `services/browser_scraper/permit_tasks.py`

### Implementation Notes
```python
THE_COLONY_DETAIL_TASK = """
Go to The Colony eTRAKiT at https://tcol-trk.aspgov.com/etrakit/

1. Search for permits using prefix "B"
2. For each permit in results:
   - Click the permit number link
   - Extract: permit_number, full_address, permit_type, status, issue_date
   - Click "Back" to return to results
3. Return all permits as JSON array
"""
```

---

## Option 4: Accept Partial Data

Modify the loader to accept street-name-only addresses for The Colony specifically.

### Approach
1. Flag permits as `address_incomplete = True`
2. Load anyway with street name only
3. Enrich later when possible
4. Exclude from scoring until enriched

### Pros
- Quickest fix
- Gets data into system for later enrichment
- No scraper changes needed

### Cons
- Incomplete data in database
- Cannot score/sell these leads until enriched
- May never get enriched

### Effort
**Low** - Just loader modification in `scripts/load_permits.py`

### Implementation Notes
```python
# In load_permits.py
if city == 'the_colony' and not is_full_address(address):
    permit['address_incomplete'] = True
    permit['needs_enrichment'] = True
```

---

## Recommendation

**Option 1 (Detail Pages)** is the best long-term solution:
- Gets complete data at source
- One-time implementation effort
- No ongoing API costs or external dependencies

**Option 4 (Accept Partial)** is the quickest if you need data now and can enrich later.

---

## Solution Implemented (December 2025)

The Colony address enrichment uses a multi-stage pipeline:

1. **Scrape** - `etrakit.py the_colony 100` extracts permits with street names only
2. **CAD Lookup** - `enrich_colony_addresses.py` queries Denton CAD for addresses on each street
3. **Ambiguous Handling** - When multiple addresses exist (common), permits are marked `DENTON_CAD_AMBIGUOUS` with top 10 candidates stored

### Commands

```bash
# Scrape The Colony permits
python3 scrapers/etrakit.py the_colony 100

# Enrich with Denton CAD (dry-run first)
python3 scripts/enrich_colony_addresses.py --dry-run
python3 scripts/enrich_colony_addresses.py

# Check results
cat data/raw/the_colony_enriched.json | python3 -m json.tool | head -50
```

### Data Limitations

The Colony's eTRAKiT portal only displays street names in search results (e.g., "BAKER DR" without house number). This means:

- **Single-address streets**: Fully enriched with exact address
- **Multi-address streets**: Marked as ambiguous with candidate list for manual review

### Output Format

```json
{
  "permit_id": "0701-4211",
  "address": "",
  "street_name": "BAKER DR",
  "address_candidates": ["5601 BAKER DR", "5613 BAKER DR", ...],
  "address_source": "DENTON_CAD_AMBIGUOUS"
}
```

---

## Next Steps

1. **Investigate detail page structure:**
   ```bash
   curl -s "https://tcol-trk.aspgov.com/etrakit/Search/permit.aspx" | grep -i "address"
   ```

2. **Test clicking a permit manually** to see what data is available

3. **Decide on approach** based on detail page findings

---

## Session Context

This document was created after successfully implementing scrapers for 5 cities:

| City | Result |
|------|--------|
| Southlake | 316 permits scraped, 253 loaded |
| The Colony | 106 permits scraped, 0 loaded (this issue) |
| NRH | Blocked - Tyler SSO required |
| University Park | Blocked - portal doesn't exist |
| Forney | Blocked - no public portal |

**Date:** 2025-12-22
