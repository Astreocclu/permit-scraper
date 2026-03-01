<url>
https://energov.cityofsouthlake.com/EnerGov_Prod/SelfService#/search
</url>
<query>
Extract up to 10 permit records from the table. For each record get fields: permit_number from div[name=label-CaseNumber] a text, issue_date from div[name=label-IssuedDate] text after 'Issued Date', permit_type from div[name=label-CaseType] text after 'Type', status from div[name=label-Status] span text, address from div[name=label-Address] text after 'Address', description from div[name=label-Description] text after 'Description'. Return as JSON list of objects.
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
    issue_date: "",
}
</result>