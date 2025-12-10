# DFW Permit Scraper

Automated lead generation for home service contractors. Scrapes building permits from DFW city portals, enriches with County Appraisal District (CAD) data, and scores leads to identify high-value homeowners.

## Status: Active

**Last Updated:** December 9, 2025

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
# Dallas
python3 scrapers/accela.py dallas 1000

# Fort Worth
python3 scrapers/accela.py fort_worth 1000

# Frisco (fast, no LLM)
python3 scrapers/etrakit_fast.py frisco 1000

# Arlington (API-based)
python3 scrapers/dfw_big4_socrata.py

# Grand Prairie
python3 scrapers/accela.py grand_prairie 1000

# Plano
python3 scrapers/etrakit.py plano 1000
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

## Output Files

| File | Description |
|------|-------------|
| `{city}_raw.json` | Raw scraped permits |
| `{city}_enriched.json` | Permits + CAD property data |
| `{city}_leads.csv` | Scored leads ready for outreach |
| `data/permits.db` | SQLite database |

## Documentation

- **SCRAPER_STATUS.md** - Detailed status of each scraper
- **_archive/** - Historical session logs

## Project Structure

```
scrapers/           # City-specific scrapers
scripts/            # Pipeline processing (load, enrich, score)
data/               # Database and exports
debug_html/         # Screenshots for debugging
```
