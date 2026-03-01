# /begin

1. `TZ="America/Chicago" date +%Y-%m-%d` → TODAY, `+%H:%M` → TIME
2. Skim `state/local-index.md` — workspace file map (unlocks cross-workspace searches)
3. Read `state/current.md`
4. Read `state/carry-forward.md`
5. Read `state/handoffs.md` — include pending items in briefing
6. If `sessions/{TODAY}.md` missing → create: `# Session: {TODAY}\n## Started: {TIME} CT`

## Critical Reminders

- Every new or modified `.md` file MUST start with `<system_meta>` XML block at line 1. Use `[TAG]` inline content tags. Files without metadata are invisible to the index. See CLAUDE.md XML Metadata section.

## My Place

Upstream: City permit portals, CAD APIs
My Job: Scrape permits, enrich with property data, score leads
Downstream: Database → Auditor, Outbound
I Own: leads_permit, leads_property, clients_scoredlead tables

7. Brief: date, active scraping jobs, carry-forward, pending handoffs, "What to collect?"
