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
    if days_old >= 45:
        return 0

    # Freshness score (0-44 points) - HEAVY weight
    # 1 day = 44 points, 44 days = 0 points
    freshness_score = max(0, 45 - days_old - 1)

    # Property value score (0-14 points) - LIGHT weight
    # $200k = 0, $800k+ = 14
    value_normalized = min(max(market_value - 200000, 0) / 600000, 1.0)
    value_score = int(value_normalized * 14)

    # Total capped at 60
    return min(freshness_score + value_score, 60)


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
