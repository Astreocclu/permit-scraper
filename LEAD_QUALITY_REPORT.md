# Permit Lead Quality Analysis Report

**Generated:** 2025-12-13 17:29:07

**Objective:** Validate lead quality by determining the percentage of permits filed by Homeowners (Owner-Builder/DIY) vs Contractors.

## Data Coverage (Funnel)
| Stage | Count | % of Previous |
|-------|-------|---------------|
| Total Permits | 34,000 | - |
| With Applicant Name | 0 | 0.0% |
| With CAD Owner Match | 0 | 0.0% |

## Executive Summary

**Permits Analyzed:** 0

| Category | Count | Percentage |
|----------|-------|------------|

### Interpretation
❌ **LOW OWNER-BUILDER RATE:** Only 0.0% of permits are owner-filed. Most permits may already have contractors attached.

## Breakdown by City

| City | Total | Owner-Builder | Contractor | Possible Contractor | % Owner-Builder |
|------|-------|---------------|------------|---------------------|-----------------|

## Sample Permits for Verification

### Owner-Builder (DIY) Samples
| Applicant | Owner (CAD) | City | Reason |
|-----------|-------------|------|--------|

### Contractor Samples
| Applicant | Owner (CAD) | City | Reason |
|-----------|-------------|------|--------|

### Possible Contractor (Name Mismatch) Samples
| Applicant | Owner (CAD) | City | Reason |
|-----------|-------------|------|--------|

## Methodology

- **Owner-Builder**: Applicant name matches CAD owner name (exact, subset, or family name match)
- **Contractor**: Applicant contains business entity keywords (LLC, Inc, Roofing, Construction, etc.)
- **Possible Contractor**: Applicant is a person but doesn't match owner name (could be contractor, property manager, or agent)
- **Unknown**: Missing applicant or owner data

**Note:** Name matching uses token-based comparison to handle format differences (e.g., "SMITH JOHN" vs "John Smith").
