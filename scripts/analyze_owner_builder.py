#!/usr/bin/env python3
"""
Owner-Builder Analysis Report

Analyzes permit leads to determine the percentage filed by homeowners (DIY/Owner-Builder)
vs contractors. Used to validate lead quality.

Usage:
    python3 scripts/analyze_owner_builder.py
    python3 scripts/analyze_owner_builder.py --output report.md
"""

import re
import os
import argparse
from datetime import datetime
from collections import Counter, defaultdict

import psycopg2

DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'postgresql://contractors_user:localdev123@localhost/contractors_dev'
)


# Business entity suffixes
ENTITY_SUFFIXES = {'llc', 'inc', 'corp', 'ltd', 'lp', 'llp', 'pllc', 'pc'}

# Contractor industry keywords
CONTRACTOR_KEYWORDS = {
    'construction', 'roofing', 'plumbing', 'electric', 'electrical', 'builders',
    'homes', 'custom', 'remodeling', 'restoration', 'services', 'solutions',
    'contractors', 'contracting', 'mechanical', 'hvac', 'solar', 'energy',
    'pool', 'pools', 'landscape', 'landscaping', 'fence', 'fencing',
    'foundation', 'renovation', 'renovations', 'repair', 'repairs',
    'exteriors', 'interiors', 'design', 'development', 'properties',
    'investments', 'holdings', 'partners', 'group', 'enterprises'
}


def normalize_name(name: str | None) -> str:
    """Normalize a name for comparison: lowercase, strip, remove punctuation."""
    if not name:
        return ""
    # Lowercase, remove non-alphanumeric except spaces
    cleaned = re.sub(r'[^a-z0-9 ]', '', name.lower())
    # Collapse multiple spaces
    return ' '.join(cleaned.split())


def is_contractor_entity(name: str | None) -> bool:
    """Check if name appears to be a contractor/business entity."""
    if not name:
        return False

    name_lower = name.lower()
    tokens = set(re.sub(r'[^a-z0-9 ]', '', name_lower).split())

    # Check for business entity suffixes
    if tokens & ENTITY_SUFFIXES:
        return True

    # Check for contractor industry keywords
    if tokens & CONTRACTOR_KEYWORDS:
        return True

    return False


def names_match(applicant: str | None, owner: str | None) -> tuple[bool, str]:
    """
    Check if applicant name matches owner name (indicating owner-builder/DIY).

    Returns: (is_match, reason)
    """
    app_norm = normalize_name(applicant)
    own_norm = normalize_name(owner)

    if not app_norm:
        return False, "No applicant name"

    if not own_norm:
        return False, "No owner name"

    # Exact match after normalization
    if app_norm == own_norm:
        return True, "Exact match"

    # Token-based matching
    app_tokens = set(app_norm.split())
    own_tokens = set(own_norm.split())

    # Remove common filler words
    filler = {'and', '&', 'the', 'of', 'a', 'an'}
    app_tokens -= filler
    own_tokens -= filler

    if not app_tokens or not own_tokens:
        return False, "Empty after filtering"

    # All applicant tokens appear in owner (subset match)
    if app_tokens <= own_tokens:
        return True, "Applicant subset of owner"

    # All owner tokens appear in applicant
    if own_tokens <= app_tokens:
        return True, "Owner subset of applicant"

    # Shared last name heuristic (at least one significant token overlap)
    # This catches spouse scenarios: "Mary Smith" vs "John Smith"
    overlap = app_tokens & own_tokens
    if overlap:
        # Check if overlap contains a likely last name (3+ chars, not a common first name)
        common_first_names = {'john', 'mary', 'james', 'michael', 'david', 'robert', 'william'}
        significant_overlap = {t for t in overlap if len(t) >= 3 and t not in common_first_names}
        if significant_overlap:
            return True, f"Family match ({', '.join(significant_overlap)})"

    return False, "No match"


def categorize_applicant(
    applicant: str | None,
    owner: str | None,
    contractor_field: str | None
) -> tuple[str, str]:
    """
    Categorize an applicant as OWNER_BUILDER, CONTRACTOR, POSSIBLE_CONTRACTOR, or UNKNOWN.

    Returns: (category, reason)
    """
    # Check for missing data
    if not applicant or not applicant.strip():
        return "UNKNOWN", "No applicant name"

    if not owner or not owner.strip():
        return "UNKNOWN", "No owner name (CAD)"

    # Check if applicant is a contractor entity by keywords
    if is_contractor_entity(applicant):
        return "CONTRACTOR", "Business entity keywords"

    # Check if applicant matches the contractor field (if populated)
    if contractor_field and contractor_field.strip():
        if normalize_name(applicant) == normalize_name(contractor_field):
            return "CONTRACTOR", "Matches contractor field"

    # Check if applicant matches owner (owner-builder scenario)
    match, reason = names_match(applicant, owner)
    if match:
        return "OWNER_BUILDER", reason

    # No match - likely a contractor or other third party
    return "POSSIBLE_CONTRACTOR", reason


def get_data_funnel(cur) -> dict:
    """Get data coverage statistics (the 'funnel')."""
    funnel = {}

    # Total permits
    cur.execute("SELECT COUNT(*) FROM leads_permit")
    funnel['total_permits'] = cur.fetchone()[0]

    # Permits with applicant_name
    cur.execute("""
        SELECT COUNT(*) FROM leads_permit
        WHERE applicant_name IS NOT NULL AND applicant_name != ''
    """)
    funnel['with_applicant'] = cur.fetchone()[0]

    # Permits that join to CAD data
    cur.execute("""
        SELECT COUNT(DISTINCT p.id)
        FROM leads_permit p
        JOIN leads_property pr ON UPPER(TRIM(p.property_address)) = UPPER(TRIM(pr.property_address))
        WHERE p.applicant_name IS NOT NULL AND p.applicant_name != ''
          AND pr.owner_name IS NOT NULL AND pr.owner_name != ''
    """)
    funnel['with_cad_match'] = cur.fetchone()[0]

    return funnel


def analyze_permits(cur, limit: int = 50000) -> tuple[list, Counter, dict]:
    """
    Query permits with CAD data and categorize each.

    Returns: (detailed_results, category_counts, city_breakdown)
    """
    query = """
        SELECT
            p.permit_id,
            p.city,
            p.property_address,
            p.applicant_name,
            p.contractor_name,
            pr.owner_name,
            p.permit_type,
            p.description
        FROM leads_permit p
        JOIN leads_property pr ON UPPER(TRIM(p.property_address)) = UPPER(TRIM(pr.property_address))
        WHERE p.applicant_name IS NOT NULL AND p.applicant_name != ''
          AND pr.owner_name IS NOT NULL AND pr.owner_name != ''
        LIMIT %s
    """

    cur.execute(query, (limit,))
    rows = cur.fetchall()

    results = []
    counts = Counter()
    city_breakdown = defaultdict(Counter)

    for row in rows:
        permit_id, city, address, applicant, contractor, owner, ptype, desc = row

        category, reason = categorize_applicant(applicant, owner, contractor)

        counts[category] += 1
        city_breakdown[city or 'Unknown'][category] += 1

        results.append({
            'permit_id': permit_id,
            'city': city,
            'address': address,
            'applicant': applicant,
            'owner': owner,
            'contractor': contractor,
            'category': category,
            'reason': reason,
            'permit_type': ptype,
        })

    return results, counts, dict(city_breakdown)


def generate_report(funnel: dict, counts: Counter, city_breakdown: dict, results: list) -> str:
    """Generate Markdown report."""
    lines = []

    # Header
    lines.append("# Permit Lead Quality Analysis Report")
    lines.append(f"\n**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("\n**Objective:** Validate lead quality by determining the percentage of permits filed by Homeowners (Owner-Builder/DIY) vs Contractors.")

    # Data Funnel
    lines.append("\n## Data Coverage (Funnel)")
    lines.append(f"| Stage | Count | % of Previous |")
    lines.append("|-------|-------|---------------|")
    lines.append(f"| Total Permits | {funnel['total_permits']:,} | - |")

    pct_applicant = (funnel['with_applicant'] / funnel['total_permits'] * 100) if funnel['total_permits'] > 0 else 0
    lines.append(f"| With Applicant Name | {funnel['with_applicant']:,} | {pct_applicant:.1f}% |")

    pct_cad = (funnel['with_cad_match'] / funnel['with_applicant'] * 100) if funnel['with_applicant'] > 0 else 0
    lines.append(f"| With CAD Owner Match | {funnel['with_cad_match']:,} | {pct_cad:.1f}% |")

    # Executive Summary
    total_analyzed = sum(counts.values())
    owner_builder = counts.get('OWNER_BUILDER', 0)
    contractor = counts.get('CONTRACTOR', 0)
    possible_contractor = counts.get('POSSIBLE_CONTRACTOR', 0)
    unknown = counts.get('UNKNOWN', 0)

    lines.append("\n## Executive Summary")
    lines.append(f"\n**Permits Analyzed:** {total_analyzed:,}")
    lines.append("")
    lines.append("| Category | Count | Percentage |")
    lines.append("|----------|-------|------------|")

    for cat, count in counts.most_common():
        pct = (count / total_analyzed * 100) if total_analyzed > 0 else 0
        emoji = {"OWNER_BUILDER": "✅", "CONTRACTOR": "🏗️", "POSSIBLE_CONTRACTOR": "❓", "UNKNOWN": "❔"}.get(cat, "")
        lines.append(f"| {emoji} {cat} | {count:,} | {pct:.1f}% |")

    # Interpretation
    lines.append("\n### Interpretation")
    owner_pct = (owner_builder / total_analyzed * 100) if total_analyzed > 0 else 0
    if owner_pct >= 50:
        lines.append(f"✅ **MAJORITY OWNER-BUILDER:** {owner_pct:.1f}% of permits are filed by the homeowner. These are DIY projects where the homeowner is the applicant - **excellent leads for contractors**.")
    elif owner_pct >= 30:
        lines.append(f"✅ **SIGNIFICANT OWNER-BUILDER:** {owner_pct:.1f}% of permits are filed by the homeowner. A substantial portion are DIY projects - **good quality leads**.")
    elif owner_pct >= 15:
        lines.append(f"⚠️ **MIXED RESULTS:** {owner_pct:.1f}% of permits are owner-filed. Lead quality is moderate.")
    else:
        lines.append(f"❌ **LOW OWNER-BUILDER RATE:** Only {owner_pct:.1f}% of permits are owner-filed. Most permits may already have contractors attached.")

    # City Breakdown
    lines.append("\n## Breakdown by City")
    lines.append("\n| City | Total | Owner-Builder | Contractor | Possible Contractor | % Owner-Builder |")
    lines.append("|------|-------|---------------|------------|---------------------|-----------------|")

    for city in sorted(city_breakdown.keys()):
        city_counts = city_breakdown[city]
        city_total = sum(city_counts.values())
        ob = city_counts.get('OWNER_BUILDER', 0)
        co = city_counts.get('CONTRACTOR', 0)
        pc = city_counts.get('POSSIBLE_CONTRACTOR', 0)
        ob_pct = (ob / city_total * 100) if city_total > 0 else 0
        lines.append(f"| {city} | {city_total:,} | {ob:,} | {co:,} | {pc:,} | {ob_pct:.1f}% |")

    # Sample Permits
    lines.append("\n## Sample Permits for Verification")

    # Owner-Builder samples
    ob_samples = [r for r in results if r['category'] == 'OWNER_BUILDER'][:5]
    lines.append("\n### Owner-Builder (DIY) Samples")
    lines.append("| Applicant | Owner (CAD) | City | Reason |")
    lines.append("|-----------|-------------|------|--------|")
    for s in ob_samples:
        lines.append(f"| {s['applicant'][:30]} | {s['owner'][:30]} | {s['city']} | {s['reason']} |")

    # Contractor samples
    co_samples = [r for r in results if r['category'] == 'CONTRACTOR'][:5]
    lines.append("\n### Contractor Samples")
    lines.append("| Applicant | Owner (CAD) | City | Reason |")
    lines.append("|-----------|-------------|------|--------|")
    for s in co_samples:
        lines.append(f"| {s['applicant'][:30]} | {s['owner'][:30]} | {s['city']} | {s['reason']} |")

    # Possible Contractor samples
    pc_samples = [r for r in results if r['category'] == 'POSSIBLE_CONTRACTOR'][:5]
    lines.append("\n### Possible Contractor (Name Mismatch) Samples")
    lines.append("| Applicant | Owner (CAD) | City | Reason |")
    lines.append("|-----------|-------------|------|--------|")
    for s in pc_samples:
        lines.append(f"| {s['applicant'][:30]} | {s['owner'][:30]} | {s['city']} | {s['reason']} |")

    # Methodology
    lines.append("\n## Methodology")
    lines.append("""
- **Owner-Builder**: Applicant name matches CAD owner name (exact, subset, or family name match)
- **Contractor**: Applicant contains business entity keywords (LLC, Inc, Roofing, Construction, etc.)
- **Possible Contractor**: Applicant is a person but doesn't match owner name (could be contractor, property manager, or agent)
- **Unknown**: Missing applicant or owner data

**Note:** Name matching uses token-based comparison to handle format differences (e.g., "SMITH JOHN" vs "John Smith").
""")

    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description='Analyze permit lead quality')
    parser.add_argument('--output', '-o', default='LEAD_QUALITY_REPORT.md',
                        help='Output file path (default: LEAD_QUALITY_REPORT.md)')
    parser.add_argument('--limit', '-l', type=int, default=50000,
                        help='Max permits to analyze (default: 50000)')
    args = parser.parse_args()

    print("=" * 60)
    print("PERMIT LEAD QUALITY ANALYSIS")
    print("=" * 60)
    print(f"Connecting to database...")

    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
    except Exception as e:
        print(f"ERROR: Failed to connect to database: {e}")
        print("Ensure DATABASE_URL is set or local postgres is running.")
        return 1

    try:
        # Get data funnel
        print("Calculating data coverage...")
        funnel = get_data_funnel(cur)
        print(f"  Total permits: {funnel['total_permits']:,}")
        print(f"  With applicant name: {funnel['with_applicant']:,}")
        print(f"  With CAD match: {funnel['with_cad_match']:,}")

        # Analyze permits
        print(f"\nAnalyzing permits (limit: {args.limit:,})...")
        results, counts, city_breakdown = analyze_permits(cur, args.limit)
        print(f"  Analyzed: {len(results):,} permits")

        # Print summary to console
        print("\n" + "-" * 40)
        print("RESULTS:")
        for cat, count in counts.most_common():
            pct = (count / len(results) * 100) if results else 0
            print(f"  {cat}: {count:,} ({pct:.1f}%)")

        # Generate and save report
        report = generate_report(funnel, counts, city_breakdown, results)

        with open(args.output, 'w') as f:
            f.write(report)

        print(f"\nReport saved to: {args.output}")

    finally:
        cur.close()
        conn.close()

    return 0


if __name__ == '__main__':
    exit(main())
