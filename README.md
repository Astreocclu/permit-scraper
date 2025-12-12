# DFW Permit Scraper

Automated lead generation for home service contractors. Scrapes building permits from DFW city portals, enriches with County Appraisal District (CAD) data, and scores leads to identify high-value homeowners.

## Status: Active
**Last Updated:** December 12, 2025

## Quick Start

### 1. Setup
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Add DEEPSEEK_API_KEY and credentials
```

### 2. Scrape Permits
```bash
# Dallas (Fast DOM)
python3 scrapers/accela_fast.py dallas 1000

# Fort Worth (Fast DOM)
python3 scrapers/accela_fast.py fort_worth 1000

# Frisco (Fast DOM)
python3 scrapers/etrakit_fast.py frisco 1000

# Flower Mound (Fast DOM)
python3 scrapers/etrakit_fast.py flower_mound 1000

# Arlington (API-based)
python3 scrapers/dfw_big4_socrata.py

# Grand Prairie (Fast DOM)
python3 scrapers/accela_fast.py grand_prairie 1000

# Plano (eTRAKiT with login)
python3 scrapers/etrakit.py plano 1000

# Carrollton (CityView)
python3 scrapers/cityview.py carrollton 500

# Southlake (EnerGov CSS - Residential Filtered)
python3 scrapers/citizen_self_service.py southlake 500 --permit-type "Residential Remodel"

# Colleyville (EnerGov CSS)
python3 scrapers/citizen_self_service.py colleyville 500

# Westlake (MyGov - Address Harvested)
python3 scrapers/westlake_harvester.py  # First, harvest addresses
python3 scrapers/mygov_westlake.py      # Then, scrape permits
```

### 3. Process Pipeline
```bash
# Load raw JSON into database
python3 scripts/load_permits.py

# Enrich with CAD data (property values, owner names)
python3 scripts/enrich_cad.py

# Score and export leads (A/B/C tiers)
python3 scripts/score_leads.py
```

## Scraper Status Summary

| City | Scraper | Status | Notes |
|------|---------|--------|-------|
| **Dallas** | `accela_fast.py` | Working | Fast DOM extraction |
| **Fort Worth** | `accela_fast.py` | Working | Fast DOM extraction |
| **Arlington** | `dfw_big4_socrata.py` | Working | API-based, bulk CSV |
| **Plano** | `etrakit.py` | Working | Public Login required |
| **Frisco** | `etrakit_fast.py` | Working | Fast DOM extraction |
| **Flower Mound** | `etrakit_fast.py` | Working | Fast DOM extraction |
| **Grand Prairie** | `accela_fast.py` | Working | Fast DOM extraction |
| **Carrollton** | `cityview.py` | Working | CityView portal |
| **Southlake** | `citizen_self_service.py` | Working | EnerGov CSS (Residential filtered) |
| **Colleyville** | `citizen_self_service.py` | Working | EnerGov CSS |
| **Westlake** | `mygov_westlake.py` | Working | MyGov (Address-based) |
| **Irving** | `mgo_connect.py` | Partial | Login works, PDF extraction needed |
| **McKinney** | `citizen_self_service.py` | Blocked | Angular timeouts |
| **Denton** | `mgo_connect.py` | Blocked | Anti-bot detection |

**Total: 11 working / 1 partial / 2+ blocked**

## Platform Summary

| Platform | Cities | Notes |
|----------|--------|-------|
| Accela | Dallas, Fort Worth, Grand Prairie | Fast DOM extraction |
| eTRAKiT | Frisco, Flower Mound, Plano | Fast DOM (Plano needs login) |
| Socrata API | Arlington | Bulk CSV download |
| CityView | Carrollton | Limited to 20 results per search |
| EnerGov CSS | Southlake, Colleyville | Residential filtering available |
| MyGov | Westlake | Address-based lookup |
| MGO Connect | Irving, Denton | Anti-bot issues |

## Output Files

| File | Description |
|------|-------------|
| `{city}_raw.json` | Raw scraped permits |
| `exports/{trade_group}/{category}/tier_{a,b,c}.csv` | Scored leads by category |
| Database: `leads_permit` | All scraped permits |
| Database: `leads_property` | CAD enrichment data |
| Database: `clients_scoredlead` | AI-scored leads |

## Project Structure

```
scrapers/           # City-specific scrapers
scripts/            # Pipeline processing (load, enrich, score)
data/               # Database and exports
debug_html/         # Screenshots for debugging
tests/              # Pytest test suite
```

## Scraper File Reference

| File | Type | Description |
|------|------|-------------|
| `accela_fast.py` | Production | Fast DOM for Accela (Dallas, Fort Worth, Grand Prairie) |
| `etrakit_fast.py` | Production | Fast DOM for eTRAKiT (Frisco, Flower Mound) |
| `etrakit.py` | Production | eTRAKiT with login (Plano) |
| `dfw_big4_socrata.py` | Production | API-based (Arlington) |
| `cityview.py` | Production | CityView (Carrollton) |
| `citizen_self_service.py` | Production | EnerGov CSS (Southlake, Colleyville) |
| `mygov_westlake.py` | Production | MyGov address-based (Westlake) |
| `westlake_harvester.py` | Production | Address harvester for Westlake |
| `filters.py` | Utility | Residential permit filter |
| `mgo_connect.py` | Partial | MGO Connect (Irving) - needs work |
