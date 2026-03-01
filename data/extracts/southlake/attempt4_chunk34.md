<url>
https://energov.cityofsouthlake.com/EnerGov_Prod/SelfService#/search
</url>
<query>
Extract permit_number, issue_date, permit_type, status, address, description for each permit record visible on this page. Return as JSON list with max 10 items.
</query>
<result>
[
  {
    "permit_number": "RPOOL24-0003",
    "issue_date": "01/30/2024",
    "permit_type": "Pool (Residential)",
    "status": "Closed",
    "address": "825 E DOVE RD",
    "description": "In-Ground Swimming Pool/Spa ONLY (Fire Feature/Grill/Kitchen - REMOVED FROM SCOPE OF WORK 3/21/2024)"
  },
  {
    "permit_number": "PLMB24-0035",
    "issue_date": "01/29/2024",
    "permit_type": "Plumbing Permit (Residential)",
    "status": "Expired",
    "address": "1355 BENT TRAIL CIR",
    "description": "gas line installation- Heat Pump to swimming pool"
  },
  {
    "permit_number": "DEMO24-0003",
    "issue_date": "01/29/2024",
    "permit_type": "Demolition (Residential)",
    "status": "Closed",
    "address": "300 FOXBOROUGH LN",
    "description": "Remove current in ground swimming pool.-"
  },
  {
    "permit_number": "RPOOL24-0004",
    "issue_date": "01/26/2024",
    "permit_type": "Pool & Spa (Residential)",
    "status": "Issued",
    "address": "2612 CANOPY CT",
    "description": "Installation of gunite pool and spa"
  },
  {
    "permit_number": "RADD23-0116",
    "issue_date": null,
    // Note: The 'Issued Date' field for this permit is not visible in the provided content. The 'Applied Date' is shown as 12/05/2023, but the 'Issued Date' is not listed in the snippet. Therefore, issue_date is set to null.
    // However, a closer look at the snippet shows: 
      // | Permit NumberRPOOL24-0003
      // | Applied Date01/23/2024
      // | TypePool (Residential)
      // | Issued Date01/30/2024
      // ...
      // For RADD23-0116, the snippet shows:
      // | Permit NumberRADD23-0116
      // | Applied Date12/05/2023
      // | TypeResidential Addition Conditioned & Uncond
      // | Issued Date01/24/2024
      // ...
      // So the Issued Date is present. Let's correct.
    
"issue_date":"01/24/2024",

"permit_type":"Residential Addition Conditioned & Uncond",

"status":"Expired",

"address":"1584 RANDOL MILL AVE",

"description":"Adding: Master bed, bath, Pool bath, Laundry rm, expanding Kitchen. New mother-in-law's quarters, new 2 car Garage. Remodeling old garage to Family room, pantry, kitchen remodel. Extending the front Porch cover. Adding new 620 sf back attached Patio cover"

},

{

"permit_number":"RPOOL24-0002",

"issue_date":"01/24/2024",

"permit_type":"Pool & Spa (Residential)",

"status":"Closed",

"address":"2405 AMELIA ISLAND PATH",

"description":"Building a Pool and Outdoor Kitchen and Fire Pit"

},

{

"permit_number":"RPOOL24-0001",

"issue_date":"01/22/2024",

"permit_type":"Pool & Spa (Residential)",

"status":"Closed",

"address":"300 SANCTUARY CIR",

"description":"Installation of gunite pool/spa. With fire pit"

},

{

"permit_number":"COMR23-0157",

"issue_date":"01/17/2024",

"permit_type":"Commercial Remodel",

"status":"CO Issued",

"address":"2301 W SOUTHLAKE BLVD Unit: 300",

"description":"LESLIE'S POOL SUPPLIES - Tenant interior alteration of Suites 300-500 to include new walls, finishes, fixtures and paint - ARE THERE MULTIPLE METERS FOR THIS SPACE?"

},

{

"permit_number":"TREP23-0090",

"issue_date":"01/17/2024",

"permit_type":"Tree Protection (Residential)",

"status":"Closed",

"address":"1350 WOODBROOK LN",

"description":"tree survey showing removal for contruction of house and pool. Saving remaining trees. Request moving from ordinance 585B to 585E per discussion with Keith Martin. Only have removed trees within pad/drive/pool/deck plus 12'. Goal is to save some of those trees when possible given lean direction etc."

},

{

// The query asks for max 10 items. We have listed 9 so far. The next permit in the list is RPOOL23-0079.

// However, note that the first item in the list was RPOOL24-0003, and we have included up to TREP23-0090.

// Let's count: 
//  1. RPOOL24-0003
//  2. PLMB24-0035
//  3. DEMO24-0003
//  4. RPOOL24-0004
//  5. RADD23-0116
//  6. RPOOL24-0002
//  7. RPOOL24-0001
//  8. COMR23-0157
//  9. TREP23-0090

// We need one more to reach max 10.

// The next permit after TREP23-0090 in the content is RPOOL23-0079.

// However, note that the content shows a paging structure and there are multiple pages.

// But we are only to extract from the visible page.

// The visible page includes permits from RPOOL24-0003 down to at least RPOOL23-0082.

// Let's take the next one in sequence from the content after TREP23-0090:

// The content shows:

// PreviousNextNextTopTopPaging OptionsPaging OptionsFilter OptionsFilter OptionsMain MenuMain Menu

// Permit NumberRPOOL23-0079

// Applied Date12/14/2023

// TypePool & Spa (Residential)

// Issued Date01/12/2024

// Project Name

// Expiration Date11/12/2024

// StatusClosed

// Finalized Date05/16/2024

// Main Parcel00006-1-20R1

// Address1150 HAVEN CIR

// DescriptionInground pool with spa only

//

So we can include that as the 10th.

But note: The query says max 10 items. We can stop at 10.

Let's create the 10th item.

}

]
</result>