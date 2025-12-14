# Permit Leads Inventory

**Last Updated:** 2025-12-13
**Total Permits:** 5,334
**Sellable Leads:** 2,110 (39.6%)

---

## Quick Stats

| Value Tier | Count | % of Total |
|------------|------:|----------:|
| HIGH | 322 | 6.0% |
| MEDIUM-HIGH | 48 | 0.9% |
| MEDIUM | 1,740 | 32.6% |
| LOW (skip) | 647 | 12.1% |
| UNCATEGORIZED | 2,502 | 46.9% |

**Sellable (HIGH + MED-HIGH + MED): 2,110 leads**

---

## HIGH VALUE LEADS (322 total)

| Category | Count | Top Cities |
|----------|------:|------------|
| New Construction | 176 | DeSoto (105), Fort Worth (21), Mesquite (23) |
| Residential Remodel | 146 | Fort Worth (54), Mesquite (36), Colleyville (9) |

---

## MEDIUM-HIGH VALUE LEADS (48 total)

| Category | Count | Top Cities |
|----------|------:|------------|
| Roofing | 48 | Dallas (16), McKinney (10), Grapevine (5) |

---

## MEDIUM VALUE LEADS (1,740 total)

| Category | Count | Top Cities |
|----------|------:|------------|
| Solar | 352 | Cedar Hill (320) |
| Plumbing | 285 | Fort Worth (145), Carrollton (52), Grapevine (34) |
| HVAC/Mechanical | 256 | Flower Mound (100), Fort Worth (98), Carrollton (27) |
| Commercial Remodel | 211 | Colleyville (85), Westlake (50), Carrollton (32) |
| Electrical | 196 | Fort Worth (120), Dallas (28), Grapevine (16) |
| Residential Plumbing | 161 | Dallas (75), DeSoto (57), McKinney (11) |
| Residential Electrical | 77 | Dallas (41), DeSoto (23), Grapevine (8) |
| Residential HVAC | 75 | Dallas (31), DeSoto (20), McKinney (6) |
| Fence/Deck/Patio | 47 | DeSoto (24) |
| Pool/Spa | 29 | Carrollton (20) |
| Foundation Repair | 25 | Allen (6), McKinney (8) |
| Water Heater | 23 | McKinney (11) |

---

## BY CITY - Detailed Breakdown

### TIER 1: Major Cities

#### Dallas
- **Total:** 500 | **Sellable:** 282 (56%)
- HIGH: 28 | MED-HIGH: 16 | MEDIUM: 238
- **Top Categories:**
  - Residential Plumbing: 75
  - Residential Electrical: 41
  - Plumbing: 33
  - Residential HVAC: 31
  - Electrical: 28
  - Roofing: 16
  - New Construction: 28

#### Fort Worth
- **Total:** 500 | **Sellable:** 448 (90%)
- HIGH: 75 | MED-HIGH: 0 | MEDIUM: 373
- **Top Categories:**
  - Plumbing: 145
  - Electrical: 120
  - HVAC/Mechanical: 98
  - Residential Remodel: 54
  - New Construction: 21

### TIER 2: Mid-Size Cities

#### Flower Mound
- **Total:** 897 | **Sellable:** 100 (11%)
- **Issue:** 797 permits UNCATEGORIZED (needs type extraction)
- **Top Categories:**
  - HVAC/Mechanical: 100

#### Cedar Hill
- **Total:** 500 | **Sellable:** 320 (64%)
- HIGH: 0 | MEDIUM: 320
- **Top Categories:**
  - Solar: 320 (heavy solar market)

#### DeSoto
- **Total:** 500 | **Sellable:** 276 (55%)
- HIGH: 119 | MEDIUM: 157
- **Top Categories:**
  - New Construction: 105 (best for new builds!)
  - Residential Plumbing: 57
  - Fence/Deck/Patio: 24
  - Residential Electrical: 23
  - Residential HVAC: 20

#### Mesquite (NEW - Fixed Dec 2024)
- **Total:** 100 | **Sellable:** 74 (74%)
- HIGH: 59 | MEDIUM: 15
- **Top Categories:**
  - Residential Remodel: 36
  - New Construction: 23
  - Commercial Remodel: 8

#### Carrollton
- **Total:** 258 | **Sellable:** 146 (57%)
- **Top Categories:**
  - Plumbing: 52
  - Commercial Remodel: 32
  - HVAC/Mechanical: 27
  - Pool/Spa: 20

#### McKinney
- **Total:** 100 | **Sellable:** 64 (64%)
- HIGH: 6 | MED-HIGH: 10 | MEDIUM: 48
- **Top Categories:**
  - Water Heater: 11
  - Residential Plumbing: 11
  - Roofing: 10
  - Residential Remodel: 6

#### Frisco
- **Total:** 200 | **Sellable:** 1 (0%)
- **Issue:** 199 permits UNCATEGORIZED (needs type extraction from permit ID)

### TIER 3: Suburban Cities

#### Grapevine (NEW - Fixed Dec 2024)
- **Total:** 100 | **Sellable:** 91 (91%)
- HIGH: 5 | MED-HIGH: 5 | MEDIUM: 81
- **Top Categories:**
  - Plumbing: 34
  - Electrical: 16
  - HVAC/Mechanical: 15
  - Roofing: 5

#### Colleyville
- **Total:** 100 | **Sellable:** 94 (94%)
- **Top Categories:**
  - Commercial Remodel: 85
  - New Construction: 9

#### Westlake
- **Total:** 180 | **Sellable:** 78 (43%)
- **Top Categories:**
  - Commercial Remodel: 50
  - Electrical: 11
  - Plumbing: 7

#### Prosper
- **Total:** 100 | **Sellable:** 3 (3%)
- **Issue:** Most permits are CO/utility - need different search

#### Sachse
- **Total:** 1,000 | **Sellable:** 0 (0%)
- **Issue:** ALL 1,000 permits UNCATEGORIZED - needs type extraction

---

## CITIES NEEDING WORK

| City | Issue | Fix Needed |
|------|-------|------------|
| Sachse | 1,000 permits with no type | Add type extraction to SmartGov scraper |
| Flower Mound | 797 permits uncategorized | Add type inference from permit ID prefix |
| Frisco | 199 permits uncategorized | Add type inference from permit ID prefix |
| Prosper | Only 3% sellable | Try different search terms/prefixes |
| Southlake | 82 permits but 0 categorized | Check data format |

---

## VALUE CATEGORIES REFERENCE

### SELL THESE (High/Medium Value)
- New Construction / New Single Family
- Residential Remodel / Addition
- Roofing / Reroof
- Plumbing (esp. Residential)
- Electrical (esp. Residential)
- HVAC / Mechanical
- Pool / Spa
- Foundation Repair
- Solar Panel
- Water Heater

### SKIP THESE (Low Value)
- Certificate of Occupancy
- Right of Way / ROW
- Utility / Meter permits
- Sign permits
- Temporary structures
- Demolition
- Irrigation / Landscape
- Telecom / Antenna

---

## ACTION ITEMS

1. **URGENT:** Fix Sachse/Flower Mound/Frisco type extraction (+2,000 leads at stake)
2. **HIGH:** Re-scrape Prosper with residential-focused prefixes
3. **MEDIUM:** Run larger scrapes for McKinney, Grapevine (low volume cities)
4. **MEDIUM:** Check Southlake data format (82 permits, 0 categorized)
5. **LOW:** Set up daily cron for Dallas/Fort Worth (high volume, high value)
