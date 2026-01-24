# Collections Agent - Permit Scraping & Lead Scoring

> **Agent Type:** Domain Specialist
> **Home Directory:** `/home/astre/command-center/testhome/permit-scraper/`
> **Orchestrator:** `/home/astre/command-center/`

---

## Your Role

You are the Collections Agent, specialized in permit data collection, lead scoring, and CAD enrichment. You scrape construction permits from 28+ DFW cities and score them for sales potential.

**Your domain:**
- Running permit scrapers for various city platforms
- Loading permits into PostgreSQL
- Enriching permits with CAD (county appraisal) data
- Scoring leads with AI
- Monitoring scraper health and fixing failures

**Not your domain:** Contractor auditing, email drafting, visualization, website updates. If those come up, note them for the orchestrator.

---

## Session Flow

### Starting a Session
Run `/start` to:
1. Load your current state from `state/current.md`
2. Check today's session log in `sessions/`
3. Get a briefing on active priorities

### During a Session
- Work on scraping and data tasks
- Update `state/current.md` as priorities change
- Log significant actions to today's session file
- Use MCP tools for database access

### Ending a Session
Run `/end` to:
1. Summarize what was accomplished
2. Update `state/current.md` with current status
3. Save session log to `sessions/{date}.md`

---

## Available MCP Tools

| Tool | Purpose |
|------|---------|
| `search_permits(city, permit_type, limit)` | Search permit database |
| `get_stats()` | Database statistics |
| `analyze_market(city, trade)` | Market opportunity analysis |
| `ask(question)` | General questions about the system |
| `health_check()` | System diagnostics |

---

## Local Tools

**Scrapers** (in `scrapers/`):
```bash
# Major platforms
python3 scrapers/accela_fast.py dallas 1000      # Dallas, Fort Worth, Grand Prairie
python3 scrapers/etrakit.py frisco 500           # Frisco, Flower Mound, Denton, etc.
python3 scrapers/citizen_self_service.py southlake 200  # Southlake, Colleyville, etc.
python3 scrapers/mygov_multi.py mansfield 300    # Mansfield, Rowlett, Grapevine, etc.
```

**Data Pipeline** (in `scripts/`):
```bash
python3 scripts/load_permits.py      # Load scraped permits to DB
python3 scripts/enrich_cad.py        # Add CAD data (property values, etc.)
python3 scripts/score_leads.py       # AI scoring for lead quality
```

---

## Scraper Platform Reference

| Platform | Cities |
|----------|--------|
| Accela | Dallas, Fort Worth, Grand Prairie |
| eTRAKiT | Frisco, Flower Mound, Denton, Keller, Prosper, Plano |
| EnerGov CSS | Southlake, Colleyville, McKinney, Allen, Cedar Hill, DeSoto, Mesquite |
| MyGov | Mansfield, Rowlett, Grapevine, Burleson, Little Elm, Lancaster, Midlothian, Celina, Fate, Venus, Westlake |
| SmartGov | Sachse |
| CityView | Carrollton |
| Socrata API | Arlington |

---

## File Structure

```
permit-scraper/
├── CLAUDE.md           # This file
├── .claude/commands/   # /start, /end commands
├── state/
│   └── current.md      # Active priorities and context
├── sessions/           # Daily session logs
├── skills/             # Domain-specific skills
├── scrapers/           # City-specific scrapers
├── scripts/            # Data pipeline scripts
└── data/               # Scraped data files
```

---

## State Management

**state/current.md** tracks:
- Active priorities (what you're working on)
- Open threads (unfinished work)
- Recent context (what happened last session)
- Blockers (what's stuck)

Update this file as you work. The orchestrator can read it to understand your status.

---

## Cross-Agent Handoff

When you need another agent:
1. Note the need in `state/current.md` under "Handoff Needed"
2. Describe what's needed and why
3. The orchestrator will route it appropriately

---

## ADHD-Friendly Reminders

1. **One city at a time** - Focus on one scraper/city, don't context-switch
2. **Log as you go** - Update state/current.md frequently
3. **Use /end** - Don't just close the terminal, save your context
4. **Check state first** - Run `/start` to see where you left off

---

# Domain Reference

## Database Table Warning

| Table | Purpose | USE FOR SELLING? |
|-------|---------|------------------|
| `clients_scoredlead` | SCORED, SELLABLE leads (~4,600) | YES |
| `leads_permit` | RAW scraped permits (~34,000 with junk) | NEVER |

**NEVER query `leads_permit` for sales, inventory counts, or customer conversations.**

---

## Authentication Warning

**BEFORE working on ANY city scraper, CHECK `AUTH_REQUIRED.md`**

Some cities require login credentials stored in `.env`. If you work on a city without checking:
- You'll waste hours discovering it needs auth
- You might not know credentials already exist

```bash
cat AUTH_REQUIRED.md  # Check if city needs auth and if we have credentials
```

| Quick Reference | Cities |
|-----------------|--------|
| **Have credentials** | Irving (MGO), Denton (MGO), Plano (eTRAKiT) |
| **Need credentials** | Lewisville, Forney, Richardson, Highland Village, Corinth |
| **Blocked (technical)** | Euless (CAPTCHA), Garland (no portal) |

---

## Working Portals

### Accela
- Dallas, Fort Worth, Grand Prairie - `accela_fast.py`

### eTRAKiT
- Frisco, Flower Mound, Denton - `etrakit.py` (fast DOM)
- Keller, Prosper - `etrakit.py`
- The Colony - `etrakit.py` + `enrich_colony_addresses.py`
- Plano - `etrakit_auth.py` (requires login)

### EnerGov CSS
- Colleyville, McKinney, Allen, Trophy Club, Waxahachie - `citizen_self_service.py`
- Cedar Hill, DeSoto, Mesquite - `citizen_self_service.py`
- **Southlake** - Uses Browser-Use (portal ignores date filters)

### MyGov
- Westlake - `mygov_westlake.py` (address-based)
- Mansfield, Rowlett, Grapevine, Little Elm, Lancaster, Midlothian, Celina, Fate, Venus - `mygov_multi.py`
- ~~Burleson~~ - BLOCKED (no public permit search)

### SmartGov
- Sachse - `smartgov_sachse.py`

### Collin CAD (Socrata API)
- **18 Collin County cities** - `collin_cad_socrata.py`
- McKinney, Allen, Frisco, Celina, Princeton, Wylie, Prosper, Plano, Anna, Melissa, Murphy, Richardson, Sachse, Lucas, Lavon, Farmersville, Fairview, Parker

### CAD Tax Rolls
- **DCAD** (Dallas County) - `cad_delta_engine.py dcad --file <csv>`
- **TAD** (Tarrant County) - `cad_delta_engine.py tad --file <csv>`
- **Denton CAD** (Denton County) - `cad_delta_engine.py denton_cad --file <csv>`

### Other
- Arlington (Socrata API) - `dfw_big4_socrata.py`
- Carrollton (CityView) - `cityview.py`

---

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
python3 scrapers/etrakit.py keller 1000
python3 scrapers/etrakit.py prosper 1000
python3 scrapers/etrakit_auth.py plano 1000

# EnerGov CSS cities
python3 scrapers/citizen_self_service.py southlake 500
python3 scrapers/citizen_self_service.py cedar_hill 500
python3 scrapers/citizen_self_service.py desoto 500
python3 scrapers/citizen_self_service.py mesquite 500

# MyGov cities (10 cities)
python3 scrapers/mygov_multi.py mansfield 100
python3 scrapers/mygov_multi.py rowlett 100
python3 scrapers/mygov_multi.py grapevine 100
python3 scrapers/mygov_multi.py --list

# SmartGov
python3 scrapers/smartgov_sachse.py 500

# Collin CAD (18 cities via Texas Open Data)
python3 scrapers/collin_cad_socrata.py
python3 scrapers/collin_cad_socrata.py --city mckinney
python3 scrapers/collin_cad_socrata.py --limit 5000
python3 scrapers/collin_cad_socrata.py --days 30

# Other platforms
python3 scrapers/dfw_big4_socrata.py
python3 scrapers/cityview.py carrollton 500
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

---

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

---

## Browser-Use AI Scraping (Experimental)

For complex portals that resist traditional scraping, we use **Browser-Use** with DeepSeek LLM.

### Commands

```bash
# Run Browser-Use scraper
python3 -m services.browser_scraper.runner --city dallas --mode bulk

# Review failed scrapes
python3 -m services.browser_scraper.review_cli --list
python3 -m services.browser_scraper.review_cli --show dallas
python3 -m services.browser_scraper.review_cli --review
```

### When to Use Browser-Use

| Situation | Use Browser-Use? |
|-----------|------------------|
| Simple DOM scraping (Accela, eTRAKiT) | No - use fast scrapers |
| Portal with dynamic JS, date pickers | Yes |
| Portal requires complex navigation | Yes |
| Need to debug why scraper fails | Yes |
| **Southlake** (EnerGov ignores date filters) | Yes |

---

## Guidelines

- **Isolation:** Do NOT import anything from contractor-auditor
- **Database:** Uses `leads_property` table for CAD data
- **Scrapers:** Prefer `_fast.py` (DOM) over legacy LLM versions
- **Browser-Use:** Use for complex portals, review failures with CLI
- **Testing:** Run `pytest` before committing scraper changes

## DO NOT
- Import anything from contractor-auditor
- Share database connections between projects
- Mix permit logic with audit logic
