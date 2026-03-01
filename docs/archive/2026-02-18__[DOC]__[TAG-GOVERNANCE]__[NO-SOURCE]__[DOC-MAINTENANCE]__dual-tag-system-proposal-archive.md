# Dual Tag System Proposal (Collections)

Date: 2026-02-18

## Current Locked Baseline [DECIDED]
- Claim-status tags are frozen to: `[VERIFIED]`, `[UNVERIFIED]`, `[DECIDED]`, `[OBSERVED]`, `[PROPOSED]`, `[INTERPRETIVE]`.
- Canonical naming is `[PREMISE-6]`; `[PREMISE6]` is non-canonical.
- Claim-status tags do not go in file names.
- Taxonomy-tagged file names use:
  - `YYYY-MM-DD__[ARTIFACT]__[DOMAIN]__[ENTITY-OR-NO-SOURCE]__[WORKFLOW]__short-title.md`
- This proposal is retained as historical context; implementation follows the locked policy.

## Classification [PROPOSED] (Historical)
- `hybrid`
- Reason: Collections work mixes operational memory logs (`state`/`sessions`) with research-style portal and data notes, so both policy and evidence workflows must be supported.

## Claim Status Tags [PROPOSED] (Historical)
- Required set for this workspace (fixed claim-status vocabulary):
  - `[VERIFIED]`: claim is backed by direct evidence (run output, source doc, logs).
  - `[UNVERIFIED]`: plausible claim pending validation.
  - `[DECIDED]`: explicit policy/process choice already made.
  - `[OBSERVED]`: factual outcome/status seen in this session.
  - `[PROPOSED]`: recommendation or next action awaiting approval/execution.
  - `[INTERPRETIVE]`: inference drawn from evidence, not a direct fact.
- Optional extras:
  - None proposed in this pass (keep claim-status layer stable and small).

## Taxonomy Tags [PROPOSED] (Historical)
- Controlled vocabulary by category:
  - Domain:
    - `[PERMITS]`, `[CONTRACTORS]`, `[CAD]`, `[LEAD-SCORING]`, `[TAG-POLICY]`
  - Artifact/Thread:
    - `[STATE-LOG]`, `[SESSION-LOG]`, `[RUNBOOK]`, `[RESEARCH-NOTE]`, `[PROPOSAL]`
  - Entity/Source:
    - `[ACCELA]`, `[ETRAKIT]`, `[ENERGOV-CSS]`, `[MYGOV]`, `[SOCRATA]`, `[CLIENTS-SCOREDLEAD]`, `[AUTH-REQUIRED-MD]`
  - Workflow Area:
    - `[SCRAPE]`, `[LOAD]`, `[ENRICH]`, `[SCORE]`, `[DEBUG]`, `[HANDOFF]`
  - Location/City (additional category, if approved):
    - `[CITY-DALLAS]`, `[CITY-FORT-WORTH]`, `[CITY-FRISCO]`, `[CITY-PLANO]`, `[CITY-SOUTHLAKE]`, `[CITY-FLOWER-MOUND]`

## How They Combine
- `[VERIFIED] [PERMITS] [ACCELA] [SCRAPE] [CITY-DALLAS] Dallas Accela run produced 1000 permits in \`data/raw/dallas_raw.json\`.`
- `[UNVERIFIED] [PERMITS] [ETRAKIT] [DEBUG] [CITY-FLOWER-MOUND] Flower Mound timeout appears rate-limit related; retry with trace capture pending.`
- `[OBSERVED] [CONTRACTORS] [CLIENTS-SCOREDLEAD] [STATE-LOG] [LOAD] Sales-facing lead counts were pulled from \`clients_scoredlead\`, not \`leads_permit\`.`
- `[INTERPRETIVE] [CAD] [SOCRATA] [ENRICH] [RESEARCH-NOTE] Missing parcel joins likely come from address normalization drift.`
- `[PROPOSED] [TAG-POLICY] [PROPOSAL] [HANDOFF] [SESSION-LOG] Keep dual-tag policy in proposal state until user approves an option.`

## Additional Categories Needed?
- Yes.
- Category: `Location/City`.
- Why: most Collections claims are city-scoped, and city tags make debugging, reporting, and follow-up dispatches filterable.

## Options

### Lean
Score: `78/100`
- Required claim-status tags: `[OBSERVED]`, `[PROPOSED]`, `[VERIFIED]`, `[UNVERIFIED]`
- Required taxonomy categories: `Domain`, `Workflow Area`
- Scope: touched `state/*.md`, `sessions/*.md`, and evidence-heavy docs only.
- Tradeoffs: low overhead, but weak decision/inference visibility (no required `[DECIDED]` or `[INTERPRETIVE]`).

### Balanced (Recommended)
Score: `94/100`
- Required claim-status tags: `[VERIFIED]`, `[UNVERIFIED]`, `[DECIDED]`, `[OBSERVED]`, `[PROPOSED]`, `[INTERPRETIVE]`
- Required taxonomy categories: `Domain`, `Artifact/Thread`, `Entity/Source`, `Workflow Area` (`Location/City` required only when claim is city-specific).
- Scope: all touched human-written files in `state/*.md`, `sessions/*.md`, and `docs/**/*.md` (excluding untouched archives/generated outputs).
- Tradeoffs: clear separation of claim truth state vs topical indexing, with manageable daily overhead.

### Strict
Score: `86/100`
- Required claim-status tags: all six on every non-trivial claim line.
- Required taxonomy categories: all five categories, including mandatory `Location/City`.
- Scope: every edited paragraph in `state/*.md`, `sessions/*.md`, and `docs/**/*.md`.
- Tradeoffs: maximum auditability and search precision, but highest friction and risk of tag fatigue during rapid ops notes.

## Recommendation [PROPOSED] (Historical)
- Recommend `Balanced (Recommended)` at `94/100`.
- Reason: it enforces explicit claim-state discipline while keeping taxonomy concrete and small enough for consistent use in live operations.

## User Approval Questions
1. Which option do you approve? (`A` Lean / `B` Balanced / `C` Strict)
2. Approve `hybrid` as the workspace classification? (Yes/No)
3. Should `Location/City` be part of the required taxonomy categories for city-specific claims? (Yes/No)
4. Enforcement scope: touched files only going forward (`A`) or require backlog retrofit (`B`)?
5. Keep claim-status vocabulary fixed to the six tags above unless explicitly approved later? (Yes/No)
