# Permit Scraper Implementation Plan

**Status:** In Progress (Gemini review paused due to quota)
**Last Updated:** 2025-12-10
**Claude Confidence:** 65%
**Gemini Confidence (Round 1):** 40% → improvements made, awaiting Round 2 review

---

## Task Overview

Address all three permit scraper priorities:
1. Research unknown portals for Garland, Carrollton, Flower Mound
2. Solve MGO Connect anti-automation blocking (Irving, Denton, Lewisville)
3. Fix MyGov broken URLs (Rowlett, Grapevine)

---

## PHASE 0: TECHNICAL VERIFICATION (Before Any Code)

**Goal:** Confirm actual portal status via manual browser testing

**Steps:**
1. Open Grapevine permit URL in browser - check if:
   - Redirects to new vendor
   - Requires .exe download (noted in SCRAPER_STATUS.md)
   - Shows different portal type
2. Open Rowlett permit URL - same checks
3. Open Irving/Denton/Lewisville MGO URLs - observe:
   - Is Cloudflare challenge present?
   - Can a human navigate it?
   - Note exact error/block behavior
4. Search Garland permit portal - document what exists
5. Check existing `flower_mound_raw.json` for API endpoint clues
6. Verify Carrollton uses CityView as noted in status

**Output:** Updated assessment document with actual findings

---

## PHASE 1: FIX MYGOV (Rowlett, Grapevine) - Based on Verification

**Scenario A: URLs just changed**
- Update URL constants in `scrapers/mygov.py`
- Test and verify

**Scenario B: Migrated to different vendor**
- Identify new vendor
- If existing scraper type (Accela, eTRAKiT), add city config
- If new vendor, create scraper template

**Scenario C: Requires .exe/desktop client**
- Mark city as "Manual Only" in SCRAPER_STATUS.md
- Document manual export process
- Move on (no code fix possible)

---

## PHASE 2: MGO CONNECT STEALTH UPGRADE (Irving, Denton, Lewisville)

**Step 2a: Playwright Stealth Integration**
```bash
pip install playwright-stealth
```
- Modify `mgo_connect.py` to use stealth plugin
- Test in `headless=False` mode first (sometimes bypasses basic detection)

**Step 2b: If stealth fails, diagnose blocking type**
- If IP-based: Consider residential proxy
- If fingerprint-based: Try `undetected-chromedriver` as alternative
- If CAPTCHA/Turnstile: Document as "Manual Only"

**Step 2c: Fallback - Manual Export Documentation**
- If technical solutions fail, document manual CSV export process
- Create `scrapers/mgo_manual.md` with step-by-step instructions

---

## PHASE 3: RESEARCH UNKNOWN PORTALS

**Garland (240k pop - high priority):**
- Search "City of Garland building permit portal"
- Search "City of Garland EnerGov" and "Garland TRAKiT"
- May be manual/email only - document if so

**Carrollton:**
- Verify CityView claim from SCRAPER_STATUS.md
- If confirmed, research CityView API/scraping approach
- Check if CityView has standardized endpoints

**Flower Mound:**
- First check `flower_mound_raw.json` for existing data/endpoints
- Research current portal if file unhelpful

---

## Files to Modify

- `SCRAPER_STATUS.md` (update with findings)
- `scrapers/mgo_connect.py` (add stealth)
- Possibly new city configs for existing scrapers

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Stealth still blocked | Documented manual fallback |
| Cities have no public portal | Mark as Manual/Email |
| CityView requires complex auth | Research API first |
| Grapevine requires .exe client | Verify first, mark Manual if true |

---

## Execution Order

1. **Phase 0** - Verify (research before coding)
2. **Phase 1** - MyGov fix (likely quickest)
3. **Phase 2** - MGO stealth (highest value if successful)
4. **Phase 3** - Research unknowns (can run parallel with Phase 2)

---

## Gemini Feedback from Round 1

**Key concerns addressed in this revision:**
- Added Phase 0 verification before any coding
- Added playwright-stealth approach before jumping to expensive proxies
- Will check existing data files (`flower_mound_raw.json`) for clues
- Acknowledged Grapevine `.exe` client risk
- Added CityView vendor identification for Carrollton
- Reordered phases: Verify first, then implement

**Still needs Gemini Round 2 review when quota resets**

---

## Resume Command

When Gemini quota resets, continue planning with:
```bash
cat PLAN_IN_PROGRESS.md | gemini -p "Review this plan. Rate confidence 0-100%. What concerns remain?"
```
