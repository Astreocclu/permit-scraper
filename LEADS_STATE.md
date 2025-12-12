# DFW Signal Engine - Leads State Report
**Generated**: December 12, 2025
**Database**: `contractors_dev`

---

## Executive Summary

| Metric | Count |
|--------|-------|
| **Total Permits** | 26,487 |
| **Scored Leads** | 5,517 |
| **Properties Enriched** | 8,069 |
| **Unscored Permits** | 20,970 |
| **Lead Status** | 100% Available |

### Tier Distribution

| Tier | Count | Avg Score | Description |
|------|-------|-----------|-------------|
| **A** | 297 | 85.5 | High-value, fresh leads (top priority) |
| **B** | 388 | 65.7 | Good leads, moderate value |
| **C** | 3,589 | 15.6 | Lower priority leads |
| **U** | 1,243 | 41.3 | Unverified freshness (missing dates) |

---

## Leads by Trade Group

| Trade Group | Tier A | Tier B | Tier C | Tier U | Total |
|-------------|--------|--------|--------|--------|-------|
| **home_systems** | 120 | 160 | 502 | 199 | **981** |
| **luxury_outdoor** | 68 | 52 | 239 | 19 | **378** |
| **structural** | 28 | 66 | 1,054 | 54 | **1,202** |
| **home_exterior** | 33 | 53 | 402 | 41 | **529** |
| **commercial** | 0 | 7 | 202 | 37 | **246** |
| **other** | 46 | 49 | 1,153 | 888 | **2,136** |
| **unsellable** | 2 | 1 | 37 | 5 | **45** |

### Top Sellable Categories

**Home Systems (981 leads)**
| Category | A | B | C | U | Total |
|----------|---|---|---|---|-------|
| plumbing | 72 | 101 | 271 | 48 | 492 |
| electrical | 34 | 39 | 154 | 32 | 259 |
| hvac | 14 | 20 | 66 | 119 | 219 |

**Luxury Outdoor (378 leads)**
| Category | A | B | C | U | Total |
|----------|---|---|---|---|-------|
| pool | 43 | 18 | 65 | 2 | 128 |
| outdoor_living | 14 | 16 | 72 | 12 | 114 |
| concrete | 8 | 19 | 50 | 13 | 90 |
| fence | 11 | 18 | 102 | 5 | 136 |

**Structural (1,202 leads)**
| Category | A | B | C | U | Total |
|----------|---|---|---|---|-------|
| foundation | 10 | 23 | 313 | 25 | 371 |
| remodel | 5 | 26 | 346 | 16 | 393 |
| addition | 13 | 17 | 180 | 4 | 214 |
| new_construction | 0 | 0 | 215 | 9 | 224 |

**Home Exterior (529 leads)**
| Category | A | B | C | U | Total |
|----------|---|---|---|---|-------|
| windows | 3 | 14 | 261 | 4 | 282 |
| roof | 21 | 20 | 85 | 24 | 150 |
| siding | 1 | 0 | 6 | 0 | 7 |

---

## Leads by City

### Working Scrapers (High Volume)

| City | Tier A | Tier B | Tier C | Tier U | Total | Unscored |
|------|--------|--------|--------|--------|-------|----------|
| **Dallas** | 227 | 157 | 1,182 | 70 | 1,636 | 1,034 |
| **Fort Worth** | 18 | 44 | 488 | 45 | 595 | 656 |
| **Arlington** | 1 | 14 | 1,226 | 0 | 1,241 | 17,436 |
| **Carrollton** | 20 | 53 | 131 | 0 | 204 | 54 |
| **Irving** | 11 | 58 | 184 | 47 | 300 | 75 |
| **Lewisville** | 8 | 35 | 104 | 67 | 214 | 46 |
| **N. Richland Hills** | 1 | 14 | 155 | 0 | 170 | 37 |

### Missing Date Issues (All Tier U)

| City | Tier U | Notes |
|------|--------|-------|
| **Flower Mound** | 772 | eTRAKiT scraper doesn't extract dates |
| **Frisco** | 149 | Date extraction needs fix |
| **Allen** | 52 | EnerGov CSS - no date parsing |
| **Colleyville** | 37 | EnerGov CSS - no date parsing |

### High-Value Suburbs (Low Volume)

| City | Tier A | Tier B | Tier C | Total |
|------|--------|--------|--------|-------|
| **Westlake** | 4 | 0 | 29 | 33 |
| **Southlake** | 3 | 0 | 36 | 43* |
| **Plano** | 2 | 7 | 16 | 25 |
| **Grapevine** | 2 | 6 | 34 | 42 |

*Southlake mostly commercial - residential batch scrape needed

---

## High-Value Leads (Top 20)

Properties with market value > $500K and Tier A/B:

| Category | City | Tier | Score | Market Value |
|----------|------|------|-------|--------------|
| electrical | dallas | A | 85 | $12,716,310 |
| commercial_plumbing | carrollton | B | 65 | $11,098,430 |
| remodel | carrollton | B | 65 | $8,832,093 |
| roof | dallas | A | 85 | $8,799,370 |
| commercial_plumbing | dallas | B | 65 | $8,641,561 |
| fence | dallas | A | 85 | $8,063,620 |
| pool | dallas | A | 85 | $8,063,620 |
| other | dallas | B | 65 | $6,850,000 |
| other | dallas | A | 85 | $6,461,030 |
| other | dallas | A | 85 | $6,200,270 |
| other | dallas | A | 85 | $5,349,640 |
| plumbing | dallas | A | 85 | $4,525,260 |
| electrical | dallas | A | 85 | $4,109,400 |
| electrical | dallas | A | 95 | $4,041,480 |
| electrical | westlake | A | 85 | $3,995,881 |
| other | dallas | A | 85 | $3,936,000 |
| siding | dallas | A | 85 | $3,869,690 |
| plumbing | dallas | A | 85 | $3,794,580 |
| other | fort_worth | A | 85 | $3,787,677 |
| other | fort_worth | A | 85 | $3,787,677 |

---

## Pipeline Analysis

### Scoring Efficiency

```
Total Permits:     26,487
├── Scored:         5,517 (20.8%)
├── Unscored:      20,970 (79.2%)
│   ├── Arlington: 17,436 (stale data from Socrata bulk)
│   ├── Other:      3,534 (pending enrichment/scoring)
```

### Enrichment Status

```
Total Properties:  10,140
├── Enriched:       8,069 (79.6%)
├── Failed:         2,071 (20.4%)
```

### Tier U Analysis

1,243 leads (22.5%) are Tier U (unverified freshness) because:
- Scraper doesn't extract `issued_date` (Flower Mound, Frisco, Allen, Colleyville)
- Permits genuinely have no date in source portal
- **Impact**: Potential high-value leads stuck in limbo

**Cities Most Affected:**
| City | Tier U Count | % of City's Leads |
|------|--------------|-------------------|
| Flower Mound | 772 | 100% |
| Frisco | 149 | 100% |
| Allen | 52 | 100% |
| Colleyville | 37 | 100% |
| Dallas | 70 | 4% |
| Fort Worth | 45 | 8% |

---

## Actionable Recommendations

### Immediate (High ROI)

1. **Score Arlington backlog** - 17,436 unscored permits (apply date filtering first)
2. **Fix date extraction** - Flower Mound, Frisco scrapers (772+ leads → Tier A/B potential)
3. **Email Tier A pool leads** - 43 pool leads ready for contractor outreach

### Short-Term

4. **Complete Southlake residential scrape** - Run batch scraper for all 14 permit types
5. **Run Westlake full scrape** - 367 harvested addresses ready
6. **Review Tier U manually** - 1,243 leads with avg score 41 could be valuable

### Medium-Term

7. **Fix McKinney/Allen EnerGov** - Apply Southlake fixes (Angular timeout fixes)
8. **Irving PDF parser** - Implement pdfplumber for MGO Connect PDF exports
9. **Add playwright-stealth** - Attempt Denton/Lewisville MGO Connect bypass

---

## Database Queries

```sql
-- Tier distribution
SELECT tier, COUNT(*), ROUND(AVG(score)::numeric, 1) as avg_score
FROM clients_scoredlead GROUP BY tier ORDER BY tier;

-- Category breakdown by tier
SELECT category, tier, COUNT(*)
FROM clients_scoredlead GROUP BY category, tier ORDER BY category, tier;

-- High-value leads
SELECT sl.category, p.city, sl.tier, sl.score, prop.market_value
FROM clients_scoredlead sl
JOIN leads_permit p ON sl.permit_id = p.id
LEFT JOIN leads_property prop ON p.property_address = prop.property_address
WHERE sl.tier IN ('A', 'B') AND prop.market_value > 500000
ORDER BY prop.market_value DESC;

-- Unscored by city
SELECT p.city, COUNT(*) as unscored FROM leads_permit p
WHERE NOT EXISTS (SELECT 1 FROM clients_scoredlead sl WHERE sl.permit_id = p.id)
GROUP BY p.city ORDER BY unscored DESC;
```

---

## Key Files

```
/home/reid/testhome/permit-scraper/
├── scripts/
│   ├── score_leads.py       # AI scoring with Tier U support
│   ├── enrich_cad.py        # CAD enrichment (4 counties)
│   └── load_permits.py      # JSON → PostgreSQL loader
├── scrapers/
│   ├── accela_fast.py       # Dallas, Fort Worth, Grand Prairie
│   ├── etrakit_fast.py      # Frisco, Flower Mound
│   ├── cityview.py          # Carrollton
│   ├── citizen_self_service.py  # Southlake, Colleyville
│   ├── mygov_westlake.py    # Westlake (address-based)
│   └── dfw_big4_socrata.py  # Arlington (API)
├── exports/                 # CSV exports by trade/tier
├── SCRAPER_STATUS.md        # Municipality status tracker
└── LEADS_STATE.md           # This document
```
