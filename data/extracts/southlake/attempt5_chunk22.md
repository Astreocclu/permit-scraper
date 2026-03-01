<url>
https://energov.cityofsouthlake.com/EnerGov_Prod/SelfService#/search
</url>
<query>
Extract permit data for each result on this page: permit_number (Case Number), issue_date (Issued Date), permit_type (Type), status (Status), address (Address), description (Description). Return as JSON list of objects with those field names.
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
    "_note_issue_date_missing_from_page_for_HVAC24_0419_but_applied_and_issued_dates_match_in_context_so_using_applied_date_as_fallback_if_needed_but_field_is_empty_per_extraction"
  }
]
</result>