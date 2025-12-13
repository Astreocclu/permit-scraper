# Permit Leads Inventory

**Last Updated:** 2025-12-13
**Purpose:** Running account of all scraped permit leads by tier, city, and category.

> **Read this file with Gemini first** to understand current lead inventory before any scraping session.

---

## Summary

| Tier | Cities | Total Leads | Residential | Status |
|------|--------|-------------|-------------|--------|
| Tier 1 (Major) | 4 | ~1,500 | ~800 | Active |
| Tier 2 (Mid-Size) | 8 | ~2,500 | ~1,200 | Active |
| Tier 3 (Suburban) | 12 | ~1,800 | ~900 | Active |
| **TOTAL** | **24** | **~5,800** | **~2,900** | |

---

## Tier 1: Major Cities (Pop 200k+)

### Dallas (Accela)
- **File:** `dallas_raw.json`
- **Count:** 500 permits
- **Categories:**
  - Residential Plumbing Permit: 75
  - Residential Electrical Permit: 41
  - Permit Extension: 36
  - Single Family Residence: 28
- **Quality:** HIGH - Good residential mix
- **Scraper:** `accela_fast.py`

### Fort Worth (Accela)
- **File:** `fort_worth_raw.json`
- **Count:** 500 permits
- **Categories:**
  - Electrical Umbrella Permit: 74
  - Mechanical Umbrella Permit: 68
  - Plumbing Standalone Permit: 61
  - Residential Addition/Remodel: ~40
- **Quality:** HIGH - Strong trade permit volume
- **Scraper:** `accela_fast.py`

### Arlington (Socrata API)
- **File:** Via API
- **Count:** Variable (API access)
- **Quality:** HIGH - Direct API, reliable
- **Scraper:** `dfw_big4_socrata.py`

### Plano (eTRAKiT)
- **File:** `plano_raw.json`
- **Count:** 50 permits (limited - requires auth)
- **Categories:**
  - Water Heater Online: 9
  - Simple Plumbing Online: 8
  - HVAC: 5
- **Quality:** MEDIUM - Auth required limits volume
- **Scraper:** `etrakit_auth.py`

---

## Tier 2: Mid-Size Cities (Pop 75k-200k)

### Frisco (eTRAKiT)
- **File:** `frisco_raw.json`
- **Count:** 200 permits
- **Categories:** Building permits (types need extraction from ID prefix)
- **Quality:** HIGH - Fast growing, premium market
- **Scraper:** `etrakit.py`

### McKinney (EnerGov CSS)
- **File:** `mckinney_raw.json`
- **Count:** 100 permits
- **Categories:**
  - Water Heater: 11
  - Residential Stand-Alone Plumbing: 11
  - Residential Reroof: 10
  - Foundation Repair: 8
- **Quality:** HIGH - Good residential variety
- **Scraper:** `citizen_self_service.py`

### Carrollton (CityView)
- **File:** `carrollton_raw.json`
- **Count:** 258 permits
- **Categories:**
  - Plumbing: 52
  - Renovation/Remodel: 31
  - Sign: 31
  - Electrical: 28
- **Quality:** HIGH - Strong residential remodel
- **Scraper:** `cityview.py`

### Denton (eTRAKiT)
- **File:** `denton_raw.json`
- **Count:** 5 permits (needs larger scrape)
- **Quality:** NEEDS WORK
- **Scraper:** `etrakit.py`

### Mesquite (EnerGov CSS) - NEW
- **File:** `mesquite_raw.json`
- **Count:** 100 permits
- **Categories:**
  - Plumbing - Residential Addition/Remodel: 16
  - Building-Residential Accessory Structure: 9
  - Electrical - New Residential Building: 8
  - Mechanical - Residential: 7
- **Quality:** HIGH - Fixed Dec 2024, good residential
- **Scraper:** `citizen_self_service.py`

### Cedar Hill (EnerGov CSS)
- **File:** `cedar_hill_raw.json`
- **Count:** 500 permits
- **Categories:**
  - Solar Panel (Residential): 320
  - Special Event Sign: 90
  - Commercial Temp Building: 46
- **Quality:** MEDIUM - Heavy solar, less traditional
- **Scraper:** `citizen_self_service.py`

### DeSoto (EnerGov CSS)
- **File:** `desoto_raw.json`
- **Count:** 500 permits
- **Categories:**
  - New Single Family: 105
  - Plumbing - Single: 57
  - Right of Way: 158
- **Quality:** HIGH - Good new construction
- **Scraper:** `citizen_self_service.py`

### Flower Mound (eTRAKiT)
- **File:** `flower_mound_raw.json`
- **Count:** 897 permits
- **Categories:** Mixed (types need prefix extraction)
- **Quality:** HIGH - Premium suburb, high volume
- **Scraper:** `etrakit.py`

---

## Tier 3: Suburban Cities (Pop 25k-75k)

### Southlake (EnerGov CSS)
- **File:** `southlake_raw.json`
- **Count:** 82 permits
- **Categories:**
  - Residential Remodel: 11
  - Irrigation (Residential): 10
  - Mechanical Permit (Residential): 10
  - Pool/Spa: 8
- **Quality:** PREMIUM - Wealthy suburb, high-value leads
- **Scraper:** `citizen_self_service.py`

### Colleyville (EnerGov CSS)
- **File:** `colleyville_raw.json`
- **Count:** 100 permits
- **Categories:**
  - Building Commercial - Alteration: 83
  - Building Commercial - New: 9
- **Quality:** MEDIUM - Mostly commercial
- **Scraper:** `citizen_self_service.py`

### Allen (EnerGov CSS)
- **File:** `allen_raw.json`
- **Count:** 50 permits
- **Categories:**
  - Over the Counter Trade: 6
  - Foundation Repair - Residential: 6
  - ROW Telecom: 4
- **Quality:** MEDIUM - Mixed, needs larger scrape
- **Scraper:** `citizen_self_service.py`

### Prosper (eTRAKiT) - FIXED
- **File:** `prosper_raw.json`
- **Count:** 100 permits
- **Categories:**
  - Building Final: 23
  - Commercial: 13
  - Certificate of Occupancy: 11
  - Grading/Site: 10
- **Quality:** HIGH - Fast growing, new construction
- **Scraper:** `etrakit.py`

### Grapevine (MyGov) - FIXED
- **File:** `data/raw/grapevine_mygov_raw.json`
- **Count:** 129 permits
- **Categories:**
  - Building Commercial Alteration: 40+
  - Electrical Permit: 30+
  - Mechanical Permit: 20+
- **Quality:** HIGH - Fixed Dec 2024
- **Scraper:** `mygov_multi.py`

### Sachse (SmartGov)
- **File:** `data/raw/sachse_raw.json`
- **Count:** 1,000 permits
- **Categories:** Needs categorization
- **Quality:** HIGH VOLUME - Needs type filtering
- **Scraper:** `smartgov_sachse.py`

### Mansfield (MyGov)
- **File:** `data/raw/mansfield_mygov_raw.json`
- **Count:** ~100 permits
- **Quality:** ACTIVE
- **Scraper:** `mygov_multi.py`

### Rowlett (MyGov)
- **File:** `data/raw/rowlett_mygov_raw.json`
- **Count:** ~100 permits
- **Quality:** ACTIVE
- **Scraper:** `mygov_multi.py`

### Trophy Club (EnerGov CSS)
- **File:** `trophy_club_raw.json`
- **Count:** 5 permits (needs work)
- **Quality:** NEEDS WORK
- **Scraper:** `citizen_self_service.py`

### Waxahachie (EnerGov CSS)
- **File:** `waxahachie_raw.json`
- **Count:** 5 permits (needs work)
- **Quality:** NEEDS WORK
- **Scraper:** `citizen_self_service.py`

### Westlake (MyGov)
- **File:** `westlake_raw.json`
- **Count:** 180 permits
- **Quality:** PREMIUM - Wealthy area
- **Scraper:** `mygov_westlake.py`

---

## Blocked/Unavailable Cities

### Keller (eTRAKiT)
- **Status:** BLOCKED - Contractor-only portal
- **Reason:** No public permit search access
- **Marked:** Dec 2024

---

## Valuable Lead Categories (Worth Selling)

### High Value (New Construction)
- New Single Family Residence
- New Residential Building
- Foundation (New)
- Framing Inspection

### Medium-High Value (Major Remodel)
- Residential Addition/Remodel
- Room Addition
- Garage Conversion
- Kitchen Remodel
- Bathroom Remodel

### Medium Value (Trade Work)
- Residential Plumbing Permit
- Residential Electrical Permit
- HVAC/Mechanical Permit
- Water Heater Replacement
- Reroof/Roofing

### Medium Value (Specialty)
- Pool/Spa Construction
- Solar Panel Installation
- Foundation Repair
- Fence/Deck

### Low Value (Skip)
- Certificate of Occupancy (CO)
- Permit Extension
- Right of Way
- Sign Permits
- Temporary Structures
- Utility/Meter permits

---

## Scraping Schedule

### Daily (High Priority)
- Dallas, Fort Worth (Accela) - High volume
- Frisco, Flower Mound (eTRAKiT) - Premium markets

### Weekly
- McKinney, Southlake, Colleyville (CSS)
- Mesquite, Cedar Hill, DeSoto (CSS)
- Prosper, Grapevine (eTRAKiT/MyGov)

### Monthly
- Smaller cities: Allen, Trophy Club, Waxahachie
- MyGov cities: Mansfield, Rowlett, Westlake

---

## Data Quality Notes

1. **eTRAKiT scrapers** - Type often needs inference from permit ID prefix
2. **EnerGov CSS** - Best data quality, includes descriptions
3. **MyGov** - Good addresses, limited type info
4. **Accela** - High volume, good categorization

## Action Items

- [ ] Run larger scrapes for Denton, Trophy Club, Waxahachie
- [ ] Add type inference to Flower Mound eTRAKiT data
- [ ] Implement daily cron for Tier 1 cities
- [ ] Add CAD enrichment pipeline for address validation
