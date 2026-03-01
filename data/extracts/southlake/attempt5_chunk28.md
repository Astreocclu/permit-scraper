<url>
https://energov.cityofsouthlake.com/EnerGov_Prod/SelfService#/search
</url>
<query>
Extract all permits on this page with fields: permit_number (Case Number), issue_date (Issued Date), permit_type (Type), status (Status), address (Address), description (Description). Return JSON list.
</query>
<result>
[
  {
    "permit_number": "RPOOL24-0077",
    "issue_date": "12/23/2024",
    "permit_type": "Pool & Spa (Residential)",
    "status": "Issued",
    "address": "2050 SHADY OAKS DR",
    "description": "Inground pool with fire feature appliance insert with fountain"
  },
  {
    "permit_number": "TREP24-0085",
    "issue_date": "12/20/2024",
    "permit_type": "Tree Protection (Residential)",
    "status": "Closed",
    "address": "1214 WHISPERING LN",
    "description": "I am planning to put a pool in and I have one oak tree that will be near the construction."
  },
  {
    "permit_number": "PLMB24-0298",
    "issue_date": "12/19/2024",
    "permit_type": "Plumbing Permit (Residential)",
    "status": "Closed",
    "address": "708 ASHLEIGH LN",
    "description": "gas line capped to pool heater"
  },
  {
    "permit_number": "RPOOL24-0078",
    "issue_date": "12/09/2024",
    "permit_type": "Pool (Residential)",
    "status": "Issued",
    "address": "408 KEEN CT",
    "description": "Install gunite pool/spa and gas fire pit"
  },
  {
    "permit_number": "DEMO24-0052",
    "issue_date": "",
    issue_date: The provided content shows an Issued Date of 12/02/2024 for DEMO24-0052. However, the query asks for issue_date (Issued Date). The JSON should reflect the Issued Date from the content.
  }
]
</result>