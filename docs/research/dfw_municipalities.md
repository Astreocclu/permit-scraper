# DFW Municipalities Coverage Report

Generated: 2024-12-13

## Executive Summary

This document tracks permit scraper coverage for **106 municipalities** in the Dallas-Fort Worth Metroplex across 8 counties (Dallas, Tarrant, Collin, Denton, Rockwall, Kaufman, Ellis, Johnson).

### Coverage Statistics

| Status | Count | Percentage |
|--------|-------|------------|
| Working | 24 | 23% |
| Blocked | 5 | 5% |
| Unknown | 77 | 72% |

### Population Coverage

| Category | Cities | Population |
|----------|--------|------------|
| Working scrapers | 24 | ~3.8M (est) |
| Blocked | 5 | ~520k |
| Unknown | 77 | ~1.2M |

**Current coverage captures ~70% of DFW population.**

---

## Top 10 Priority Research - COMPLETED

Research completed 2024-12-13. Results below:

| Rank | City | Population | Platform | Status | Action |
|------|------|------------|----------|--------|--------|
| 1 | **Garland** | 240,000 | Custom | research_needed | No public portal found |
| 2 | **Mesquite** | 150,000 | **EnerGov CSS** | **READY** | Add to citizen_self_service.py |
| 3 | **Richardson** | 120,000 | Custom | research_needed | Custom cor.net portal |
| 4 | **North Richland Hills** | 70,000 | Enterprise Permitting | research_needed | NRH E-Portal system |
| 5 | **Euless** | 60,000 | Cityworks | new_platform | Would need new scraper |
| 6 | **Grapevine** | 50,000 | **MyGov** | **READY** | Add to mygov_multi.py |
| 7 | **Rockwall** | 45,000 | Custom/Manual | research_needed | No public search portal |
| 8 | **Keller** | 45,000 | **eTRAKiT** | **READY** | Add to etrakit_fast.py |
| 9 | **Wylie** | 55,000 | Citizenserve | new_platform | Would need new scraper |
| 10 | **Prosper** | 35,000 | **eTRAKiT** | **READY** | Add to etrakit_fast.py |

### Immediate Easy Wins (4 cities, ~280k population)

| City | Platform | Portal URL | Scraper to Update |
|------|----------|------------|-------------------|
| **Mesquite** | EnerGov CSS | https://energov.cityofmesquite.com | citizen_self_service.py |
| **Grapevine** | MyGov | https://www.grapevinetexas.gov/1862 | mygov_multi.py |
| **Keller** | eTRAKiT | https://trakitweb.cityofkeller.com/etrakit/ | etrakit_fast.py |
| **Prosper** | eTRAKiT | http://etrakit.prospertx.gov/eTRAKIT/Search/permit.aspx | etrakit_fast.py |

### New Platforms Discovered (2 cities)

| City | Platform | Portal URL | Notes |
|------|----------|------------|-------|
| **Euless** | Cityworks | https://euless.newedgeservices.com/PermitPortal | NewEdge Services |
| **Wylie** | Citizenserve | https://www4.citizenserve.com/Portal/... | Common platform |

### Requires Further Research (4 cities)

| City | Issue | Portal URL |
|------|-------|------------|
| **Garland** | No public search portal | garlandtx.gov |
| **Richardson** | Custom portal, limited online | cor.net |
| **North Richland Hills** | Unknown "Enterprise Permitting" system | nrhtx.com |
| **Rockwall** | Manual reports only | rockwall.com |

---

## Coverage by Platform

### Accela (Fast DOM) - 4 Cities Working
| City | Population | Status |
|------|------------|--------|
| Dallas | 1,300,000 | Working |
| Fort Worth | 960,000 | Working |
| Grand Prairie | 200,000 | Working |

### eTRAKiT - 4 Cities Working
| City | Population | Status |
|------|------------|--------|
| Plano | 290,000 | Working |
| Frisco | 220,000 | Working |
| Denton | 150,000 | Working |
| Flower Mound | 80,000 | Working |

### EnerGov CSS - 6 Cities Working, 2 Blocked
| City | Population | Status |
|------|------------|--------|
| Southlake | 32,000 | Working |
| Colleyville | 26,000 | Working |
| Trophy Club | 13,000 | Working |
| Waxahachie | 40,000 | Working |
| Cedar Hill | 48,000 | Working |
| DeSoto | 55,000 | Working |
| McKinney | 210,000 | **Blocked** (Angular timeouts) |
| Allen | 110,000 | **Blocked** (Angular timeouts) |

### MyGov - 10 Cities Working
| City | Population | Status |
|------|------------|--------|
| Westlake | 1,600 | Working |
| Mansfield | 75,000 | Working |
| Rowlett | 65,000 | Working |
| Burleson | 48,000 | Working |
| Little Elm | 50,000 | Working |
| Midlothian | 35,000 | Working |
| Celina | 30,000 | Working |
| Lancaster | 40,000 | Working |
| Fate | 18,000 | Working |
| Venus | 6,000 | Working |

### SmartGov - 1 City Working
| City | Population | Status |
|------|------------|--------|
| Sachse | 27,000 | Working |

### Socrata API - 1 City Working
| City | Population | Status |
|------|------------|--------|
| Arlington | 400,000 | Working |

### CityView - 1 City Working
| City | Population | Status |
|------|------------|--------|
| Carrollton | 133,000 | Working (20-result limit) |

### MGO Connect - 3 Cities Blocked
| City | Population | Status |
|------|------------|--------|
| Irving | 250,000 | **Blocked** (Anti-bot) |
| Lewisville | 110,000 | **Blocked** (Anti-bot) |
| Forney | 25,000 | **Blocked** (No public portal) |

---

## Tier Definitions

| Tier | Criteria | Focus |
|------|----------|-------|
| **A** | Big 4 cities OR high-wealth enclaves OR ultra-high growth | Maximum volume or value |
| **B** | Population >30k OR high growth (>3%) OR wealthy suburbs | Primary targets |
| **C** | Smaller cities, low growth | Backlog / opportunistic |

---

## Quick Wins - VERIFIED

These cities use platforms we already support and are ready to add:

| Priority | City | Population | Platform | Portal URL |
|----------|------|------------|----------|------------|
| 1 | **Mesquite** | 150,000 | EnerGov CSS | energov.cityofmesquite.com |
| 2 | **Keller** | 45,000 | eTRAKiT | trakitweb.cityofkeller.com |
| 3 | **Prosper** | 35,000 | eTRAKiT | etrakit.prospertx.gov |
| 4 | **Grapevine** | 50,000 | MyGov | grapevinetexas.gov/1862 |

**Total Easy Win Population: ~280,000**

### Still Need Research

1. **Kaufman** - Probably MyGov (research files exist)
2. **The Colony** - Check for eTRAKiT or EnerGov
3. **Coppell** - Check for eTRAKiT or EnerGov
4. **Highland Village** - Check for eTRAKiT (Denton County pattern)

---

## Research Methodology

For each unknown city:

1. **Search Query:** `"{city} TX building permits (etrakit OR energov OR mygov OR citizen self service)"`
2. **URL Pattern Check:**
   - `*.accela.com` → Accela
   - `etrakit.*` → eTRAKiT
   - `*.tylerhost.net` or `citizenportal.*` → EnerGov CSS
   - `public.mygov.us` → MyGov
   - `*.smartgovcommunity.com` → SmartGov
3. **Test public accessibility** (no login required)
4. **Update JSON** with findings

---

## Next Steps

### Immediate (Easy Wins - Add to existing scrapers)
1. **Add Mesquite** to `citizen_self_service.py` (EnerGov CSS)
2. **Add Keller** to `etrakit_fast.py` (eTRAKiT)
3. **Add Prosper** to `etrakit_fast.py` (eTRAKiT)
4. **Add Grapevine** to `mygov_multi.py` (MyGov)

### Short-term (Fix blocked cities)
5. Fix EnerGov Angular timeouts for **McKinney** and **Allen** (320k population)
6. Investigate MGO Connect workarounds for **Irving/Lewisville** (360k population)

### Medium-term (New platforms)
7. Develop **Citizenserve** scraper for Wylie (and potentially other cities)
8. Develop **Cityworks** scraper for Euless (and potentially other cities)

### Research Needed
9. Investigate **Garland** (240k) - largest uncovered city
10. Investigate **Richardson** (120k) - custom portal
11. Investigate **North Richland Hills** (70k) - Enterprise Permitting system
12. Research remaining Tier B/C cities for platform identification
