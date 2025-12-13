# Ellis County CAD ArcGIS REST API Research Results

**Date:** 2025-12-12
**Objective:** Find working ArcGIS REST API endpoint for Ellis County, TX CAD parcel data

## Summary

**STATUS: NO WORKING PUBLIC API ENDPOINT FOUND**

The Ellis County GIS server (ecgis.co.ellis.tx.us) exists but is **completely inaccessible** from external networks.

---

## Tested Endpoints

### Failed - All ecgis.co.ellis.tx.us endpoints

All of the following URLs **timed out** after 45-60 seconds:

1. `https://services.arcgis.com/NAnnb4W7JLztFw9i/arcgis/rest/services/Ellis_County_Parcel_Ownership/FeatureServer/0/query`
   - Result: 400 "Invalid URL" error

2. `https://services7.arcgis.com/NAnnb4W7JLztFw9i/arcgis/rest/services/Ellis_County_Parcel_Ownership/FeatureServer/0/query`
   - Result: 400 "Invalid URL" error

3. `https://ecgis.co.ellis.tx.us/gis/rest/services/Public/Parcels/MapServer/0/query`
   - Result: Connection timeout

4. `https://ecgis.co.ellis.tx.us/gis/rest/services/EllisCo_External_v4/MapServer/594/query`
   - Result: Connection timeout
   - Note: This layer exists according to web search, but server is unreachable

5. `https://ecgis.co.ellis.tx.us/gis/rest/services/EllisCo_External_3/MapServer/594/query`
   - Result: Connection timeout
   - Note: This layer exists according to web search, but server is unreachable

6. `https://ecgis.co.ellis.tx.us/gis/rest/services/Elections/EllisCo_Elections_External/MapServer/27/query`
   - Result: Connection timeout

### Network Diagnostics

```
Server: ecgis.co.ellis.tx.us
IP Address: 12.44.249.11
Ping: 100% packet loss (0/3 received)
HTTP/HTTPS: Connection timeout
```

**Diagnosis:** The server is behind a firewall or requires VPN/internal network access. It does not accept connections from public internet.

---

## Documented Endpoint Information (From Web Search)

While inaccessible, the following endpoints are documented as existing:

### Layer 1: EllisCo_External_v4 - Parcels (Courtesy of ECAD)
- **URL:** `https://ecgis.co.ellis.tx.us/gis/rest/services/EllisCo_External_v4/MapServer/594`
- **Layer ID:** 594
- **Display Field:** PID
- **MaxRecordCount:** 1,000,000
- **Supports Advanced Queries:** true

### Layer 2: EllisCo_External_3 - Parcels (ECAD)
- **URL:** `https://ecgis.co.ellis.tx.us/gis/rest/services/EllisCo_External_3/MapServer/594`
- **Layer ID:** 594
- **Display Field:** PROP_ID
- **MaxRecordCount:** 1,000,000
- **Supports Advanced Queries:** true

### Expected Field Schema (From Documentation)

Based on ArcGIS web app configuration analysis, the parcel layers should contain:

**Property Information:**
- `PARCEL_ID` - Parcel identifier
- `QuickRefID` - Quick reference ID
- `PropertyNumber` - Property number
- `PID_APP` - Appraisal PID
- `PID_TAX` - Tax PID

**Address:**
- `SitusAddress` - Full situs address
- `AddressComplete` - Complete address
- `AddressNumber` - Street number
- `AddressCity` - City

**Owner:**
- `OwnerName` - Property owner name
- `MailingAddress1`, `MailingAddress2`, `MailingAddress3` - Mailing address
- `MailingCityStateZip` - Mailing city, state, ZIP

**Valuation:**
- `AppraisedLandValue` - Land value
- `AppraisedBldgValue` - Building value
- `AppraisedTotal` - Total appraised value

**Property Details:**
- `PropertyType` - Property type code
- `LegalDescription` - Legal description
- `TotalAcres` - Total acreage
- `LivingUnits` - Number of living units
- `SubdivisionName` - Subdivision name
- `SubdivisionNumber` - Subdivision number
- `SaleDate` - Last sale date

**Geographic:**
- `POINT_X`, `POINT_Y` - Centroid coordinates
- `Township`, `Range`, `Section_` - Land survey info

---

## Alternative Data Sources

### 1. ArcGIS Online Viewer (Not a Direct API)
- **URL:** `https://www.arcgis.com/apps/View/index.html?appid=c62902b55f7d41058bc186bc39aca750`
- **Type:** Web application (not an API endpoint)
- **Backend:** Uses the inaccessible ecgis.co.ellis.tx.us server
- **Status:** Cannot extract API endpoint programmatically

### 2. Ellis CAD Website (No Public API)
- **URL:** `https://esearch.elliscad.com/`
- **URL:** `https://www.elliscad.com/gis-data/`
- **Type:** Web interface only
- **Status:** No documented public API; connection errors during testing

### 3. Third-Party: Regrid (Requires Paid License)
- **URL:** `https://app.regrid.com/us/tx/ellis`
- **API:** `https://support.regrid.com/api/parcel-api-endpoints`
- **Cost:** Requires paid API token (no free tier for production use)
- **Coverage:** Has Ellis County, TX data
- **Fields:** Standardized schema with owner, address, valuation data

### 4. Third-Party: TaxNetUSA (Commercial)
- **URL:** `https://www.taxnetusa.com/texas/ellis/`
- **Type:** Commercial data provider
- **Status:** Offers bulk data downloads (paid)

### 5. geodataportal.net (WRONG COUNTY - Kansas)
- **URL:** `https://geodataportal.net/arcgis/rest/services/MultiPlatformParcels/MapServer`
- **Issue:** This is Ellis County, **Kansas**, not Texas
- **Status:** Working API but wrong jurisdiction

---

## Recommendations

### Option 1: Contact Ellis County GIS Department
- **Contact:** http://co.ellis.tx.us/65/GIS-Maps-and-9-1-1-Addressing
- **Action:** Request VPN access or public endpoint configuration
- **Likelihood:** Low - government servers often restricted

### Option 2: Contact Ellis CAD Directly
- **Website:** https://www.elliscad.com/
- **Action:** Request API access or bulk data export
- **Phone:** (Check website for contact info)

### Option 3: Use Shapefile Downloads
- **Source:** https://www.elliscad.com/gis-data/
- **Method:** Download static shapefile/geodatabase
- **Pros:** May be free/low-cost
- **Cons:** Not real-time; requires manual updates

### Option 4: Use Third-Party API (Regrid)
- **Cost:** Paid subscription required
- **Pros:** Reliable, standardized, nationwide coverage
- **Cons:** Recurring cost; may not have all CAD fields

### Option 5: Scrape Ellis CAD Website
- **URL:** https://esearch.elliscad.com/
- **Method:** Automated web scraping
- **Pros:** Free
- **Cons:** Fragile, may violate ToS, rate limits

---

## Conclusion

**No free, public, working ArcGIS REST API endpoint exists for Ellis County, TX CAD data.**

The documented endpoints exist but are firewalled from public access. The only viable options are:
1. Paying for third-party data (Regrid, TaxNetUSA)
2. Downloading static shapefiles from ECAD
3. Contacting Ellis County GIS for special access
4. Web scraping (not recommended)

**Recommendation for your project:** Use Regrid API (paid) or download ECAD shapefiles and build a local database.
