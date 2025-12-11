# Permit Scraper Session Notes

---

## Session: 2025-12-11 - Lead Scoring & Pre-Filter Pipeline Analysis

### Context
- User wanted to score unscored enriched permit records
- Initial DeepSeek API key was expired, user topped up credits
- After scoring, discovered 75% of permits were being discarded AFTER enrichment (wasted effort)

### Work Completed

1. **Ran lead scoring on enriched permits**
   - Scored 1,163 permits via DeepSeek AI
   - Results: 107 Tier A, 103 Tier B, 953 Tier C
   - Saved to `clients_scoredlead` table
   - Exported to `exports/` directory by trade_group/category/tier

2. **Fixed FK constraint bug in `scripts/score_leads.py`**
   - Line 549-616: `save_scored_leads()` function
   - Issue: `cad_property_id` was set to address even if property didn't exist in `leads_property`
   - Fix: Added lookup to check if property exists first, set NULL if not found
   - Added per-record commits with rollback on failure

3. **Analyzed pipeline inefficiency**
   - 75% of permits discarded by pre-filter in scoring step
   - Discard reasons: no data (50%), too old >90 days (36%), junk projects (10%), production builders (4%)
   - Problem: Enrichment happens BEFORE filtering, wasting CAD API calls

4. **Investigated "would_score" permits (1,087)**
   - Found filter gaps: "ashton dallas" not in production builder list, "sewer line repair" not caught by "sewer repair"
   - Fort Worth description field is chaotic - no consistent pattern for contractor names

5. **Started Gemini planning for pre-filter solution** (incomplete)
   - Proposed: Add DeepSeek classification BEFORE enrichment
   - Architecture: New `permit_classifications` sidecar table (avoids Django schema issues)
   - Gemini got stuck in tool-calling loop, planning incomplete

### Current State

**Database counts:**
| Table | Count |
|-------|-------|
| leads_permit | 7,598 |
| leads_property | 7,705 |
| clients_scoredlead | 3,127 |
| Enriched (success) | 6,186 |
| Enriched (failed) | 1,516 |
| Unscored but enriched | 2,619 |

**Scored leads by tier:**
- Tier A: 209
- Tier B: 336
- Tier C: 2,582

**Top cities:** Arlington (3,274), Dallas (2,257), Fort Worth (751)

### Next Steps

1. **PRIORITY: Implement pre-filter classification**
   - Create `scripts/classify_leads.py`
   - Add `permit_classifications` sidecar table
   - Call DeepSeek to classify permits BEFORE enrichment
   - Modify `enrich_cad.py` to skip discarded permits

2. **Fix filter gaps in scoring**
   - Add "ashton dallas" to production builders list
   - Add "sewer line" to junk projects
   - Consider: Should classification replace regex filtering entirely?

3. **Re-run scoring** on the 1,087 "would_score" permits that slipped through

### Notes

**DeepSeek API:**
- Key in `.env`: `DEEPSEEK_API_KEY`
- Same key used in contractor-auditor project
- Cost: ~$0.14/1M input tokens (very cheap)

**Pre-filter prompt design (from Gemini planning):**
- KEEP: Pool, patio, addition, remodel, kitchen, bath, roof replacement, fence, deck, pergola, ADU
- DISCARD: Production builders (DR Horton, Lennar, M/I Homes, etc.), sewer, water heater, gas line, demo, fire sprinkler, electrical panel, shed, irrigation, Habitat for Humanity, City of, ISD, church

**Architecture decision:** Use sidecar table `permit_classifications` instead of modifying `leads_permit` to avoid breaking Django ORM in contractor-auditor.

**Data quality issue:** Fort Worth descriptions are a dumping ground - contractor names, addresses, person names, project descriptions all mixed in. Can't reliably parse.

### Key Files

- `scripts/score_leads.py` - Lead scoring with DeepSeek (modified this session)
- `scripts/enrich_cad.py` - CAD enrichment (needs modification for pre-filter)
- `scripts/load_permits.py` - Permit loading
- `.env` - Contains DEEPSEEK_API_KEY, DATABASE_URL
- `exports/` - CSV exports by trade_group/category/tier
