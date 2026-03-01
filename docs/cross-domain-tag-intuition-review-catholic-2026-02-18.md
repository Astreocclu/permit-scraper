# Cross-Domain Tag Intuition Review

- Target agent: `catholic`
- Target workspace: `/home/astre/command-center/src/christian-alpha/catholic`
- Reviewer workspace: `/home/astre/command-center/src/greenlit/collections`
- Review date: `2026-02-18`

## Intuitiveness Score

`84/100`

Rationale (non-domain reader view):
- Locked tag policy rules are explicit and internally consistent across the three tag-policy docs. [OBSERVED]
- Onboarding and policy entry points are incomplete (`AGENTS.md`, `README.md`, and `docs/README.md` missing), which increases first-read friction. [OBSERVED]

## Top 5 Confusion Points

1. Required core docs list is only partially present, so a new reader has no lightweight workspace map before opening the long `CLAUDE.md`. [OBSERVED]
2. `TAG_SYSTEM_PROPOSAL.md` is still present after lock adoption; despite notes that it is superseded, the name can imply active decision space for first-time readers. [INTERPRETIVE]
3. Claim-status requirements call for tagging factual/assertive lines in onboarding docs, but `CLAUDE.md` is largely untagged; that creates a model-to-practice mismatch. [OBSERVED]
4. Taxonomy vocabulary is listed, but there are no catholic-specific filename examples using slot tokens, so filename composition still feels abstract. [INTERPRETIVE]
5. The policy is spread across `CLAUDE.md`, `TAG_SYSTEM_REQUIREMENTS.md`, and `DUAL_TAG_SYSTEM_PROPOSAL.md`; there is no single "edit here first" pointer for maintenance changes. [INTERPRETIVE]

## Top 5 Intuitive Strengths

1. Frozen claim-status set is explicit and stable: `[VERIFIED]`, `[UNVERIFIED]`, `[DECIDED]`, `[OBSERVED]`, `[PROPOSED]`, `[INTERPRETIVE]`. [OBSERVED]
2. Canonical token guidance is clear and repeated: `[PREMISE-6]` canonical, `[PREMISE6]` disallowed. [OBSERVED]
3. Bracket-only token convention is consistent in all tag-policy files. [OBSERVED]
4. Claim-status and taxonomy systems are clearly separated conceptually and operationally. [OBSERVED]
5. Domain examples tie tag governance to actual catholic screening content, which helps transfer from policy to usage. [INTERPRETIVE]

## Compliance Checks

- Bracket-only compliance: `pass`
- Filename slot process clarity:
  `YYYY-MM-DD__[ARTIFACT]__[DOMAIN]__[ENTITY-OR-NO-SOURCE]__[WORKFLOW]__short-title.md` -> `pass`

## 5 Plain -> Tagged Claim Mappings

1. Plain: `Layer 0 excludes direct euthanasia exposure.`
   Tagged: `Layer 0 excludes direct euthanasia exposure [OBSERVED] [SCREENING-LAYERS] [LAYER-0] [NO-SOURCE] [ANALYSIS]`

2. Plain: `Use [PREMISE-6] and never [PREMISE6].`
   Tagged: `Use [PREMISE-6] and never [PREMISE6] [DECIDED] [TAG-GOVERNANCE] [PREMISE-6] [INTERNAL-WORKSPACE] [VERIFICATION]`

3. Plain: `Tag-policy updates should be made in the canonical requirements file first.`
   Tagged: `Tag-policy updates should be made in the canonical requirements file first [PROPOSED] [TAG-GOVERNANCE] [CLAUDE-MD] [INTERNAL-WORKSPACE] [DOC-MAINTENANCE]`

4. Plain: `Some catholic source mappings still need citation validation.`
   Tagged: `Some catholic source mappings still need citation validation [UNVERIFIED] [MORAL-THEOLOGY] [LAYER-3] [EXTERNAL-REFERENCE] [VERIFICATION]`

5. Plain: `The current docs prioritize policy rigor over onboarding speed.`
   Tagged: `The current docs prioritize policy rigor over onboarding speed [INTERPRETIVE] [TAG-GOVERNANCE] [DUAL-TAG-PROPOSAL] [NO-SOURCE] [ANALYSIS]`

## Final Recommendation

`accept-with-edits`

Suggested edits:
1. Add `README.md` with a 60-second map and "read these 3 files first." [PROPOSED]
2. Add a one-paragraph canonical-maintenance pointer in `CLAUDE.md` ("edit order: requirements -> onboarding -> state/session"). [PROPOSED]
3. Add 2-3 catholic-specific filename slot examples in `TAG_SYSTEM_REQUIREMENTS.md`. [PROPOSED]
4. Rename or archive `TAG_SYSTEM_PROPOSAL.md` to reduce false "still open" signals. [PROPOSED]
