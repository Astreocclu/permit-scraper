# Scraper Run Results - 2026-01-06

## Summary
- **Total permits scraped today:** 14,467
- **Cities scraped:** 23

## Results by Platform

### Accela (3 cities)
| City | Permits | Status |
|------|---------|--------|
| Dallas | 1,000 | SUCCESS |
| Fort Worth | 1,000 | SUCCESS |
| Grand Prairie | 0 | FAILED - Portal issue |

### eTRAKiT (6 cities)
| City | Permits | Status |
|------|---------|--------|
| Frisco | 500 | SUCCESS (deduped) |
| Flower Mound | 917 | SUCCESS (deduped) |
| Denton | 980 | SUCCESS (deduped) |
| Keller | 0 | NOT IN CONFIG |
| Prosper | 0 | TIMEOUT ERROR |
| Plano | 0 | AUTH REQUIRED - no output |

### EnerGov CSS (10 cities)
| City | Permits | Status |
|------|---------|--------|
| Southlake | 0 | RUNNING/TIMEOUT |
| Colleyville | 1,000 | SUCCESS |
| McKinney | 0 | RUNNING/TIMEOUT |
| Allen | 1,000 | SUCCESS |
| Cedar Hill | 1,000 | SUCCESS |
| DeSoto | 0 | RUNNING |
| Trophy Club | 1,000 | SUCCESS |
| Waxahachie | 1,000 | SUCCESS |
| Hurst | 1,000 | SUCCESS |
| Coppell | 0 | FAILED - No permits in DOM |
| Farmers Branch | 0 | RUNNING |

### MyGov (10 cities)
| City | Permits | Status |
|------|---------|--------|
| Mansfield | 452 | SUCCESS |
| Rowlett | 179 | SUCCESS |
| Grapevine | 259 | SUCCESS |
| Little Elm | 103 | SUCCESS |
| Lancaster | 187 | SUCCESS |
| Midlothian | 171 | SUCCESS |
| Celina | 182 | SUCCESS |
| Fate | 124 | SUCCESS |
| Venus | 58 | SUCCESS |
| Westlake | 100 | SUCCESS |

### Other Platforms
| City | Platform | Permits | Status |
|------|----------|---------|--------|
| Sachse | SmartGov | 1,000 | SUCCESS |
| Carrollton | CityView | 255 | SUCCESS |
| Arlington | Socrata API | 17,895 | SUCCESS (already in DB) |
| Collin CAD | Socrata API | 1,000 | SUCCESS (18 cities) |

## Issues to Address (Second Pass)

### Failed/Empty Scrapers
1. **Grand Prairie** - Portal not loading results table
2. **Prosper** - Playwright timeout on screenshot
3. **Plano** - Auth scraper returned no output
4. **Coppell** - No permits found in DOM
5. **Southlake** - Still running/timeout
6. **McKinney** - Still running/timeout

### Config Issues
- **Keller** - Not in eTRAKiT config, needs to be added

## Database Load Results

| Metric | Count |
|--------|-------|
| **New permits loaded** | 19,892 |
| **Duplicates skipped** | 18,409 |
| **Total in database** | 61,432 |

### Top Loaders (Today)
| City | Loaded | Skipped |
|------|--------|---------|
| Euless | 1,069 | 59 |
| Cedar Hill | 999 | 1 |
| Fort Worth | 998 | 2 |
| Hurst | 998 | 2 |
| Duncanville | 997 | 3 |
| Allen | 996 | 4 |
| Sachse | 983 | 17 |
| Colleyville | 968 | 32 |
| Trophy Club | 924 | 76 |
| Denton | 924 | 56 |

## Next Steps (Second Pass)
1. Re-run failed scrapers individually:
   - Grand Prairie (portal issue)
   - Prosper (timeout)
   - Plano (auth issue)
   - Coppell (DOM issue)
   - Southlake (still running)
   - McKinney (still running)
2. Add Keller to eTRAKiT config
3. Run CAD enrichment: `python3 scripts/enrich_cad.py`
4. Run AI scoring: `python3 scripts/score_leads.py`
