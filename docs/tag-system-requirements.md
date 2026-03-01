# Tag System Requirements (Collections)

Last updated: 2026-02-18

## Lock Reference [DECIDED]
- Lock ID: `TAG-TAXONOMY-V1-2026-02-18T02:00:04Z`
- Locked At (UTC): `2026-02-18T02:00:04Z`
- Source of truth: `/home/astre/command-center/TAG_TAXONOMY_POLICY_LOCKED.md`
- This workspace follows the locked policy on all new and edited lines/files in scope.

## Agent Classification
- `hybrid` (operations-first permit/data pipeline work, plus occasional research/portal analysis docs)

## Canonical Edit Order [DECIDED]
When touching tagging guidance:
1. Update `CLAUDE.md` (source file behind the `AGENTS.md` symlink).
2. Apply the same change here in `docs/tag-system-requirements.md`.
3. Reflect any reader-facing cue in `docs/README.md` (Always/Sometimes/Legacy map).
4. Capture the impact in `state/current.md` and `sessions/{today}.md`.

> Note: Other workspaces may reference `TAG_SYSTEM_REQUIREMENTS.md` in the repo root. For Collections, that pointer resolves to this file inside `docs/`.

## Scope
Applies to human-written workspace docs and memory files:
- `state/current.md`
- `sessions/*.md`
- `docs/*.md` (especially `docs/research/*.md` and `docs/portal-analysis/*.md`)

Does not apply to code, raw scraper output, generated CSV/JSON, or untouched archived files.

## Claim-Status Set [DECIDED]
- Claim-status tags are frozen and unchanged:
  - `[VERIFIED]`
  - `[UNVERIFIED]`
  - `[DECIDED]`
  - `[OBSERVED]`
  - `[PROPOSED]`
  - `[INTERPRETIVE]`
- Claim-status tags and taxonomy tags are separate systems:
  - Claim-status = truth/decision state.
  - Taxonomy = classification/context.

## Canonical Naming Decision [DECIDED]
- Use `[PREMISE-6]`.
- Do not use `[PREMISE6]` (non-canonical).

## File Name Tag Process [DECIDED]
- Taxonomy tags in file names use this exact slot format:
  - `YYYY-MM-DD__[ARTIFACT]__[DOMAIN]__[ENTITY-OR-NO-SOURCE]__[WORKFLOW]__short-title.md`
- Claim-status tags do not go in file names.
- Taxonomy tags in file names are bracketed and uppercase with numbers/hyphens as needed.

## Mandatory Claim-Status Tags and Where
- `[OBSERVED]`:
  Required for factual status updates in `state/current.md` and `sessions/*.md` (runs, failures, counts, file changes).
- `[DECIDED]`:
  Required for policy/process choices in `state/current.md`, `sessions/*.md`, and onboarding docs.
- `[PROPOSED]`:
  Required for next actions, handoffs, and recommended follow-ups in `state/current.md` and `sessions/*.md`.
- `[VERIFIED]`:
  Required in research-style docs (`docs/research/*.md`, `docs/portal-analysis/*.md`) when a claim is backed by direct run output, logs, or source material.
- `[UNVERIFIED]`:
  Required in research-style docs when a claim is plausible but not yet confirmed.
- `[INTERPRETIVE]`:
  Required when making inferences from evidence (for example "likely rate-limited", "probably selector drift").

## Tag Token Rules [DECIDED]
- Every tag token is bracketed, always.
- Taxonomy token format uses uppercase letters, numbers, and hyphens inside brackets.
- Example taxonomy tokens: `[GENETICS]`, `[PREMISE-6]`, `[CASANOVA-2024]`, `[WORKFLOW-ANALYSIS]`.

## Not Required for This Agent
- Tags are not required in Python code, tests, shell scripts, `.env`, raw permit JSON, exports, or DB rows.
- Tags are not required retroactively in archived docs unless you edit those files.
- Every entry does not need all six claim-status tags; use the tags required by the content type.

## Examples (Collections Domain)
- `[OBSERVED] Dallas Accela scrape returned 1000 records; output saved to data/raw/dallas_raw.json.`
- `[DECIDED] Use clients_scoredlead (not leads_permit) for any sales-facing counts.`
- `[PROPOSED] Handoff to orchestrator: restart MCP server before next tool-heavy session.`
- `[VERIFIED] AUTH_REQUIRED.md confirms Plano requires etrakit_auth.py with stored credentials.`
- `[UNVERIFIED] Flower Mound timeout appears to be portal-side throttling; rerun with debug capture pending.`
- `[INTERPRETIVE] Repeated eTRAKiT timeouts after login suggest anti-bot behavior instead of bad credentials.`

### Collections Filename Examples [OBSERVED]
- `2026-02-18__[STATE]__[PERMITS]__[NO-SOURCE]__[OPERATIONS]__scraper-refresh.md`
- `2026-02-18__[SESSION]__[PERMITS]__[NO-SOURCE]__[OPERATIONS]__southlake-browser-use.md`
- `2026-02-18__[DOC]__[TAG-GOVERNANCE]__[COLLECTIONS]__[DOC-MAINTENANCE]__cross-domain-review.md`

## Enforcement Checklist (Before /end)
1. `state/current.md` updates include `[OBSERVED]`, `[DECIDED]`, and `[PROPOSED]` as appropriate.
2. `sessions/{today}.md` summary lines include tags for outcomes and next actions.
3. Any new or edited research/portal docs mark claims as `[VERIFIED]` or `[UNVERIFIED]`.
4. Inferences in docs are tagged `[INTERPRETIVE]`.
5. Claim-status tags are never placed in file names.
6. Taxonomy-tagged file names use `YYYY-MM-DD__[ARTIFACT]__[DOMAIN]__[ENTITY-OR-NO-SOURCE]__[WORKFLOW]__short-title.md`.
7. No writes were made to `state/lessons.md` (deprecated pointer).
