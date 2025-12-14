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
from dataclasses import dataclass, field, asdict
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv
load_dotenv()

import aiohttp


# =============================================================================
# ADDRESS NORMALIZATION
# =============================================================================

# Unit/apartment indicators to extract
# Note: patterns require word boundary or punctuation to avoid matching mid-word (e.g., "STEMMONS")
UNIT_PATTERNS = [
    r'\b(apt\.?|apartment)\s*#?\s*(\S+)',
    r'\b(unit)\s*#?\s*(\S+)',
    r'\b(suite)\s*#?\s*(\S+)',  # Full word only
    r'(?<![A-Za-z])(ste\.)\s*#?\s*(\S+)',  # Abbreviated requires period
    r'\b(bldg\.?|building)\s*#?\s*(\S+)',
    r'\b(fl\.?|floor)\s*#?\s*(\S+)',
    r'\b(rm\.?|room)\s*#?\s*(\S+)',
    r'#\s*(\d+\w*)',  # Standalone # numbers
]

# Street suffixes to standardize
STREET_SUFFIX_MAP = {
    'avenue': 'AVE', 'ave': 'AVE', 'av': 'AVE',
    'boulevard': 'BLVD', 'blvd': 'BLVD',
    'circle': 'CIR', 'cir': 'CIR',
    'court': 'CT', 'ct': 'CT',
    'drive': 'DR', 'dr': 'DR',
    'expressway': 'EXPY', 'expy': 'EXPY',
    'freeway': 'FWY', 'fwy': 'FWY',
    'highway': 'HWY', 'hwy': 'HWY',
    'lane': 'LN', 'ln': 'LN',
    'parkway': 'PKWY', 'pkwy': 'PKWY',
    'place': 'PL', 'pl': 'PL',
    'road': 'RD', 'rd': 'RD',
    'street': 'ST', 'st': 'ST', 'str': 'ST',
    'terrace': 'TER', 'ter': 'TER',
    'trail': 'TRL', 'trl': 'TRL',
    'way': 'WAY',
}

# Directional abbreviations
DIRECTIONAL_MAP = {
    'north': 'N', 'n': 'N',
    'south': 'S', 's': 'S',
    'east': 'E', 'e': 'E',
    'west': 'W', 'w': 'W',
    'northeast': 'NE', 'ne': 'NE',
    'northwest': 'NW', 'nw': 'NW',
    'southeast': 'SE', 'se': 'SE',
    'southwest': 'SW', 'sw': 'SW',
}


def normalize_address(raw_address: str, default_city: str = "") -> dict:
    """
    Normalize address to standard format.

    Returns dict with:
        - address: Normalized street address (uppercase, no unit/city/zip)
        - unit: Extracted apartment/suite/unit number
        - city: Extracted or default city (Title Case)
        - zip_code: Extracted ZIP code
    """
    if not raw_address:
        return {"address": "", "unit": "", "city": default_city.title(), "zip_code": ""}

    addr = raw_address.strip()
    unit = ""
    city = default_city
    zip_code = ""

    # Extract ZIP code (5 or 9 digit) - must be at end or after state abbrev
    # Pattern: either "TX 75201" or just "75201" at end of string
    zip_match = re.search(r'\b([A-Z]{2})\s+(\d{5})(?:-\d{4})?\s*$', addr, re.IGNORECASE)
    if zip_match:
        zip_code = zip_match.group(2)
        addr = addr[:zip_match.start()].strip()
    else:
        # Try ZIP at very end without state
        zip_match = re.search(r'\s(\d{5})(?:-\d{4})?\s*$', addr)
        if zip_match:
            zip_code = zip_match.group(1)
            addr = addr[:zip_match.start()].strip()

    # Extract city if it follows a comma
    # Pattern: "123 Main St, Dallas" or "123 Main St, Dallas, TX"
    city_match = re.search(r',\s*([A-Za-z\s]+?)(?:,|\s*$)', addr)
    if city_match:
        potential_city = city_match.group(1).strip()
        # Only treat as city if it's not a street suffix
        if potential_city.lower() not in STREET_SUFFIX_MAP:
            city = potential_city
            addr = addr[:city_match.start()]

    # Extract unit/apt/suite
    for pattern in UNIT_PATTERNS:
        match = re.search(pattern, addr, re.IGNORECASE)
        if match:
            if len(match.groups()) >= 2:
                unit = match.group(2).strip()
            else:
                unit = match.group(1).strip()
            addr = addr[:match.start()] + addr[match.end():]
            break

    # Clean up the address
    addr = addr.upper()

    # Standardize street suffixes
    words = addr.split()
    normalized_words = []
    for word in words:
        word_clean = word.strip('.,;:')
        word_lower = word_clean.lower()

        if word_lower in STREET_SUFFIX_MAP:
            normalized_words.append(STREET_SUFFIX_MAP[word_lower])
        elif word_lower in DIRECTIONAL_MAP:
            normalized_words.append(DIRECTIONAL_MAP[word_lower])
        else:
            normalized_words.append(word_clean)

    # Rebuild address
    addr = ' '.join(normalized_words)

    # Remove trailing punctuation
    addr = re.sub(r'[.,;:\s]+$', '', addr)

    # Collapse multiple spaces
    addr = re.sub(r'\s+', ' ', addr).strip()

    return {
        "address": addr,
        "unit": unit.upper() if unit else "",
        "city": city.title() if city else "",
        "zip_code": zip_code,
    }


import psycopg2
from psycopg2.extras import execute_values

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = None  # Use DATABASE_URL environment variable


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
# COMMERCIAL ENTITY DETECTION (Pre-Score Filter)
# =============================================================================

COMMERCIAL_ENTITY_PATTERNS = [
    # Business entity suffixes (word boundary required)
    r'\b(llc|l\.l\.c|inc|incorporated|corp|corporation|ltd|limited|lp|l\.p)\b',
    r'\b(properties|investments|holdings|partners|enterprises|ventures)\b',
    r'\b(development|developers|construction\s+co|builders\s+inc|building\s+co)\b',
    r'\b(real\s+estate|realty|investments)\b',

    # Government/municipal (word boundary required)
    r'\b(city\s+of|county\s+of|state\s+of)\b',
    r'\bcounty\b',  # Catches "X County" pattern
    r'\b(isd|school\s+district|municipality|municipal|government)\b',
    r'\b(dept\s+of|department\s+of)\b',

    # Institutional (word boundary required)
    r'\b(church|temple|mosque|synagogue)\b',
    r'\b(hospital|clinic|medical\s+center)\b',
    r'\b(university|college|foundation)\b',
    r'\bnon-?profit\b',
    r'\b(association|society)\b',

    # Property management / multi-family
    r'\b(apartments?|apt)\b',
    r'\b(multifamily|multi-family)\b',
    r'\b(property\s+management|leasing|residential\s+services)\b',
]

# Compile patterns for performance
_COMMERCIAL_PATTERNS_COMPILED = [re.compile(p, re.IGNORECASE) for p in COMMERCIAL_ENTITY_PATTERNS]


def is_commercial_entity(name: str) -> bool:
    """
    Check if name indicates a commercial entity that should be filtered pre-score.

    This catches:
    - LLCs, Corps, Inc (business entities)
    - Government/municipal (City of X, County, ISD)
    - Institutional (churches, hospitals, universities)
    - Multi-family/apartments
    - Production builders (via is_production_builder)

    Returns True if commercial (should filter), False if residential (keep).
    """
    if not name or name in ("Unknown", ""):
        return False

    # Check production builders first (reuse existing function)
    if is_production_builder(name):
        return True

    # Check commercial patterns
    for pattern in _COMMERCIAL_PATTERNS_COMPILED:
        if pattern.search(name):
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

# Positive indicators that override "demolition" being junk
REMODEL_INDICATORS = [
    "addition", "remodel", "rebuild", "new construction",
    "second story", "second-story", "2nd story", "expansion",
    "renovate", "renovation", "convert", "build new",
]


def is_junk_project(description: str) -> bool:
    """Check if project description indicates a junk/low-value project."""
    if not description:
        return False
    desc_lower = description.lower()

    for junk in JUNK_PROJECTS:
        if junk in desc_lower:
            # Special case: demolition + remodel indicators = not junk
            if junk in ["demolition", "demo permit"]:
                if any(indicator in desc_lower for indicator in REMODEL_INDICATORS):
                    continue  # Skip this junk keyword, it's part of a real project
            return True

    return False


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class PermitData:
    """Normalized permit data for scoring."""
    permit_id: str
    city: str
    property_address: str  # Original raw address
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
    # Normalized address fields
    normalized_address: str = ""  # Clean: "1234 MAIN ST"
    unit: str = ""  # Extracted: "APT 101", "STE 200"
    zip_code: str = ""  # Extracted: "75001"


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

    # Check for commercial entity FIRST (catches LLCs, govt, churches, apartments, etc.)
    if is_commercial_entity(permit.owner_name):
        return True, f"Commercial entity: {permit.owner_name[:50]}"

    # Production builder in description (backup check)
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

# Layer 1: permit_type takes priority (most reliable signal from source system)
PERMIT_TYPE_PRIORITY = {
    "demolition": ["demolition", "demo"],
    "solar": ["solar", "photovoltaic", "pv"],
    "outdoor_living": ["patio", "carport", "pergola", "deck", "porch", "cover"],
    "roof": ["roof", "roofing", "re-roof", "reroof"],
    "foundation": ["foundation"],
    "fence": ["fence"],
    "pool": ["pool", "swimming"],
    "electrical": ["electrical"],
    "plumbing": ["plumbing"],
    "hvac": ["mechanical", "hvac"],
}

# Keywords that need word boundary matching to prevent false positives
# e.g., "deck" should not match "decking" or "redeck" in roof permits
WORD_BOUNDARY_KEYWORDS = {"deck", "demo"}

# Layer 2: Priority-ordered categories (order matters - check specific first)
CATEGORY_KEYWORDS = [
    ("demolition", ["demo", "demolition", "tear down"]),
    ("new_construction", ["new home", "new construction", "new sfd", "custom home"]),
    ("solar", ["solar", "photovoltaic", "pv system"]),
    ("roof", ["roof", "roofing", "re-roof", "reroof", "shingle", "metal roof"]),
    ("pool", ["pool", "swim", "spa", "hot tub", "gunite", "fiberglass pool"]),
    ("outdoor_living", ["patio", "deck", "pergola", "outdoor kitchen", "cabana",
                        "gazebo", "arbor", "screen enclosure", "covered patio",
                        "shade structure", "pavilion", "outdoor living", "porch"]),
    ("fence", ["fence", "fencing", "privacy fence", "iron fence", "wood fence"]),
    ("siding", ["siding", "hardie", "stucco", "exterior finish"]),
    ("windows", ["window", "door replacement", "sliding door", "french door"]),
    ("concrete", ["driveway", "sidewalk", "concrete", "flatwork", "stamped concrete", "pavers"]),
    ("hvac", ["hvac", "air condition", "ac unit", "furnace", "heat pump", "ductwork", "mini split"]),
    ("plumbing", ["plumb", "water heater", "tankless", "water line", "gas line", "repipe", "sewer"]),
    ("electrical", ["electric", "panel", "outlet", "circuit", "wire", "ev charger", "generator"]),
    ("foundation", ["foundation", "pier", "underpinning", "slab repair", "leveling"]),
    ("addition", ["addition", "room addition", "add on", "expansion"]),
    ("remodel", ["remodel", "renovation", "kitchen remodel", "bath remodel"]),
    ("temporary", ["temporary", "temp permit"]),
    ("signage", ["sign permit", "signage", "banner"]),
]

COMMERCIAL_INDICATORS = [
    "commercial", "office", "retail", "restaurant", "warehouse", "industrial",
    "tenant", "suite", "shopping", "plaza", "mall", "store", "business",
    "corp", "inc.", "llc", "church", "school", "hospital", "medical", "clinic"
]


def is_commercial_property(permit: PermitData) -> bool:
    text = f"{permit.project_description} {permit.owner_name} {permit.property_address}".lower()
    return any(indicator in text for indicator in COMMERCIAL_INDICATORS)


def categorize_permit(permit: PermitData) -> str:
    """Categorize permit using 3-layer approach: permit_type priority, word boundaries, category order."""
    desc = (permit.project_description + " " + permit.permit_type).lower()
    ptype = permit.permit_type.lower() if permit.permit_type else ""
    is_commercial = is_commercial_property(permit)

    # Layer 1: Check permit_type first (most reliable signal)
    for category, type_keywords in PERMIT_TYPE_PRIORITY.items():
        if any(kw in ptype for kw in type_keywords):
            if is_commercial and category in ["pool", "roof", "hvac", "plumbing", "electrical"]:
                return f"commercial_{category}"
            return category

    # Layer 2: Keyword matching in priority order
    for category, keywords in CATEGORY_KEYWORDS:
        for kw in keywords:
            # Use word boundary only for problematic keywords
            if kw in WORD_BOUNDARY_KEYWORDS:
                pattern = rf'\b{re.escape(kw)}\b'
                if re.search(pattern, desc):
                    if is_commercial and category in ["pool", "roof", "hvac", "plumbing", "electrical"]:
                        return f"commercial_{category}"
                    return category
            else:
                if kw in desc:
                    if is_commercial and category in ["pool", "roof", "hvac", "plumbing", "electrical"]:
                        return f"commercial_{category}"
                    return category

    return "other"


def get_trade_group(category: str) -> str:
    return TRADE_GROUPS.get(category, "other")


# =============================================================================
# AI SCORING (DeepSeek)
# =============================================================================

# Median days_old by category (for leads with unknown freshness)
CATEGORY_MEDIAN_DAYS = {
    "addition": 21,
    "commercial_electrical": 4,
    "commercial_hvac": 4,
    "commercial_plumbing": 4,
    "commercial_pool": 5,
    "commercial_roof": 1,
    "concrete": 6,
    "demolition": 2,
    "electrical": 3,
    "fence": 14,
    "foundation": 43,
    "hvac": 5,
    "new_construction": 33,
    "other": 8,
    "outdoor_living": 22,
    "plumbing": 4,
    "pool": 26,
    "remodel": 18,
    "roof": 5,
    "siding": 6,
    "signage": 1,
    "solar": 14,
    "temporary": 1,
    "windows": 49,
}
CATEGORY_MEDIAN_DAYS_DEFAULT = 7

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
            # Get category first to determine median freshness if needed
            category = categorize_permit(permit)

            # Use median days_old for category if freshness is unknown
            days_old_for_ai = permit.days_old
            if permit.days_old == -1:
                days_old_for_ai = CATEGORY_MEDIAN_DAYS.get(category, CATEGORY_MEDIAN_DAYS_DEFAULT)

            lead_data = {
                "project_description": permit.project_description,
                "permit_type": permit.permit_type,
                "owner_name": permit.owner_name,
                "market_value": permit.market_value,
                "days_old": days_old_for_ai,
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

                # Override tier based on priority: D (score=0) > U (no date) > A/B/C (normal)
                score = result.get("score", 50)
                tier = result.get("tier", "B")
                flags = result.get("flags", [])

                # Tier D: AI gave score 0 (confirmed garbage)
                if score == 0:
                    tier = "D"
                    flags = flags + ["ai_confirmed_garbage"]
                # Tier U: Can't verify freshness (no date)
                elif permit.days_old == -1:
                    tier = "U"
                    flags = flags + ["unverified_freshness"]
                # Normal tier assignment based on score
                elif score >= 80:
                    tier = "A"
                elif score >= 50:
                    tier = "B"
                else:
                    tier = "C"

                return ScoredLead(
                    permit=permit,
                    score=score,
                    tier=tier,
                    reasoning=result.get("reasoning", ""),
                    flags=flags,
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

def get_db_connection():
    """Get PostgreSQL connection from DATABASE_URL."""
    url = os.environ.get('DATABASE_URL')
    if not url:
        raise ValueError("DATABASE_URL environment variable not set")
    return psycopg2.connect(url)


def load_permits_for_scoring(conn, options: dict) -> List[PermitData]:
    """Load permits with enrichment data for scoring.

    Only loads permits that have been successfully enriched (have CAD data).
    """
    query = """
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
        JOIN leads_property prop ON p.property_address = prop.property_address
        LEFT JOIN clients_scoredlead sl ON p.id = sl.permit_id
        WHERE prop.enrichment_status = 'success'
          AND p.processing_bin = 'active'
    """

    conditions = []
    params = []

    # Exclude already scored unless --rescore
    if not options.get('rescore'):
        conditions.append("sl.id IS NULL")

    # Filter by city
    if options.get('city'):
        conditions.append("LOWER(p.city) = LOWER(%s)")
        params.append(options['city'])

    if conditions:
        query += " AND " + " AND ".join(conditions)

    query += " ORDER BY p.issued_date DESC NULLS LAST"

    if options.get('limit'):
        query += f" LIMIT {options['limit']}"

    with conn.cursor() as cur:
        cur.execute(query, params)
        rows = cur.fetchall()

    permits = []
    today = date.today()

    for row in rows:
        pg_id = row[0]  # PostgreSQL id for FK
        issued_date = None
        days_old = -1  # Sentinel: unknown freshness (will become tier "U")
        if row[10]:  # issued_date is now at index 10
            try:
                if isinstance(row[10], date):
                    issued_date = row[10]
                else:
                    issued_date = datetime.strptime(str(row[10])[:10], '%Y-%m-%d').date()
                days_old = (today - issued_date).days
            except (ValueError, TypeError):
                pass

        # Normalize address at load time
        raw_address = row[3] or ""
        city_from_db = row[2] or ""
        addr_parts = normalize_address(raw_address, default_city=city_from_db)

        permit = PermitData(
            permit_id=row[1],
            city=addr_parts["city"] or city_from_db.title(),  # Use extracted or DB city
            property_address=raw_address,  # Keep original
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
        # Store pg_id as an attribute for later FK lookup
        permit._pg_id = pg_id
        permits.append(permit)

    return permits


def save_scored_leads(conn, leads: List[ScoredLead]) -> Dict[str, int]:
    """Save scored leads to PostgreSQL clients_scoredlead table."""
    counts = {'saved': 0, 'skipped': 0}

    for lead in leads:
        if lead.tier == "RETRY":
            counts['skipped'] += 1
            continue

        try:
            # Get the PostgreSQL permit_id FK
            pg_permit_id = getattr(lead.permit, '_pg_id', None)
            if not pg_permit_id:
                logger.warning(f"No PostgreSQL ID for {lead.permit.permit_id}")
                counts['skipped'] += 1
                continue

            is_commercial = lead.trade_group == 'commercial'

            # Check if property exists in leads_property (for FK constraint)
            cad_property_id = None
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT property_address FROM leads_property WHERE property_address = %s",
                    (lead.permit.property_address,)
                )
                if cur.fetchone():
                    cad_property_id = lead.permit.property_address

            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO clients_scoredlead (
                        permit_id, category, trade_group, is_commercial, score, tier,
                        reasoning, chain_of_thought, flags, ideal_contractor,
                        contact_priority, scoring_method, scored_at, status, sold_to,
                        cad_property_id
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (permit_id) DO UPDATE SET
                        category = EXCLUDED.category,
                        trade_group = EXCLUDED.trade_group,
                        score = EXCLUDED.score,
                        tier = EXCLUDED.tier,
                        reasoning = EXCLUDED.reasoning,
                        ideal_contractor = EXCLUDED.ideal_contractor,
                        contact_priority = EXCLUDED.contact_priority,
                        scored_at = EXCLUDED.scored_at
                """, (
                    pg_permit_id,
                    (lead.category or 'other')[:50],
                    (lead.trade_group or 'other')[:50],
                    is_commercial,
                    lead.score,
                    (lead.tier or 'C')[:5],
                    lead.reasoning or '',
                    lead.chain_of_thought or '',
                    json.dumps(lead.flags),
                    (lead.ideal_contractor or '')[:200],
                    (lead.contact_priority or 'email')[:20],
                    (lead.scoring_method or 'ai')[:20],
                    lead.scored_at,
                    'available',
                    '',
                    cad_property_id
                ))
            conn.commit()  # Commit each save individually
            counts['saved'] += 1
        except psycopg2.Error as e:
            conn.rollback()  # Rollback failed transaction
            logger.warning(f"Failed to save {lead.permit.permit_id}: {e}")
            counts['skipped'] += 1

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
            buckets[trade_group][category] = {"a": [], "b": [], "c": [], "u": []}

        buckets[trade_group][category][tier].append(lead)

    counts = {}
    csv_fields = [
        "permit_id", "city", "normalized_address", "unit", "zip_code",
        "property_address", "owner_name",
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
                                "normalized_address": lead.permit.normalized_address,
                                "unit": lead.permit.unit,
                                "zip_code": lead.permit.zip_code,
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
        'tier_d': 0,
        'tier_u': 0,
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
        elif lead.tier == "D":
            stats['tier_d'] += 1
        elif lead.tier == "U":
            stats['tier_u'] += 1
        else:
            stats['tier_c'] += 1

    return scored_leads, stats


def main():
    parser = argparse.ArgumentParser(description='Score leads using AI')
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

    # Connect to PostgreSQL
    try:
        conn = get_db_connection()
    except ValueError as e:
        print(f"ERROR: {e}")
        return 1

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
    print(f"Database: PostgreSQL (from DATABASE_URL)")
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
    print(f"Tier D (garbage): {stats['tier_d']}")
    print(f"Tier U (unverified): {stats['tier_u']}")
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
