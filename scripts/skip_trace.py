#!/usr/bin/env python3
"""
Tracerfy Skip Tracing Integration

Enriches permit leads with phone/email via Tracerfy API.
Cost: $0.009/lead

Usage:
    python scripts/skip_trace.py --limit 20          # Test with 20 leads
    python scripts/skip_trace.py                     # Process all Tier A+B leads
    python scripts/skip_trace.py --export            # Export enriched sales packs
"""

import os
import re
import csv
import json
import time
import argparse
import logging
import requests
import psycopg2
from io import StringIO
from datetime import datetime
from typing import Optional, Tuple, List, Dict

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# =============================================================================
# NAME PARSING
# =============================================================================

def parse_owner_name(name: str) -> Tuple[str, str]:
    """
    Parse owner name into first_name and last_name.

    Examples:
        "THOMSON, KENNETH DEREK & LEAH BALLARD THOMSON" → ("KENNETH DEREK", "THOMSON")
        "KOSLOW, JUDY" → ("JUDY", "KOSLOW")
        "FELTY BRIAN & WENDY" → ("BRIAN", "FELTY")
        "BAXTER JEFFERY D &" → ("JEFFERY D", "BAXTER")
    """
    if not name or name.strip() in ("", "Unknown", "None"):
        return ("", "")

    name = name.strip().upper()

    # Remove trailing & or & SPOUSE
    name = re.sub(r'\s*&\s*[\w\s]*$', '', name).strip()

    if ',' in name:
        # Format: "LASTNAME, FIRSTNAME ..."
        parts = name.split(',', 1)
        last_name = parts[0].strip()
        first_name = parts[1].strip() if len(parts) > 1 else ""
        # Remove anything after & in first name
        first_name = re.sub(r'\s*&.*$', '', first_name).strip()
    else:
        # Format: "LASTNAME FIRSTNAME ..."
        parts = name.split()
        if len(parts) >= 2:
            last_name = parts[0]
            # Take remaining parts until we hit & or end
            first_parts = []
            for p in parts[1:]:
                if p == '&':
                    break
                first_parts.append(p)
            first_name = ' '.join(first_parts)
        elif len(parts) == 1:
            last_name = parts[0]
            first_name = ""
        else:
            last_name = ""
            first_name = ""

    return (first_name.title(), last_name.title())


# =============================================================================
# ADDRESS PARSING
# =============================================================================

def parse_address(address: str, default_city: str = "") -> Dict[str, str]:
    """
    Parse address string, extracting embedded city/state/zip if present.

    Examples:
        "4412 HOCKADAY DR, Dallas TX 75229" → {street: "4412 HOCKADAY DR", city: "Dallas", state: "TX", zip: "75229"}
        "2625 SIR LANCELOT BLVD" → {street: "2625 SIR LANCELOT BLVD", city: default_city, state: "TX", zip: ""}
    """
    if not address:
        return {"street": "", "city": default_city.title(), "state": "TX", "zip": ""}

    address = address.strip()

    # Pattern: "STREET, CITY STATE ZIP" or "STREET, CITY STATE ZIP COUNTRY"
    # Also handle "STREET, CITY TX" without zip
    pattern = r'^(.+?),\s*([A-Za-z\s]+?)\s+TX\s*(\d{5})?\s*(United States)?$'
    match = re.match(pattern, address, re.IGNORECASE)

    if match:
        street = match.group(1).strip()
        city = match.group(2).strip().title()
        zip_code = match.group(3) or ""
        return {"street": street, "city": city, "state": "TX", "zip": zip_code}

    # No embedded city/state, use the whole thing as street
    return {
        "street": address,
        "city": default_city.title() if default_city else "",
        "state": "TX",
        "zip": ""
    }


# =============================================================================
# DATABASE CONNECTION
# =============================================================================

def get_db_connection():
    """Get PostgreSQL connection from DATABASE_URL."""
    url = os.environ.get('DATABASE_URL')
    if not url:
        raise ValueError("DATABASE_URL environment variable not set")
    return psycopg2.connect(url)


def get_leads_for_tracing(conn, limit: Optional[int] = None, category: Optional[str] = None) -> List[Dict]:
    """
    Fetch Tier A+B leads that haven't been skip-traced yet.
    """
    query = """
        SELECT
            sl.id as scored_lead_id,
            p.id as permit_id,
            p.property_address,
            p.city,
            pr.owner_name,
            pr.market_value,
            sl.score,
            sl.category,
            sl.phone,
            sl.email
        FROM clients_scoredlead sl
        JOIN leads_permit p ON sl.permit_id = p.id
        LEFT JOIN leads_property pr ON p.property_address = pr.property_address
        WHERE sl.score >= 50
          AND (sl.phone IS NULL OR sl.phone = '')
          AND pr.owner_name IS NOT NULL
          AND pr.owner_name != ''
          AND pr.owner_name != 'Unknown'
    """

    conditions = []
    params = []

    if category:
        conditions.append("sl.category = %s")
        params.append(category)

    if conditions:
        query += " AND " + " AND ".join(conditions)

    query += " ORDER BY sl.score DESC"

    if limit:
        query += f" LIMIT {limit}"

    with conn.cursor() as cur:
        cur.execute(query, params)
        columns = [desc[0] for desc in cur.description]
        rows = cur.fetchall()

    return [dict(zip(columns, row)) for row in rows]


# =============================================================================
# TRACERFY API
# =============================================================================

class TracerfyClient:
    """Client for Tracerfy skip tracing API."""

    BASE_URL = "https://tracerfy.com/v1/api"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

    def transform_leads_to_csv(self, leads: List[Dict]) -> str:
        """
        Transform leads into Tracerfy-ready CSV format.
        """
        output = StringIO()
        writer = csv.writer(output)

        # Header row
        writer.writerow([
            'address', 'city', 'state', 'zip',
            'first_name', 'last_name',
            'mail_address', 'mail_city', 'mail_state', 'mail_zip',
            'scored_lead_id'  # Keep for merging later
        ])

        for lead in leads:
            # Parse owner name
            first_name, last_name = parse_owner_name(lead.get('owner_name', ''))

            # Parse address
            addr = parse_address(lead.get('property_address', ''), lead.get('city', ''))

            # Use property address as mailing address
            writer.writerow([
                addr['street'],
                addr['city'],
                addr['state'],
                addr['zip'],
                first_name,
                last_name,
                addr['street'],  # mail_address
                addr['city'],    # mail_city
                addr['state'],   # mail_state
                addr['zip'],     # mail_zip
                lead.get('scored_lead_id', '')
            ])

        return output.getvalue()

    def submit_trace(self, csv_data: str) -> Dict:
        """
        Submit CSV for skip tracing via multipart form upload.
        Returns: {"queue_id": "...", "status": "pending", ...}
        """
        # Write CSV to temp file for upload
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_data)
            temp_path = f.name

        try:
            # Multipart form upload
            with open(temp_path, 'rb') as csv_file:
                files = {'csv_file': ('leads.csv', csv_file, 'text/csv')}
                data = {
                    'address_column': 'address',
                    'city_column': 'city',
                    'state_column': 'state',
                    'zip_column': 'zip',
                    'first_name_column': 'first_name',
                    'last_name_column': 'last_name',
                    'mail_address_column': 'mail_address',
                    'mail_city_column': 'mail_city',
                    'mail_state_column': 'mail_state',
                    'mailing_zip_column': 'mail_zip'
                }

                # Don't include Content-Type header - requests sets it for multipart
                headers = {"Authorization": f"Bearer {self.api_key}"}

                response = requests.post(
                    f"{self.BASE_URL}/trace/",
                    headers=headers,
                    files=files,
                    data=data,
                    timeout=60
                )
            response.raise_for_status()
            return response.json()
        finally:
            os.unlink(temp_path)

    def get_queues(self) -> List[Dict]:
        """List all queues with retry on temporary errors."""
        for attempt in range(3):
            try:
                response = requests.get(
                    f"{self.BASE_URL}/queues/",
                    headers=self.headers,
                    timeout=30
                )
                response.raise_for_status()
                return response.json()
            except requests.exceptions.HTTPError as e:
                if response.status_code in (502, 503, 504) and attempt < 2:
                    logger.warning(f"Server error {response.status_code}, retrying in 5s...")
                    time.sleep(5)
                else:
                    raise
        return []

    def get_queue(self, queue_id: int) -> Dict:
        """Get individual queue status by filtering from list."""
        queues = self.get_queues()
        for q in queues:
            if q.get('id') == queue_id:
                return q
        return {'pending': True}  # Not found, assume pending

    def wait_for_completion(self, queue_id: str, poll_interval: int = 10, max_wait: int = 600) -> Dict:
        """
        Poll queue until completion or timeout.
        Returns the final queue data with results.
        """
        start_time = time.time()

        while True:
            elapsed = time.time() - start_time
            if elapsed > max_wait:
                raise TimeoutError(f"Queue {queue_id} did not complete within {max_wait}s")

            queue_data = self.get_queue(queue_id)

            # Check if complete (pending: false)
            if not queue_data.get('pending', True):
                logger.info(f"Queue {queue_id} completed!")
                return queue_data

            logger.info(f"Queue {queue_id} still pending... ({int(elapsed)}s elapsed)")
            time.sleep(poll_interval)

    def download_results(self, download_url: str) -> List[Dict]:
        """Download traced results from URL (CSV format)."""
        response = requests.get(download_url, timeout=60)
        response.raise_for_status()

        # Parse CSV response
        reader = csv.DictReader(StringIO(response.text))
        results = []
        for row in reader:
            # Extract best phone and email
            phone = row.get('primary_phone') or row.get('Mobile-1') or row.get('Landline-1') or ''
            email = row.get('Email-1') or ''

            results.append({
                'address': row.get('address', ''),
                'first_name': row.get('first_name', ''),
                'last_name': row.get('last_name', ''),
                'phone': phone,
                'email': email,
                'scored_lead_id': row.get('scored_lead_id', '')  # Our tracking ID
            })

        return results


# =============================================================================
# MERGE & UPDATE
# =============================================================================

def normalize_address(addr: str) -> str:
    """Normalize address for matching: uppercase, remove punctuation, collapse whitespace."""
    if not addr:
        return ""
    # Uppercase
    addr = addr.upper()
    # Remove commas, periods, extra spaces
    addr = re.sub(r'[,.]', ' ', addr)
    addr = re.sub(r'\s+', ' ', addr).strip()
    return addr


def update_leads_with_trace_data(conn, trace_results: List[Dict], original_leads: List[Dict]):
    """
    Update scored_lead records with phone/email from trace results.
    Matches by normalized address since Tracerfy doesn't preserve our IDs.
    """
    # Build lookup from normalized address -> trace result
    trace_lookup = {}
    for result in trace_results:
        addr = normalize_address(result.get('address', ''))
        if addr:
            trace_lookup[addr] = result

    updated = 0
    with conn.cursor() as cur:
        for lead in original_leads:
            # Parse the address we sent to get the street portion
            parsed = parse_address(lead.get('property_address', ''), lead.get('city', ''))
            norm_addr = normalize_address(parsed['street'])

            # Find matching trace result
            trace_result = trace_lookup.get(norm_addr)
            if not trace_result:
                continue

            phone = trace_result.get('phone', '')
            email = trace_result.get('email', '')

            if phone or email:
                cur.execute("""
                    UPDATE clients_scoredlead
                    SET phone = %s, email = %s, skip_traced_at = NOW()
                    WHERE id = %s
                """, (phone, email, lead.get('scored_lead_id')))
                updated += 1

    conn.commit()
    logger.info(f"Updated {updated} leads with contact info")
    return updated


# =============================================================================
# EXPORT ENRICHED PACKS
# =============================================================================

def export_enriched_packs(conn, output_dir: str = "sales_packs_enriched"):
    """Export sales packs with phone/email included."""

    os.makedirs(output_dir, exist_ok=True)

    categories = {
        'pool': 'pool_builder_pack_enriched.csv',
        'plumbing': 'plumber_pack_enriched.csv',
        'roof': 'roofer_pack_enriched.csv',
        'electrical': 'electrician_pack_enriched.csv',
        'hvac': 'hvac_pack_enriched.csv',
    }

    for category, filename in categories.items():
        query = """
            SELECT
                p.property_address as "Address",
                p.city as "City",
                pr.owner_name as "Owner Name",
                sl.phone as "Phone",
                sl.email as "Email",
                pr.market_value as "Property Value",
                sl.score as "Lead Score",
                p.permit_type as "Permit Type",
                p.issued_date as "Permit Date"
            FROM clients_scoredlead sl
            JOIN leads_permit p ON sl.permit_id = p.id
            LEFT JOIN leads_property pr ON p.property_address = pr.property_address
            WHERE sl.category = %s AND sl.score >= 50
            ORDER BY sl.score DESC
        """

        with conn.cursor() as cur:
            cur.execute(query, (category,))
            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()

        filepath = os.path.join(output_dir, filename)
        with open(filepath, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(columns)
            writer.writerows(rows)

        logger.info(f"Exported {len(rows)} leads to {filepath}")

    # Full pack
    query = """
        SELECT
            p.property_address as "Address",
            p.city as "City",
            pr.owner_name as "Owner Name",
            sl.phone as "Phone",
            sl.email as "Email",
            pr.market_value as "Property Value",
            sl.score as "Lead Score",
            sl.category as "Category",
            p.permit_type as "Permit Type",
            p.issued_date as "Permit Date"
        FROM clients_scoredlead sl
        JOIN leads_permit p ON sl.permit_id = p.id
        LEFT JOIN leads_property pr ON p.property_address = pr.property_address
        WHERE sl.score >= 50
        ORDER BY sl.score DESC
    """

    with conn.cursor() as cur:
        cur.execute(query)
        columns = [desc[0] for desc in cur.description]
        rows = cur.fetchall()

    filepath = os.path.join(output_dir, "full_dfw_pack_enriched.csv")
    with open(filepath, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(columns)
        writer.writerows(rows)

    logger.info(f"Exported {len(rows)} leads to {filepath}")


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description='Tracerfy Skip Tracing Integration')
    parser.add_argument('--limit', type=int, help='Limit number of leads to process')
    parser.add_argument('--category', type=str, help='Only process specific category (pool, plumbing, etc.)')
    parser.add_argument('--export', action='store_true', help='Export enriched sales packs')
    parser.add_argument('--dry-run', action='store_true', help='Transform and show CSV without submitting')
    parser.add_argument('--check-queues', action='store_true', help='Check status of pending queues')
    args = parser.parse_args()

    # Get API key
    api_key = os.environ.get('TRACERFY_API_KEY')
    if not api_key and not args.export and not args.dry_run:
        raise ValueError("TRACERFY_API_KEY environment variable not set")

    conn = get_db_connection()

    try:
        if args.export:
            export_enriched_packs(conn)
            return

        if args.check_queues:
            client = TracerfyClient(api_key)
            queues = client.get_queues()
            print(json.dumps(queues, indent=2))
            return

        # Fetch leads
        leads = get_leads_for_tracing(conn, limit=args.limit, category=args.category)

        if not leads:
            logger.info("No leads to process (all already have phone/email or no valid owner name)")
            return

        logger.info(f"Found {len(leads)} leads to skip trace")

        # Calculate cost
        cost = len(leads) * 0.009
        logger.info(f"Estimated cost: ${cost:.2f}")

        # Transform to CSV (works without API key for dry-run)
        client = TracerfyClient(api_key or "dry-run-no-key")
        csv_data = client.transform_leads_to_csv(leads)

        if args.dry_run:
            print("\n=== TRANSFORMED CSV (first 20 lines) ===")
            lines = csv_data.split('\n')[:20]
            for line in lines:
                print(line)
            print(f"\n... ({len(leads)} total rows)")
            return

        # Submit to Tracerfy
        logger.info("Submitting to Tracerfy API...")
        result = client.submit_trace(csv_data)
        queue_id = result.get('queue_id')
        logger.info(f"Submitted! Queue ID: {queue_id}")

        # Wait for completion
        logger.info("Waiting for trace completion...")
        queue_data = client.wait_for_completion(queue_id)

        # Get results
        if 'download_url' in queue_data:
            trace_results = client.download_results(queue_data['download_url'])
        elif 'results' in queue_data:
            trace_results = queue_data['results']
        else:
            trace_results = []

        logger.info(f"Received {len(trace_results)} traced records")

        # Update database (pass original leads for address matching)
        updated = update_leads_with_trace_data(conn, trace_results, leads)

        # Summary
        print(f"\n=== SKIP TRACE COMPLETE ===")
        print(f"Leads processed: {len(leads)}")
        print(f"Records returned: {len(trace_results)}")
        print(f"Database updated: {updated}")
        print(f"Cost: ${cost:.2f}")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
