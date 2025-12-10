# Permit Scraper (Signal Engine)

## STARTUP PROTOCOL

**IMPORTANT: Use Gemini to read all documentation - do NOT use Claude's Read tool for startup.**

Gemini has 5x context and should handle reading/summarizing. Claude executes what Gemini advises.

On session start, run this command to get Gemini to read and summarize the entire codebase state:
```bash
cd /home/reid/testhome/permit-scraper && find . -type f \( -name "*.py" -o -name "*.md" -o -name "*.json" \) -not -path "./node_modules/*" -not -path "./.git/*" -not -name "package-lock.json" | head -50 | xargs cat 2>/dev/null | gemini -p "Read SCRAPER_STATUS.md first, then summarize this permit scraping codebase. What scrapers exist, what works, what's broken, and what should we work on next? Be concise."
```

This single command has Gemini read everything (including SCRAPER_STATUS.md) and provide a summary. Claude should NOT read files in parallel - wait for Gemini's summary.

## STATUS: ACTIVE

This repo contains permit portal scrapers for the DFW Signal Engine.
Scrapes building permits, enriches with CAD data, scores leads for contractor marketing.

## Working Portals (All Fast DOM Extraction)
- Dallas (Accela) - `accela_fast.py`
- Fort Worth (Accela) - `accela_fast.py`
- Frisco (eTRAKiT) - `etrakit_fast.py`
- Arlington (Socrata API) - `dfw_big4_socrata.py`
- Grand Prairie (Accela) - `accela_fast.py`
- Plano (eTRAKiT) - `etrakit.py`

## Architecture

```
scrapers/*.py      → {city}_raw.json     (Scraping)
scripts/load_permits.py   → data/permits.db      (Loading)
scripts/enrich_cad.py     → {city}_enriched.json (Enrichment)
scripts/score_leads.py    → {city}_leads.csv     (Scoring/Export)
```

## Isolation
- Completely separate from contractor-auditor
- No shared database
- No shared services

## DO NOT
- Import anything from contractor-auditor
- Share database connections
- Mix permit logic with audit logic
