# Data Architecture & Reliability Map

**STATUS: AUTHORITATIVE SOURCE OF TRUTH**
*Last Updated: 2025-12-13*

## PRIMER: The "Empty Field" Trap

**READ THIS FIRST:** The database contains columns that exist in the schema but are **structurally empty** (0% population) due to scraper limitations.

*   **`leads_permit.applicant_name` is 100% EMPTY.**
*   **`leads_permit.contractor_name` is <10% populated.**

**RULE #1:** NEVER build analysis assuming a column has data.
**RULE #2:** ALWAYS run a `SELECT COUNT(NULLIF(col, ''))` before writing script logic.
**RULE #3:** NEVER use AI "Reasoning" text as a substitute for missing raw data.

---

## 1. Data Hierarchy & Source of Truth

The system consists of three distinct layers. You must query the correct layer for your question.

| Layer | Table | Type | Source of Truth For... | Reliability |
|-------|-------|------|------------------------|-------------|
| **1. RAW** | `leads_permit` | Scraped Data | **Permit Counts, Types, Dates, Cities** | HIGH |
| **2. CONTEXT** | `leads_property` | CAD Match | **Owner Name, Market Value, Year Built** | HIGH |
| **3. INTELLIGENCE** | `clients_scoredlead` | AI Derived | **Lead Quality (Tier), Commercial vs. Resi** | DERIVED |

### Join Logic

*   **Permit -> Property:** `JOIN leads_property ON leads_permit.property_address = leads_property.property_address`
    *   *Note:* Not all permits match to CAD. Use `LEFT JOIN` unless you specifically need enriched data.
*   **Permit -> Score:** `JOIN clients_scoredlead ON leads_permit.id = clients_scoredlead.permit_id`
    *   *Note:* Only "Active" permits are scored.

---

## 2. Column-Level Reliability Map

Before querying, check this map. If a field is marked EMPTY, **DO NOT USE IT** for business logic.

### Table: `leads_permit` (Raw Scrapes)

| Column | Reliability | Notes |
|--------|-------------|-------|
| `permit_id` | HIGH | Primary Key equivalent from source. |
| `property_address` | HIGH | The pivot key for everything. |
| `permit_type` | HIGH | Reliable categorization string. |
| `description` | HIGH | Critical for AI analysis. |
| `issued_date` | HIGH (95%) | Usually present, format varies. |
| `applicant_name` | **EMPTY (0%)** | **DO NOT USE.** Scrapers do not capture this. |
| `contractor_name` | **LOW (<10%)** | **DO NOT USE.** Rarely populated. |
| `owner_name` | **LOW (<5%)** | **DO NOT USE.** Use `leads_property.owner_name` instead. |

### Table: `leads_property` (CAD Data)

| Column | Reliability | Notes |
|--------|-------------|-------|
| `owner_name` | HIGH | The TRUSTED source for "Who owns this?". |
| `market_value` | HIGH | Reliable proxy for budget/wealth. |
| `year_built` | HIGH | Good for filtering. |

### Table: `clients_scoredlead` (AI Output)

| Column | Reliability | Notes |
|--------|-------------|-------|
| `tier` | DERIVED | A/B/C ratings. Reliable for *sorting*, not legal proof. |
| `is_commercial` | DERIVED | AI's guess based on desc/owner. ~99% accurate. |
| `reasoning` | **TEXT ONLY** | **NEVER** parse this for stats. It is free-text explanation. |

---

## 3. Decision Tree: Which Table?

**Q: "How many permits were issued in Dallas yesterday?"**
*   Use `leads_permit` (count by date/city)

**Q: "Who is the homeowner for this permit?"**
*   Use `leads_property` (`owner_name`)
*   NOT `leads_permit` (Columns are empty)

**Q: "Is this a homeowner project or a contractor project?"**
*   Use `clients_scoredlead` (Use `tier` and `is_commercial`).
    *   *Context:* We assume Tier A/B are homeowner-driven based on project type/value, but we **CANNOT PROVE** identity because `applicant_name` is missing.
*   NOT `leads_permit` (Cannot compare applicant vs owner).

**Q: "What is the average project value?"**
*   Use `leads_property` (`market_value` of the house).
*   NOT `leads_permit` (We do not capture *project cost* from the city, only *property value* from CAD).

---

## 4. Verification Protocol (The "Claude Check")

Before writing ANY analysis script, you must execute this sequence:

1.  **Hypothesis:** "I want to analyze X using column Y."
2.  **Verification Query:** Run `SELECT COUNT(NULLIF(column_y, '')) FROM table;`
3.  **Go/No-Go:**
    *   If count is 0 or low -> **STOP.** Report "Data not available".
    *   If count is high -> **PROCEED.**
4.  **Schema Check:** `\d table_name` to verify column types.

### Example Check

```sql
-- Before building applicant analysis
SELECT COUNT(NULLIF(applicant_name, '')) FROM leads_permit;
-- Result: 0
-- Action: STOP. Do not build. Report data unavailable.
```

---

## 5. Known Limitations & "Do Not Touch" Zones

1.  **Applicant Identity:** We strictly **DO NOT KNOW** who applied for the permit. Any analysis claiming "Homeowner applied" is an **inference**, not a fact.

2.  **Contractor Presence:** We **DO NOT KNOW** if a contractor is already attached. `contractor_name` is empty.

3.  **Project Cost:** We **DO NOT KNOW** the cost of the renovation. We only know the value of the property (`leads_property.market_value`). Do not confuse the two.

---

## 6. How to Handle Missing Data Requests

If the user asks: *"Analyze how many homeowners applied for their own permits."*

**Correct Response:**
> "I checked `leads_permit` and `applicant_name` is 100% empty. I cannot verify identity match.
> However, I can analyze `clients_scoredlead` to show how many permits are *rated* as Tier A/B (Homeowner-grade), acknowledging this is an inference based on project type and property value, not a verified name match."

**Incorrect Response:**
> *Writes a script trying to match `applicant_name` to `owner_name` and returns 0 results or hallucinates logic.*

---

## 7. Post-Mortem: 2025-12-13 Failure

On this date, Claude wasted hours building an "owner-builder analysis" that:

1. Built entire analysis around `applicant_name` field
2. Never checked if `applicant_name` had data (it was 100% empty)
3. Claimed "91.8% homeowner leads" by counting word occurrences in AI reasoning text
4. Confused AI inference with data verification

**Cost:** ~3 hours of development time, 290 lines of code that produced no usable output.

**Root Cause:** Did not run verification query before building.

**Prevention:** Follow the "Claude Check" protocol in Section 4.
