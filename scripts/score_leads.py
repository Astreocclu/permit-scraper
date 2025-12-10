#!/usr/bin/env python3
"""
Lead Scoring - AI-Powered Sales Director Scoring (Standalone)

Ported from contractor-auditor's scoring_v2.py.

Three-layer scoring system:
1. Layer 1: Pre-filter (discard junk before AI sees it)
2. Layer 2: AI Scoring (DeepSeek scores 0-100 with reasoning)
3. Layer 3: Export buckets by category and tier

Usage:
    python3 scripts/score_leads.py                    # Score all enriched permits
    python3 scripts/score_leads.py --limit 100        # Score first 100
    python3 scripts/score_leads.py --dry-run          # Preview without API calls
    python3 scripts/score_leads.py --city "fort worth"
    python3 scripts/score_leads.py --category pool    # Only pool permits
"""

import argparse
import asyncio
import csv
import json
import logging
import os
import random
import re
import sqlite3
from dataclasses import dataclass, field, asdict
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import aiohttp

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = "data/permits.db"


# =============================================================================
# PRODUCTION BUILDER DETECTION
# =============================================================================

PRODUCTION_BUILDERS = [
    # National builders
    "lennar", "dr horton", "d.r. horton", "pulte", "pultegroup", "kb home",
    "meritage", "toll brothers", "centex", "nvr", "ryan homes", "m/i homes",
    "taylor morrison", "beazer", "ashton woods", "weekley", "david weekley",
    "highland homes", "perry homes", "gehan", "tri pointe", "shea homes",
    "standard pacific", "ryland", "kb homes",

    # Texas regional builders
    "bloomfield homes", "history maker", "impression homes", "antares homes",
    "first texas", "grand homes", "plantation homes", "altura homes",
    "coventry homes", "newmark homes", "westin homes", "trendmaker",
    "saratoga homes", "chesmar", "sitterle", "empire communities",
    "mcguyer homebuilders", "stylecraft", "pacesetter", "dunhill",
    "brightland", "southgate", "chesmar homes", "trophy signature",
    "landon homes", "ashton dallas",

    # Builder indicators in names
    "homes llc", "homes inc", "homebuilders", "home builders",
    "development llc", "development inc", "developers llc",
    "builders llc", "builders inc", "construction llc",
    "communities llc", "communities inc", "residential llc",
]

PRODUCTION_BUILDER_PATTERNS = [
    r"\bhomes\s+(of|at|in)\s+",
    r"\bhome\s+builders?\b",
    r"\bdevelopment\s+(group|corp|co)\b",
    r"\bbuilders?\s+(group|corp|co)\b",
    r"\bresidential\s+(group|corp|co)\b",
]


def is_production_builder(text: str) -> bool:
    """Check if text indicates a production builder."""
    if not text:
        return False

    text_lower = text.lower().strip()

    for builder in PRODUCTION_BUILDERS:
        if builder in text_lower:
            return True

    for pattern in PRODUCTION_BUILDER_PATTERNS:
        if re.search(pattern, text_lower):
            return True

    return False


# =============================================================================
# JUNK PROJECT DETECTION
# =============================================================================

JUNK_PROJECTS = [
    "shed", "storage building", "carport",
    "fire repair", "fire damage",
    "storm damage", "hail damage", "water damage",
    "electrical panel", "water heater",
    "hvac replacement", "ac replacement", "furnace replacement",
    "sewer repair", "sewer replacement", "sewer line repair",
    "demolition", "demo permit", "tear down house", "tear down building",
    "temporary", "temp permit", "construction trailer",
    "sign permit", "signage", "banner",
    "tenant finish", "tenant improvement", "ti permit",
]


def is_junk_project(description: str) -> bool:
    """Check if project description indicates a junk/low-value project."""
    if not description:
        return False
    desc_lower = description.lower()
    return any(junk in desc_lower for junk in JUNK_PROJECTS)


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class PermitData:
    """Normalized permit data for scoring."""
    permit_id: str
    city: str
    property_address: str
    owner_name: str = "Unknown"
    contractor_name: str = ""
    project_description: str = ""
    permit_type: str = ""
    market_value: float = 0.0
    is_absentee: bool = False
    issued_date: Optional[date] = None
    days_old: int = 0
    county: str = ""
    year_built: Optional[int] = None
    square_feet: Optional[int] = None


@dataclass
class ScoredLead:
    """Result from AI scoring."""
    permit: PermitData
    score: int
    tier: str  # A, B, C, or RETRY
    reasoning: str
    flags: List[str] = field(default_factory=list)
    ideal_contractor: str = ""
    contact_priority: str = "email"
    category: str = "other"
    trade_group: str = "other"
    chain_of_thought: str = ""
    scored_at: datetime = field(default_factory=datetime.now)
    scoring_method: str = "ai"

    def to_dict(self) -> Dict[str, Any]:
        return {
            **asdict(self.permit),
            "score": self.score,
            "tier": self.tier,
            "reasoning": self.reasoning,
            "chain_of_thought": self.chain_of_thought,
            "flags": self.flags,
            "ideal_contractor": self.ideal_contractor,
            "contact_priority": self.contact_priority,
            "category": self.category,
            "trade_group": self.trade_group,
            "scored_at": self.scored_at.isoformat(),
            "scoring_method": self.scoring_method,
        }


# =============================================================================
# PRE-FILTER
# =============================================================================

def should_discard(permit: PermitData) -> Tuple[bool, str]:
    """Returns (True, reason) if lead should be thrown out entirely."""
    if is_production_builder(permit.owner_name):
        return True, f"Production builder: {permit.owner_name[:50]}"

    if is_production_builder(permit.project_description):
        return True, f"Production builder in desc: {permit.project_description[:50]}"

    if is_junk_project(permit.project_description):
        return True, f"Junk project: {permit.project_description[:50]}"

    if permit.days_old > 90:
        return True, f"Too old: {permit.days_old} days"

    has_owner = permit.owner_name not in ("Unknown", "", None)
    has_value = permit.market_value and permit.market_value > 0
    has_contractor = permit.contractor_name not in ("Unknown", "", None)
    if not has_owner and not has_value and not has_contractor:
        return True, "No owner AND no value AND no contractor"

    return False, ""


# =============================================================================
# CATEGORY DETECTION
# =============================================================================

TRADE_GROUPS = {
    "pool": "luxury_outdoor", "outdoor_living": "luxury_outdoor", "fence": "luxury_outdoor",
    "roof": "home_exterior", "siding": "home_exterior", "windows": "home_exterior",
    "garage_door": "home_exterior", "concrete": "home_exterior", "painting": "home_exterior",
    "hvac": "home_systems", "plumbing": "home_systems", "electrical": "home_systems",
    "solar": "home_systems", "insulation": "home_systems",
    "foundation": "structural", "addition": "structural",
    "new_construction": "structural", "remodel": "structural",
    "commercial_pool": "commercial", "commercial_roof": "commercial",
    "commercial_hvac": "commercial", "commercial_plumbing": "commercial",
    "demolition": "unsellable", "temporary": "unsellable", "signage": "unsellable",
    "other": "other",
}

CATEGORY_KEYWORDS = {
    "pool": ["pool", "swim", "spa", "hot tub", "gunite", "fiberglass pool"],
    "outdoor_living": ["patio", "deck", "pergola", "outdoor kitchen", "cabana",
                       "gazebo", "arbor", "screen enclosure", "covered patio",
                       "shade structure", "pavilion", "outdoor living"],
    "fence": ["fence", "fencing", "privacy fence", "iron fence", "wood fence"],
    "roof": ["roof", "roofing", "re-roof", "reroof", "shingle", "metal roof"],
    "siding": ["siding", "hardie", "stucco", "exterior finish"],
    "windows": ["window", "door replacement", "sliding door", "french door"],
    "concrete": ["driveway", "sidewalk", "concrete", "flatwork", "stamped concrete", "pavers"],
    "hvac": ["hvac", "air condition", "ac unit", "furnace", "heat pump", "ductwork", "mini split"],
    "plumbing": ["plumb", "water heater", "tankless", "water line", "gas line", "repipe"],
    "electrical": ["electric", "panel", "outlet", "circuit", "wire", "ev charger", "generator"],
    "solar": ["solar", "photovoltaic", "pv system"],
    "foundation": ["foundation", "pier", "underpinning", "slab repair", "leveling"],
    "new_construction": ["new home", "new construction", "new sfd", "custom home"],
    "addition": ["addition", "room addition", "add on", "expansion"],
    "remodel": ["remodel", "renovation", "kitchen remodel", "bath remodel"],
    "demolition": ["demo", "demolition", "tear down"],
    "temporary": ["temporary", "temp permit"],
    "signage": ["sign permit", "signage", "banner"],
}

COMMERCIAL_INDICATORS = [
    "commercial", "office", "retail", "restaurant", "warehouse", "industrial",
    "tenant", "suite", "shopping", "plaza", "mall", "store", "business",
    "corp", "inc.", "llc", "church", "school", "hospital", "medical", "clinic"
]


def is_commercial_property(permit: PermitData) -> bool:
    text = f"{permit.project_description} {permit.owner_name} {permit.property_address}".lower()
    return any(indicator in text for indicator in COMMERCIAL_INDICATORS)


def categorize_permit(permit: PermitData) -> str:
    desc = (permit.project_description + " " + permit.permit_type).lower()
    is_commercial = is_commercial_property(permit)

    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in desc for kw in keywords):
            if is_commercial and category in ["pool", "roof", "hvac", "plumbing", "electrical"]:
                return f"commercial_{category}"
            return category

    return "other"


def get_trade_group(category: str) -> str:
    return TRADE_GROUPS.get(category, "other")


# =============================================================================
# AI SCORING (DeepSeek)
# =============================================================================

SALES_DIRECTOR_PROMPT = """You are a Sales Director scoring leads for a contractor lead marketplace in DFW (Dallas-Fort Worth).

YOUR BUYERS (contractors who will pay for these leads):
- Luxury outdoor: Pool builders, patio/outdoor living contractors, fence companies
- Home exterior: Roofers, concrete contractors, window/siding installers
- Home systems: HVAC contractors, plumbers, electricians
- Structural: Foundation repair specialists, custom home builders

SCORE 0-100 BASED ON: "How quickly can a premium contractor monetize this lead?"

PRINCIPLES:
1. APPLICANT TYPE MATTERS MOST
   - Homeowner doing their own permit = gold (active buyer)
   - Custom/boutique builder = okay
   - LLC/investor = depends on property value
   - Production builder = trash (score 0)

2. FRESHNESS (days_old)
   - Roof leads go stale in 2 weeks
   - Foundation repair: 3-4 weeks
   - Pool leads stay warm for 2 months
   - Everything else: 30 days is the line

3. WEALTH = WILLINGNESS TO PAY
   - $1M+ property = pays for quality
   - $500-750k = solid
   - <$400k in DFW = price shopping

4. ABSENTEE IS CONTEXTUAL
   - Absentee + high value = vacation home, wealthy
   - Absentee + low value = landlord, will choose cheapest

5. MISSING DATA = ASSUME THE WORST

OUTPUT JSON:
{
  "score": 0-100,
  "tier": "A" (80+) | "B" (50-79) | "C" (<50),
  "reasoning": "2-3 sentences",
  "flags": ["concerns"],
  "ideal_contractor": "who should buy this",
  "contact_priority": "call" | "email" | "skip"
}"""


class DeepSeekScorer:
    """AI scorer using DeepSeek API."""

    API_BASE = "https://api.deepseek.com/v1"
    MODEL = "deepseek-chat"

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv('DEEPSEEK_API_KEY')
        if not self.api_key:
            logger.warning("No DeepSeek API key - scoring will fail")

    async def score_single(self, permit: PermitData, session: aiohttp.ClientSession) -> ScoredLead:
        if not self.api_key:
            return self._mark_for_retry(permit, "No API key")

        try:
            lead_data = {
                "project_description": permit.project_description,
                "permit_type": permit.permit_type,
                "owner_name": permit.owner_name,
                "market_value": permit.market_value,
                "days_old": permit.days_old,
                "is_absentee": permit.is_absentee,
                "city": permit.city,
            }

            prompt = f"Score this lead:\n\n{json.dumps(lead_data, indent=2)}"

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": self.MODEL,
                "messages": [
                    {"role": "system", "content": SALES_DIRECTOR_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 500,
                "temperature": 0.3
            }

            async with session.post(
                f"{self.API_BASE}/chat/completions",
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as response:
                response.raise_for_status()
                data = await response.json()

                content = data["choices"][0]["message"]["content"]
                result = self._parse_response(content)

                category = categorize_permit(permit)
                return ScoredLead(
                    permit=permit,
                    score=result.get("score", 50),
                    tier=result.get("tier", "B"),
                    reasoning=result.get("reasoning", ""),
                    flags=result.get("flags", []),
                    ideal_contractor=result.get("ideal_contractor", ""),
                    contact_priority=result.get("contact_priority", "email"),
                    category=category,
                    trade_group=get_trade_group(category),
                    scoring_method="ai"
                )

        except asyncio.TimeoutError:
            return self._mark_for_retry(permit, "Timeout")
        except Exception as e:
            return self._mark_for_retry(permit, str(e)[:50])

    def _parse_response(self, response: str) -> Dict[str, Any]:
        if "```json" in response:
            response = response.split("```json")[1].split("```")[0]
        elif "```" in response:
            response = response.split("```")[1].split("```")[0]

        match = re.search(r'\{[\s\S]*\}', response)
        if match:
            response = match.group(0)

        return json.loads(response.strip())

    def _mark_for_retry(self, permit: PermitData, error: str) -> ScoredLead:
        category = categorize_permit(permit)
        return ScoredLead(
            permit=permit,
            score=-1,
            tier="RETRY",
            reasoning=f"API failed: {error}",
            flags=["PENDING_RETRY"],
            category=category,
            trade_group=get_trade_group(category),
            contact_priority="skip",
            scoring_method="pending_retry"
        )

    async def score_batch(self, permits: List[PermitData], max_concurrent: int = 5) -> List[ScoredLead]:
        semaphore = asyncio.Semaphore(max_concurrent)

        async def score_with_semaphore(permit: PermitData, session: aiohttp.ClientSession):
            async with semaphore:
                await asyncio.sleep(0.2)  # Rate limiting
                return await self.score_single(permit, session)

        async with aiohttp.ClientSession() as session:
            tasks = [score_with_semaphore(p, session) for p in permits]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        scored = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                scored.append(self._mark_for_retry(permits[i], str(result)[:50]))
            else:
                scored.append(result)

        return scored


# =============================================================================
# DATABASE OPERATIONS
# =============================================================================

def setup_scored_leads_table(conn: sqlite3.Connection):
    """Create scored_leads table if it doesn't exist."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS scored_leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            permit_id TEXT,
            city TEXT,
            property_address TEXT,
            owner_name TEXT,
            market_value REAL,
            is_absentee INTEGER,
            days_old INTEGER,
            score INTEGER,
            tier TEXT,
            category TEXT,
            trade_group TEXT,
            reasoning TEXT,
            chain_of_thought TEXT,
            flags TEXT,
            ideal_contractor TEXT,
            contact_priority TEXT,
            scoring_method TEXT,
            scored_at TEXT,
            UNIQUE(permit_id, city)
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_scored_tier ON scored_leads(tier)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_scored_category ON scored_leads(category)")
    conn.commit()


def load_permits_for_scoring(conn: sqlite3.Connection, options: dict) -> List[PermitData]:
    """Load permits with enrichment data for scoring."""
    query = """
        SELECT
            p.permit_id, p.city, p.property_address,
            COALESCE(prop.owner_name, p.applicant_name, p.owner_name, 'Unknown') as owner_name,
            p.contractor_name,
            COALESCE(p.description, p.permit_type, '') as project_description,
            p.permit_type,
            COALESCE(prop.market_value, 0) as market_value,
            COALESCE(prop.is_absentee, 0) as is_absentee,
            p.issued_date,
            prop.county,
            prop.year_built,
            prop.square_feet
        FROM permits p
        LEFT JOIN properties prop ON p.property_address = prop.property_address
        LEFT JOIN scored_leads sl ON p.permit_id = sl.permit_id AND p.city = sl.city
        WHERE (prop.enrichment_status = 'success' OR prop.enrichment_status IS NULL)
    """

    conditions = []
    params = []

    # Exclude already scored unless --rescore
    if not options.get('rescore'):
        conditions.append("sl.id IS NULL")

    # Filter by city
    if options.get('city'):
        conditions.append("LOWER(p.city) = LOWER(?)")
        params.append(options['city'])

    if conditions:
        query += " AND " + " AND ".join(conditions)

    query += " ORDER BY p.issued_date DESC"

    if options.get('limit'):
        query += f" LIMIT {options['limit']}"

    cursor = conn.execute(query, params)

    permits = []
    today = date.today()

    for row in cursor:
        issued_date = None
        days_old = 0
        if row[9]:
            try:
                issued_date = datetime.strptime(row[9][:10], '%Y-%m-%d').date()
                days_old = (today - issued_date).days
            except (ValueError, TypeError):
                pass

        permit = PermitData(
            permit_id=row[0],
            city=row[1],
            property_address=row[2],
            owner_name=row[3] or "Unknown",
            contractor_name=row[4] or "",
            project_description=row[5] or "",
            permit_type=row[6] or "",
            market_value=float(row[7]) if row[7] else 0.0,
            is_absentee=bool(row[8]),
            issued_date=issued_date,
            days_old=days_old,
            county=row[10] or "",
            year_built=row[11],
            square_feet=row[12]
        )
        permits.append(permit)

    return permits


def save_scored_leads(conn: sqlite3.Connection, leads: List[ScoredLead]) -> Dict[str, int]:
    """Save scored leads to database."""
    counts = {'saved': 0, 'skipped': 0}

    for lead in leads:
        if lead.tier == "RETRY":
            counts['skipped'] += 1
            continue

        try:
            conn.execute("""
                INSERT OR REPLACE INTO scored_leads (
                    permit_id, city, property_address, owner_name, market_value,
                    is_absentee, days_old, score, tier, category, trade_group,
                    reasoning, chain_of_thought, flags, ideal_contractor,
                    contact_priority, scoring_method, scored_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                lead.permit.permit_id, lead.permit.city, lead.permit.property_address,
                lead.permit.owner_name, lead.permit.market_value, lead.permit.is_absentee,
                lead.permit.days_old, lead.score, lead.tier, lead.category, lead.trade_group,
                lead.reasoning, lead.chain_of_thought, json.dumps(lead.flags),
                lead.ideal_contractor, lead.contact_priority, lead.scoring_method,
                lead.scored_at.isoformat()
            ))
            counts['saved'] += 1
        except sqlite3.Error as e:
            logger.warning(f"Failed to save {lead.permit.permit_id}: {e}")
            counts['skipped'] += 1

    conn.commit()
    return counts


# =============================================================================
# EXPORT
# =============================================================================

def export_leads(leads: List[ScoredLead], output_dir: str = "exports") -> Dict[str, int]:
    """Export scored leads to CSV files by trade_group/category/tier."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    buckets: Dict[str, Dict[str, Dict[str, List[ScoredLead]]]] = {}

    for lead in leads:
        if lead.tier == "RETRY":
            continue

        trade_group = lead.trade_group
        category = lead.category
        tier = lead.tier.lower()

        if trade_group not in buckets:
            buckets[trade_group] = {}
        if category not in buckets[trade_group]:
            buckets[trade_group][category] = {"a": [], "b": [], "c": []}

        buckets[trade_group][category][tier].append(lead)

    counts = {}
    csv_fields = [
        "permit_id", "city", "property_address", "owner_name",
        "project_description", "market_value", "days_old", "is_absentee",
        "score", "tier", "category", "reasoning", "ideal_contractor", "contact_priority"
    ]

    for trade_group, categories in buckets.items():
        for category, tiers in categories.items():
            for tier, tier_leads in tiers.items():
                if tier_leads:
                    filepath = output_path / trade_group / category / f"tier_{tier}.csv"
                    filepath.parent.mkdir(parents=True, exist_ok=True)

                    with open(filepath, 'w', newline='', encoding='utf-8') as f:
                        writer = csv.DictWriter(f, fieldnames=csv_fields)
                        writer.writeheader()

                        for lead in tier_leads:
                            writer.writerow({
                                "permit_id": lead.permit.permit_id,
                                "city": lead.permit.city,
                                "property_address": lead.permit.property_address,
                                "owner_name": lead.permit.owner_name,
                                "project_description": lead.permit.project_description,
                                "market_value": lead.permit.market_value,
                                "days_old": lead.permit.days_old,
                                "is_absentee": lead.permit.is_absentee,
                                "score": lead.score,
                                "tier": lead.tier,
                                "category": lead.category,
                                "reasoning": lead.reasoning,
                                "ideal_contractor": lead.ideal_contractor,
                                "contact_priority": lead.contact_priority,
                            })

                    counts[str(filepath)] = len(tier_leads)

    return counts


# =============================================================================
# MAIN PIPELINE
# =============================================================================

async def score_leads_async(permits: List[PermitData], max_concurrent: int = 5) -> Tuple[List[ScoredLead], dict]:
    """Main scoring pipeline."""
    stats = {
        'total_input': len(permits),
        'discarded': 0,
        'scored': 0,
        'tier_a': 0,
        'tier_b': 0,
        'tier_c': 0,
        'retry': 0,
        'discard_reasons': {}
    }

    # Filter
    valid_permits = []
    for permit in permits:
        discard, reason = should_discard(permit)
        if discard:
            stats['discarded'] += 1
            reason_key = reason.split(":")[0] if ":" in reason else reason
            stats['discard_reasons'][reason_key] = stats['discard_reasons'].get(reason_key, 0) + 1
        else:
            valid_permits.append(permit)

    logger.info(f"Filtered: {stats['discarded']} discarded, {len(valid_permits)} valid")

    if not valid_permits:
        return [], stats

    # Score
    scorer = DeepSeekScorer()
    scored_leads = await scorer.score_batch(valid_permits, max_concurrent=max_concurrent)

    stats['scored'] = len(scored_leads)

    for lead in scored_leads:
        if lead.tier == "RETRY":
            stats['retry'] += 1
        elif lead.tier == "A":
            stats['tier_a'] += 1
        elif lead.tier == "B":
            stats['tier_b'] += 1
        else:
            stats['tier_c'] += 1

    return scored_leads, stats


def main():
    parser = argparse.ArgumentParser(description='Score leads using AI')
    parser.add_argument('--db', default=DEFAULT_DB_PATH, help='Path to SQLite database')
    parser.add_argument('--limit', type=int, help='Maximum permits to process')
    parser.add_argument('--city', help='Filter to specific city')
    parser.add_argument('--category', help='Filter to category (pool, hvac, roof, etc.)')
    parser.add_argument('--dry-run', action='store_true', help='Preview without scoring')
    parser.add_argument('--no-export', action='store_true', help='Skip CSV export')
    parser.add_argument('--export-dir', default='exports', help='Export directory')
    parser.add_argument('--concurrent', type=int, default=5, help='Max concurrent API calls')
    parser.add_argument('--rescore', action='store_true', help='Re-score already scored permits')
    args = parser.parse_args()

    # Check API key
    if not args.dry_run and not os.getenv('DEEPSEEK_API_KEY'):
        print("ERROR: DEEPSEEK_API_KEY environment variable not set")
        print("Set it with: export DEEPSEEK_API_KEY='your-key-here'")
        return 1

    # Connect to database
    conn = sqlite3.connect(args.db)
    setup_scored_leads_table(conn)

    # Load permits
    options = {
        'limit': args.limit,
        'city': args.city,
        'rescore': args.rescore,
    }
    permits = load_permits_for_scoring(conn, options)

    # Filter by category if specified
    if args.category:
        permits = [p for p in permits if categorize_permit(p) == args.category]

    print(f"\n=== LEAD SCORING ===")
    print(f"Database: {args.db}")
    print(f"Permits found: {len(permits)}")

    if not permits:
        print("No permits to score")
        conn.close()
        return 0

    if args.dry_run:
        print("\n--- DRY RUN ---")
        keep = []
        discard_counts = {}

        for permit in permits:
            discard, reason = should_discard(permit)
            if discard:
                reason_key = reason.split(":")[0] if ":" in reason else reason
                discard_counts[reason_key] = discard_counts.get(reason_key, 0) + 1
            else:
                keep.append(permit)

        if discard_counts:
            print("\nWould discard:")
            for reason, count in sorted(discard_counts.items(), key=lambda x: -x[1]):
                print(f"  {reason}: {count}")

        category_counts = {}
        for permit in keep:
            cat = categorize_permit(permit)
            category_counts[cat] = category_counts.get(cat, 0) + 1

        print("\nWould score by category:")
        for cat, count in sorted(category_counts.items(), key=lambda x: -x[1]):
            print(f"  {cat}: {count}")

        print(f"\nTotal: {len(permits)} input -> {len(keep)} to score")
        conn.close()
        return 0

    # Score
    print(f"\nScoring {len(permits)} permits...")
    scored_leads, stats = asyncio.run(score_leads_async(permits, max_concurrent=args.concurrent))

    # Results
    print("\n" + "=" * 50)
    print("SCORING RESULTS")
    print("=" * 50)
    print(f"Input:     {stats['total_input']}")
    print(f"Discarded: {stats['discarded']}")
    print(f"Scored:    {stats['scored']}")
    print(f"\nTier A (80+):   {stats['tier_a']}")
    print(f"Tier B (50-79): {stats['tier_b']}")
    print(f"Tier C (<50):   {stats['tier_c']}")
    if stats['retry']:
        print(f"Retry (failed): {stats['retry']}")

    if stats['discard_reasons']:
        print("\nDiscard reasons:")
        for reason, count in sorted(stats['discard_reasons'].items(), key=lambda x: -x[1]):
            print(f"  {reason}: {count}")

    # Save to database
    if scored_leads:
        db_counts = save_scored_leads(conn, scored_leads)
        print(f"\nSaved to database: {db_counts['saved']}")

    # Export
    if not args.no_export and scored_leads:
        print(f"\nExporting to {args.export_dir}/...")
        export_counts = export_leads(scored_leads, args.export_dir)
        for filepath, count in sorted(export_counts.items()):
            print(f"  {filepath}: {count}")

    conn.close()
    print("\nDone!")
    return 0


if __name__ == "__main__":
    exit(main())
