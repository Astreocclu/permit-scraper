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


if __name__ == "__main__":
    print("Adjacent Trade Router")
    print("Usage: python scripts/adjacent_trades.py [--limit N]")
