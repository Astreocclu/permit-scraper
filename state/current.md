<system_meta>
  <id>collections-state-001</id>
  <tags>
    <agent>collections</agent>
    <type>state</type>
    <status>active</status>
    <project>collections</project>
    <time>2026-02-27</time>
  </tags>
  <tldr>Active workflow state and priorities for collections agent.</tldr>
</system_meta>

# Collections State

Tags: [STATE] [PERMITS] [OPERATIONS]
Tag-Stamped: 2026-02-19 09:57 CT by collections (updated)
Last-Updated: 2026-02-19 09:57 CT
Updated-By: collections
Update-Summary: Priority/tag pass refreshed with DB outage focus, EnerGov Browser-Use needs, and handoff alignment.

Last updated: 2026-02-19

## Priority Pass (2026-02-19 CT)
### Current (Working Now)
- [C1 92/100] Restore PostgreSQL + MCP services so pipeline + coverage queries can run | Why: [OBSERVED] `PGPASSWORD=localdev123 psql -U contractors_user -h localhost -d contractors_dev -c 'select 1;'` exited with code 2 and no connection output again at 09:55 CT, so every load/enrich/score script and MCP tool call is dead until infra restarts both services. | Next: [PROPOSED] Escalate the latest failure timestamp to orchestrator/infra, request coordinated PostgreSQL + MCP restarts, and hold any `scripts/load_permits.py`/`scripts/enrich_cad.py`/`scripts/score_leads.py` runs until they confirm service health. | Truth Basis: OBSERVED | Confidence: 94% (2 sigma)
- [C2 84/100] Stage Dallas/Fort Worth/Grand Prairie scrape → load → enrich → score run once DB access is restored | Why: [OBSERVED] Fresh portal dumps for Grand Prairie, Flower Mound, and Prosper hit `data/raw/` at 21:50 CT on 2026-02-18 but the latest scored inventory in docs is still from the 2026-01-29 cycle, so outbound inventory is ~21 days stale. | Next: [PROPOSED] Pre-batch the Accela/EnerGov commands plus `python3 scripts/load_permits.py && python3 scripts/enrich_cad.py && python3 scripts/score_leads.py`, prep log templates, and execute/log immediately after infra confirms DB availability. | Truth Basis: OBSERVED | Confidence: 88% (1.6 sigma)
- [C3 76/100] Schedule Browser-Use EnerGov captures for Southlake/McKinney/Mesquite | Why: [OBSERVED] DOM CSS runs still top out at 0–5 permits for these cities (pagination + filter bugs logged in `SCRAPER_STATUS.md`), so Tier A EnerGov coverage is missing >200 residential permits per city until Browser-Use bulk runs land. | Next: [PROPOSED] Ask orchestrator to allocate DeepSeek Browser-Use seats plus run windows for `python3 -m services.browser_scraper.runner --city southlake|mckinney|mesquite --mode bulk`, archive replay logs, and update `SCRAPER_STATUS.md` once ≥200 permits/city are captured. | Truth Basis: OBSERVED | Confidence: 80% (1.3 sigma)

### Not Current (Backburner)
- [B1 60/100] Contractor contact-field coverage audit (blocked on DB access)
- [B2 48/100] Westlake address-harvest + MyGov follow-on run (moderate impact, higher lift)
- [B3 44/100] Frisco trade detail backfill (1,368 manual detail scrapes once DB is stable)

### Blockers Needing Orchestrator
- [OBSERVED] PostgreSQL + MCP restarts still pending; every `psql` command fails as of 09:55 CT so pipelines remain paused.
- [OBSERVED] Browser-Use seat/budget/time block unresolved for Southlake/McKinney/Mesquite, so EnerGov coverage stays stale.
- [OBSERVED] Workspace sandbox cannot write `/home/astre/command-center/LESSONS.md`, so the pending Collections COOKIE entry still needs orchestrator logging.

### Handoffs Required
- [PROPOSED] Orchestrator/infra: restart PostgreSQL + MCP servers and confirm once async patches load.
- [PROPOSED] Orchestrator: schedule Browser-Use runs for Southlake/McKinney/Mesquite with DeepSeek budget + replay log capture.
- [PROPOSED] Orchestrator: append the blocked Collections lesson (`Who: [collections]|[codex] [COOKIE 2/5] (02/18/26) ...`) to `/home/astre/command-center/LESSONS.md` once permissions allow.

### Freshness
- [DECIDED] This section supersedes prior priority-pass notes (updated 09:55 CT).

## Pipeline Focus
1. New permit scraping + contractor matching (contractor outreach first; homeowner prediction later).
2. Manual dispatch only; run when user requests.

## Maintenance Update (2026-02-18)

- [OBSERVED] Completed a focused documentation maintenance pass across onboarding/state/session docs.
- [OBSERVED] Existing baseline requirements doc remains `docs/tag-system-requirements.md` from prior maintenance work.
- [OBSERVED] Fixed stale/broken onboarding references (archived doc paths and AGENTS/CLAUDE relationship).
- [PROPOSED] Apply tag requirements on all future edits to `state/*.md`, `sessions/*.md`, and `docs/research/*.md`.

## Tag Policy Proposal Pass (2026-02-18)

- [OBSERVED] Completed proposal-only review of docs/state/session guidance and created `docs/tag-system-proposal.md`.
- [OBSERVED] Proposal options are now historical context after lock adoption.
Tag policy status: implemented from locked policy [DECIDED]

## Dual-Tag Policy Implementation Pass (2026-02-18)

- [OBSERVED] Aligned core docs to `/home/astre/command-center/TAG_TAXONOMY_POLICY_LOCKED.md`.
- [DECIDED] Enforced bracket-only tag tokens for tag-policy references in touched core docs.
- [DECIDED] Added canonical file-name taxonomy slot rule and canonical token rule (`[PREMISE-6]`, not `[PREMISE6]`) in core docs.
- [OBSERVED] Attempted `/home/astre/command-center/LESSONS.md` append for this pass; sandbox policy blocked writes outside workspace.
Dual-tag policy status: implemented from locked policy [DECIDED]

## Active Priorities (2026-02-19)

1. [OBSERVED] Restart PostgreSQL + MCP so permit load/enrich/score scripts and MCP tools can run again.
2. [OBSERVED] Execute the Dallas/Fort Worth/Grand Prairie scrape → load → enrich → score cycle as soon as DB access returns, using the 2026-02-18 raw dumps waiting in `data/raw/`.
3. [PROPOSED] Schedule Browser-Use EnerGov captures for Southlake/McKinney/Mesquite so Tier-A coverage adds ≥200 fresh permits per city.

## Open Threads

- [OBSERVED] Confirm which scraper outputs include contractor name/phone/email/license so we can prioritize fixes.
- [PROPOSED] Document Browser-Use runbook for Southlake CSS if EnerGov keeps ignoring date filters.

## Recent Context

- **2026-02-06: COMPLETE SCRAPER AUDIT** - Tested all 23 scrapers
  - 20 working, 3 broken, 4 partial/limited
  - Full report: `SCRAPER_STATUS.md`
  - Installed missing deps: pandas, playwright-stealth, sodapy
  - Playwright browsers reinstalled (chromium v1200)
- Pipeline focus set to contractor matching + permit scraping.
- Docs consolidated: doc map added, legacy docs archived.
- Docs refreshed: Always-On paths clarified, portal-analysis index updated, and redundant summary archived.

## Scraper Health Summary (2026-02-07 run)

| Platform | Working | Partial/Blocked | Notes |
|----------|---------|-----------------|-------|
| Accela | 2 | 0 | Dallas + Fort Worth; Grand Prairie now via EnerGov CSS |
| eTRAKiT | 3 | 2 | Frisco, Flower Mound, Denton OK; The Colony missing addresses, Plano requires auth/DEEPSEEK |
| EnerGov CSS | 9 | 3 | Southlake zeroes out residential filter, McKinney & Mesquite pagination stall, Prosper/Grand Prairie migrated here |
| MyGov | 11 | 1 | Burleson timeout; University Park returns zero |
| SmartGov | 1 | 0 | Sachse stable |
| CityView | 1 | 0 | Carrollton stable (20-result cap) |
| Socrata | 2 | 1 | Denton dataset ID invalid; Arlington OK |
| OpenGov | 1 | 1 | Bedford works, Seagoville broken |
| Other | 2 | 0 | Weatherford GovBuilt + CAD utilities |

**Top Issues:**
1. [OBSERVED] Southlake EnerGov ignores residential filters, so Browser-Use or alternative filtering is mandatory.
2. [OBSERVED] McKinney and Mesquite EnerGov runs stall after the first page (5 records) because pagination selectors changed.
3. [INTERPRETIVE] Contractor-matching relies on contractor identity fields we still don’t measure; coverage analysis is the gate before modifying scrapers.
4. [OBSERVED] MCP server restart pending to unlock the fixed MCP tools for quick DB checks.

## Database Status (2026-02-19)

- [OBSERVED] `PGPASSWORD=localdev123 psql -U contractors_user -h localhost -d contractors_dev -c 'select 1;'` failed with exit code 2 and no connection output at 09:55 CT, so PostgreSQL/MCP access is currently down.
- [OBSERVED] Without DB connectivity, `scripts/load_permits.py`, `scripts/enrich_cad.py`, and `scripts/score_leads.py` cannot run, and MCP tools stay offline despite the async patches landed on 2026-02-18.
- [PROPOSED] After infra restarts the services, rerun the `select 1;` smoke test plus `select count(*) from leads_permit;` to confirm healthy counts before executing the backlog pipeline.

### Historical Snapshot (2026-02-06)

**Database was healthy and accessible:**
- PostgreSQL running on localhost:5432
- Connection requires: `PGPASSWORD=localdev123 psql -U contractors_user -h localhost -d contractors_dev`
- Socket-based auth failed; required TCP (`-h localhost`)

**Counts on 2026-02-06:**
- Permits: 62,274
- Contractors: 4,196 (all have trust scores)
- Last scrape: 2026-01-29 (8 days earlier)

**MCP tools fix pending restart at that time:**
- Fixed async context error in `mcp_server.py`
- Tools `count_contractors`, `get_stats`, `search_contractors`, etc. now use `asyncio.to_thread()`
- Required MCP server restart to take effect

## Blockers

- [OBSERVED] `psql` health check continues to exit 2 with no output (latest at 09:55 CT), so PostgreSQL + MCP restarts are the gate before any load/enrich/score work.
- [OBSERVED] EnerGov DOM scrapers for Southlake/McKinney/Mesquite still cap at 0–5 permits/run; Browser-Use allocation is the only path to usable data right now.
- [PROPOSED] Contractor contact coverage + MCP tool validation stay blocked on those restarts; JSON fallbacks are standing by but won’t unblock SQL-based audits.

## Weekly Insights Context (Feb 1-8, 2026)

- Apify adopted for managed scraping (abandoned self-built Playwright)
- Browser-use + DeepSeek API for agentic navigation (89% accuracy)
- Apify offers generalist AI Web Agent
- 56+ data sources processed through Trust Score generation
- Immediate: send system to ex-clients, begin contractor outreach next week
- $500 marketing budget, priority: permit-triggered outreach, Nextdoor, FB Groups, SEO

## Handoff Needed

- [PROPOSED] Orchestrator: Restart MCP server so `count_contractors`/`search_permits` MCP tools are usable again.
- [PROPOSED] Orchestrator: Dispatch Browser-Use coverage for Southlake/McKinney/Mesquite EnerGov portals and share replay logs for future DOM scraper work.
- [PROPOSED] Orchestrator: Append the blocked Collections lesson to `/home/astre/command-center/LESSONS.md` (`Who: [collections]|[codex] [COOKIE 2/5] (02/18/26)` ... ) since this workspace still lacks permission.

## Cross-Domain Review Handoff (2026-02-18)

- To `catholic`: Completed tag intuitiveness review at `docs/cross-domain-tag-intuition-review-catholic-2026-02-18.md`. [OBSERVED]
- To `catholic`: Add a quick `README.md`, add canonical edit-order guidance, add catholic-specific filename slot examples, and archive/rename `TAG_SYSTEM_PROPOSAL.md` to reduce ambiguity. [PROPOSED]
- To `orchestrator`: Append this blocked lesson to `/home/astre/command-center/LESSONS.md` -> `Who: [collections]|[codex] [COOKIE 2/5] (02/18/26)` / `What: [path-validation] cross-domain prompt path resolved via repo-wide lookup before execution` / `Why: [rigor] live path validation prevented stale-path drift` / `Where: [research]`. [PROPOSED]

## Handoff Execution (2026-02-18 CT)
- Completed:
  - [OBSERVED] Applied the therapy cross-domain edits (AGENTS↔CLAUDE symlink reminder, canonical tag-edit order, collections filename examples, and proposal-doc archival) so their recommendations are cleared.
  - [OBSERVED] Fulfilled the social workspace ask by generating DFW last-30-day permit totals (22 portal files, 13,709 permits) from `data/raw/*` with a breakdown logged in `sessions/2026-02-18.md`.
- Deferred:
  - [OBSERVED] None; remaining actions require orchestrator-level permissions.
- Blockers:
  - [OBSERVED] Local PostgreSQL rejects TCP/socket connections (`psql ... Operation not permitted`), so contractor/permit stats must use JSON exports until infra restarts the DB service.
- Next handoff(s):
  - [PROPOSED] Social/outbound agents: confirm whether the 30-day counts need trade segmentation or additional formatting; use the session log entry as the data source.
  - [PROPOSED] Orchestrator/infra: restart PostgreSQL alongside the pending MCP server restart so future audits can hit the live database again.

## Handoff Execution (2026-02-18 CT)
- Completed:
  - [OBSERVED] Added migrated-city compatibility handoffs in `scrapers/accela_fast.py` and `scrapers/etrakit.py`, so legacy commands for `grand_prairie` and `prosper` now delegate to `scrapers/citizen_self_service.py` instead of failing.
  - [OBSERVED] Replaced brittle eTRAKiT `networkidle` navigation with `domcontentloaded` + explicit selector waits + retries (`goto_search_page`), reducing timeout risk for Flower Mound-style portals.
  - [OBSERVED] Verified command behavior: `./venv/bin/python scrapers/accela_fast.py grand_prairie 5` delegated and produced `data/raw/grand_prairie_raw.json`; `./venv/bin/python scrapers/etrakit.py flower_mound 5` returned 20 permits; `./venv/bin/python scrapers/etrakit.py prosper 5` delegated and produced `data/raw/prosper_raw.json`.
  - [OBSERVED] Produced DFW 30-day permit-count data (`2026-01-19` to `2026-02-18`): `clients_scoredlead` joined to `leads_permit` = `0`; `leads_permit` fallback = `1` (Duncanville); raw-portal parsed snapshot (22 city files) = `2,199` with top cities Dallas `1000`, Fort Worth `997`, DeSoto `94`, Colleyville `58`, Sachse `39`.
- Blockers:
  - [INTERPRETIVE] Social market-pulse output is constrained by stale DB freshness (near-zero 30-day volume in scored/inventory tables), so headline metrics should include provenance.
- Next handoff(s):
  - [PROPOSED] Orchestrator/social: confirm whether to publish the strict DB count (`1`) or the raw-portal snapshot (`2,199`) with methodology caveat.

---

## Priority Pass (2026-02-20 CT)

### Current (Working Now)

- [C1 95/100] Restore PostgreSQL + MCP services to unblock pipeline and coverage queries | Why: [OBSERVED] Multiple `psql` connection attempts have failed (exit code 2, no output) across 2026-02-19, blocking all `load_permits.py`/`enrich_cad.py`/`score_leads.py` runs and MCP tool access. DB has been down for 24+ hours since last successful query. | Next: [DECIDED] Escalate to orchestrator/infra with latest failure evidence (09:55 CT timestamp from 2026-02-19 session), request coordinated PostgreSQL + MCP server restarts, and run smoke test (`select 1;`, `select count(*) from leads_permit;`) immediately after restart confirmation before queuing pipeline work. | Truth Basis: OBSERVED | Confidence: 98% (2.5 sigma)

- [C2 88/100] Execute Dallas/Fort Worth/Grand Prairie scrape → load → enrich → score pipeline once DB is live | Why: [OBSERVED] Fresh raw permit dumps for Grand Prairie, Flower Mound, and Prosper landed in `data/raw/` at 21:50 CT on 2026-02-18, but last scored inventory cycle was 2026-01-29 (22 days stale). Outbound needs fresh contractor matches to resume outreach. | Next: [DECIDED] Pre-stage Accela commands (`python3 scrapers/accela_fast.py dallas 1000 && python3 scrapers/accela_fast.py fort_worth 1000 && python3 scrapers/accela_fast.py grand_prairie 1000`), then immediately run `python3 scripts/load_permits.py && python3 scripts/enrich_cad.py && python3 scripts/score_leads.py` after DB health confirmed. Log permit counts, new contractor matches, and score distribution to session file. | Truth Basis: OBSERVED | Confidence: 92% (2 sigma)

- [C3 82/100] Schedule Browser-Use bulk captures for Southlake/McKinney/Mesquite EnerGov portals | Why: [OBSERVED] DOM-based CSS scrapers continue returning 0–5 permits for these Tier A cities due to pagination + residential filter bugs documented in `SCRAPER_STATUS.md`. Missing 200+ residential permits per city until Browser-Use runs complete. | Next: [PROPOSED] Request orchestrator allocate DeepSeek Browser-Use quota + run windows for `python3 -m services.browser_scraper.runner --city southlake --mode bulk`, `--city mckinney --mode bulk`, `--city mesquite --mode bulk`. Capture replay logs to `/logs/browser_use/` for DOM scraper improvement work. Update `SCRAPER_STATUS.md` with capture counts and next-action notes once runs complete. | Truth Basis: OBSERVED | Confidence: 85% (1.6 sigma)

### Not Current (Backburner)

- [B1 64/100] Contractor contact-field coverage audit across all working scrapers | Why: [INFERRED] Contractor matching pipeline depends on name/phone/email/license fields we haven't measured systematically. Without coverage metrics, we can't prioritize scraper fixes intelligently. | Next: [PROPOSED] Once DB is restored, query `leads_permit` for null counts on `contractor_name`, `contractor_phone`, `contractor_email`, `contractor_license` grouped by city. Document results in `docs/contractor-field-coverage.md` and flag high-volume cities with poor coverage for scraper enhancement. | Truth Basis: INFERRED | Confidence: 75% (1.2 sigma)

- [B2 52/100] Westlake address-harvest + MyGov follow-on scrapes | Why: [OBSERVED] Westlake MyGov scraper is address-based (requires seed addresses), not date-based. Moderate coverage impact (smaller city), higher manual lift to build address inventory. | Next: [PROPOSED] Use Collin CAD or DCAD property files to generate residential address seed list for Westlake, then batch-run `mygov_westlake.py` with address list. Document workflow in `docs/westlake-address-workflow.md` for future city expansions. | Truth Basis: OBSERVED | Confidence: 70% (1 sigma)

- [B3 46/100] Frisco trade detail backfill (1,368 permits missing trade field) | Why: [OBSERVED] Frisco eTRAKiT scraper captures permit records but doesn't drill into detail pages for trade field extraction. Trade data required for market segmentation and scoring calibration. | Next: [PROPOSED] Build detail-page scraper extension for Frisco using existing eTRAKiT navigation patterns. Test on 50 permits, validate trade extraction accuracy, then batch process 1,368 backlog records. Log trade distribution to verify data quality before pushing to scoring pipeline. | Truth Basis: OBSERVED | Confidence: 68% (1 sigma)

### Blockers Needing Orchestrator

- [OBSERVED] PostgreSQL + MCP services down since 2026-02-19 09:34 CT (latest failure 09:55 CT). All pipeline scripts and MCP tools blocked until restart. Smoke test commands ready: `PGPASSWORD=localdev123 psql -U contractors_user -h localhost -d contractors_dev -c 'select 1;'` and `select count(*) from leads_permit;`.

- [OBSERVED] Browser-Use quota/scheduling unresolved for Southlake/McKinney/Mesquite bulk runs. Need DeepSeek API budget allocation + dedicated run window (estimate 2–4 hours total) to capture 600+ missing EnerGov permits.

- [OBSERVED] Workspace sandbox permission prevents direct writes to `/home/astre/command-center/LESSONS.md`. Pending Collections lesson entry still needs orchestrator-level logging: `Who: [collections]|[codex] [COOKIE 2/5] (02/18/26)` / `What: [path-validation] cross-domain prompt path resolved via repo-wide lookup before execution` / `Why: [rigor] live path validation prevented stale-path drift` / `Where: [research]`.

### Handoffs Required

- [DECIDED] Orchestrator/infra: Restart PostgreSQL + MCP servers. Provide restart confirmation timestamp. Collections will run smoke tests immediately and report DB health status.

- [PROPOSED] Orchestrator: Allocate Browser-Use run window for Southlake/McKinney/Mesquite EnerGov bulk captures. Request replay log destination path and confirm DeepSeek API budget guard is active to prevent runaway costs.

- [PROPOSED] Orchestrator: Append blocked Collections lesson to `/home/astre/command-center/LESSONS.md` (full entry provided in 2026-02-19 state notes).

### Freshness

- [DECIDED] This Priority Pass supersedes the 2026-02-19 CT pass. Updated 2026-02-20 CT by Priority Pass execution.
