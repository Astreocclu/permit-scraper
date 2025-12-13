#!/usr/bin/env python3
"""
Rescore a subset of permits by permit_id.
Reads permit IDs from stdin or a file.

Usage:
    python3 scripts/rescore_subset.py < /tmp/rescore_permit_ids.txt
    python3 scripts/rescore_subset.py --file /tmp/rescore_permit_ids.txt
"""

import argparse
import asyncio
import sys
import os
from datetime import date, datetime

from dotenv import load_dotenv
load_dotenv()

import psycopg2

# Import from score_leads
from score_leads import (
    PermitData, ScoredLead, DeepSeekScorer,
    categorize_permit, get_trade_group, should_discard,
    normalize_address, save_scored_leads
)


def load_permits_by_ids(conn, permit_ids: list) -> list:
    """Load specific permits by permit_id."""
    if not permit_ids:
        return []

    placeholders = ','.join(['%s'] * len(permit_ids))
    query = f"""
        SELECT
            p.id, p.permit_id, p.city, p.property_address,
            COALESCE(prop.owner_name, p.applicant_name, 'Unknown') as owner_name,
            p.contractor_name,
            COALESCE(p.description, p.permit_type, '') as project_description,
            p.permit_type,
            COALESCE(prop.market_value, 0) as market_value,
            COALESCE(prop.is_absentee, false) as is_absentee,
            p.issued_date,
            prop.county,
            prop.year_built,
            prop.square_feet
        FROM leads_permit p
        LEFT JOIN leads_property prop ON p.property_address = prop.property_address
        WHERE p.permit_id IN ({placeholders})
    """

    with conn.cursor() as cur:
        cur.execute(query, permit_ids)
        rows = cur.fetchall()

    permits = []
    today = date.today()

    for row in rows:
        pg_id = row[0]
        issued_date = None
        days_old = -1
        if row[10]:
            try:
                if isinstance(row[10], date):
                    issued_date = row[10]
                else:
                    issued_date = datetime.strptime(str(row[10])[:10], '%Y-%m-%d').date()
                days_old = (today - issued_date).days
            except (ValueError, TypeError):
                pass

        raw_address = row[3] or ""
        city_from_db = row[2] or ""
        addr_parts = normalize_address(raw_address, default_city=city_from_db)

        permit = PermitData(
            permit_id=row[1],
            city=addr_parts["city"] or city_from_db.title(),
            property_address=raw_address,
            owner_name=row[4] or "Unknown",
            contractor_name=row[5] or "",
            project_description=row[6] or "",
            permit_type=row[7] or "",
            market_value=float(row[8]) if row[8] else 0.0,
            is_absentee=bool(row[9]),
            issued_date=issued_date,
            days_old=days_old,
            county=row[11] or "",
            year_built=row[12],
            square_feet=row[13],
            normalized_address=addr_parts["address"],
            unit=addr_parts["unit"],
            zip_code=addr_parts["zip_code"],
        )
        permit._pg_id = pg_id
        permits.append(permit)

    return permits


async def rescore_permits(permits: list) -> tuple:
    """Score permits with AI."""
    scorer = DeepSeekScorer()

    # Filter out discards
    valid = []
    discarded = 0
    for p in permits:
        discard, reason = should_discard(p)
        if discard:
            discarded += 1
        else:
            valid.append(p)

    if not valid:
        return [], {'discarded': discarded, 'scored': 0}

    scored = await scorer.score_batch(valid, max_concurrent=5)
    return scored, {'discarded': discarded, 'scored': len(scored)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--file', '-f', help='File with permit IDs (one per line)')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be scored')
    args = parser.parse_args()

    # Read permit IDs
    if args.file:
        with open(args.file) as f:
            permit_ids = [line.strip() for line in f if line.strip()]
    else:
        permit_ids = [line.strip() for line in sys.stdin if line.strip()]

    if not permit_ids:
        print("No permit IDs provided")
        return 1

    print(f"Loading {len(permit_ids)} permits...")

    conn = psycopg2.connect(os.environ['DATABASE_URL'])
    permits = load_permits_by_ids(conn, permit_ids)
    print(f"Found {len(permits)} permits in database")

    if args.dry_run:
        print("\n--- DRY RUN ---")
        for p in permits[:10]:
            cat = categorize_permit(p)
            print(f"  {p.permit_id}: {cat} - {p.project_description[:50]}...")
        if len(permits) > 10:
            print(f"  ... and {len(permits) - 10} more")
        conn.close()
        return 0

    # Score
    print(f"Scoring {len(permits)} permits with AI...")
    scored, stats = asyncio.run(rescore_permits(permits))

    print(f"Discarded: {stats['discarded']}, Scored: {stats['scored']}")

    # Count tiers
    tiers = {'A': 0, 'B': 0, 'C': 0, 'U': 0, 'RETRY': 0}
    for s in scored:
        tiers[s.tier] = tiers.get(s.tier, 0) + 1

    print(f"Results: A={tiers['A']}, B={tiers['B']}, C={tiers['C']}, U={tiers['U']}, RETRY={tiers['RETRY']}")

    # Save
    if scored:
        counts = save_scored_leads(conn, scored)
        print(f"Saved: {counts['saved']}, Skipped: {counts['skipped']}")

    conn.close()
    print("Done!")
    return 0


if __name__ == "__main__":
    exit(main())
