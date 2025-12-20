# DFW Municipality Optimization Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Maximize DFW permit coverage by implementing researched scrapers, testing existing ones, and researching high-value unimplemented cities.

**Architecture:** Three-tier approach: (1) implement confirmed-scrapable cities first, (2) test/fix existing partial scrapers, (3) research high-population unimplemented cities using browser-use agent.

**Tech Stack:** Python 3.11, Playwright, browser-use LLM agent, PostgreSQL

---

## Current State Summary

| Status | Count | Cities |
|--------|-------|--------|
| Working | 22 | Dallas, Fort Worth, Arlington, Plano, Frisco, Denton, McKinney, Grand Prairie, Mesquite, Carrollton, Flower Mound, Allen, Coppell, Hurst, Southlake, Colleyville, Trophy Club, Waxahachie, Westlake, Grapevine, Little Elm, Farmers Branch |
| Scrapable (needs impl) | 2 | Weatherford, Sachse |
| Partial | 3 | Irving, Bedford, Lewisville |
| Blocked | 6 | Forney, Mansfield, Celina, Fate, Euless, Richardson, Garland |
| Not Researched | 20+ | See Tier 3 below |

---

## Priority Tier 1: IMPLEMENT CONFIRMED SCRAPABLE

### Task 1: Run Sachse SmartGov Scraper

**Files:**
- Existing: `scrapers/smartgov_sachse.py`
- Output: `data/raw/sachse_smartgov.json`

**Step 1: Verify scraper exists and check code**

Run: `head -50 scrapers/smartgov_sachse.py`
Expected: Python scraper with SmartGov URL

**Step 2: Test scraper with small batch**

Run: `python3 scrapers/smartgov_sachse.py 50 2>&1 | tee /tmp/sachse_test.log`
Expected: JSON output with permits, check for errors

**Step 3: If success, run full scrape**

Run: `python3 scrapers/smartgov_sachse.py 500`
Expected: `data/raw/sachse_smartgov.json` with permits

**Step 4: Load permits to database**

Run: `python3 scripts/load_permits.py --file sachse_smartgov.json --dir data/raw`
Expected: "Loaded X permits" message

**Step 5: Commit if working**

```bash
git add data/raw/sachse_smartgov.json
git commit -m "data: add Sachse SmartGov permits"
```

---

### Task 2: Build Weatherford GovBuilt Scraper

**Files:**
- Create: `scrapers/govbuilt_weatherford.py`
- Output: `data/raw/weatherford_govbuilt.json`
- Reference: Session notes Dec 17 - 203 permits found at `https://permits.weatherfordtx.gov/`

**Step 2.1: Research GovBuilt API structure**

Run browser-use to explore the API:
```bash
python3.11 -m services.browser_scraper.runner \
  --city weatherford \
  --url "https://permits.weatherfordtx.gov/" \
  --mode explore \
  2>&1 | tee /tmp/weatherford_explore.log
```

Expected: Find JSON API endpoint or table structure

**Step 2.2: Write the scraper skeleton**

Create `scrapers/govbuilt_weatherford.py`:

```python
#!/usr/bin/env python3
"""GovBuilt scraper for Weatherford, TX.

Portal: https://permits.weatherfordtx.gov/
Access: PUBLIC (no login)
CAD: Parker County - NO PUBLIC API (permits only, no enrichment)
"""

import json
import httpx
from datetime import datetime, timedelta
from pathlib import Path

BASE_URL = "https://permits.weatherfordtx.gov"
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "raw"

def fetch_permits(days_back: int = 30, limit: int = 500) -> list[dict]:
    """Fetch permits from GovBuilt API."""
    # TODO: Implement after API exploration
    # GovBuilt typically has /api/permits or similar endpoint
    permits = []

    # Placeholder - replace with actual API call
    with httpx.Client(timeout=30) as client:
        # Try common GovBuilt API patterns
        endpoints = [
            f"{BASE_URL}/api/permits",
            f"{BASE_URL}/api/v1/permits",
            f"{BASE_URL}/permits/api",
        ]
        for endpoint in endpoints:
            try:
                resp = client.get(endpoint)
                if resp.status_code == 200:
                    data = resp.json()
                    print(f"Found working endpoint: {endpoint}")
                    permits = data if isinstance(data, list) else data.get("permits", [])
                    break
            except Exception as e:
                print(f"Endpoint {endpoint} failed: {e}")

    return permits[:limit]

def transform_permit(raw: dict) -> dict:
    """Transform GovBuilt permit to standard format."""
    return {
        "permit_id": raw.get("permitNumber") or raw.get("id"),
        "permit_type": raw.get("permitType") or raw.get("type"),
        "description": raw.get("description", ""),
        "address": raw.get("address") or raw.get("siteAddress", ""),
        "city": "Weatherford",
        "issued_date": raw.get("issuedDate") or raw.get("issueDate"),
        "value": raw.get("valuation") or raw.get("value") or 0,
        "contractor_name": raw.get("contractor") or raw.get("contractorName", ""),
        "contractor_phone": raw.get("contractorPhone", ""),
        "contractor_email": raw.get("contractorEmail", ""),
        "status": raw.get("status", ""),
    }

def main(limit: int = 500):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Fetching permits from Weatherford GovBuilt...")
    raw_permits = fetch_permits(limit=limit)

    if not raw_permits:
        print("No permits found. Check API endpoints.")
        return

    permits = [transform_permit(p) for p in raw_permits]

    output_file = OUTPUT_DIR / "weatherford_govbuilt.json"
    with open(output_file, "w") as f:
        json.dump(permits, f, indent=2)

    print(f"Saved {len(permits)} permits to {output_file}")

    # Stats
    with_contractor = sum(1 for p in permits if p.get("contractor_name"))
    print(f"With contractor name: {with_contractor}")

if __name__ == "__main__":
    import sys
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 500
    main(limit)
```

**Step 2.3: Run and test the scraper**

Run: `python3 scrapers/govbuilt_weatherford.py 100`
Expected: Either success or error pointing to correct API structure

**Step 2.4: Debug and fix based on actual API**

If API discovery fails, use browser-use to extract permits from DOM:
```bash
python3.11 -m services.browser_scraper.runner \
  --city weatherford \
  --url "https://permits.weatherfordtx.gov/" \
  --mode bulk \
  --days 30 \
  2>&1 | tee /tmp/weatherford_bulk.log
```

**Step 2.5: Load to database**

Run: `python3 scripts/load_permits.py --file weatherford_govbuilt.json --dir data/raw`

**Step 2.6: Commit**

```bash
git add scrapers/govbuilt_weatherford.py data/raw/weatherford_govbuilt.json
git commit -m "feat: add Weatherford GovBuilt scraper (no CAD - Parker County)"
```

**Note:** Parker County has NO public CAD API. Weatherford permits cannot be enriched with property data.

---

## Priority Tier 2: FIX PARTIAL SCRAPERS

### Task 3: Debug Lewisville MGO Connect (0 permits returned)

**Files:**
- Existing: `scrapers/mgo_connect.py`
- Logs: `/tmp/lewisville.log`

**Step 3.1: Review existing log**

Run: `tail -100 /tmp/lewisville.log`
Expected: See why 0 permits returned

**Step 3.2: Test with browser-use for manual exploration**

```bash
python3.11 -m services.browser_scraper.runner \
  --city lewisville \
  --url "https://permits.lewisville.com" \
  --mode explore \
  2>&1 | tee /tmp/lewisville_explore.log
```

**Step 3.3: Check if different date range needed**

MGO Connect may have different date formats or require specific search criteria. Check the actual portal URL and test manually.

**Step 3.4: Update scraper if needed**

Modify `scrapers/mgo_connect.py` based on findings.

---

### Task 4: Create Little Elm Excel Parser (Formalize the Manual Process)

**Files:**
- Create: `scripts/parse_littleelm_excel.py`
- Input: Excel file from MyGov Reports
- Output: `data/raw/little_elm_mygov.json`

**Step 4.1: Write the Excel parser**

Create `scripts/parse_littleelm_excel.py`:

```python
#!/usr/bin/env python3
"""Parse Little Elm MyGov Excel export to standard permit JSON.

Source: MyGov Reports > "All Issued Permits - Commercial, Residential, and Pools"
Download location: /tmp/browser-use-downloads-*/
"""

import json
import pandas as pd
from pathlib import Path
from datetime import datetime

def find_latest_excel() -> Path:
    """Find most recent Little Elm Excel file."""
    import glob
    patterns = [
        "/tmp/browser-use-downloads-*/All Issued Permits*.xlsx",
        "/tmp/browser-use-downloads-*/little*.xlsx",
    ]
    for pattern in patterns:
        files = glob.glob(pattern)
        if files:
            return Path(max(files, key=lambda f: Path(f).stat().st_mtime))
    raise FileNotFoundError("No Little Elm Excel file found")

def parse_excel(filepath: Path) -> list[dict]:
    """Parse Excel to standard permit format."""
    df = pd.read_excel(filepath)
    print(f"Loaded {len(df)} rows from {filepath}")
    print(f"Columns: {list(df.columns)}")

    permits = []
    for _, row in df.iterrows():
        # Extract contractor from "Credential Contacts" field
        contacts = str(row.get("Credential Contacts", ""))
        contractor_name = ""
        contractor_phone = ""
        contractor_email = ""

        if contacts and contacts != "nan":
            lines = contacts.split("\n")
            if lines:
                contractor_name = lines[0].strip()
            for line in lines:
                if "@" in line:
                    contractor_email = line.strip()
                elif any(c.isdigit() for c in line) and len(line) > 8:
                    contractor_phone = line.strip()

        # Parse date
        issued_date = row.get("Permit Issued", "")
        if pd.notna(issued_date):
            if hasattr(issued_date, "strftime"):
                issued_date = issued_date.strftime("%Y-%m-%d")
            else:
                issued_date = str(issued_date)[:10]
        else:
            issued_date = ""

        permit = {
            "permit_id": str(row.get("Permit Number", "")),
            "permit_type": str(row.get("Template name", "")),
            "description": str(row.get("Permit Description", "")),
            "address": str(row.get("Project Address", "")),
            "city": "Little Elm",
            "issued_date": issued_date,
            "value": 0,  # Not in export
            "contractor_name": contractor_name,
            "contractor_phone": contractor_phone,
            "contractor_email": contractor_email,
            "status": str(row.get("Status (Project)", "")),
        }
        permits.append(permit)

    return permits

def main():
    output_dir = Path(__file__).parent.parent / "data" / "raw"
    output_dir.mkdir(parents=True, exist_ok=True)

    excel_file = find_latest_excel()
    print(f"Processing: {excel_file}")

    permits = parse_excel(excel_file)

    output_file = output_dir / "little_elm_mygov.json"
    with open(output_file, "w") as f:
        json.dump(permits, f, indent=2)

    print(f"Saved {len(permits)} permits to {output_file}")
    with_contractor = sum(1 for p in permits if p.get("contractor_name"))
    print(f"With contractor name: {with_contractor}")

if __name__ == "__main__":
    main()
```

**Step 4.2: Test the parser**

Run: `python3 scripts/parse_littleelm_excel.py`
Expected: JSON file created with permits

**Step 4.3: Commit**

```bash
git add scripts/parse_littleelm_excel.py
git commit -m "feat: add Little Elm Excel parser for MyGov Reports"
```

---

## Priority Tier 3: RESEARCH HIGH-VALUE UNIMPLEMENTED CITIES

These cities have 20K+ population and no scraper research yet.

### Task 5: Research North Richland Hills (70K pop)

**Context:** Tarrant County, should have CAD enrichment available.

**Step 5.1: Run browser-use exploration**

```bash
python3.11 -m services.browser_scraper.runner \
  --city "north richland hills" \
  --mode explore \
  2>&1 | tee /tmp/nrh_explore.log
```

**Step 5.2: Check common platforms**

Try these URLs manually or via browser-use:
- `https://permits.nrhtx.com`
- `https://nrhtx.gov/permits`
- Search: "North Richland Hills permit portal"

**Step 5.3: Document findings in SCRAPER_STATUS.md**

Add entry with platform type, URL, access status.

---

### Task 6: Research Rowlett (68K pop)

**Context:** Dallas/Rockwall County, CAD available.

**Step 6.1: Run browser-use exploration**

```bash
python3.11 -m services.browser_scraper.runner \
  --city rowlett \
  --mode explore \
  2>&1 | tee /tmp/rowlett_explore.log
```

**Step 6.2: Check if already in MyGov multi**

Run: `grep -i rowlett scrapers/mygov_multi.py`
If found, test with existing scraper.

**Step 6.3: Document findings**

---

### Task 7: Research Wylie (56K pop)

**Context:** Collin County, CAD available.

```bash
python3.11 -m services.browser_scraper.runner \
  --city wylie \
  --mode explore \
  2>&1 | tee /tmp/wylie_explore.log
```

---

### Task 8: Research Keller (52K pop)

**Context:** Tarrant County, CAD available.

**Note:** May already be in eTRAKiT - check CLAUDE.md reference.

Run: `grep -i keller scrapers/*.py`
If found, test existing scraper.

---

### Task 9: Research Burleson (52K pop)

**Context:** Johnson/Tarrant County.

```bash
python3.11 -m services.browser_scraper.runner \
  --city burleson \
  --mode explore \
  2>&1 | tee /tmp/burleson_explore.log
```

---

### Task 10: Research Rockwall (49K pop)

**Context:** Rockwall County - may need new CAD integration.

```bash
python3.11 -m services.browser_scraper.runner \
  --city rockwall \
  --mode explore \
  2>&1 | tee /tmp/rockwall_explore.log
```

---

### Task 11: Research Cedar Hill (49K pop)

**Context:** Dallas County, CAD available.

```bash
python3.11 -m services.browser_scraper.runner \
  --city "cedar hill" \
  --mode explore \
  2>&1 | tee /tmp/cedarhill_explore.log
```

---

### Task 12: Research The Colony (48K pop)

**Context:** Denton County, CAD available.

```bash
python3.11 -m services.browser_scraper.runner \
  --city "the colony" \
  --mode explore \
  2>&1 | tee /tmp/thecolony_explore.log
```

---

### Task 13: Research Haltom City (46K pop)

**Context:** Tarrant County, CAD available.

```bash
python3.11 -m services.browser_scraper.runner \
  --city "haltom city" \
  --mode explore \
  2>&1 | tee /tmp/haltomcity_explore.log
```

---

### Task 14: Research Lancaster (42K pop)

**Context:** Dallas County, CAD available.

```bash
python3.11 -m services.browser_scraper.runner \
  --city lancaster \
  --mode explore \
  2>&1 | tee /tmp/lancaster_explore.log
```

---

### Task 15: Research Duncanville (40K pop)

**Context:** Dallas County, CAD available.

```bash
python3.11 -m services.browser_scraper.runner \
  --city duncanville \
  --mode explore \
  2>&1 | tee /tmp/duncanville_explore.log
```

---

## Blocked Cities Reference (DO NOT RESEARCH)

| City | Population | Reason | Login URL (if applicable) |
|------|------------|--------|---------------------------|
| Forney | 35K | Login Required | `https://mygov.us/collaborator/forneytx` |
| Mansfield | 75K | MyGov module disabled | - |
| Celina | 30K | MyGov module disabled | - |
| Fate | 25K | MyGov module disabled | - |
| Euless | 60K | Access Denied + CAPTCHA | - |
| Richardson | 120K | Access Denied on cor.net | `https://www.citizenserve.com/Portal/PortalController?Action=showPermit&ctzPagePrefix=Portal_&installationID=343` |
| Garland | 240K | No public portal (PDF/email only) | - |

---

## Success Metrics

**Current:** 22 working cities, ~4.6M population coverage

**After Tier 1:** +2 cities (Sachse, Weatherford) = 24 cities

**After Tier 2:** Fix partial scrapers = better data quality

**After Tier 3:** +5-10 cities = 29-34 cities, ~5.5M+ population

**Target:** 35+ working cities covering 80%+ of DFW metro population

---

## Appendix: Platform Quick Reference

| Platform | Scraper | Working Cities |
|----------|---------|----------------|
| Accela | `accela_fast.py` | Dallas, Fort Worth, Grand Prairie, Mesquite |
| eTRAKiT | `etrakit.py`, `etrakit_auth.py` | Frisco, Flower Mound, Denton, Plano, Keller, Prosper |
| EnerGov CSS | `citizen_self_service.py` | Southlake, Colleyville, McKinney, Allen, Hurst, Coppell, Trophy Club, Waxahachie, Farmers Branch |
| MyGov | `mygov_westlake.py`, `parse_grapevine_pdf.py` | Westlake, Grapevine, Little Elm |
| CityView | `cityview.py` | Carrollton |
| Socrata | `dfw_big4_socrata.py` | Arlington |
| SmartGov | `smartgov_sachse.py` | Sachse (pending) |
| GovBuilt | `govbuilt_weatherford.py` | Weatherford (pending) |
| MGO Connect | `mgo_connect.py` | Irving (partial), Lewisville (0 results) |

---

## Notes

- **CAD Limitations:** Parker County (Weatherford) has NO public CAD API - permits only
- **Ellis County CAD:** Firewalled - Waxahachie permits cannot be enriched
- **Kaufman County CAD:** Partial - missing year_built, square_feet fields
- **Browser-use timeout:** Default 5 minutes, increase with `--timeout 600` for slow portals
