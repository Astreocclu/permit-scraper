#!/usr/bin/env python3
"""
Little Elm Excel Parser
Parses MyGov Excel exports from Little Elm into standardized JSON format.

Little Elm (55K pop) uses MyGov with Excel export from Reports section.
Excel files are typically found in /tmp/browser-use-downloads-*/
"""

import pandas as pd
import json
import os
import re
from pathlib import Path
from datetime import datetime

# Output directory
OUTPUT_FILE = Path(__file__).parent.parent / "data" / "raw" / "little_elm_mygov.json"


def find_latest_excel():
    """Find the most recent Little Elm Excel file in browser-use downloads."""
    search_patterns = [
        "/tmp/browser-use-downloads-*/All Issued Permits*.xlsx",
        "/tmp/browser-use-downloads-*/all issued permits*.xlsx",
    ]

    excel_files = []
    for pattern in search_patterns:
        import glob
        excel_files.extend(glob.glob(pattern))

    if not excel_files:
        raise FileNotFoundError(
            "No Little Elm Excel files found in /tmp/browser-use-downloads-*/"
        )

    # Filter for files with actual data (size > 10KB)
    valid_files = [(f, os.path.getsize(f), os.path.getmtime(f))
                   for f in excel_files if os.path.getsize(f) > 10000]

    if not valid_files:
        raise FileNotFoundError(
            f"Found {len(excel_files)} Excel files but none had significant data (>10KB)"
        )

    # Sort by modification time, return most recent
    valid_files.sort(key=lambda x: x[2], reverse=True)
    latest = valid_files[0]

    print(f"Found {len(valid_files)} valid Excel file(s)")
    print(f"Using most recent: {latest[0]}")
    print(f"  Size: {latest[1]:,} bytes")
    print(f"  Modified: {datetime.fromtimestamp(latest[2])}")

    return latest[0]


def parse_contractor_from_credential(credential_contacts):
    """
    Parse contractor info from 'Credential Contacts' field.

    Format: "Name CompanyName (Type), Name2 Company2 (Type2), ..."
    We extract the first General Contractor, or failing that, the first contractor.

    Returns: (name, company) or (None, None)
    """
    if pd.isna(credential_contacts) or not credential_contacts:
        return None, None

    # Split by comma to get individual contractors
    contractors = credential_contacts.split(", ")

    # Look for General Contractor first
    general_contractor = None
    first_contractor = None

    for contractor in contractors:
        # Skip if it's just a continuation
        if not contractor.strip():
            continue

        if first_contractor is None:
            first_contractor = contractor

        if "General Contractor" in contractor:
            general_contractor = contractor
            break

    # Use general contractor if found, otherwise first contractor
    selected = general_contractor or first_contractor

    if not selected:
        return None, None

    # Parse: "FirstName LastName CompanyName (Type)"
    # Remove the type in parentheses
    match = re.match(r"^(.+?)\s+\(.*?\)\s*$", selected.strip())
    if match:
        name_company = match.group(1).strip()
    else:
        name_company = selected.strip()

    # Split into name and company
    # Heuristic: First two words are name, rest is company
    parts = name_company.split()
    if len(parts) >= 3:
        name = " ".join(parts[:2])
        company = " ".join(parts[2:])
    elif len(parts) == 2:
        # Could be "FirstName LastName" or "FirstName Company"
        # If second word is capitalized and looks like a company, treat as company
        if parts[1][0].isupper() and len(parts[1]) > 3:
            name = parts[0]
            company = parts[1]
        else:
            name = " ".join(parts)
            company = None
    else:
        name = name_company
        company = None

    return name, company


def clean_phone(phone):
    """Clean phone number - remove non-digits."""
    if pd.isna(phone):
        return None
    phone_str = str(phone).strip()
    digits = re.sub(r"\D", "", phone_str)
    return digits if digits else None


def clean_email(email):
    """Clean email address."""
    if pd.isna(email):
        return None
    email_str = str(email).strip().lower()
    return email_str if "@" in email_str else None


def parse_date(date_val):
    """Parse date from Excel."""
    if pd.isna(date_val):
        return None

    # If it's already a datetime object
    if isinstance(date_val, pd.Timestamp):
        return date_val.strftime("%m/%d/%Y")

    # Try parsing string
    date_str = str(date_val).strip()
    try:
        dt = pd.to_datetime(date_str)
        return dt.strftime("%m/%d/%Y")
    except:
        return date_str


def parse_excel(file_path):
    """Parse Little Elm Excel file into standard permit format."""
    print(f"\nParsing: {file_path}")

    df = pd.read_excel(file_path)
    print(f"Found {len(df)} permits in Excel file")

    permits = []

    for idx, row in df.iterrows():
        # Extract basic fields
        permit = {
            "permit_id": str(row["Permit Number"]).strip() if pd.notna(row["Permit Number"]) else None,
            "permit_type": str(row["Template name"]).strip() if pd.notna(row["Template name"]) else None,
            "description": str(row["Permit Description"]).strip() if pd.notna(row["Permit Description"]) else None,
            "address": str(row["Project Address"]).strip() if pd.notna(row["Project Address"]) else None,
            "issued_date": parse_date(row["Permit Issued Date"]),
        }

        # Add value if present
        if pd.notna(row["Project Valuation"]) and row["Project Valuation"] != 0:
            try:
                permit["value"] = float(row["Project Valuation"])
            except:
                pass

        # Try to get contractor from dedicated fields first
        contractor_name = None
        contractor_phone = None
        contractor_email = None

        if pd.notna(row["Contractor Name"]):
            contractor_name = str(row["Contractor Name"]).strip()

        if pd.notna(row["Contractor Phone Number"]):
            contractor_phone = clean_phone(row["Contractor Phone Number"])

        if pd.notna(row["Contractor Email"]):
            contractor_email = clean_email(row["Contractor Email"])

        # If contractor name not in dedicated field, parse from Credential Contacts
        if not contractor_name:
            name, company = parse_contractor_from_credential(row["Credential Contacts"])
            if company:
                contractor_name = company
            elif name:
                contractor_name = name

        # Add contractor fields (even if None, to match existing format)
        permit["contractor_name"] = contractor_name
        permit["contractor_phone"] = contractor_phone
        permit["contractor_email"] = contractor_email

        permits.append(permit)

    return permits


def main():
    """Main execution function."""
    print("Little Elm Excel Parser")
    print("=" * 50)

    try:
        # Find latest Excel file
        excel_file = find_latest_excel()

        # Parse Excel
        permits = parse_excel(excel_file)

        # Save to JSON
        OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

        with open(OUTPUT_FILE, "w") as f:
            json.dump(permits, f, indent=2)

        print(f"\n✓ Successfully parsed {len(permits)} permits")
        print(f"✓ Saved to: {OUTPUT_FILE}")

        # Show statistics
        with_contractor = sum(1 for p in permits if p["contractor_name"])
        with_phone = sum(1 for p in permits if p["contractor_phone"])
        with_email = sum(1 for p in permits if p["contractor_email"])
        with_value = sum(1 for p in permits if "value" in p)

        print(f"\nStatistics:")
        print(f"  Total permits: {len(permits)}")
        print(f"  With contractor name: {with_contractor} ({with_contractor/len(permits)*100:.1f}%)")
        print(f"  With phone: {with_phone} ({with_phone/len(permits)*100:.1f}%)")
        print(f"  With email: {with_email} ({with_email/len(permits)*100:.1f}%)")
        print(f"  With value: {with_value} ({with_value/len(permits)*100:.1f}%)")

        # Show sample
        print(f"\nSample permit:")
        print(json.dumps(permits[0], indent=2))

        return 0

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
