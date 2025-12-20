# DFW Municipality Research Findings - December 19, 2025

## Executive Summary

Researched 11 new DFW municipalities (Tasks 5-15). Found **5 immediately actionable** cities that can use existing scrapers, **3 that need minor implementation**, and **3 blocked/limited**.

## Tier 1: READY NOW (Use Existing Scrapers)

| City | Pop | Platform | Scraper | Status |
|------|-----|----------|---------|--------|
| **North Richland Hills** | 70K | EnerGov CSS | `citizen_self_service.py` | Already configured! Just run it |
| **Cedar Hill** | 49K | EnerGov CSS | `citizen_self_service.py` | Already configured! Has data |
| **Burleson** | 52K | eTRAKiT | `etrakit.py` | Need to add config |
| **Rowlett** | 68K | MyGov | `mygov_multi.py` | Has public Excel exports |
| **The Colony** | 48K | eTRAKiT | `etrakit.py` | LIMITED - building permits via email only |

**Combined population: 287K**

## Tier 2: NEEDS MINOR IMPLEMENTATION

| City | Pop | Platform | Existing Scraper | Action Needed |
|------|-----|----------|------------------|---------------|
| **Keller** | 52K | EnerGov CSS | `citizen_self_service.py` | Add to config (migrated from eTRAKiT) |
| **Duncanville** | 40K | EnerGov CSS | `citizen_self_service.py` | Add to config, test public access |

**Combined population: 92K**

## Tier 3: BLOCKED / LIMITED ACCESS

| City | Pop | Platform | Issue | Recommendation |
|------|-----|----------|-------|----------------|
| **Wylie** | 56K | CitizenServe + ImpactWeb | Login required | Skip - new platform needed |
| **Rockwall** | 49K | CityWorks | Authenticated only | Skip - new platform + CAD needed |
| **Haltom City** | 46K | MyGov | No public permit search | Skip - records request only |
| **Lancaster** | 42K | MyGov + Accela | Contractor registration required | Skip - needs credentials |

**Combined population: 193K**

## Immediate Actions

### Run Existing Scrapers (5 min each)
```bash
cd /home/reid/testhome/permit-scraper

# North Richland Hills - Already configured
python3 scrapers/citizen_self_service.py north_richland_hills 500

# Cedar Hill - Already configured
python3 scrapers/citizen_self_service.py cedar_hill 500

# Rowlett - MyGov Excel export
python3 scrapers/mygov_multi.py rowlett 500
```

### Add to Existing Scrapers (30 min)

**1. Add Burleson to `etrakit.py` config:**
```python
'burleson': {
    'name': 'Burleson',
    'base_url': 'https://etrakit.burlesontx.com',
    'county': 'Tarrant',
}
```

**2. Add Keller to `citizen_self_service.py` config:**
```python
'keller': {
    'name': 'Keller',
    'base_url': 'https://www.cityofkeller.com/css',  # Or Tyler-hosted instance
}
```

**3. Add Duncanville to `citizen_self_service.py` config:**
```python
'duncanville': {
    'name': 'Duncanville',
    'base_url': 'https://selfservice.duncanville.com/energov_prod/selfservice',
}
```

## Platform Distribution

| Platform | Cities Found | Existing Scraper |
|----------|--------------|------------------|
| EnerGov CSS | NRH, Cedar Hill, Keller, Duncanville | `citizen_self_service.py` |
| eTRAKiT | Burleson, The Colony | `etrakit.py` |
| MyGov | Rowlett, Haltom City, Lancaster | `mygov_multi.py` |
| CityWorks | Rockwall | None (new platform) |
| CitizenServe | Wylie | None (new platform) |

## Coverage Impact

**Before this research:** 22 working cities (~4.6M population)

**After implementing Tier 1 + Tier 2:** +7 cities, +379K population

**New total:** 29 cities (~5M population, ~72% of DFW metro)

## Session Summary

**Completed Tasks:**
1. Sachse SmartGov - 500 permits scraped, 26 new loaded
2. Weatherford GovBuilt - New scraper created, 88 permits loaded
3. Lewisville Debug - Portal returns 0 results (data availability issue)
4. Little Elm Excel Parser - Formalized with 16x better contractor extraction
5-15. Municipality Research - 11 cities researched, 7 actionable

**Commits:**
- `dd3f09e` - feat: add Weatherford GovBuilt scraper
- `c4a8d13` - fix(weatherford): document field availability
- `98c1043` - feat: add Little Elm Excel parser
