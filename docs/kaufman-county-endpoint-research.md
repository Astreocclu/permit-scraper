# Kaufman County CAD ArcGIS Endpoint Research

**Date:** 2025-12-12
**Task:** Find working ArcGIS REST API endpoint for Kaufman County CAD parcel data

## Results

### ✅ Working Endpoint Found

**Service URL:**
```
https://services9.arcgis.com/26s7bQ5Q51Gt4J2Q/arcgis/rest/services/KaufmanCADWebService/FeatureServer
```

**Query Endpoint (Parcels Layer 0):**
```
https://services9.arcgis.com/26s7bQ5Q51Gt4J2Q/arcgis/rest/services/KaufmanCADWebService/FeatureServer/0/query
```

**Service Owner:** bis_kaufmancad (Official Kaufman CAD account)
**Access:** Public (no authentication required)
**Status:** ✅ Active and working

---

## Available Fields

### Address Fields
- `situs_num` - House/building number
- `situs_street_prefx` - Street prefix (N, S, E, W)
- `situs_street` - Street name
- `situs_street_sufix` - Street suffix (St, Ave, Rd, etc.)
- `situs_city` - City name
- `situs_state` - State (TX)
- `situs_zip` - ZIP code
- `addr_line1` - Mailing address line 1
- `addr_line2` - Mailing address line 2
- `addr_line3` - Mailing address line 3
- `addr_city` - Mailing city
- `addr_state` - Mailing state
- `zip` - Mailing ZIP

### Owner Fields
- `file_as_name` - Owner name (primary field)
- `owner_tax_yr` - Tax year for ownership

### Value Fields
- `market` - Total market value
- `land_val` - Land value
- `imprv_val` - Improvement/building value

### Property Fields
- `prop_id` - Property ID (numeric)
- `prop_id_text` - Property ID (text)
- `legal_acreage` - Property acreage
- `legal_desc` - Legal description line 1
- `legal_desc2` - Legal description line 2
- `legal_desc3` - Legal description line 3
- `tract_or_lot` - Tract or lot number
- `abs_subdv_cd` - Abstract/subdivision code
- `block` - Block number
- `map_id` - Map ID
- `geo_id` - Geographic ID

### Administrative Fields
- `hood_cd` - Neighborhood code
- `school` - School district code
- `city` - City code
- `county` - County code
- `Deed_Date` - Deed date
- `Deed_Seq` - Deed sequence
- `Volume` - Deed volume
- `Page` - Deed page
- `Number` - Deed number

---

## Field Mapping for Integration

| Required Field | Kaufman CAD Field | Type | Notes |
|---------------|-------------------|------|-------|
| `owner_name` | `file_as_name` | String | ✅ Available |
| `address` | Composite of `situs_num`, `situs_street`, `situs_city` | String | ✅ Available (combine fields) |
| `market_value` | `market` | Double | ✅ Available |
| `year_built` | N/A | N/A | ❌ **NOT AVAILABLE** |
| `square_feet` | N/A | N/A | ❌ **NOT AVAILABLE** |

**Additional Available:**
- `land_val` - Land value separate from improvements
- `imprv_val` - Improvement value (but no building details)
- `legal_acreage` - Property acreage

---

## Query Examples

### Basic Query (Get Sample Record)
```python
import requests

url = 'https://services9.arcgis.com/26s7bQ5Q51Gt4J2Q/arcgis/rest/services/KaufmanCADWebService/FeatureServer/0/query'

params = {
    'where': '1=1',
    'outFields': '*',
    'resultRecordCount': 1,
    'f': 'json'
}

response = requests.get(url, params=params, timeout=15)
data = response.json()
```

### Query by City
```python
params = {
    'where': "situs_city = 'FORNEY'",
    'outFields': 'file_as_name,situs_num,situs_street,situs_city,market,land_val,imprv_val',
    'resultRecordCount': 10,
    'f': 'json'
}
```

### Query by Street Name
```python
params = {
    'where': "situs_street LIKE '%MAIN%'",
    'outFields': 'file_as_name,situs_num,situs_street,situs_city,market',
    'resultRecordCount': 10,
    'f': 'json'
}
```

### Query by Address Components
```python
params = {
    'where': "situs_num = '100' AND situs_street LIKE '%MAIN%' AND situs_city = 'FORNEY'",
    'outFields': 'file_as_name,situs_num,situs_street,situs_city,market,land_val,imprv_val,legal_acreage',
    'f': 'json'
}
```

---

## Sample Response

```json
{
  "features": [
    {
      "attributes": {
        "prop_id": 6531,
        "prop_id_text": "6531",
        "owner_tax_yr": 2026,
        "file_as_name": "CRENSHAW JOHN WESLEY & PATSY",
        "legal_acreage": 7.693,
        "legal_desc": "JNO GREGG, TRACT 550.00; 7.693 ACRES",
        "land_val": 670214,
        "imprv_val": 0,
        "market": 670214,
        "situs_num": "0",
        "situs_street": "HWY 80",
        "situs_city": "FORNEY",
        "situs_state": "TX",
        "addr_line2": "PO BOX 905",
        "addr_city": "FORNEY",
        "addr_state": "TX",
        "zip": "75126"
      }
    }
  ]
}
```

---

## Testing URLs That Failed

### ❌ URL 1 - Invalid
```
https://services.arcgis.com/f9Y1T9P58f25zDlm/arcgis/rest/services/PD_GIS_WebMap__DFW_External/MapServer/475/query
```
**Status:** Returns "Invalid URL" error (400)

### ❌ URL 2 - SSL Error
```
https://gis.pape-dawson.com/arcgis/rest/services/PD_GIS_WebMap__DFW_External/MapServer/475/query
```
**Status:** SSL certificate verification failed

### ❌ Other Attempted URLs
- `https://gis.kaufmancad.org` - Connection timeout
- `https://maps.kaufmancad.org` - Connection timeout
- `https://gis.kaufmancounty.net` - Connection timeout
- `https://gis.kaufmancounty.org` - Connection timeout

---

## Discovery Method

1. Searched ArcGIS Online portal for "Kaufman County parcel"
2. Found official service: `KaufmanCADWebService` by user `bis_kaufmancad`
3. Verified public access and tested query functionality
4. Documented available fields and query patterns

---

## Limitations

### ⚠️ Missing Building Data
The Kaufman County CAD endpoint **does NOT include** the following fields:
- `year_built` - Year building was constructed
- `square_feet` - Building square footage
- Building details (stories, bedrooms, bathrooms, etc.)

**Available building-related data:**
- `imprv_val` - Value of improvements (buildings)
- `legal_acreage` - Lot size in acres

### Possible Solutions
1. **Accept limitation** - Use available fields (owner, address, market value, acreage)
2. **Combine sources** - Use this endpoint for basic data, supplement with:
   - Kaufman County Appraisal District website scraping
   - Texas Open Data Portal
   - County assessor records (if available via API)
3. **Contact Kaufman CAD** - Request access to building detail data

---

## Recommendation

**Proceed with this endpoint** for Kaufman County integration with the following caveats:

✅ **Use for:**
- Owner name lookups
- Property address verification
- Market value / appraisal data
- Land value vs. improvement value
- Property acreage

❌ **Cannot provide:**
- Year built
- Square footage
- Building characteristics

**Integration Priority:** Medium
If year_built and square_feet are critical requirements, consider deprioritizing Kaufman County until alternative data sources are found, or implement with partial data and clearly document the limitations.

---

## Test Script

Full test script available at:
```
/home/reid/testhome/permit-scraper/kaufman_endpoint_test.py
```

Run with:
```bash
python3 kaufman_endpoint_test.py
```
