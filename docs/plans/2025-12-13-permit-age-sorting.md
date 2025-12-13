# Permit Age Sorting Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Automatically sort permits into bins at scrape time - recent permits (<=60 days) flow through enrichment/scoring, old permits go to archive for trusthome verification.

**Architecture:** Add `processing_bin` column to `leads_permit` table. Set bin at INSERT time based on `issued_date`. Update all consumer scripts to filter on `processing_bin='active'` by default.

**Tech Stack:** PostgreSQL, Python, psycopg2

---

## Task 1: Add Database Column

**Files:**
- Execute: SQL against `contractors_dev` database

**Step 1: Add the processing_bin column**

```sql
ALTER TABLE leads_permit
ADD COLUMN processing_bin VARCHAR(20) DEFAULT 'active';
```

**Step 2: Add index for query performance**

```sql
CREATE INDEX idx_leads_permit_processing_bin ON leads_permit(processing_bin);
```

**Step 3: Verify column exists**

Run: `psql -d contractors_dev -c "\d leads_permit" | grep processing_bin`

Expected: `processing_bin | character varying(20) | | | 'active'`

---

## Task 2: Backfill Existing Old Permits to Archive

**Files:**
- Execute: SQL against `contractors_dev` database

**Step 1: Count permits to be archived**

```sql
SELECT COUNT(*) FROM leads_permit
WHERE issued_date < NOW() - INTERVAL '60 days';
```

**Step 2: Move old permits to archive bin**

```sql
UPDATE leads_permit
SET processing_bin = 'archive'
WHERE issued_date IS NOT NULL
  AND issued_date < NOW() - INTERVAL '60 days';
```

**Step 3: Verify bin distribution**

```sql
SELECT processing_bin, COUNT(*)
FROM leads_permit
GROUP BY processing_bin;
```

Expected: Two rows - `active` (recent + NULL dates) and `archive` (old permits)

---

## Task 3: Update sync_to_postgres.py to Set Bin at INSERT

**Files:**
- Modify: `/home/reid/testhome/permit-scraper/scripts/sync_to_postgres.py:61-106`

**Step 1: Add datetime import (if not present)**

At top of file, ensure:
```python
from datetime import datetime, timedelta
```

**Step 2: Update INSERT SQL to include processing_bin**

Replace lines 61-72:

```python
    insert_sql = """
        INSERT INTO leads_permit (
            permit_id, city, property_address, permit_type, description,
            status, issued_date, applicant_name, contractor_name,
            estimated_value, scraped_at, lead_type, processing_bin
        ) VALUES %s
        ON CONFLICT ON CONSTRAINT clients_permit_city_permit_id_33861e17_uniq DO UPDATE SET
            property_address = EXCLUDED.property_address,
            description = EXCLUDED.description,
            status = EXCLUDED.status,
            estimated_value = EXCLUDED.estimated_value,
            processing_bin = EXCLUDED.processing_bin
    """
```

**Step 3: Calculate bin when building rows**

Replace lines 74-101 with:

```python
    pg_rows = []
    cutoff_date = (datetime.now() - timedelta(days=60)).date()

    for row in rows:
        permit_id, city, prop_addr, permit_type, description, status, \
        issued_date, applicant, contractor, est_value, scraped_at, lead_type = row

        # Handle issued_date conversion
        issued = None
        if issued_date:
            try:
                issued = datetime.strptime(issued_date[:10], '%Y-%m-%d').date()
            except (ValueError, TypeError):
                pass

        # Handle scraped_at - ensure it's a datetime
        scraped = datetime.now()
        if scraped_at:
            try:
                scraped = datetime.fromisoformat(scraped_at.replace('Z', '+00:00'))
            except (ValueError, TypeError):
                try:
                    scraped = datetime.strptime(scraped_at[:19], '%Y-%m-%d %H:%M:%S')
                except (ValueError, TypeError):
                    pass

        # Calculate processing bin: active if recent or unknown, archive if old
        if issued is None or issued >= cutoff_date:
            processing_bin = 'active'
        else:
            processing_bin = 'archive'

        pg_rows.append((
            permit_id, city, prop_addr, permit_type, description,
            status, issued, applicant, contractor, est_value, scraped, lead_type,
            processing_bin
        ))
```

**Step 4: Verify changes compile**

Run: `python3 -m py_compile scripts/sync_to_postgres.py`

Expected: No output (success)

**Step 5: Commit**

```bash
git add scripts/sync_to_postgres.py
git commit -m "feat: add processing_bin to permit sync - active/archive based on issued_date"
```

---

## Task 4: Update enrich_cad.py to Filter by Bin

**Files:**
- Modify: `/home/reid/testhome/permit-scraper/scripts/enrich_cad.py:810-895`

**Step 1: Add --bin argument to argparser**

After line 813 (`--fresh` argument), add:

```python
    parser.add_argument('--bin', default='active',
                        help='Processing bin to target (active, archive, all). Default: active')
```

**Step 2: Add bin filter variable**

After line 831 (recent_filter setup), add:

```python
    # Bin filter: only process active permits by default
    bin_filter = ""
    if args.bin != 'all':
        bin_filter = f"AND p.processing_bin = '{args.bin}'"
        print(f"Filtering to '{args.bin}' bin\n")
```

**Step 3: Add bin_filter to all SQL queries**

Update line 867 (force query):
```python
        sql = f"SELECT DISTINCT property_address FROM leads_permit p WHERE property_address IS NOT NULL {recent_filter} {fresh_filter} {bin_filter}"
```

Update lines 875-883 (never_tried query):
```python
        sql = f"""
            SELECT DISTINCT p.property_address
            FROM leads_permit p
            LEFT JOIN leads_property prop ON p.property_address = prop.property_address
            WHERE p.property_address IS NOT NULL
              AND prop.property_address IS NULL
              {recent_filter}
              {fresh_filter}
              {bin_filter}
        """
```

Update lines 886-894 (default query):
```python
        sql = f"""
            SELECT DISTINCT p.property_address
            FROM leads_permit p
            LEFT JOIN leads_property prop ON p.property_address = prop.property_address
            WHERE p.property_address IS NOT NULL
              AND (prop.property_address IS NULL OR prop.enrichment_status != 'success')
              {recent_filter}
              {fresh_filter}
              {bin_filter}
        """
```

**Step 4: Verify changes compile**

Run: `python3 -m py_compile scripts/enrich_cad.py`

Expected: No output (success)

**Step 5: Test --help shows new flag**

Run: `python3 scripts/enrich_cad.py --help | grep bin`

Expected: `--bin BIN  Processing bin to target (active, archive, all). Default: active`

**Step 6: Commit**

```bash
git add scripts/enrich_cad.py
git commit -m "feat: add --bin filter to enrich_cad.py - defaults to active permits only"
```

---

## Task 5: Update score_leads.py to Filter by Bin

**Files:**
- Modify: `/home/reid/testhome/permit-scraper/scripts/score_leads.py:711-728`

**Step 1: Add processing_bin filter to base query**

Update lines 711-728, adding the bin filter:

```python
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
```

**Step 2: Verify changes compile**

Run: `python3 -m py_compile scripts/score_leads.py`

Expected: No output (success)

**Step 3: Commit**

```bash
git add scripts/score_leads.py
git commit -m "feat: filter score_leads.py to active bin only"
```

---

## Task 6: Update Django Model (Optional - for Admin/API access)

**Files:**
- Modify: `/home/reid/command-center/contractors_data/models.py:114-140`

**Step 1: Add processing_bin field to Permit model**

After line 132 (`categorization_confidence`), add:

```python
    processing_bin = models.CharField(max_length=20, default='active')
```

**Step 2: Verify Django can load models**

Run: `cd /home/reid/command-center && python3 manage.py check`

Expected: `System check identified no issues`

**Step 3: Commit**

```bash
git add contractors_data/models.py
git commit -m "feat: add processing_bin field to Permit model"
```

---

## Task 7: Verification - End-to-End Test

**Step 1: Check bin distribution**

```bash
psql -d contractors_dev -c "SELECT processing_bin, COUNT(*) FROM leads_permit GROUP BY processing_bin;"
```

Expected: `active` and `archive` rows with counts

**Step 2: Test enrichment only processes active**

```bash
cd /home/reid/testhome/permit-scraper
python3 scripts/enrich_cad.py --limit 5 --dry-run
```

Expected: Output shows "Filtering to 'active' bin"

**Step 3: Test scoring only processes active**

```bash
python3 scripts/score_leads.py --dry-run --limit 5
```

Expected: Only sees permits from active bin

---

## Summary

| Step | File | Change |
|------|------|--------|
| 1 | Database | Add `processing_bin` column |
| 2 | Database | Backfill old permits to archive |
| 3 | sync_to_postgres.py | Set bin at INSERT time |
| 4 | enrich_cad.py | Add `--bin` filter, default active |
| 5 | score_leads.py | Filter to active bin |
| 6 | models.py | Add field to Django model |
| 7 | - | End-to-end verification |

**Total estimated tasks: 7**
**Estimated time: 30-45 minutes**
