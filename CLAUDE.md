# Permit Scraper (Signal Engine)

## STARTUP PROTOCOL

**IMPORTANT: Use Gemini to read all documentation - do NOT use Claude's Read tool for startup.**

Gemini has 5x context and should handle reading/summarizing. Claude executes what Gemini advises.

On session start, run this command to get Gemini to read and summarize the entire codebase state:
```bash
cd /home/reid/testhome/permit-scraper && find . -type f \( -name "*.py" -o -name "*.md" -o -name "*.json" \) -not -path "./node_modules/*" -not -path "./.git/*" -not -name "package-lock.json" | head -50 | xargs cat 2>/dev/null | gemini -p "Read README.md and TODO.md first, then summarize this permit scraping codebase. What scrapers exist, what works, what's broken, and what should we work on next? Be concise."
```

This single command has Gemini read everything and provide a summary. Claude should NOT read files in parallel - wait for Gemini's summary.

## STATUS: ACTIVE

This repo contains permit portal scrapers for the DFW Signal Engine.
Scrapes building permits, enriches with CAD data, scores leads for contractor marketing.

## Working Portals (All Fast DOM Extraction)

### Accela
- Dallas, Fort Worth, Grand Prairie - `accela_fast.py`

### eTRAKiT
- Frisco, Flower Mound, Denton - `etrakit.py` (fast DOM)
- Keller, Prosper - `etrakit.py` (NEW - Dec 2024)
- Plano - `etrakit_auth.py` (requires login)

### EnerGov CSS
- Southlake, Colleyville, McKinney, Allen, Trophy Club, Waxahachie - `citizen_self_service.py`
- Cedar Hill, DeSoto, Mesquite - `citizen_self_service.py` (Mesquite NEW - Dec 2024)

### MyGov
- Westlake - `mygov_westlake.py` (address-based)
- Mansfield, Rowlett, Grapevine, Burleson, Little Elm, Lancaster, Midlothian, Celina, Fate, Venus - `mygov_multi.py` (Grapevine NEW - Dec 2024)

### SmartGov
- Sachse - `smartgov_sachse.py` (NEW)

### Other
- Arlington (Socrata API) - `dfw_big4_socrata.py`
- Carrollton (CityView) - `cityview.py`

## Common Commands

### Scraping (Production)
```bash
# Accela cities (Fast DOM)
python3 scrapers/accela_fast.py dallas 1000
python3 scrapers/accela_fast.py fort_worth 1000
python3 scrapers/accela_fast.py grand_prairie 1000

# eTRAKiT cities (Fast DOM)
python3 scrapers/etrakit.py frisco 1000
python3 scrapers/etrakit.py flower_mound 1000
python3 scrapers/etrakit.py keller 1000          # Keller (NEW)
python3 scrapers/etrakit.py prosper 1000         # Prosper (NEW)
python3 scrapers/etrakit_auth.py plano 1000

# EnerGov CSS cities
python3 scrapers/citizen_self_service.py southlake 500   # Southlake
python3 scrapers/citizen_self_service.py cedar_hill 500  # Cedar Hill
python3 scrapers/citizen_self_service.py desoto 500      # DeSoto
python3 scrapers/citizen_self_service.py mesquite 500    # Mesquite (NEW)

# MyGov cities (10 cities)
python3 scrapers/mygov_multi.py mansfield 100   # Mansfield
python3 scrapers/mygov_multi.py rowlett 100     # Rowlett
python3 scrapers/mygov_multi.py grapevine 100   # Grapevine (NEW)
python3 scrapers/mygov_multi.py --list          # Show all MyGov cities
python3 scrapers/mygov_westlake.py              # Westlake (address-based)

# SmartGov
python3 scrapers/smartgov_sachse.py 500         # Sachse (NEW)

# Other platforms
python3 scrapers/dfw_big4_socrata.py            # Arlington (API)
python3 scrapers/cityview.py carrollton 500     # Carrollton
```

### Pipeline
```bash
python3 scripts/load_permits.py      # Load raw JSON to database
python3 scripts/enrich_cad.py        # Enrich with CAD property data
python3 scripts/score_leads.py       # AI scoring with DeepSeek
```

### Testing
```bash
pytest
pytest tests/test_filters.py -v
```

## Architecture

```
scrapers/*.py             -> data/raw/{city}_raw.json  (Scraping)
scripts/load_permits.py   -> PostgreSQL (contractors_dev)  (Loading)
scripts/enrich_cad.py     -> PostgreSQL                (Enrichment)
scripts/score_leads.py    -> clients_scoredlead table  (Scoring)
```

**Database:** PostgreSQL `contractors_dev` (shared with contractor-auditor)
- Tables: `leads_permit`, `leads_property`, `clients_scoredlead`
- Connection: `DATABASE_URL` in `.env`

## Guidelines

- **Isolation:** Do NOT import anything from contractor-auditor
- **Database:** Uses `leads_property` table for CAD data
- **Scrapers:** Prefer `_fast.py` (DOM) over legacy LLM versions
- **Testing:** Run `pytest` before committing scraper changes

## DO NOT
- Import anything from contractor-auditor
- Share database connections between projects
- Mix permit logic with audit logic
