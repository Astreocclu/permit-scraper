# Permit Scraper (Signal Engine)

## ⛔⛔⛔ DATABASE TABLE WARNING ⛔⛔⛔

| Table | Purpose | USE FOR SELLING? |
|-------|---------|------------------|
| `clients_scoredlead` | SCORED, SELLABLE leads (~4,600) | ✅ YES |
| `leads_permit` | RAW scraped permits (~34,000 with junk) | ❌ NEVER |

**NEVER query `leads_permit` for sales, inventory counts, or customer conversations.**

---

## ⛔⛔⛔ AUTHENTICATION WARNING ⛔⛔⛔

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

## MANDATORY READING BEFORE ANY DATA WORK

**`docs/DATA_ARCHITECTURE.md`** - The authoritative source of truth for:
- Which columns are EMPTY and must NOT be used
- Which table to query for which question
- The "Claude Check" verification protocol

```bash
cat docs/DATA_ARCHITECTURE.md | gemini -p "What columns are empty/unreliable? What is the Claude Check protocol?"
```

**If you skip this, you WILL waste hours building on empty fields.**

---

> **THEN: Read `LEADS_INVENTORY.md` with Gemini** - Contains running account of all leads by tier, city, and category.
> ```bash
> cat LEADS_INVENTORY.md | gemini -p "Summarize current lead inventory: totals by tier, which cities need work, what categories are worth selling"
> ```

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
- Colleyville, McKinney, Allen, Trophy Club, Waxahachie - `citizen_self_service.py`
- Cedar Hill, DeSoto, Mesquite - `citizen_self_service.py` (Mesquite NEW - Dec 2024)
- **Southlake** - Uses Browser-Use (portal ignores date filters, requires AI sorting)

### MyGov
- Westlake - `mygov_westlake.py` (address-based)
- Mansfield, Rowlett, Grapevine, Little Elm, Lancaster, Midlothian, Celina, Fate, Venus - `mygov_multi.py` (Grapevine NEW - Dec 2024)
- ~~Burleson~~ - BLOCKED (portal has no public permit search module)

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

## Browser-Use AI Scraping (Experimental)

For complex portals that resist traditional scraping, we use **Browser-Use** with DeepSeek LLM to navigate dynamically.

### How It Works

```
Browser-Use Agent → ScrapeContext → Review Queue → Claude Code Review
```

1. **Agent runs** - DeepSeek navigates the portal using natural language instructions
2. **Context captured** - Screenshots, URLs, actions, errors all saved
3. **Failures queued** - Failed scrapes go to `data/review_queue/pending/`
4. **Claude reviews** - Use CLI to see what failed and why, then fix

### Commands

```bash
# Run Browser-Use scraper (uses DeepSeek API)
python3 -m services.browser_scraper.runner --city dallas --mode bulk

# Review failed scrapes
python3 -m services.browser_scraper.review_cli --list          # See pending failures
python3 -m services.browser_scraper.review_cli --show dallas   # Detail for a city
python3 -m services.browser_scraper.review_cli --review        # Interactive review

# Screenshots saved to data/screenshots/{city}/
```

### When to Use Browser-Use

| Situation | Use Browser-Use? |
|-----------|------------------|
| Simple DOM scraping (Accela, eTRAKiT) | No - use fast scrapers |
| Portal with dynamic JS, date pickers | Yes |
| Portal requires complex navigation | Yes |
| Need to debug why scraper fails | Yes - captures full context |
| **Southlake** (EnerGov ignores date filters) | Yes - requires date sorting workaround |

### City-Specific Issues

| City | Portal | Issue | Status |
|------|--------|-------|--------|
| **Southlake** | EnerGov CSS | Portal ignores date filters, returns 20yr old permits | ✅ FIXED - BrowserUse sorts by date desc |
| **Burleson** | MyGov | No public permit search module visible | ❌ BLOCKED - portal lacks functionality |

**Burleson Note:** Despite having a MyGov portal at `public.mygov.us/burleson_tx`, it only exposes Address Lookup, Knowledge Base, Code Violations, and GIS Map - no permit search. May need to contact city or find alternate data source.

### Key Files

| File | Purpose |
|------|---------|
| `services/browser_scraper/agent.py` | Browser-Use agent wrapper |
| `services/browser_scraper/runner.py` | Scraping orchestrator |
| `services/browser_scraper/review_queue.py` | Queue for failed scrapes |
| `services/browser_scraper/review_cli.py` | CLI for reviewing failures |
| `services/browser_scraper/models.py` | ScrapeContext dataclass |

### Environment Variables

```bash
DEEPSEEK_API_KEY=your_key_here  # Required for Browser-Use
BROWSER_USE_HEADLESS=true       # Set to false to see browser
```

### Review Workflow

When a Browser-Use scrape fails:

1. Full context saved: screenshots, URLs visited, actions taken, errors
2. `python3 -m services.browser_scraper.review_cli --list` shows pending
3. `--show <city>` reveals exactly what happened
4. Fix the scraper or portal-specific logic
5. Mark as reviewed with resolution (fixed, skip, permanent_block)

This creates a feedback loop: Browser-Use gathers data → Claude Code analyzes failures → improves scraper.

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
