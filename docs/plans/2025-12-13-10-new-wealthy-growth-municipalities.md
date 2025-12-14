# 10 New Wealthy/Growth DFW Municipalities - Implementation Plan

> **Status:** Draft - Pending Review
> **Created:** 2025-12-13
> **Confidence:** Claude 85%

## Executive Summary

Research identified 10 new DFW municipalities prioritized by wealth and growth. Of these, **only 3 have compatible online portals** for immediate implementation. The remaining 7 either lack public portals or use unsupported platforms.

**Total Addressable Population:** ~128,000
**Easy Win Population (3 cities):** ~37,000

---

## Research Findings

### Cities with Compatible Portals (IMPLEMENT)

| City | Population | Growth | Tier | Platform | Scraper |
|------|------------|--------|------|----------|---------|
| **Highland Park** | 9,000 | 0% | A (ultra-wealth) | MyGov | `mygov_multi.py` |
| **Princeton** | 15,000 | 8% | C (high-growth) | EnerGov CSS | `citizen_self_service.py` |
| **Royse City** | 13,000 | 5% | C (high-growth) | MyGov | `mygov_multi.py` |

### Cities Needing Investigation

| City | Population | Growth | Platform | Issue |
|------|------------|--------|----------|-------|
| **Heath** | 10,000 | 3% | MyGov + OpenGov | Hybrid system, may work |
| **Lucas** | 8,000 | 3% | MGO Connect | Likely blocked (same as Irving) |

### Cities Without Online Portals (NOT FEASIBLE)

| City | Population | Growth | Reason |
|------|------------|--------|--------|
| **Anna** | 15,000 | 10% | Email-only, no search |
| **Melissa** | 12,000 | 10% | No public portal found |
| **Fairview** | 10,000 | 3% | Email-only, no search |
| **Highland Village** | 16,000 | 1% | PDF forms, no search portal |
| **Murphy** | 20,000 | 1% | Custom portal, contractor login required |

---

## Implementation Plan

### Task 1: Add Highland Park to MyGov Scraper

**Files:** `scrapers/mygov_multi.py`
**Risk:** Low - Standard MyGov platform

Highland Park is the #1 wealthiest city in DFW (median home >$1.5M). Uses MyGov for contractor portal.

**Step 1: Add config to MYGOV_CITIES**

```python
'highland_park': {'name': 'Highland Park', 'slug': 'highland_park_tx', 'pop': 9000},
```

**Step 2: Test**
```bash
cd /home/reid/testhome/permit-scraper && python3 scrapers/mygov_multi.py highland_park 10
```

**Expected:** Should return permits. Low volume city (9k pop) but high-value leads.

**Step 3: Commit**
```bash
git add scrapers/mygov_multi.py && git commit -m "feat: add Highland Park to MyGov scraper"
```

---

### Task 2: Add Princeton to EnerGov CSS Scraper

**Files:** `scrapers/citizen_self_service.py`
**Risk:** Low - Standard EnerGov CSS platform

Princeton is one of the fastest-growing cities in DFW (8% growth). Uses EnerGov Self-Service Portal.

**Step 1: Research portal URL**

Visit https://princetontx.gov/604/Permitting and find the EnerGov portal link.

Expected URL pattern: `https://energov.princetontx.gov/EnerGov_Prod/SelfService` or similar.

**Step 2: Add config to CSS_CITIES**

```python
'princeton': {
    'name': 'Princeton',
    'base_url': 'https://energov.princetontx.gov/EnerGov_Prod/SelfService',  # VERIFY URL
},
```

**Step 3: Test**
```bash
cd /home/reid/testhome/permit-scraper && python3 scrapers/citizen_self_service.py princeton 10
```

**Expected:** Should return permits. High-growth city = high permit volume.

**Step 4: Commit**
```bash
git add scrapers/citizen_self_service.py && git commit -m "feat: add Princeton to EnerGov CSS scraper"
```

---

### Task 3: Add Royse City to MyGov Scraper

**Files:** `scrapers/mygov_multi.py`
**Risk:** Low - Standard MyGov platform

Royse City explicitly uses MyGov per their website. Fast-growing Rockwall County suburb.

**Step 1: Add config to MYGOV_CITIES**

```python
'royse_city': {'name': 'Royse City', 'slug': 'royse_city_tx', 'pop': 13000},
```

**Step 2: Test**
```bash
cd /home/reid/testhome/permit-scraper && python3 scrapers/mygov_multi.py royse_city 10
```

**Expected:** Should return permits.

**Step 3: Commit**
```bash
git add scrapers/mygov_multi.py && git commit -m "feat: add Royse City to MyGov scraper"
```

---

### Task 4: Investigate Heath (MyGov/OpenGov Hybrid)

**Files:** `scrapers/mygov_multi.py`
**Risk:** Medium - May require custom handling

Heath moved to OpenGov in Sept 2025 but still has MyGov references.

**Step 1: Test standard MyGov first**

```python
'heath': {'name': 'Heath', 'slug': 'heath_tx', 'pop': 10000},
```

**Step 2: Test**
```bash
cd /home/reid/testhome/permit-scraper && python3 scrapers/mygov_multi.py heath 10
```

**Expected:** May work or may require OpenGov-specific handling.

**Step 3: If fails, investigate OpenGov API**

OpenGov may have a different API structure. Note findings for future scraper.

---

### Task 5: Investigate Lucas (MGO Connect)

**Files:** Research only
**Risk:** High - MGO Connect is blocked for other cities

Lucas uses MGO Connect, same platform as Irving/Lewisville (both blocked by anti-bot).

**Step 1: Check if MGO Connect portal is accessible**

```bash
curl -sI "https://www.lucastexas.us/permits/" | head -20
```

**Step 2: If blocked, mark as BLOCKED in JSON**

```json
{
  "city": "Lucas",
  "status": "blocked",
  "platform": "MGO Connect",
  "notes": "Same anti-bot as Irving/Lewisville"
}
```

---

### Task 6: Update Documentation

**Files:** `docs/research/dfw_municipalities.json`, `docs/research/dfw_municipalities.md`

Update with findings:
- Highland Park: working (MyGov)
- Princeton: working (EnerGov CSS)
- Royse City: working (MyGov)
- Heath: research_needed (OpenGov hybrid)
- Lucas: blocked (MGO Connect)
- Anna/Melissa/Fairview/Highland Village/Murphy: no_portal

---

## Verification Checklist

After implementation, verify each city:

```bash
cd /home/reid/testhome/permit-scraper

# Easy wins
python3 scrapers/mygov_multi.py highland_park 5
python3 scrapers/citizen_self_service.py princeton 5
python3 scrapers/mygov_multi.py royse_city 5

# Investigations
python3 scrapers/mygov_multi.py heath 5
```

All should return at least 1 permit or clearly indicate why not.

---

## Risk Summary

| City | Risk | Mitigation |
|------|------|------------|
| Highland Park | Low | Standard MyGov, wealthy city = lower volume |
| Princeton | Low | Standard EnerGov, verify URL first |
| Royse City | Low | Standard MyGov, explicitly stated on website |
| Heath | Medium | Test MyGov first, may need OpenGov research |
| Lucas | High | Likely blocked, same as Irving |

---

## Outcome

**Best Case (3 cities work):** +37,000 population coverage
- Highland Park: Ultra-wealthy leads ($1M+ homes)
- Princeton: High-growth construction volume
- Royse City: Growing Rockwall suburb

**Stretch (Heath works):** +47,000 population coverage

**Cities Not Feasible:** Anna, Melissa, Fairview, Highland Village, Murphy (no online portals)

---

## Alternative High-Value Cities

If the above cities don't yield enough leads, consider these alternatives with known compatible platforms:

| City | Pop | Platform | Notes |
|------|-----|----------|-------|
| **Weatherford** | 30k | Unknown | Parker County seat, research needed |
| **Cleburne** | 31k | Unknown | Johnson County seat, research needed |
| **Ennis** | 20k | Unknown | Ellis County, research needed |

---

## Sources

- [Highland Park Permits](https://www.hptx.org/583/Online-Permits-Inspections)
- [Princeton Permitting](https://princetontx.gov/604/Permitting)
- [Royse City Permits](https://www.roysecity.com/181/Permits)
- [Heath Permits](https://www.heathtx.com/citizen-contractor-communication-portals/)
- [Lucas Permits](https://www.lucastexas.us/permits/)
