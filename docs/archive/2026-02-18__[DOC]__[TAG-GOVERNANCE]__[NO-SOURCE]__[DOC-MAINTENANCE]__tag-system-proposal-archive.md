# Tag System Proposal (Collections)

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
- Reason: this workspace has operations-first state/session logging plus recurring research and portal-analysis documentation, so one single-mode policy is too narrow.

## Options

### Lean
Score: `74/100`

Required tags:
- `[OBSERVED]`
- `[PROPOSED]`
- `[VERIFIED]`

Where they apply:
- `state/current.md` and `sessions/*.md`: `[OBSERVED]` for outcomes, `[PROPOSED]` for next actions.
- `docs/research/*.md` and `docs/portal-analysis/*.md`: `[VERIFIED]` for confirmed claims.

Tradeoffs:
- Lowest friction and fastest compliance.
- Weak separation between decisions vs facts (no required `[DECIDED]`).
- Higher ambiguity for unconfirmed claims and interpretation.

### Balanced (Recommended)
Score: `92/100`

Required tags:
- `[OBSERVED]`
- `[DECIDED]`
- `[PROPOSED]`
- `[VERIFIED]`
- `[UNVERIFIED]`
- `[INTERPRETIVE]`

Where they apply:
- `state/current.md` and `sessions/*.md`: `[OBSERVED]`, `[DECIDED]`, `[PROPOSED]`.
- `docs/research/*.md` and `docs/portal-analysis/*.md`: `[VERIFIED]`, `[UNVERIFIED]`, `[INTERPRETIVE]`.
- Policy/onboarding docs when changed: `[DECIDED]` for finalized rules.

Tradeoffs:
- Strong clarity between facts, choices, next actions, and inference.
- Moderate overhead that is practical for daily use.
- Good auditability without slowing active scraper operations.

### Strict
Score: `84/100`

Required tags:
- `[OBSERVED]`
- `[DECIDED]`
- `[PROPOSED]`
- `[VERIFIED]`
- `[UNVERIFIED]`
- `[INTERPRETIVE]`
- `[SOURCE]`
- `[OWNER]`
- `[DUE]`
- `[CONFIDENCE]`

Where they apply:
- All edited docs and memory notes: `state/*.md`, `sessions/*.md`, `docs/**/*.md`.
- Every non-trivial claim/action line must include at least one operational tag plus traceability tags where applicable.

Tradeoffs:
- Maximum traceability and handoff precision.
- Highest writing overhead and higher risk of tag fatigue.
- Slower for rapid incident/debug notes.

## Recommendation [PROPOSED] (Historical)
- Choose `Balanced (Recommended)` (`92/100`).
- Rationale: it gives clear claim typing and decision traceability with manageable overhead, and it fits the current collections workflow without forcing broad retroactive cleanup.

## User Approval Questions
1. Approve `hybrid` as the workspace classification? (Yes/No)
2. Which option do you approve? (A = Lean, B = Balanced, C = Strict)
3. Should enforcement apply only to files touched going forward? (A = Yes, touched-only; B = No, require backlog retrofit)
4. Should `/end` fail hard when required tags are missing in edited state/session/doc files? (Yes/No)
5. Should policy/onboarding docs require `[DECIDED]` whenever a rule is finalized? (Yes/No)
