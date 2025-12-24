# Dual-Source Scraping Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Ensure all Collin County cities with dual data sources (city portal + Collin CAD) are scraped from BOTH sources to maximize permit coverage.

**Architecture:** Create a unified scraping script that runs both the city-specific scraper (eTRAKiT, EnerGov, etc.) AND the Collin CAD Socrata scraper for each applicable city, then deduplicates by permit_id during load.

**Tech Stack:** Python, Playwright (city scrapers), Requests (Collin CAD API), PostgreSQL

---

## Current State Analysis

### Dual-Source Cities (Collin County)

| City | City Portal Scraper | Collin CAD | Status |
|------|---------------------|------------|--------|
| Frisco | `etrakit.py` | `collin_cad_socrata.py` | Both exist |
| Plano | `etrakit_auth.py` (login required) | `collin_cad_socrata.py` | CAD stale |
| Allen | `citizen_self_service.py` | `collin_cad_socrata.py` | Both exist |
| McKinney | `citizen_self_service.py` | `collin_cad_socrata.py` | Both exist |
| Prosper | `etrakit.py` | `collin_cad_socrata.py` | Both exist |
| Celina | MyGov (mygov_multi.py) | `collin_cad_socrata.py` | Both exist |
| Princeton | None | `collin_cad_socrata.py` | CAD only |
| Wylie | None | `collin_cad_socrata.py` | CAD only |
| Anna | None | `collin_cad_socrata.py` | CAD only |
| Melissa | None | `collin_cad_socrata.py` | CAD only |
| Murphy | None | `collin_cad_socrata.py` | CAD only |

### Key Issues Found

1. **Plano**: Only 50 permits from eTRAKiT (requires login), 100 from CAD (stale)
2. **Frisco**: Only 200 from eTRAKiT, 285 from CAD - should be 1000+
3. **Collin CAD data lags** for Richardson (83 days) and Sachse (73 days)
4. **No deduplication** when loading from multiple sources

---

## Task 1: Create Dual-Source Scraping Script

**Files:**
- Create: `scripts/scrape_dual_source.py`

**Step 1: Write the script skeleton**

```python
#!/usr/bin/env python3
"""
Dual-Source Scraping Script

Runs both city portal scraper AND Collin CAD scraper for cities with dual sources.
Ensures maximum permit coverage by combining both data sources.

Usage:
    python scripts/scrape_dual_source.py frisco 1000
    python scripts/scrape_dual_source.py --all 500
    python scripts/scrape_dual_source.py --list
"""

import argparse
import subprocess
import sys
from pathlib import Path

SCRAPERS_DIR = Path(__file__).parent.parent / "scrapers"

# Cities with dual sources: city portal + Collin CAD
DUAL_SOURCE_CITIES = {
    'frisco': {
        'city_scraper': 'etrakit.py',
        'city_args': ['frisco'],
        'cad_city': 'frisco',
    },
    'plano': {
        'city_scraper': 'etrakit_auth.py',
        'city_args': ['plano'],
        'cad_city': 'plano',
    },
    'allen': {
        'city_scraper': 'citizen_self_service.py',
        'city_args': ['allen'],
        'cad_city': 'allen',
    },
    'mckinney': {
        'city_scraper': 'citizen_self_service.py',
        'city_args': ['mckinney'],
        'cad_city': 'mckinney',
    },
    'prosper': {
        'city_scraper': 'etrakit.py',
        'city_args': ['prosper'],
        'cad_city': 'prosper',
    },
    'celina': {
        'city_scraper': 'mygov_multi.py',
        'city_args': ['celina'],
        'cad_city': 'celina',
    },
}

# Cities with Collin CAD only (no city portal scraper)
CAD_ONLY_CITIES = [
    'princeton', 'wylie', 'anna', 'melissa', 'murphy',
    'lucas', 'lavon', 'farmersville', 'fairview', 'parker',
    'richardson', 'sachse',
]


def run_city_scraper(city: str, limit: int) -> bool:
    """Run the city-specific portal scraper."""
    config = DUAL_SOURCE_CITIES.get(city)
    if not config:
        print(f"  [SKIP] No city portal scraper for {city}")
        return False

    scraper = SCRAPERS_DIR / config['city_scraper']
    args = ['python3', str(scraper)] + config['city_args'] + [str(limit)]

    print(f"  [CITY] Running {config['city_scraper']} {city} {limit}...")
    result = subprocess.run(args, capture_output=False)
    return result.returncode == 0


def run_cad_scraper(city: str, limit: int, days: int = 90) -> bool:
    """Run the Collin CAD Socrata scraper."""
    scraper = SCRAPERS_DIR / 'collin_cad_socrata.py'
    args = ['python3', str(scraper), '--city', city, '--limit', str(limit), '--days', str(days)]

    print(f"  [CAD] Running collin_cad_socrata.py --city {city} --limit {limit} --days {days}...")
    result = subprocess.run(args, capture_output=False)
    return result.returncode == 0


def scrape_city(city: str, limit: int):
    """Scrape a city from all available sources."""
    print(f"\n{'='*60}")
    print(f"SCRAPING: {city.upper()}")
    print(f"{'='*60}")

    city_lower = city.lower()

    # Run city portal scraper if available
    if city_lower in DUAL_SOURCE_CITIES:
        run_city_scraper(city_lower, limit)

    # Run Collin CAD scraper
    cad_city = DUAL_SOURCE_CITIES.get(city_lower, {}).get('cad_city', city_lower)
    run_cad_scraper(cad_city, limit, days=90)

    print(f"  [DONE] {city} complete")


def main():
    parser = argparse.ArgumentParser(description='Dual-source scraping for Collin County cities')
    parser.add_argument('city', nargs='?', help='City to scrape')
    parser.add_argument('limit', nargs='?', type=int, default=500, help='Permit limit per source')
    parser.add_argument('--all', action='store_true', help='Scrape all dual-source cities')
    parser.add_argument('--list', action='store_true', help='List available cities')
    parser.add_argument('--cad-only', action='store_true', help='Also scrape CAD-only cities')
    args = parser.parse_args()

    if args.list:
        print("Dual-source cities (city portal + CAD):")
        for city in sorted(DUAL_SOURCE_CITIES.keys()):
            print(f"  {city}")
        print("\nCAD-only cities:")
        for city in sorted(CAD_ONLY_CITIES):
            print(f"  {city}")
        return

    if args.all:
        for city in DUAL_SOURCE_CITIES:
            scrape_city(city, args.limit)
        if args.cad_only:
            for city in CAD_ONLY_CITIES:
                scrape_city(city, args.limit)
    elif args.city:
        scrape_city(args.city, args.limit)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
```

**Step 2: Save the file and test --list**

Run: `python3 scripts/scrape_dual_source.py --list`

Expected output:
```
Dual-source cities (city portal + CAD):
  allen
  celina
  frisco
  mckinney
  plano
  prosper

CAD-only cities:
  anna
  ...
```

**Step 3: Commit**

```bash
git add scripts/scrape_dual_source.py
git commit -m "feat: add dual-source scraping script for Collin County cities"
```

---

## Task 2: Add Allen and McKinney to EnerGov CSS Scraper

**Files:**
- Modify: `scrapers/citizen_self_service.py`

**Step 1: Check if Allen/McKinney are already configured**

Run: `grep -E "allen|mckinney" scrapers/citizen_self_service.py`

If not present, add them to the CITIES dict:

```python
'allen': {
    'name': 'Allen',
    'url': 'https://energovweb.cityofallen.org/EnerGov_Prod/SelfService',
    'state': 'TX',
},
'mckinney': {
    'name': 'McKinney',
    'url': 'https://mckinney.energovweb.com/EnerGov_Prod/SelfService',
    'state': 'TX',
},
```

**Step 2: Test the scraper**

Run: `python3 scrapers/citizen_self_service.py allen 50`

Expected: JSON output in `data/raw/allen_raw.json`

**Step 3: Commit**

```bash
git add scrapers/citizen_self_service.py
git commit -m "feat: add Allen and McKinney to EnerGov CSS scraper"
```

---

## Task 3: Update load_permits.py for Deduplication

**Files:**
- Modify: `scripts/load_permits.py`

**Step 1: Check current dedup logic**

Run: `grep -A 10 "dedup\|duplicate\|unique" scripts/load_permits.py`

**Step 2: Add deduplication by permit_id + city**

The loader should skip permits that already exist with the same `permit_id` and `city` combination. Update the insert logic:

```python
# Before inserting, check if permit exists
existing = session.query(Permit).filter_by(
    permit_id=permit_data['permit_id'],
    city=permit_data['city']
).first()

if existing:
    # Update if CAD has richer data (owner_name, builder, etc.)
    if permit_data.get('owner_name') and not existing.owner_name:
        existing.owner_name = permit_data['owner_name']
    # ... update other fields
    stats['updated'] += 1
else:
    session.add(Permit(**permit_data))
    stats['inserted'] += 1
```

**Step 3: Commit**

```bash
git add scripts/load_permits.py
git commit -m "feat: add deduplication logic for dual-source permits"
```

---

## Task 4: Run Full Dual-Source Scrape for Priority Cities

**Step 1: Scrape Frisco from both sources**

Run: `python3 scripts/scrape_dual_source.py frisco 1000`

Expected:
- `data/raw/frisco_raw.json` (city portal)
- `data/raw/collin_cad_frisco_raw.json` (CAD)

**Step 2: Scrape Plano from both sources**

Run: `python3 scripts/scrape_dual_source.py plano 1000`

Note: Plano requires login, so city portal may fail. CAD should still work.

**Step 3: Scrape all dual-source cities**

Run: `python3 scripts/scrape_dual_source.py --all 500`

**Step 4: Load all raw data**

Run: `python3 scripts/load_permits.py`

---

## Task 5: Verify Database Freshness

**Step 1: Check permit counts by city**

```sql
SELECT city, COUNT(*) as permits, MAX(issued_date) as latest
FROM leads_permit
WHERE city IN ('frisco', 'plano', 'allen', 'mckinney', 'prosper')
GROUP BY city
ORDER BY permits DESC;
```

**Step 2: Compare to expected counts**

| City | Expected (city + CAD) | Actual |
|------|----------------------|--------|
| Frisco | 500+ | ? |
| Plano | 200+ | ? |
| Allen | 300+ | ? |
| McKinney | 400+ | ? |
| Prosper | 200+ | ? |

---

## Task 6: Document Dual-Source Strategy in CLAUDE.md

**Files:**
- Modify: `CLAUDE.md`

**Step 1: Add dual-source section**

Add after the "Collin CAD" section:

```markdown
## Dual-Source Strategy

Cities in Collin County have TWO data sources:
1. **City Portal** (eTRAKiT, EnerGov, MyGov) - Most current data
2. **Collin CAD** (Texas Open Data) - Richer data (owner names, builders, values)

**ALWAYS scrape both** for maximum coverage:

```bash
# Scrape single city from both sources
python3 scripts/scrape_dual_source.py frisco 1000

# Scrape all dual-source cities
python3 scripts/scrape_dual_source.py --all 500
```

The loader deduplicates by `permit_id + city` and merges data from both sources.
```

**Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: add dual-source scraping strategy to CLAUDE.md"
```

---

## Summary

| Task | Description | Files |
|------|-------------|-------|
| 1 | Create dual-source scraping script | `scripts/scrape_dual_source.py` |
| 2 | Add Allen/McKinney to EnerGov | `scrapers/citizen_self_service.py` |
| 3 | Add deduplication to loader | `scripts/load_permits.py` |
| 4 | Run full scrape for priority cities | (execution) |
| 5 | Verify database freshness | (verification) |
| 6 | Document strategy | `CLAUDE.md` |

**Execution order:** 1 → 2 → 3 → 4 → 5 → 6
