# Permit Scraper Status Summary
**Last Updated**: December 11, 2025
**Archive**: See `_archive/` for historical session logs.

## Working Scrapers

| City | Scraper | Command | Notes |
|------|---------|---------|-------|
| **Dallas** | `accela_fast.py` | `python3 scrapers/accela_fast.py dallas 1000` | ⚡ Fast DOM extraction (no LLM) - VERIFIED 12/09/25 |
| **Fort Worth** | `accela_fast.py` | `python3 scrapers/accela_fast.py fort_worth 1000` | ⚡ Fast DOM extraction (migrated from LLM) |
| **Frisco** | `etrakit_fast.py` | `python3 scrapers/etrakit_fast.py frisco 1000` | ⚡ Fast DOM extraction, no LLM |
| **Arlington** | `dfw_big4_socrata.py` | `python3 scrapers/dfw_big4_socrata.py` | API-based, bulk CSV |
| **Grand Prairie** | `accela_fast.py` | `python3 scrapers/accela_fast.py grand_prairie 1000` | ⚡ Fast DOM extraction |
| **Plano** | `etrakit.py` | `python3 scrapers/etrakit.py plano 1000` | Working (Public Login) |
| **Flower Mound** | `etrakit_fast.py` | `python3 scrapers/etrakit_fast.py flower_mound 1000` | ⚡ Fast DOM extraction (eTRAKiT) |
| **Carrollton** | `cityview.py` | `python3 scrapers/cityview.py carrollton 500` | CityView portal (limits to ~20 results per search) |

## Data Inventory (Verified 12/09/25)

| File | Rows | Description |
|------|------|-------------|
| `dallas_leads.csv` | 988 | Enriched & scored Dallas leads |
| `dfw_big4_contractor_leads.csv` | 19,478 | Raw Arlington/Socrata data |
| `arlington_filtered.csv` | 8,009 | Filtered Arlington permits |
| `frisco_raw.json` | ~1000 | Raw Frisco permits |
| `fort_worth_raw.json` | 1000 | Raw Fort Worth permits |
| `plano_raw.json` | 54 | Raw Plano permits |

---

## DFW Metro - All 30 Municipalities

| # | City | Pop (est) | Platform | Scraper | Status |
|---|------|-----------|----------|---------|--------|
| 1 | **Dallas** | 1.3M | Accela | `accela_fast.py` | ✅ Working (Fast DOM) |
| 2 | **Fort Worth** | 950K | Accela | `accela_fast.py` | ✅ Working (Fast DOM) |
| 3 | **Arlington** | 400K | Socrata API | `dfw_big4_socrata.py` | ✅ Working |
| 4 | **Plano** | 290K | eTRAKiT | `etrakit.py` | ✅ Working |
| 5 | **Frisco** | 220K | eTRAKiT | `etrakit_fast.py` | ✅ Working (Fast DOM) |
| 6 | **Grand Prairie** | 200K | Accela | `accela_fast.py` | ✅ Working (Fast DOM) |
| 7 | **Irving** | 250K | MGO Connect | `mgo_connect.py` | ❌ Anti-bot blocked |
| 8 | **McKinney** | 200K | EnerGov CSS | `citizen_self_service.py` | ❌ Angular timeouts |
| 9 | **Garland** | 240K | None | — | ❌ No unified portal |
| 10 | **Denton** | 150K | MGO Connect | `mgo_connect.py` | ❌ Anti-bot blocked |
| 11 | **Lewisville** | 115K | MGO Connect | `mgo_connect.py` | ❌ Anti-bot blocked |
| 12 | **Carrollton** | 140K | CityView | `cityview.py` | ✅ Working |
| 13 | **Richardson** | 120K | Custom (cor.net) | — | ❌ Not Accela (404) |
| 14 | **Allen** | 110K | EnerGov CSS | `citizen_self_service.py` | ❌ Angular timeouts |
| 15 | **Flower Mound** | 80K | eTRAKiT | `etrakit_fast.py` | ✅ Working |
| 16 | **Cedar Hill** | 50K | MGO Connect | `mgo_connect.py` | ❌ Anti-bot blocked |
| 17 | **Mesquite** | 150K | EnerGov CSS | `energov.py` | ❌ Angular timeouts (tested 12/09) |
| 18 | **Southlake** | 32K | EnerGov CSS | `citizen_self_service.py` | ❌ Angular timeouts |
| 19 | **Rowlett** | 68K | MyGov | — | ❌ Requires contractor login |
| 20 | **Grapevine** | 55K | MyGov (.exe) | — | ❌ Requires desktop client |
| 21 | **Duncanville** | 40K | MGO Connect | `mgo_connect.py` | ❌ Anti-bot blocked |
| 22 | **Keller** | 50K | EnerGov CSS | — | 🔍 Migrated from eTRAKiT |
| 23 | **DeSoto** | 55K | Unknown | — | 🔍 Not researched |
| 24 | **Lancaster** | 42K | MyGov | `mygov.py` | 🔍 Not tested |
| 25 | **Euless** | 58K | Unknown | — | 🔍 Not researched |
| 26 | **Bedford** | 50K | Unknown | — | 🔍 Not researched |
| 27 | **Hurst** | 40K | Unknown | — | 🔍 Not researched |
| 28 | **Coppell** | 45K | Unknown | — | 🔍 Not researched |
| 29 | **Watauga** | 25K | MyGov | `mygov.py` | 🔍 Not tested |
| 30 | **The Colony** | 45K | Unknown | — | 🔍 Not researched |

### Legend
- ✅ **Working** - Scraper runs, data extracted
- ❌ **Blocked** - Technical barrier (anti-bot, timeouts, broken)
- ⚠️ **Partial** - Works but limited/old data
- 🔍 **Not researched** - Need to identify portal platform
- 🔻 **TBD** - Low priority / difficult access (Grapevine requires .exe)

---

## Platform Summary

| Platform | Working | Blocked | Not Scrapeable |
|----------|---------|---------|----------------|
| Accela | 4 | 0 | 0 |
| eTRAKiT | 3 | 0 | 0 |
| CityView | 1 | 0 | 0 |
| Socrata API | 1 | 0 | 0 |
| MGO Connect | 0 | 5 | 0 |
| EnerGov CSS | 0 | 4 | 0 |
| MyGov | 0 | 0 | 2 |
| None | 0 | 0 | 1 |
| Unknown | 0 | 1 | 9 |

**Total: 9 working / 10 blocked / 12 not scrapeable or not researched**

---

## Quick Reference

- **Credentials**: Stored in `.env` file
- **Raw Output**: `{city}_raw.json` in repo root
- **Processed Output**: `{city}_leads.csv` or `exports/` directory
- **Debug**: Screenshots saved to `debug_html/`

## Scraper File Inventory

| File | Type | Description |
|------|------|-------------|
| `scrapers/accela_fast.py` | ⚡ Production | Fast DOM extraction for Accela portals (Dallas, Fort Worth, Grand Prairie) |
| `scrapers/etrakit_fast.py` | ⚡ Production | Fast DOM extraction for eTRAKiT (Frisco, Flower Mound) - GOLD STANDARD |
| `scrapers/cityview.py` | Production | CityView portal scraper (Carrollton) |
| `scrapers/dfw_big4_socrata.py` | ⚡ Production | API-based bulk extraction (Arlington) |
| `scrapers/etrakit.py` | Production | eTRAKiT with login support (Plano) |
| `scrapers/accela.py` | Legacy | LLM-based Accela scraper (slow, expensive) - DEPRECATED |
| `scrapers/mgo_connect.py` | ❌ Blocked | MGO Connect scraper - anti-bot detection |
| `scrapers/citizen_self_service.py` | ❌ Broken | EnerGov CSS Angular scraper - timeout issues |
| `scrapers/energov.py` | ❌ Broken | EnerGov scraper - Angular timeouts (same as citizen_self_service) |
| `scrapers/mygov.py` | ❌ Broken | MyGov scraper - URLs 404 |
| `scrapers/deepseek.py` | Utility | LLM structured extraction helper |
| `scrapers/mgo_test.py` | Debug | MGO Connect debugging tool |

## Next Steps

1. ~~**Optimize Fort Worth**~~ ✅ DONE - Migrated to `accela_fast.py`
2. ~~**Research unknown cities**~~ ✅ DONE - Flower Mound (eTRAKiT), Carrollton (CityView), Garland (no portal)
3. **MGO Decision** - Irving/Lewisville/Denton blocked by anti-automation (consider playwright-stealth + proxies)
4. ~~**Grapevine/Rowlett**~~ ❌ CLOSED - MyGov requires login/desktop client, not scrapeable
