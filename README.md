# DFW Permit Scraper

Automated lead generation for home service contractors. Scrapes building permits from DFW city portals, enriches with County Appraisal District (CAD) data, and scores leads to identify high-value homeowners.

## Status: Active
**Last Updated:** 2026-02-18

## Live Status Sources

Use these as source of truth instead of hard-coded counts in docs:
- `state/current.md` for active priorities, blockers, and latest context
- `SCRAPER_STATUS.md` for current scraper health by city/platform
- `docs/DATA_ARCHITECTURE.md` for data flow and table usage
- `docs/tag-system-requirements.md` for required claim tags in docs/state/session notes

## Locked Tag Policy [DECIDED]

- Claim-status tags are frozen to: `[VERIFIED]`, `[UNVERIFIED]`, `[DECIDED]`, `[OBSERVED]`, `[PROPOSED]`, `[INTERPRETIVE]`.
- Canonical naming is `[PREMISE-6]`; `[PREMISE6]` is non-canonical.
- Claim-status tags do not go in file names.
- Taxonomy tags in file names use this exact slot format:
  - `YYYY-MM-DD__[ARTIFACT]__[DOMAIN]__[ENTITY-OR-NO-SOURCE]__[WORKFLOW]__short-title.md`

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

# eTRAKiT Cities (Frisco, Flower Mound, Denton, The Colony partial)
python3 scrapers/etrakit.py frisco 1000
python3 scrapers/etrakit.py flower_mound 1000
python3 scrapers/etrakit.py denton 500
python3 scrapers/etrakit.py the_colony 500   # run enrich_colony_addresses.py for addresses
# Plano requires login: python3 scrapers/etrakit_auth.py plano 1000

# EnerGov CSS Cities (Mesquite, Prosper, Grand Prairie, Allen, McKinney, etc.)
python3 scrapers/citizen_self_service.py prosper 500
python3 scrapers/citizen_self_service.py grand_prairie 500
python3 scrapers/citizen_self_service.py mesquite 500    # pagination flaky
python3 scrapers/citizen_self_service.py southlake 500   # may require Browser-Use for filters
python3 scrapers/citizen_self_service.py mckinney 500    # watch for pagination stall
python3 scrapers/citizen_self_service.py allen 500

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

## Scraper Status

Current city/platform status is maintained in `SCRAPER_STATUS.md`.

## Output Files

| File | Description |
|------|-------------|
| `data/raw/{city}_raw.json` | Raw scraped permits |
| `data/exports/` | Processed data exports |
| `exports/{trade_group}/{category}/tier_{a,b,c}.csv` | Scored leads by category |
| Database: `leads_permit` | All scraped permits |
| Database: `leads_property` | CAD enrichment data |
| Database: `clients_scoredlead` | AI-scored leads |

## Project Structure

```
scrapers/           # City-specific scrapers
scripts/            # Pipeline processing (load, enrich, score)
data/raw/           # Raw scraped JSON files
data/exports/       # Processed exports
data/downloads/     # Downloaded Excel files from scrapers
_archive/           # Archived logs and screenshots
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
