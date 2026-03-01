<url>
https://energov.cityofsouthlake.com/EnerGov_Prod/SelfService#/search
</url>
<query>
Extract all permit entries from the search results on this page. For each permit entry (each entityRecord div), extract:
- permit_number: text of the link inside the div with name=label-CaseNumber (e.g., 'WILD24-0001')
- issue_date: text after 'Issued Date' label in div with name=label-IssuedDate (format mm/dd/yyyy)
- permit_type: text after 'Type' label in div with name=label-CaseType
- status: text inside span within tyler-highlight inside div with name=label-Status
- address: text after 'Address' label in div with name=label-Address
- description: text after 'Description' label in div with name=label-Description if present
Return as a list of objects with keys exactly as above.
</query>
<result>
[
  {
    "permit_number": "WILD24-0001",
    "issue_date": "02/28/2024",
    "permit_type": "Wildflower",
    "status": "Closed",
    "address": "307 PARKWOOD DR",
    "description": "Establishment of a no-mow area to allow wildflowers to grow until approximately July."
  },
  {
    "permit_number": "WHTR24-0344",
    "issue_date": "12/23/2024",
    "permit_type": "Plumbing Water Heater",
    "status": "Closed",
    "address": "1209 OAKWOOD TRL",
    "description": "50 gallon gas water heater in home."
  },
  {
    "permit_number": "WHTR24-0343",
    "issue_date": "12/19/2024",
    "permit_type": "Plumbing Water Heater",
    "status": "Closed",
    "address": "309 TRAIL DUST DR",
    "description": "TANK TO TANKLESS INSTALL"
  },
  {
    "permit_number": "WHTR24-0342",
    "issue_date": "12/18/2024",
    "permit_type": "Plumbing Water Heater",
    "status": "Closed",
    "address": "204 CANYON LAKE DR",
    "description": "replacing one water heater 5o gal"
  },
  {
    "permit_number": "WHTR24-0341",
    "issue_date": "12/17/2024",
    permit_type: Plumbing Water Heater,
    status: Closed,
    address: 2370 LONESOME DOVE AVE,
    description: Replace water heater in garage
  },
  {
    permit_number: WHTR24-0340,
    issue_date: 12/16/2024,
    permit_type: Plumbing Water Heater,
    status: Closed,
    address: 1435 N PEYTONVILLE AVE,
    description: install 50 gal gas water heater
  },
  {
    permit_number: WHTR24-0339,
    issue_date: 12/12/2024,
    permit_type: Plumbing Water Heater,
    status: Closed,
    address: 1795 KINGSWOOD DR,
    description: REPLACE 50 GAL GAS WATER HEATER IN CLOSET
  },
  {
    permit_number: WHTR24-0338,
    issue_date: 12/12/2024,
    permit_type: Plumbing Water Heater,
    status: Closed,
    address: 1601 BYRON NELSON PKWY,

</result>