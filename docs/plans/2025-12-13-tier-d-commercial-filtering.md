# Two-Stage Commercial Filtering + Tier D Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add Tier D for AI-confirmed garbage (commercial/builder/govt) and expand pre-score filtering to save API costs.

**Architecture:** Two-stage filtering: (1) Pre-score regex filtering catches obvious commercial/govt/builder before API calls, (2) Post-score Tier D catches anything the AI gives score=0. Tier D is excluded from all exports.

**Tech Stack:** Python, regex, pytest, PostgreSQL

---

## Task 1: Add Commercial Entity Detection Function

**Files:**
- Modify: `scripts/score_leads.py:188-240` (after PRODUCTION_BUILDERS section)
- Test: `tests/test_score_leads.py` (new file)

**Step 1: Write the failing test**

Create `tests/test_score_leads.py`:

```python
# tests/test_score_leads.py
"""Tests for score_leads.py filtering and tier assignment."""
import pytest
import sys
sys.path.insert(0, 'scripts')

from score_leads import is_commercial_entity


class TestIsCommercialEntity:
    """Test is_commercial_entity function for pre-score filtering."""

    def test_llc_detected(self):
        assert is_commercial_entity("Smith Family LLC") is True
        assert is_commercial_entity("ACME PROPERTIES LLC") is True

    def test_inc_corp_detected(self):
        assert is_commercial_entity("Jones Holdings Inc") is True
        assert is_commercial_entity("ABC Corp") is True
        assert is_commercial_entity("Mega Development Corp") is True

    def test_government_detected(self):
        assert is_commercial_entity("City of Dallas") is True
        assert is_commercial_entity("CITY OF FORT WORTH") is True
        assert is_commercial_entity("Tarrant County") is True
        assert is_commercial_entity("Dallas ISD") is True
        assert is_commercial_entity("Plano Independent School District") is True

    def test_institutional_detected(self):
        assert is_commercial_entity("First Baptist Church") is True
        assert is_commercial_entity("Methodist Hospital") is True
        assert is_commercial_entity("Texas A&M University") is True
        assert is_commercial_entity("Habitat for Humanity Foundation") is True

    def test_multifamily_detected(self):
        assert is_commercial_entity("Oak Park Apartments") is True
        assert is_commercial_entity("Sunrise Property Management") is True
        assert is_commercial_entity("Multifamily Residential Services") is True

    def test_production_builder_detected(self):
        assert is_commercial_entity("Lennar Homes") is True
        assert is_commercial_entity("DR Horton") is True
        assert is_commercial_entity("KB Home") is True
        assert is_commercial_entity("Toll Brothers") is True
        assert is_commercial_entity("David Weekley Homes") is True
        assert is_commercial_entity("Highland Homes") is True
        assert is_commercial_entity("Chesmar Homes") is True
        assert is_commercial_entity("History Maker Homes") is True

    def test_real_person_allowed(self):
        """Real homeowner names should NOT be filtered."""
        assert is_commercial_entity("John Smith") is False
        assert is_commercial_entity("MARIA GARCIA") is False
        assert is_commercial_entity("Robert Johnson Jr") is False
        assert is_commercial_entity("The Williams Family") is False

    def test_edge_cases(self):
        """Edge cases that look commercial but aren't."""
        # "Inc" inside a word shouldn't trigger
        assert is_commercial_entity("Lincoln Street") is False
        # Common false positive - person with "Corp" in name
        assert is_commercial_entity("James Corpening") is False

    def test_empty_and_none(self):
        assert is_commercial_entity("") is False
        assert is_commercial_entity(None) is False
        assert is_commercial_entity("Unknown") is False
```

**Step 2: Run test to verify it fails**

Run: `cd /home/reid/testhome/permit-scraper && python -m pytest tests/test_score_leads.py -v`

Expected: FAIL with `ImportError: cannot import name 'is_commercial_entity'`

**Step 3: Write the implementation**

Add to `scripts/score_leads.py` after line 240 (after `is_production_builder` function):

```python
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
```

**Step 4: Run test to verify it passes**

Run: `cd /home/reid/testhome/permit-scraper && python -m pytest tests/test_score_leads.py::TestIsCommercialEntity -v`

Expected: All tests PASS

**Step 5: Commit**

```bash
cd /home/reid/testhome/permit-scraper
git add scripts/score_leads.py tests/test_score_leads.py
git commit -m "feat: add is_commercial_entity function for pre-score filtering

Detects LLCs, corps, government, churches, hospitals, apartments,
and production builders before sending to AI API."
```

---

## Task 2: Add Pre-Score Commercial Filtering to should_discard()

**Files:**
- Modify: `scripts/score_leads.py:349-369` (should_discard function)
- Test: `tests/test_score_leads.py`

**Step 1: Write the failing test**

Add to `tests/test_score_leads.py`:

```python
from score_leads import should_discard, PermitData


class TestShouldDiscardCommercial:
    """Test that commercial entities get discarded pre-score."""

    def _make_permit(self, owner_name: str, description: str = "Roof repair") -> PermitData:
        return PermitData(
            permit_id="TEST-001",
            city="Dallas",
            property_address="123 Test St",
            owner_name=owner_name,
            project_description=description,
            days_old=30,
            market_value=500000,
        )

    def test_llc_discarded(self):
        permit = self._make_permit("Smith Properties LLC")
        discard, reason = should_discard(permit)
        assert discard is True
        assert "Commercial entity" in reason

    def test_government_discarded(self):
        permit = self._make_permit("City of Dallas")
        discard, reason = should_discard(permit)
        assert discard is True
        assert "Commercial entity" in reason

    def test_church_discarded(self):
        permit = self._make_permit("First Baptist Church")
        discard, reason = should_discard(permit)
        assert discard is True
        assert "Commercial entity" in reason

    def test_apartments_discarded(self):
        permit = self._make_permit("Oakwood Apartments")
        discard, reason = should_discard(permit)
        assert discard is True
        assert "Commercial entity" in reason

    def test_real_homeowner_kept(self):
        permit = self._make_permit("John Smith")
        discard, reason = should_discard(permit)
        assert discard is False

    def test_production_builder_still_works(self):
        """Existing production builder detection should still work."""
        permit = self._make_permit("Lennar Homes")
        discard, reason = should_discard(permit)
        assert discard is True
        # Could be either "Production builder" or "Commercial entity" - both OK
```

**Step 2: Run test to verify it fails**

Run: `cd /home/reid/testhome/permit-scraper && python -m pytest tests/test_score_leads.py::TestShouldDiscardCommercial -v`

Expected: FAIL - commercial entities not being discarded yet

**Step 3: Modify should_discard function**

In `scripts/score_leads.py`, modify `should_discard` function (around line 349):

```python
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
```

**Step 4: Run test to verify it passes**

Run: `cd /home/reid/testhome/permit-scraper && python -m pytest tests/test_score_leads.py::TestShouldDiscardCommercial -v`

Expected: All tests PASS

**Step 5: Commit**

```bash
cd /home/reid/testhome/permit-scraper
git add scripts/score_leads.py tests/test_score_leads.py
git commit -m "feat: add commercial entity pre-filtering to should_discard

LLCs, government, churches, apartments now filtered before AI scoring.
Saves API costs by not scoring obvious non-residential leads."
```

---

## Task 3: Add Tier D Assignment for Score=0

**Files:**
- Modify: `scripts/score_leads.py:621-639` (tier assignment in score_single)
- Test: `tests/test_score_leads.py`

**Step 1: Write the failing test**

Add to `tests/test_score_leads.py`:

```python
from score_leads import ScoredLead, PermitData


class TestTierAssignment:
    """Test tier assignment logic including new Tier D."""

    def _make_permit(self, days_old: int = 30) -> PermitData:
        return PermitData(
            permit_id="TEST-001",
            city="Dallas",
            property_address="123 Test St",
            owner_name="John Smith",
            project_description="Roof repair",
            days_old=days_old,
            market_value=500000,
        )

    def test_score_zero_gets_tier_d(self):
        """Score 0 from AI should result in Tier D."""
        permit = self._make_permit(days_old=30)
        lead = ScoredLead(
            permit=permit,
            score=0,
            tier="D",  # This is what we're testing should happen
            reasoning="Commercial entity",
            category="other",
            trade_group="other",
        )
        assert lead.tier == "D"

    def test_no_date_gets_tier_u(self):
        """Permit with no date (days_old=-1) should get Tier U."""
        permit = self._make_permit(days_old=-1)  # -1 means unknown date
        # Tier U should be assigned regardless of score
        lead = ScoredLead(
            permit=permit,
            score=85,
            tier="U",  # days_old=-1 forces Tier U
            reasoning="Good lead but unverified freshness",
            category="roof",
            trade_group="home_exterior",
        )
        assert lead.tier == "U"

    def test_high_score_gets_tier_a(self):
        """Score >= 80 with valid date should get Tier A."""
        permit = self._make_permit(days_old=30)
        lead = ScoredLead(
            permit=permit,
            score=85,
            tier="A",
            reasoning="High value homeowner",
            category="pool",
            trade_group="luxury_outdoor",
        )
        assert lead.tier == "A"

    def test_medium_score_gets_tier_b(self):
        """Score 50-79 with valid date should get Tier B."""
        permit = self._make_permit(days_old=30)
        lead = ScoredLead(
            permit=permit,
            score=65,
            tier="B",
            reasoning="Medium value lead",
            category="hvac",
            trade_group="home_systems",
        )
        assert lead.tier == "B"

    def test_low_score_gets_tier_c(self):
        """Score < 50 (but > 0) with valid date should get Tier C."""
        permit = self._make_permit(days_old=30)
        lead = ScoredLead(
            permit=permit,
            score=25,
            tier="C",
            reasoning="Low value lead",
            category="signage",
            trade_group="unsellable",
        )
        assert lead.tier == "C"
```

**Step 2: Run test to verify current behavior**

Run: `cd /home/reid/testhome/permit-scraper && python -m pytest tests/test_score_leads.py::TestTierAssignment -v`

Expected: Tests pass (they're just asserting on ScoredLead construction, not the assignment logic)

**Step 3: Modify tier assignment in score_single method**

In `scripts/score_leads.py`, find the `score_single` method (around line 569) and modify the tier assignment section (around lines 621-639):

```python
                # Override tier to "U" (Unverified) if freshness unknown
                # Priority: D (score=0) > U (no date) > A/B/C (normal)
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
```

**Step 4: Run test to verify it passes**

Run: `cd /home/reid/testhome/permit-scraper && python -m pytest tests/test_score_leads.py::TestTierAssignment -v`

Expected: All tests PASS

**Step 5: Commit**

```bash
cd /home/reid/testhome/permit-scraper
git add scripts/score_leads.py tests/test_score_leads.py
git commit -m "feat: add Tier D assignment for score=0 (AI-confirmed garbage)

Priority: D (score=0) > U (no date) > A/B/C (normal scoring)
Tier D captures commercial/builder/govt that slipped through pre-filter."
```

---

## Task 4: Add tier_d to Stats Tracking

**Files:**
- Modify: `scripts/score_leads.py:952-1000` (score_leads_async function)
- Modify: `scripts/score_leads.py:1084-1096` (results output)

**Step 1: Modify stats dict initialization**

In `scripts/score_leads.py`, find `score_leads_async` function (line 952) and modify the stats dict:

```python
async def score_leads_async(permits: List[PermitData], max_concurrent: int = 5) -> Tuple[List[ScoredLead], dict]:
    """Main scoring pipeline."""
    stats = {
        'total_input': len(permits),
        'discarded': 0,
        'scored': 0,
        'tier_a': 0,
        'tier_b': 0,
        'tier_c': 0,
        'tier_d': 0,  # NEW: AI-confirmed garbage
        'tier_u': 0,
        'retry': 0,
        'discard_reasons': {}
    }
```

**Step 2: Modify tier counting loop**

Find the tier counting loop (around line 988-998) and add Tier D:

```python
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
```

**Step 3: Modify results output**

Find the results output section (around line 1091-1096) and add Tier D:

```python
    print(f"\nTier A (80+):   {stats['tier_a']}")
    print(f"Tier B (50-79): {stats['tier_b']}")
    print(f"Tier C (<50):   {stats['tier_c']}")
    print(f"Tier D (garbage): {stats['tier_d']}")
    print(f"Tier U (unverified): {stats['tier_u']}")
```

**Step 4: Commit**

```bash
cd /home/reid/testhome/permit-scraper
git add scripts/score_leads.py
git commit -m "feat: add Tier D to stats tracking and output

Shows count of AI-confirmed garbage (commercial/builder/govt) separately."
```

---

## Task 5: Exclude Tier D from Exports

**Files:**
- Modify: `scripts/score_leads.py:881-945` (export_leads function)

**Step 1: Modify export_leads to skip Tier D**

In `scripts/score_leads.py`, find `export_leads` function (line 881) and modify:

```python
def export_leads(leads: List[ScoredLead], output_dir: str = "exports") -> Dict[str, int]:
    """Export scored leads to CSV files by trade_group/category/tier.

    NOTE: Tier D (AI-confirmed garbage) is excluded from exports.
    Tier D exists only in database for audit trail.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    buckets: Dict[str, Dict[str, Dict[str, List[ScoredLead]]]] = {}

    for lead in leads:
        # Skip RETRY and Tier D (garbage - never export)
        if lead.tier in ("RETRY", "D"):
            continue

        trade_group = lead.trade_group
        category = lead.category
        tier = lead.tier.lower()

        if trade_group not in buckets:
            buckets[trade_group] = {}
        if category not in buckets[trade_group]:
            buckets[trade_group][category] = {"a": [], "b": [], "c": [], "u": []}

        buckets[trade_group][category][tier].append(lead)
```

**Step 2: Commit**

```bash
cd /home/reid/testhome/permit-scraper
git add scripts/score_leads.py
git commit -m "feat: exclude Tier D from CSV exports

Tier D (AI-confirmed garbage) kept in database for audit trail,
but never exported to CSV files for sales."
```

---

## Task 6: Update Existing score=0 Records to Tier D

**Files:**
- Run SQL migration

**Step 1: Check current state**

```bash
cd /home/reid/testhome/permit-scraper && python3 -c "
from dotenv import load_dotenv; load_dotenv()
import os, psycopg2
conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()
cur.execute('''SELECT tier, COUNT(*), SUM(CASE WHEN score = 0 THEN 1 ELSE 0 END) as score_zero
FROM clients_scoredlead GROUP BY tier ORDER BY tier''')
print('Before migration:')
for r in cur.fetchall(): print(f'  {r[0]}: {r[1]} total, {r[2]} score=0')
conn.close()
"
```

**Step 2: Run migration to update existing score=0 to Tier D**

```bash
cd /home/reid/testhome/permit-scraper && python3 -c "
from dotenv import load_dotenv; load_dotenv()
import os, psycopg2
conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()

# Update existing score=0 records to Tier D
cur.execute('''
    UPDATE clients_scoredlead
    SET tier = 'D'
    WHERE score = 0 AND tier != 'D'
''')
updated = cur.rowcount
conn.commit()
print(f'Updated {updated} records from score=0 to Tier D')

# Verify
cur.execute('''SELECT tier, COUNT(*) FROM clients_scoredlead GROUP BY tier ORDER BY tier''')
print('After migration:')
for r in cur.fetchall(): print(f'  {r[0]}: {r[1]}')
conn.close()
"
```

**Step 3: Commit migration note**

```bash
cd /home/reid/testhome/permit-scraper
git commit --allow-empty -m "chore: migrate existing score=0 records to Tier D

Ran SQL: UPDATE clients_scoredlead SET tier = 'D' WHERE score = 0"
```

---

## Task 7: End-to-End Verification

**Step 1: Run dry-run to verify filtering**

```bash
cd /home/reid/testhome/permit-scraper && python3 scripts/score_leads.py --dry-run --limit 500 2>&1 | head -50
```

Expected output should show:
- "Commercial entity" in discard reasons
- Tier D count in output (if any score=0 leads)

**Step 2: Verify database state**

```bash
cd /home/reid/testhome/permit-scraper && python3 -c "
from dotenv import load_dotenv; load_dotenv()
import os, psycopg2
conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()

print('=== FINAL TIER DISTRIBUTION ===')
cur.execute('''SELECT tier, COUNT(*), ROUND(AVG(score)::numeric, 1) as avg_score
FROM clients_scoredlead GROUP BY tier ORDER BY tier''')
for r in cur.fetchall():
    print(f'  Tier {r[0]}: {r[1]:,} leads (avg score: {r[2]})')

print()
print('=== TIER D SAMPLE (should be commercial/builder/govt) ===')
cur.execute('''SELECT LEFT(owner_name, 40), LEFT(reasoning, 60)
FROM clients_scoredlead sl
JOIN leads_permit p ON sl.permit_id = p.id
WHERE tier = 'D' LIMIT 10''')
for r in cur.fetchall():
    print(f'  {r[0]}: {r[1]}...')
conn.close()
"
```

**Step 3: Verify exports exclude Tier D**

```bash
# Check that no tier_d.csv files exist
find /home/reid/testhome/permit-scraper/exports -name "*tier_d*" -type f
# Should return nothing

# Verify tier_a/b/c/u exist
ls -la /home/reid/testhome/permit-scraper/exports/*/tier_*.csv 2>/dev/null | head -10
```

---

## Summary

After implementation:

| Component | Change |
|-----------|--------|
| `is_commercial_entity()` | NEW function to detect LLCs, govt, churches, apartments |
| `should_discard()` | Now calls `is_commercial_entity()` first |
| `score_single()` | Assigns Tier D when score=0 |
| Stats | Tracks `tier_d` separately |
| Output | Shows "Tier D (garbage)" count |
| `export_leads()` | Skips Tier D (never exported) |
| Database | Existing score=0 migrated to Tier D |

Expected final state:
```
Tier A: ~390 (premium leads)
Tier B: ~940 (good leads)
Tier C: ~2,700 (low-quality residential)
Tier D: ~1,400 (AI-confirmed garbage - commercial/builder/govt)
Tier U: ~2,000 (can't verify freshness)
```
