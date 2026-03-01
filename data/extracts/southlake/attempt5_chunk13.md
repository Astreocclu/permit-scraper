<url>
https://energov.cityofsouthlake.com/EnerGov_Prod/SelfService#/search
</url>
<query>
Extract permit records: permit_number (div[name=label-CaseNumber] a), issue_date (div[name=label-IssuedDate]), permit_type (div[name=label-CaseType]), status (div[name=label-Status] span), address (div[name=label-Address]), description (div[name=label-Description]). Return as JSON list.
</query>
<result>
[
  {
    "permit_number": "CRET24-0047",
    "issue_date": "12/23/2024",
    "permit_type": "Concrete (Drive Approach)",
    "status": "Closed",
    "address": "4525 SODA RIDGE RD",
    "description": "Concrete drive to garage"
  },
  {
    "permit_number": "RADD24-0096",
    "issue_date": "12/23/2024",
    "permit_type": "Residential Addition Conditioned Space",
    "status": "Closed",
    "address": "1306 POWDER RIVER TRL",
    "description": "Enclose Patio to provide additional living space. Remodel Kitchen moving sink 2' and replacing cabinets. NO FORM BOARD SURVEY REQUIRED"
  },
  {
    "permit_number": "PLMB24-0300",
    "issue_date": "12/23/2024",
    "permit_type": "Plumbing Permit (Residential)",
    "status": "Closed",
    "address": "408 OAK RIDGE CT",
    "description": "replacing copper pipes up to 5 foot tunnel to access. - Slab Leak Water Line Tunnel Repair up to 5 Ft."
  },
  {
    "permit_number": "RPOOL24-0077",
    "issue_date": "12/23/2024",
    "permit_type": "Pool & Spa (Residential)",
    "status": "Issued",
    "address": "2050 SHADY OAKS DR",
    "description": "Inground pool with fire feature appliance insert with fountain"
  },
  {
    "permit_number": "HVAC24-0419",
    "issue_date": "",
    "$note_issue_date_missing_from_content_for_HVAC24_0419_but_applied_and_issued_dates_match_in_content_for_other_permits._The_content_shows_Applied_Date_12/23/2024_and_Issued_Date_12/23/2024_for_HVAC24-0419._However_the_specific_div[name=label-IssuedDate]_is_not_explicitly_found_in_the_markdown._The_permit_entry_includes_'Issued Date12/23/2024'_in_the_text._Extracting_based_on_pattern."
  }
]
</result>