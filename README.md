# DFW Permit Scraper

Automated lead generation for home service contractors. Scrapes building permits from DFW city portals, enriches with County Appraisal District (CAD) data, and scores leads to identify high-value homeowners.

## Status: Active
**Last Updated:** December 14, 2025

## Data Summary

### Scored Leads: 8,235 total
| Tier | Count | Avg Score | Description |
|------|-------|-----------|-------------|
| **A** | 383 | 85.3 | Hot leads - high value, actionable |
| **B** | 645 | 66.0 | Warm leads - moderate priority |
| **C** | 3,481 | 23.8 | Cool leads - lower priority |
| **D** | 2,021 | 0.0 | Garbage - auto-discard |
| **U** | 1,705 | 40.9 | Unverified - needs review |

### Score Distribution
| Category | Count | % |
|----------|-------|---|
| Hot (80+) | 455 | 5% |
| Warm (60-79) | 1,127 | 13% |
| Cool (40-59) | 434 | 5% |
| Cold (20-39) | 2,010 | 24% |
| Junk (0-19) | 4,209 | 51% |

### Properties Enriched: 25,641 total
| Status | Count |
|--------|-------|
| Success (CAD data found) | 19,918 |
| Failed (no CAD match) | 5,720 |
| Pending | 3 |

### Permits in Database: 39,075
Loaded from 32 cities across DFW metroplex

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
# Big Cities - Accela (Dallas, Fort Worth, Grand Prairie)
python3 scrapers/accela_fast.py dallas 1000
python3 scrapers/accela_fast.py fort_worth 1000

# eTRAKiT Cities (Frisco, Plano, Denton, Prosper, Flower Mound, Keller)
python3 scrapers/etrakit.py frisco 1000
python3 scrapers/etrakit.py denton 500

# EnerGov CSS Cities (Mesquite, Southlake, Princeton, etc.)
python3 scrapers/citizen_self_service.py mesquite 500
python3 scrapers/citizen_self_service.py princeton 500

# MyGov Multi-City (Mansfield, Celina, Fate, Royse City, etc.)
python3 scrapers/mygov_multi.py mansfield 100
python3 scrapers/mygov_multi.py celina 100
python3 scrapers/mygov_multi.py --list  # Show all available cities

# OpenGov (Bedford - NEW!)
python3 scrapers/opengov.py bedford 100

# SmartGov (Sachse)
python3 scrapers/smartgov_sachse.py 500

# Arlington (Socrata API)
python3 scrapers/dfw_big4_socrata.py

# Carrollton (CityView)
python3 scrapers/cityview.py carrollton 500

# Westlake (Ultra-wealthy - Address Harvesting)
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

| City | Pop | Scraper | Status | Notes |
|------|-----|---------|--------|-------|
| **Dallas** | 1.3M | `accela_fast.py` | Working | Fast DOM extraction |
| **Fort Worth** | 960K | `accela_fast.py` | Working | Fast DOM extraction |
| **Arlington** | 400K | `dfw_big4_socrata.py` | Working | API-based, bulk CSV |
| **Plano** | 290K | `etrakit.py` | Working | Public Login required |
| **Frisco** | 220K | `etrakit.py` | Working | Fast DOM extraction |
| **McKinney** | 210K | `citizen_self_service.py` | Blocked | Angular timeouts |
| **Grand Prairie** | 200K | `accela_fast.py` | Working | Fast DOM extraction |
| **Mesquite** | 150K | `citizen_self_service.py` | Working | EnerGov CSS |
| **Denton** | 150K | `etrakit.py` | Working | Fast DOM extraction |
| **Carrollton** | 133K | `cityview.py` | Working | CityView (20-result limit) |
| **Flower Mound** | 80K | `etrakit.py` | Working | Fast DOM extraction |
| **Mansfield** | 75K | `mygov_multi.py` | Working | MyGov multi-city |
| **Rowlett** | 65K | `mygov_multi.py` | Working | MyGov multi-city |
| **Grapevine** | 50K | `mygov_multi.py` | Working | MyGov multi-city |
| **Little Elm** | 50K | `mygov_multi.py` | Working | MyGov multi-city |
| **Bedford** | 48K | `opengov.py` | Working | **NEW** OpenGov with valuations |
| **Cedar Hill** | 48K | `citizen_self_service.py` | Working | EnerGov CSS |
| **DeSoto** | 55K | `citizen_self_service.py` | Working | EnerGov CSS |
| **Burleson** | 48K | `mygov_multi.py` | Working | MyGov multi-city |
| **Keller** | 45K | `etrakit.py` | Working | eTRAKiT |
| **Waxahachie** | 40K | `citizen_self_service.py` | Working | EnerGov CSS |
| **Lancaster** | 40K | `mygov_multi.py` | Working | MyGov multi-city |
| **Prosper** | 35K | `etrakit.py` | Working | High growth (8%) |
| **Midlothian** | 35K | `mygov_multi.py` | Working | MyGov multi-city |
| **Southlake** | 32K | `citizen_self_service.py` | Working | Wealthy suburb |
| **Celina** | 30K | `mygov_multi.py` | Working | Ultra high growth (15%) |
| **Sachse** | 27K | `smartgov_sachse.py` | Working | SmartGov |
| **Colleyville** | 26K | `citizen_self_service.py` | Working | Wealthy suburb |
| **Fate** | 18K | `mygov_multi.py` | Working | High growth (10%) |
| **Princeton** | 15K | `citizen_self_service.py` | Working | High growth (8%) |
| **Royse City** | 13K | `mygov_multi.py` | Working | MyGov multi-city |
| **Trophy Club** | 13K | `citizen_self_service.py` | Working | Wealthy suburb |
| **Westlake** | 1.6K | `mygov_westlake.py` | Working | Ultra-wealthy |
| **Highland Park** | 9K | Email Only | No Portal | TPIA request required |
| **Irving** | 250K | `mgo_connect.py` | Blocked | Anti-bot detection |
| **Allen** | 110K | `citizen_self_service.py` | Blocked | Angular timeouts |

**Total: 32 working / 3 blocked**

## Platform Summary

| Platform | Cities | Scraper | Notes |
|----------|--------|---------|-------|
| **Accela** | Dallas, Fort Worth, Grand Prairie | `accela_fast.py` | Fast DOM extraction |
| **eTRAKiT** | Frisco, Plano, Denton, Flower Mound, Prosper, Keller | `etrakit.py` | Fast DOM extraction |
| **EnerGov CSS** | Mesquite, DeSoto, Cedar Hill, Southlake, Colleyville, Waxahachie, Trophy Club, Princeton | `citizen_self_service.py` | Excel export available |
| **MyGov** | Mansfield, Rowlett, Grapevine, Little Elm, Burleson, Lancaster, Midlothian, Celina, Fate, Royse City, Venus | `mygov_multi.py` | Street name search |
| **OpenGov** | Bedford | `opengov.py` | **NEW** - Record search with valuations |
| **SmartGov** | Sachse | `smartgov_sachse.py` | Custom portal |
| **Socrata API** | Arlington | `dfw_big4_socrata.py` | Bulk CSV download |
| **CityView** | Carrollton | `cityview.py` | Limited to 20 results |
| **MyGov (Custom)** | Westlake | `mygov_westlake.py` | Ultra-wealthy, address harvesting |
| **MGO Connect** | Irving (blocked) | `mgo_connect.py` | Anti-bot detection |

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

| File | Type | Cities | Description |
|------|------|--------|-------------|
| `accela_fast.py` | Production | Dallas, Fort Worth, Grand Prairie | Fast DOM for Accela portals |
| `etrakit.py` | Production | Frisco, Plano, Denton, Flower Mound, Prosper, Keller | eTRAKiT portals |
| `citizen_self_service.py` | Production | Mesquite, DeSoto, Cedar Hill, Southlake, Colleyville, Waxahachie, Trophy Club, Princeton | EnerGov CSS with Excel export |
| `mygov_multi.py` | Production | Mansfield, Rowlett, Grapevine, Little Elm, Burleson, Lancaster, Midlothian, Celina, Fate, Royse City, Venus | MyGov street search |
| `opengov.py` | Production | Bedford | **NEW** OpenGov record search |
| `smartgov_sachse.py` | Production | Sachse | SmartGov portal |
| `dfw_big4_socrata.py` | Production | Arlington | Socrata API bulk download |
| `cityview.py` | Production | Carrollton | CityView portal (20-result limit) |
| `mygov_westlake.py` | Production | Westlake | MyGov with address harvesting |
| `westlake_harvester.py` | Utility | Westlake | Address harvester from CAD |
| `filters.py` | Utility | All | Residential permit filter |
| `mgo_connect.py` | Blocked | Irving | MGO Connect - anti-bot issues |
