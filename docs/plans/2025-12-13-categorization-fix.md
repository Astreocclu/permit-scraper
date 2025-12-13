# Permit Categorization Fix

**Date**: 2025-12-13
**Status**: Implementing

## Problem

Permits were being miscategorized due to:
1. **Substring matching too loose**: "deck" matched "decking", "redeck" in roof permits
2. **Dict order = first match wins**: "driveway" in demolition descriptions matched "concrete" before "demolition"
3. **permit_type ignored as priority signal**: Even when permit_type clearly indicated "Roof" or "Demolition"

## Evidence

```
outdoor_living -> roof: 24 permits (roof permits with "decking" in description)
concrete -> foundation: 33 permits (Foundation Repair type miscategorized)
other -> hvac: 220 permits (Mechanical type not being caught)
```

## Solution

3-layer categorization:

### Layer 1: Permit Type Priority
Check `permit_type` field first - most reliable signal from the source system.

```python
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
```

### Layer 2: Word Boundary Keywords
Only apply word boundaries to problem keywords that cause false positives:

```python
WORD_BOUNDARY_KEYWORDS = {"deck", "demo"}
```

### Layer 3: Priority-Ordered Categories
Check categories in order of specificity:

1. demolition (often mentions what's being demolished)
2. new_construction
3. solar
4. roof (before outdoor_living)
5. pool (before outdoor_living)
6. outdoor_living
7. ... rest

## Validation

- Tested against 6,117 scored leads
- 496 would change (8.1%)
- All spot-checked transitions are improvements
- No regressions in plumbing/electrical/pool categorization

## Files Changed

- `scripts/score_leads.py` - Main categorization logic
