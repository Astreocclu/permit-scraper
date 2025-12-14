# Adjacent Trade Routing Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Route contractor-pulled permits (electrical panel, HVAC replacement) to adjacent trades who can upsell the homeowner.

**Architecture:** Standalone script that queries permits currently marked as "junk" or filtered, identifies adjacent-trade candidates, scores them with freshness-weighted logic, and exports to `exports/adjacent_trades/{vertical}/`.

**Tech Stack:** Python 3, psycopg2, same patterns as score_leads.py

---

## Proposed File Structure

```
permit-scraper/
├── scripts/
│   └── adjacent_trades.py          # NEW - standalone adjacent trade router
├── exports/
│   └── adjacent_trades/
│       ├── electrical/
│       │   ├── tier_a.csv
│       │   ├── tier_b.csv
│       │   └── PITCH.md            # Sales pitch for solar/smart home/security
│       └── hvac/
│           ├── tier_a.csv
│           ├── tier_b.csv
│           └── PITCH.md            # Sales pitch for duct cleaning/insulation
└── tests/
    └── test_adjacent_trades.py     # NEW - tests for adjacent trade routing
```

---

### Task 1: Create Test File Structure

**Files:**
- Create: `tests/test_adjacent_trades.py`

**Step 1: Write the initial test file with routing tests**

```python
# tests/test_adjacent_trades.py
"""Tests for adjacent_trades.py routing and scoring."""
import pytest
import sys
sys.path.insert(0, 'scripts')


class TestAdjacentTradeKeywords:
    """Test keyword detection for adjacent trade routing."""

    def test_electrical_panel_routed(self):
        from adjacent_trades import is_adjacent_electrical
        assert is_adjacent_electrical("electrical panel upgrade") is True
        assert is_adjacent_electrical("200 amp panel upgrade") is True
        assert is_adjacent_electrical("service upgrade") is True
        assert is_adjacent_electrical("panel replacement") is True

    def test_hvac_replacement_routed(self):
        from adjacent_trades import is_adjacent_hvac
        assert is_adjacent_hvac("hvac replacement") is True
        assert is_adjacent_hvac("ac replacement") is True
        assert is_adjacent_hvac("furnace replacement") is True
        assert is_adjacent_hvac("new hvac system") is True

    def test_water_heater_not_routed(self):
        """Water heater has weak adjacencies - should NOT be routed."""
        from adjacent_trades import is_adjacent_electrical, is_adjacent_hvac
        assert is_adjacent_electrical("water heater replacement") is False
        assert is_adjacent_hvac("water heater replacement") is False

    def test_sewer_not_routed(self):
        """Sewer repair has weak adjacencies - should NOT be routed."""
        from adjacent_trades import is_adjacent_electrical, is_adjacent_hvac
        assert is_adjacent_electrical("sewer repair") is False
        assert is_adjacent_hvac("sewer repair") is False


class TestAdjacentScoring:
    """Test freshness-weighted scoring for adjacent leads."""

    def test_fresh_permit_scores_higher(self):
        from adjacent_trades import score_adjacent_lead
        # 3 days old, $300k property
        fresh_score = score_adjacent_lead(days_old=3, market_value=300000)
        # 30 days old, $300k property
        stale_score = score_adjacent_lead(days_old=30, market_value=300000)
        assert fresh_score > stale_score

    def test_property_value_less_impact(self):
        from adjacent_trades import score_adjacent_lead
        # Same freshness, different values
        low_value = score_adjacent_lead(days_old=7, market_value=200000)
        high_value = score_adjacent_lead(days_old=7, market_value=800000)
        # High value should score higher, but not by much
        assert high_value > low_value
        assert high_value - low_value < 15  # Property value impact capped

    def test_score_capped_at_60(self):
        from adjacent_trades import score_adjacent_lead
        # Best possible lead: 1 day old, $2M property
        score = score_adjacent_lead(days_old=1, market_value=2000000)
        assert score <= 60

    def test_very_old_scores_zero(self):
        from adjacent_trades import score_adjacent_lead
        # 45+ days is too stale for adjacent trades
        score = score_adjacent_lead(days_old=45, market_value=500000)
        assert score == 0
```

**Step 2: Run test to verify it fails**

Run: `cd /home/reid/testhome/permit-scraper && python -m pytest tests/test_adjacent_trades.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'adjacent_trades'"

**Step 3: Commit test file**

```bash
cd /home/reid/testhome/permit-scraper
git add tests/test_adjacent_trades.py
git commit -m "test: add adjacent trade routing tests (red)"
```

---

### Task 2: Create Adjacent Trades Script with Keyword Detection

**Files:**
- Create: `scripts/adjacent_trades.py`

**Step 1: Write minimal implementation for keyword detection**

```python
#!/usr/bin/env python3
"""
Adjacent Trade Router - Route contractor-pulled permits to adjacent trades.

Electrical panel upgrades → Solar, smart home, security companies
HVAC replacements → Duct cleaning, insulation, smart thermostat companies

These permits are contractor-pulled (homeowner can't legally pull them in Texas),
so the primary contractor already has the job. But adjacent trades can upsell.
"""

# Keywords that route to electrical adjacent trades
ELECTRICAL_ADJACENT_KEYWORDS = [
    "electrical panel",
    "panel upgrade",
    "panel replacement",
    "service upgrade",
    "200 amp",
    "400 amp",
    "meter upgrade",
]

# Keywords that route to HVAC adjacent trades
HVAC_ADJACENT_KEYWORDS = [
    "hvac replacement",
    "ac replacement",
    "furnace replacement",
    "new hvac",
    "hvac install",
    "air handler",
    "condenser replacement",
]


def is_adjacent_electrical(description: str) -> bool:
    """Check if permit should route to electrical adjacent trades."""
    if not description:
        return False
    desc_lower = description.lower()
    return any(kw in desc_lower for kw in ELECTRICAL_ADJACENT_KEYWORDS)


def is_adjacent_hvac(description: str) -> bool:
    """Check if permit should route to HVAC adjacent trades."""
    if not description:
        return False
    desc_lower = description.lower()
    return any(kw in desc_lower for kw in HVAC_ADJACENT_KEYWORDS)


def score_adjacent_lead(days_old: int, market_value: float) -> int:
    """
    Score adjacent trade lead with freshness-weighted logic.

    Freshness matters MORE (duct cleaning needs to happen right after HVAC install).
    Property value matters LESS.
    Max score capped at 60 (these are lower value than primary leads).
    """
    # Too stale - no value
    if days_old > 45:
        return 0

    # Freshness score (0-45 points) - HEAVY weight
    # 1 day = 45 points, 45 days = 0 points
    freshness_score = max(0, 45 - days_old)

    # Property value score (0-15 points) - LIGHT weight
    # $200k = 0, $800k+ = 15
    value_normalized = min(max(market_value - 200000, 0) / 600000, 1.0)
    value_score = int(value_normalized * 15)

    # Total capped at 60
    return min(freshness_score + value_score, 60)


if __name__ == "__main__":
    print("Adjacent Trade Router")
    print("Usage: python scripts/adjacent_trades.py [--limit N]")
```

**Step 2: Run tests to verify keyword detection passes**

Run: `cd /home/reid/testhome/permit-scraper && python -m pytest tests/test_adjacent_trades.py -v`
Expected: All tests PASS

**Step 3: Commit**

```bash
cd /home/reid/testhome/permit-scraper
git add scripts/adjacent_trades.py
git commit -m "feat: add adjacent trade keyword detection and scoring"
```

---

### Task 3: Add Database Query and Export Logic

**Files:**
- Modify: `scripts/adjacent_trades.py`

**Step 1: Add database query for adjacent trade permits**

Add after the scoring function:

```python
import argparse
import csv
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any
from dataclasses import dataclass

import psycopg2
from dotenv import load_dotenv

load_dotenv()


@dataclass
class AdjacentLead:
    """Adjacent trade lead data."""
    permit_id: str
    city: str
    property_address: str
    owner_name: str
    description: str
    permit_type: str
    market_value: float
    days_old: int
    score: int
    vertical: str  # "electrical" or "hvac"


def get_database_connection():
    """Get database connection from DATABASE_URL."""
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        raise ValueError("DATABASE_URL not set")
    return psycopg2.connect(db_url)


def query_adjacent_permits(limit: int = 1000) -> List[Dict[str, Any]]:
    """
    Query permits that should route to adjacent trades.

    These are permits that were filtered from main scoring but have
    adjacent trade potential.
    """
    conn = get_database_connection()
    cur = conn.cursor()

    # Get permits from last 45 days with adjacent trade keywords
    cutoff = datetime.now().date() - timedelta(days=45)

    cur.execute("""
        SELECT
            p.permit_id,
            p.city,
            p.property_address,
            pr.owner_name,
            p.description,
            p.permit_type,
            pr.market_value,
            p.issued_date
        FROM leads_permit p
        JOIN leads_property pr ON p.property_address = pr.property_address
        WHERE pr.enrichment_status = 'success'
        AND p.issued_date >= %s
        AND (
            LOWER(p.description) LIKE '%%panel%%'
            OR LOWER(p.description) LIKE '%%service upgrade%%'
            OR LOWER(p.permit_type) LIKE '%%panel%%'
            OR LOWER(p.description) LIKE '%%hvac replacement%%'
            OR LOWER(p.description) LIKE '%%ac replacement%%'
            OR LOWER(p.description) LIKE '%%furnace%%'
            OR LOWER(p.permit_type) LIKE '%%hvac%%'
        )
        ORDER BY p.issued_date DESC
        LIMIT %s
    """, (cutoff, limit))

    columns = [desc[0] for desc in cur.description]
    results = [dict(zip(columns, row)) for row in cur.fetchall()]

    conn.close()
    return results


def route_and_score_permits(permits: List[Dict]) -> List[AdjacentLead]:
    """Route permits to verticals and score them."""
    leads = []
    today = datetime.now().date()

    for p in permits:
        desc = (p.get("description") or "") + " " + (p.get("permit_type") or "")

        # Determine vertical
        vertical = None
        if is_adjacent_electrical(desc):
            vertical = "electrical"
        elif is_adjacent_hvac(desc):
            vertical = "hvac"

        if not vertical:
            continue

        # Calculate days old
        issued = p.get("issued_date")
        days_old = (today - issued).days if issued else 30

        # Score
        market_value = p.get("market_value") or 0
        score = score_adjacent_lead(days_old, market_value)

        if score == 0:
            continue  # Too stale

        leads.append(AdjacentLead(
            permit_id=p["permit_id"],
            city=p["city"],
            property_address=p["property_address"],
            owner_name=p.get("owner_name") or "Unknown",
            description=desc.strip(),
            permit_type=p.get("permit_type") or "",
            market_value=market_value,
            days_old=days_old,
            score=score,
            vertical=vertical,
        ))

    return leads


def export_leads(leads: List[AdjacentLead], output_dir: Path):
    """Export leads to CSV by vertical and tier."""
    # Group by vertical and tier
    buckets: Dict[str, Dict[str, List]] = {}

    for lead in leads:
        if lead.vertical not in buckets:
            buckets[lead.vertical] = {"a": [], "b": []}

        # Tier A: 45-60, Tier B: 1-44
        tier = "a" if lead.score >= 45 else "b"
        buckets[lead.vertical][tier].append(lead)

    # Export
    for vertical, tiers in buckets.items():
        for tier, tier_leads in tiers.items():
            if not tier_leads:
                continue

            dir_path = output_dir / "adjacent_trades" / vertical
            dir_path.mkdir(parents=True, exist_ok=True)

            filepath = dir_path / f"tier_{tier}.csv"
            with open(filepath, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=[
                    "permit_id", "city", "property_address", "owner_name",
                    "description", "market_value", "days_old", "score"
                ])
                writer.writeheader()
                for lead in sorted(tier_leads, key=lambda x: -x.score):
                    writer.writerow({
                        "permit_id": lead.permit_id,
                        "city": lead.city,
                        "property_address": lead.property_address,
                        "owner_name": lead.owner_name,
                        "description": lead.description,
                        "market_value": lead.market_value,
                        "days_old": lead.days_old,
                        "score": lead.score,
                    })

            print(f"  {filepath}: {len(tier_leads)}")


def main():
    parser = argparse.ArgumentParser(description="Route permits to adjacent trades")
    parser.add_argument("--limit", type=int, default=1000, help="Max permits to process")
    parser.add_argument("--export-dir", type=str, default="exports", help="Export directory")
    args = parser.parse_args()

    print("=== ADJACENT TRADE ROUTER ===")
    print(f"Querying permits (limit {args.limit})...")

    permits = query_adjacent_permits(args.limit)
    print(f"Found {len(permits)} candidate permits")

    leads = route_and_score_permits(permits)
    print(f"Routed {len(leads)} leads")

    # Stats
    electrical = [l for l in leads if l.vertical == "electrical"]
    hvac = [l for l in leads if l.vertical == "hvac"]
    print(f"\nBy vertical:")
    print(f"  Electrical: {len(electrical)}")
    print(f"  HVAC: {len(hvac)}")

    # Export
    print(f"\nExporting to {args.export_dir}/adjacent_trades/...")
    export_leads(leads, Path(args.export_dir))

    print("\nDone!")


if __name__ == "__main__":
    main()
```

**Step 2: Run the script to verify it works**

Run: `cd /home/reid/testhome/permit-scraper && python scripts/adjacent_trades.py --limit 100`
Expected: Output showing permits found and exported

**Step 3: Commit**

```bash
cd /home/reid/testhome/permit-scraper
git add scripts/adjacent_trades.py
git commit -m "feat: add database query and export for adjacent trades"
```

---

### Task 4: Create Pitch Templates

**Files:**
- Create: `exports/adjacent_trades/electrical/PITCH.md`
- Create: `exports/adjacent_trades/hvac/PITCH.md`

**Step 1: Create electrical pitch template**

```markdown
# Electrical Panel Upgrade Leads - Adjacent Trade Opportunities

## Who These Leads Are For

Homeowners who just had an **electrical panel upgrade** are prime prospects for:

### 1. Solar Installation Companies
- Panel upgrade = electrical capacity ready for solar
- Already invested in home infrastructure
- Likely have higher energy bills (why they upgraded)

### 2. Smart Home / Home Automation
- New panel = modern electrical system
- Tech-forward homeowner mindset
- Ready for smart devices, EV chargers

### 3. Security System Companies
- New electrical = can support cameras, sensors
- Home improvement momentum
- Invested in property value

## Lead Quality

- **Freshness**: These leads are 1-45 days old. Fresher = better response rate.
- **Score 45-60 (Tier A)**: Very fresh OR high-value property
- **Score 1-44 (Tier B)**: Still actionable, less urgent

## Pitch Angle

"I noticed you recently upgraded your electrical panel. That's perfect timing - your home now has the capacity for [solar/smart home/security]. Would you like a free assessment?"

## Pricing Suggestion

- Tier A: $15-25/lead
- Tier B: $8-15/lead
```

**Step 2: Create HVAC pitch template**

```markdown
# HVAC Replacement Leads - Adjacent Trade Opportunities

## Who These Leads Are For

Homeowners who just had an **HVAC replacement** are prime prospects for:

### 1. Duct Cleaning Services
- New HVAC = want clean air flowing through it
- Duct cleaning timing: RIGHT AFTER new install
- Easy upsell, low friction

### 2. Insulation Companies
- New HVAC = thinking about efficiency
- Insulation maximizes HVAC investment
- "Get the most out of your new system"

### 3. Smart Thermostat Installers
- New system = compatible with smart controls
- Energy savings pitch
- Home automation entry point

## Lead Quality

- **Freshness**: These leads are 1-45 days old. Fresher = MUCH better for HVAC adjacents.
- **Score 45-60 (Tier A)**: Very fresh (duct cleaning window is ~2 weeks)
- **Score 1-44 (Tier B)**: Still viable for insulation/thermostat

## Pitch Angle

"Congratulations on your new HVAC system! To get the most out of it, many homeowners also [clean their ducts/upgrade insulation/add smart controls]. Would you like a free quote?"

## Pricing Suggestion

- Tier A: $12-20/lead
- Tier B: $6-12/lead
```

**Step 3: Commit pitch templates**

```bash
cd /home/reid/testhome/permit-scraper
mkdir -p exports/adjacent_trades/electrical exports/adjacent_trades/hvac
git add exports/adjacent_trades/electrical/PITCH.md exports/adjacent_trades/hvac/PITCH.md
git commit -m "docs: add sales pitch templates for adjacent trade leads"
```

---

### Task 5: Revert JUNK_PROJECTS Change

**Files:**
- Modify: `scripts/score_leads.py`

**Step 1: Add trade permits back to JUNK_PROJECTS**

The main scoring pipeline should NOT score these - they go through adjacent_trades.py instead.

Find and replace the JUNK_PROJECTS list:

```python
JUNK_PROJECTS = [
    # Low-value minor structures
    "shed", "storage building", "carport",
    # Insurance claims (different market/buyer)
    "fire repair", "fire damage",
    "storm damage", "hail damage",
    # Demo without rebuild
    "demolition", "demo permit", "tear down house", "tear down building",
    # Temporary/construction
    "temporary", "temp permit", "construction trailer",
    # Commercial signage
    "sign permit", "signage", "banner",
    # Commercial tenant fit-out
    "tenant finish", "tenant improvement", "ti permit",
    # Contractor-pulled permits - route to adjacent_trades.py instead
    "electrical panel", "panel upgrade", "service upgrade",
    "hvac replacement", "ac replacement", "furnace replacement",
    "water heater",  # Weak adjacencies
    "sewer repair", "sewer replacement", "sewer line repair",  # Weak adjacencies
]
```

Remove the comment block that was added earlier.

**Step 2: Run existing tests to verify no regression**

Run: `cd /home/reid/testhome/permit-scraper && python -m pytest tests/test_score_leads.py -v`
Expected: All tests PASS

**Step 3: Commit**

```bash
cd /home/reid/testhome/permit-scraper
git add scripts/score_leads.py
git commit -m "fix: route trade permits to adjacent_trades.py, not main scoring"
```

---

### Task 6: Final Integration Test

**Step 1: Run adjacent trades router**

Run: `cd /home/reid/testhome/permit-scraper && python scripts/adjacent_trades.py --limit 500`

Expected output:
```
=== ADJACENT TRADE ROUTER ===
Querying permits (limit 500)...
Found X candidate permits
Routed Y leads

By vertical:
  Electrical: N
  HVAC: M

Exporting to exports/adjacent_trades/...
  exports/adjacent_trades/electrical/tier_a.csv: X
  exports/adjacent_trades/electrical/tier_b.csv: Y
  exports/adjacent_trades/hvac/tier_a.csv: X
  exports/adjacent_trades/hvac/tier_b.csv: Y

Done!
```

**Step 2: Verify exports exist**

Run: `ls -la exports/adjacent_trades/*/`

**Step 3: Run all tests**

Run: `cd /home/reid/testhome/permit-scraper && python -m pytest tests/ -v`
Expected: All tests PASS

**Step 4: Final commit**

```bash
cd /home/reid/testhome/permit-scraper
git add -A
git commit -m "feat: adjacent trade routing complete"
```

---

## Summary

| Vertical | Adjacent Buyers | Freshness Window |
|----------|-----------------|------------------|
| Electrical | Solar, smart home, security | 1-45 days |
| HVAC | Duct cleaning, insulation, thermostats | 1-45 days (duct cleaning: <14 days ideal) |

**NOT routed (weak adjacencies):**
- Water heater (no strong adjacent services)
- Sewer repair (no strong adjacent services)
