<url>
https://energov.cityofsouthlake.com/EnerGov_Prod/SelfService#/search
</url>
<query>
Extract up to 10 permit records. For each get: permit_number from div[name=label-CaseNumber] a text; issue_date from div[name=label-IssuedDate]; permit_type from div[name=label-CaseType]; status from div[name=label-Status] span; address from div[name=label-Address]; description from div[name=label-Description]. Return as JSON list.
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
    "issue_date": null,
    // Note: The provided content for HVAC24-0419 shows an Issued Date of 12/23/2024, but the div[name=label-IssuedDate] structure is not present in the markdown snippet for this record. The date is listed in a line like 'Issued Date12/23/2024'. Using the explicit data from that line.
  }
]

Note: The content appears to be truncated. To extract up to 10 complete records, more content is needed. Use start_from_char=30000 to continue from where truncation occurred.
</result>