#!/usr/bin/env python3
"""
Standalone Enrich + Score Pipeline (JSON-based, no database needed)

Reads raw permit JSON files, enriches with CAD data, scores with AI, and exports.

Usage:
    python3 scripts/enrich_and_score.py colleyville_raw.json southlake_raw.json westlake_raw.json
    python3 scripts/enrich_and_score.py --limit 50 colleyville_raw.json
    python3 scripts/enrich_and_score.py --skip-cad colleyville_raw.json  # Skip CAD enrichment
"""

import argparse
import asyncio
import csv
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import aiohttp
import requests
from dotenv import load_dotenv

load_dotenv()

# =============================================================================
# CAD ENRICHMENT CONFIGS
# =============================================================================

COUNTY_CONFIGS = {
    'tarrant': {
        'name': 'Tarrant',
        'url': 'https://tad.newedgeservices.com/arcgis/rest/services/TAD/ParcelView/MapServer/1/query',
        'address_field': 'Situs_Addr',
        'fields': ["Situs_Addr", "Owner_Name", "Owner_Addr", "Owner_City", "Owner_Zip",
                   "Total_Valu", "Land_Value", "Improvemen", "Year_Built", "Living_Are"],
    },
    'denton': {
        'name': 'Denton',
        'url': 'https://gis.dentoncad.com/server/rest/services/DCAD/DCAD_Parcels/MapServer/0/query',
        'address_field': 'situs_addr',
        'fields': ["situs_addr", "owner_name", "owner_addr", "owner_city", "owner_zip",
                   "market_val", "land_val", "imprv_val", "yr_built", "living_area"],
    },
}

# ZIP to county mapping
ZIP_TO_COUNTY = {
    # Tarrant County
    '76092': 'tarrant',  # Southlake
    '76034': 'tarrant',  # Colleyville
    '76262': 'tarrant',  # Roanoke/Trophy Club
    '76248': 'tarrant',  # Keller
    '76051': 'tarrant',  # Grapevine
    '76039': 'tarrant',  # Euless
    # Denton County
    '76262': 'denton',   # Westlake (actually Denton)
}

def get_county_from_address(address: str) -> Optional[str]:
    """Detect county from ZIP code in address."""
    if not address:
        return None
    zip_match = re.search(r'\b(\d{5})(?:-\d{4})?\b', address)
    if zip_match:
        return ZIP_TO_COUNTY.get(zip_match.group(1))
    return None

def parse_address_for_query(address: str):
    """Extract house number and street name for CAD query."""
    if not address:
        return None, None
    match = re.match(r'^(\d+)\s+(.+?)(?:\s+(?:UNIT|APT|STE|#).*)?(?:\s+\w+\s+TX\s+\d{5})?$',
                     address.upper(), re.IGNORECASE)
    if match:
        return match.group(1), match.group(2)
    return None, None

def enrich_from_cad(address: str) -> dict:
    """Query CAD API for property info."""
    county = get_county_from_address(address)
    if not county or county not in COUNTY_CONFIGS:
        return {'enrichment_status': 'unsupported_county'}

    config = COUNTY_CONFIGS[county]
    house_num, street = parse_address_for_query(address)
    if not house_num:
        return {'enrichment_status': 'parse_failed'}

    # Build query
    where_clause = f"{config['address_field']} LIKE '{house_num} {street}%'"
    params = {
        'where': where_clause,
        'outFields': ','.join(config['fields']),
        'returnGeometry': 'false',
        'f': 'json',
    }

    try:
        resp = requests.get(config['url'], params=params, timeout=15)
        data = resp.json()

        if data.get('features') and len(data['features']) > 0:
            attrs = data['features'][0]['attributes']
            return {
                'enrichment_status': 'success',
                'owner_name': attrs.get('Owner_Name') or attrs.get('owner_name'),
                'owner_address': attrs.get('Owner_Addr') or attrs.get('owner_addr'),
                'owner_city': attrs.get('Owner_City') or attrs.get('owner_city'),
                'owner_zip': attrs.get('Owner_Zip') or attrs.get('owner_zip'),
                'property_value': attrs.get('Total_Valu') or attrs.get('market_val'),
                'year_built': attrs.get('Year_Built') or attrs.get('yr_built'),
                'living_area': attrs.get('Living_Are') or attrs.get('living_area'),
                'county': county,
            }
        return {'enrichment_status': 'not_found'}
    except Exception as e:
        return {'enrichment_status': 'error', 'error': str(e)}

# =============================================================================
# AI SCORING
# =============================================================================

DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"

SCORE_PROMPT = """You are a Sales Director evaluating permit leads for a home services company.

Score this permit lead from 0-100 based on likelihood to need contractor services.

PERMIT INFO:
- Type: {type}
- Status: {status}
- Address: {address}
- Description: {description}
- Property Value: ${value:,.0f}
- Year Built: {year_built}
- Owner: {owner}

HIGH SCORE (70-100): Active construction, high property value, recent permits
MEDIUM SCORE (40-69): Maintenance work, moderate value, potential future needs
LOW SCORE (0-39): Completed work, commercial/government, low potential

Respond with ONLY a JSON object:
{{"score": <0-100>, "category": "<pool|hvac|roof|electrical|plumbing|general>", "reasoning": "<1 sentence>"}}
"""

async def score_permit_ai(permit: dict, session: aiohttp.ClientSession) -> dict:
    """Score a single permit using DeepSeek."""
    if not DEEPSEEK_API_KEY:
        return {'ai_score': 0, 'ai_category': 'unknown', 'ai_reasoning': 'No API key'}

    prompt = SCORE_PROMPT.format(
        type=permit.get('type', 'Unknown'),
        status=permit.get('status', 'Unknown'),
        address=permit.get('address', 'Unknown'),
        description=permit.get('description', ''),
        value=permit.get('property_value') or 0,
        year_built=permit.get('year_built') or 'Unknown',
        owner=permit.get('owner_name') or 'Unknown',
    )

    try:
        async with session.post(
            DEEPSEEK_URL,
            headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}"},
            json={
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 200,
            },
            timeout=aiohttp.ClientTimeout(total=30),
        ) as resp:
            data = await resp.json()
            content = data["choices"][0]["message"]["content"]

            # Parse JSON response
            json_match = re.search(r'\{[^}]+\}', content)
            if json_match:
                result = json.loads(json_match.group())
                return {
                    'ai_score': result.get('score', 0),
                    'ai_category': result.get('category', 'general'),
                    'ai_reasoning': result.get('reasoning', ''),
                }
    except Exception as e:
        return {'ai_score': 0, 'ai_category': 'error', 'ai_reasoning': str(e)}

    return {'ai_score': 0, 'ai_category': 'unknown', 'ai_reasoning': 'Parse failed'}

async def score_permits_batch(permits: list, concurrent: int = 5) -> list:
    """Score multiple permits concurrently."""
    async with aiohttp.ClientSession() as session:
        semaphore = asyncio.Semaphore(concurrent)

        async def score_with_limit(permit):
            async with semaphore:
                result = await score_permit_ai(permit, session)
                permit.update(result)
                return permit

        tasks = [score_with_limit(p) for p in permits]
        return await asyncio.gather(*tasks)

# =============================================================================
# MAIN PIPELINE
# =============================================================================

def load_permits(filepaths: list) -> list:
    """Load permits from multiple JSON files."""
    all_permits = []
    for fp in filepaths:
        path = Path(fp)
        if not path.exists():
            # Try in permit-scraper directory
            path = Path('/home/astre/command-center/testhome/permit-scraper') / fp

        if path.exists():
            with open(path) as f:
                data = json.load(f)
                permits = data.get('permits', data) if isinstance(data, dict) else data
                city = path.stem.replace('_raw', '').replace('_enriched', '')
                for p in permits:
                    p['source_city'] = city
                all_permits.extend(permits)
                print(f"  Loaded {len(permits)} from {path.name}")
    return all_permits

def export_csv(permits: list, output_path: str):
    """Export scored permits to CSV."""
    if not permits:
        return

    # Sort by score descending
    permits = sorted(permits, key=lambda p: p.get('ai_score', 0), reverse=True)

    fieldnames = ['ai_score', 'ai_category', 'permit_id', 'type', 'status', 'address',
                  'owner_name', 'property_value', 'year_built', 'source_city', 'ai_reasoning']

    with open(output_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(permits)

    print(f"  Exported {len(permits)} permits to {output_path}")

def main():
    parser = argparse.ArgumentParser(description='Enrich and score permits from JSON files')
    parser.add_argument('files', nargs='+', help='JSON files to process')
    parser.add_argument('--limit', type=int, help='Limit permits to process')
    parser.add_argument('--skip-cad', action='store_true', help='Skip CAD enrichment')
    parser.add_argument('--skip-score', action='store_true', help='Skip AI scoring')
    parser.add_argument('--concurrent', type=int, default=5, help='Concurrent API calls')
    parser.add_argument('--output', default='scored_leads.csv', help='Output CSV file')
    args = parser.parse_args()

    print("=" * 60)
    print("PERMIT ENRICHMENT & SCORING PIPELINE")
    print("=" * 60)

    # Load permits
    print("\n[1] Loading permits...")
    permits = load_permits(args.files)
    print(f"    Total: {len(permits)} permits")

    if args.limit:
        permits = permits[:args.limit]
        print(f"    Limited to: {len(permits)}")

    # Enrich with CAD
    if not args.skip_cad:
        print("\n[2] Enriching with CAD data...")
        success = 0
        for i, permit in enumerate(permits, 1):
            address = permit.get('address', '')
            if address:
                cad_data = enrich_from_cad(address)
                permit.update(cad_data)
                if cad_data.get('enrichment_status') == 'success':
                    success += 1
            if i % 10 == 0:
                print(f"    Progress: {i}/{len(permits)} ({success} enriched)")
            time.sleep(0.5)  # Rate limit
        print(f"    Enriched: {success}/{len(permits)}")
    else:
        print("\n[2] Skipping CAD enrichment")

    # Score with AI
    if not args.skip_score:
        print("\n[3] Scoring with AI...")
        if not DEEPSEEK_API_KEY:
            print("    ERROR: DEEPSEEK_API_KEY not set, skipping scoring")
        else:
            permits = asyncio.run(score_permits_batch(permits, args.concurrent))

            # Stats
            scored = [p for p in permits if p.get('ai_score', 0) > 0]
            high = len([p for p in scored if p.get('ai_score', 0) >= 70])
            med = len([p for p in scored if 40 <= p.get('ai_score', 0) < 70])
            low = len([p for p in scored if p.get('ai_score', 0) < 40])
            print(f"    Scored: {len(scored)} permits")
            print(f"    High (70+): {high}, Medium (40-69): {med}, Low (<40): {low}")
    else:
        print("\n[3] Skipping AI scoring")

    # Export
    print("\n[4] Exporting results...")
    output_path = Path('/home/astre/command-center/testhome/permit-scraper') / args.output
    export_csv(permits, str(output_path))

    # Also save enriched JSON
    json_output = output_path.with_suffix('.json')
    with open(json_output, 'w') as f:
        json.dump(permits, f, indent=2, default=str)
    print(f"    Saved JSON to {json_output}")

    print("\n" + "=" * 60)
    print("COMPLETE!")
    print("=" * 60)

if __name__ == '__main__':
    main()
