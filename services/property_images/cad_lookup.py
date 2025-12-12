"""CAD account lookup service.

Wraps the ArcGIS CAD API queries from scripts/enrich_cad.py for use
in the property image fetcher.
"""
import re
from typing import Optional

import requests


def _escape_arcgis_value(value: str) -> str:
    """Escape single quotes for ArcGIS REST API WHERE clause."""
    return value.replace("'", "''")


# County API configurations (from scripts/enrich_cad.py)
COUNTY_CONFIGS = {
    'tarrant': {
        'name': 'Tarrant',
        'url': 'https://tad.newedgeservices.com/arcgis/rest/services/TAD/ParcelView/MapServer/1/query',
        'address_field': 'Situs_Addr',
        'fields': ["Situs_Addr", "Account_Nu"],
        'account_field': 'Account_Nu',
    },
    'dallas': {
        'name': 'Dallas',
        'url': 'https://maps.dcad.org/prdwa/rest/services/Property/ParcelQuery/MapServer/4/query',
        'address_field': 'SITEADDRESS',
        'fields': ["SITEADDRESS", "PARCELID"],
        'account_field': 'PARCELID',
    },
    'denton': {
        'name': 'Denton',
        'url': 'https://gis.dentoncounty.gov/arcgis/rest/services/CAD/MapServer/0/query',
        'address_field': 'situs_num',
        'fields': ["situs_num", "situs_street", "prop_id"],
        'account_field': 'prop_id',
    },
    'collin': {
        'name': 'Collin',
        'url': 'https://gismaps.cityofallen.org/arcgis/rest/services/ReferenceData/Collin_County_Appraisal_District_Parcels/MapServer/1/query',
        'address_field': 'GIS_DBO_AD_Entity_situs_num',
        'fields': ["GIS_DBO_AD_Entity_situs_display", "GIS_DBO_Parcel_PROP_ID"],
        'account_field': 'GIS_DBO_Parcel_PROP_ID',
    },
}

# ZIP to county mapping (subset for common DFW zips)
ZIP_TO_COUNTY = {
    # Tarrant County (Fort Worth, Arlington, etc.)
    '76101': 'tarrant', '76102': 'tarrant', '76103': 'tarrant', '76104': 'tarrant',
    '76105': 'tarrant', '76106': 'tarrant', '76107': 'tarrant', '76108': 'tarrant',
    '76109': 'tarrant', '76110': 'tarrant', '76111': 'tarrant', '76112': 'tarrant',
    '76113': 'tarrant', '76114': 'tarrant', '76115': 'tarrant', '76116': 'tarrant',
    '76117': 'tarrant', '76118': 'tarrant', '76119': 'tarrant', '76120': 'tarrant',
    '76121': 'tarrant', '76122': 'tarrant', '76123': 'tarrant', '76124': 'tarrant',
    '76126': 'tarrant', '76127': 'tarrant', '76129': 'tarrant', '76130': 'tarrant',
    '76131': 'tarrant', '76132': 'tarrant', '76133': 'tarrant', '76134': 'tarrant',
    '76135': 'tarrant', '76136': 'tarrant', '76137': 'tarrant', '76140': 'tarrant',
    '76148': 'tarrant', '76155': 'tarrant', '76177': 'tarrant', '76179': 'tarrant',
    '76180': 'tarrant', '76182': 'tarrant', '76244': 'tarrant', '76248': 'tarrant',
    '76001': 'tarrant', '76002': 'tarrant', '76006': 'tarrant', '76010': 'tarrant',
    '76011': 'tarrant', '76012': 'tarrant', '76013': 'tarrant', '76014': 'tarrant',
    '76015': 'tarrant', '76016': 'tarrant', '76017': 'tarrant', '76018': 'tarrant',
    '76021': 'tarrant', '76022': 'tarrant', '76034': 'tarrant', '76039': 'tarrant',
    '76040': 'tarrant', '76051': 'tarrant', '76053': 'tarrant', '76054': 'tarrant',
    '76092': 'tarrant', '76063': 'tarrant',
    # Dallas County
    '75201': 'dallas', '75202': 'dallas', '75203': 'dallas', '75204': 'dallas',
    '75205': 'dallas', '75206': 'dallas', '75207': 'dallas', '75208': 'dallas',
    '75209': 'dallas', '75210': 'dallas', '75211': 'dallas', '75212': 'dallas',
    '75214': 'dallas', '75215': 'dallas', '75216': 'dallas', '75217': 'dallas',
    '75218': 'dallas', '75219': 'dallas', '75220': 'dallas', '75223': 'dallas',
    '75224': 'dallas', '75225': 'dallas', '75226': 'dallas', '75227': 'dallas',
    '75228': 'dallas', '75229': 'dallas', '75230': 'dallas', '75231': 'dallas',
    '75232': 'dallas', '75233': 'dallas', '75234': 'dallas', '75235': 'dallas',
    '75236': 'dallas', '75237': 'dallas', '75238': 'dallas', '75240': 'dallas',
    '75241': 'dallas', '75243': 'dallas', '75244': 'dallas', '75246': 'dallas',
    '75247': 'dallas', '75248': 'dallas', '75249': 'dallas', '75251': 'dallas',
    '75252': 'dallas', '75253': 'dallas', '75254': 'dallas',
    '75038': 'dallas', '75039': 'dallas', '75060': 'dallas', '75061': 'dallas',
    '75062': 'dallas', '75063': 'dallas', '75050': 'dallas', '75051': 'dallas',
    '75052': 'dallas',
    # Denton County
    '76201': 'denton', '76205': 'denton', '76207': 'denton', '76208': 'denton',
    '76209': 'denton', '76210': 'denton', '76226': 'denton', '76227': 'denton',
    '76247': 'denton', '76249': 'denton', '76262': 'denton',
    '75006': 'denton', '75007': 'denton', '75010': 'denton', '75022': 'denton',
    '75028': 'denton', '75056': 'denton', '75057': 'denton', '75067': 'denton',
    '75068': 'denton', '75077': 'denton',
    # Collin County
    '75002': 'collin', '75013': 'collin', '75023': 'collin', '75024': 'collin',
    '75025': 'collin', '75034': 'collin', '75035': 'collin', '75069': 'collin',
    '75070': 'collin', '75071': 'collin', '75074': 'collin', '75075': 'collin',
    '75078': 'collin', '75080': 'collin', '75082': 'collin', '75093': 'collin',
    '75094': 'collin',
}

# City to county mapping (fallback)
CITY_TO_COUNTY = {
    'fort worth': 'tarrant', 'arlington': 'tarrant', 'grapevine': 'tarrant',
    'southlake': 'tarrant', 'colleyville': 'tarrant', 'keller': 'tarrant',
    'euless': 'tarrant', 'bedford': 'tarrant', 'hurst': 'tarrant',
    'dallas': 'dallas', 'irving': 'dallas', 'grand prairie': 'dallas',
    'mesquite': 'dallas', 'garland': 'dallas', 'richardson': 'dallas',
    'denton': 'denton', 'lewisville': 'denton', 'flower mound': 'denton',
    'frisco': 'collin', 'plano': 'collin', 'mckinney': 'collin',
    'allen': 'collin', 'prosper': 'collin',
}


def _get_county_from_address(address: str) -> Optional[str]:
    """Determine county from address via ZIP code or city name."""
    if not address:
        return None

    # Try ZIP code first
    zip_match = re.search(r'\b(\d{5})(?:-\d{4})?\b', address)
    if zip_match:
        zip_code = zip_match.group(1)
        if zip_code in ZIP_TO_COUNTY:
            return ZIP_TO_COUNTY[zip_code]

    # Try city name
    address_lower = address.lower()
    for city, county in CITY_TO_COUNTY.items():
        if city in address_lower:
            return county

    return None


def _parse_address(address: str) -> tuple[Optional[str], Optional[str]]:
    """Parse address into house number and street name."""
    if not address:
        return None, None

    # Clean address - take part before comma
    street = address.split(',')[0].strip().upper()

    # Remove unit/apt
    street = re.sub(r'\s+(APT|UNIT|STE|SUITE|#)\s*\S*', '', street)

    # Extract house number and street
    match = re.match(r'^(\d+)\s+(.+)$', street)
    if not match:
        return None, None

    house_num = match.group(1)
    street_name = match.group(2)

    # Strip suffix for broader matching
    street_core = re.sub(
        r'\s+(ST|AVE|DR|RD|LN|CT|BLVD|WAY|PL|CIR|PKWY|HWY|TRAIL|TRL)\.?$',
        '', street_name, flags=re.I
    ).strip()

    return house_num, street_core if len(street_core) >= 3 else street_name


def _query_county(address: str, county: str, timeout: int = 30) -> Optional[dict]:
    """Query a specific county's CAD API."""
    if county not in COUNTY_CONFIGS:
        return None

    config = COUNTY_CONFIGS[county]
    house_num, street_core = _parse_address(address)
    if not house_num or not street_core:
        return None

    # Build WHERE clause with escaped values
    escaped_house_num = _escape_arcgis_value(house_num)
    escaped_street_core = _escape_arcgis_value(street_core)

    if county == 'tarrant':
        where = f"Situs_Addr LIKE '{escaped_house_num} %{escaped_street_core}%'"
    elif county == 'dallas':
        where = f"SITEADDRESS LIKE '{escaped_house_num} %{escaped_street_core}%'"
    elif county == 'denton':
        where = f"situs_num = '{escaped_house_num}' AND situs_street LIKE '%{escaped_street_core}%'"
    elif county == 'collin':
        where = f"GIS_DBO_AD_Entity_situs_num = '{escaped_house_num}' AND GIS_DBO_AD_Entity_situs_street LIKE '%{escaped_street_core}%'"
    else:
        return None

    params = {
        "where": where,
        "outFields": ",".join(config['fields']),
        "f": "json",
        "resultRecordCount": 5
    }

    try:
        response = requests.get(config['url'], params=params, timeout=timeout)
        response.raise_for_status()
        data = response.json()

        features = data.get('features', [])
        if not features:
            return None

        attrs = features[0]['attributes']
        account_num = attrs.get(config['account_field'])

        if not account_num:
            return None

        # Get situs address for verification
        if county == 'tarrant':
            situs = attrs.get('Situs_Addr', '')
        elif county == 'dallas':
            situs = attrs.get('SITEADDRESS', '')
        elif county == 'denton':
            situs = f"{attrs.get('situs_num', '')} {attrs.get('situs_street', '')}".strip()
        elif county == 'collin':
            situs = attrs.get('GIS_DBO_AD_Entity_situs_display', '')
        else:
            situs = ''

        return {
            'account_num': str(account_num),
            'county': config['name'],
            'situs_addr': situs,
        }

    except (requests.RequestException, KeyError, ValueError):
        return None


def lookup_cad_account(address: str, timeout: int = 30) -> Optional[dict]:
    """
    Look up CAD account number for an address.

    Args:
        address: Full property address (e.g., "3705 DESERT RIDGE DR, Fort Worth TX 76116")
        timeout: Request timeout in seconds

    Returns:
        Dict with 'account_num', 'county', 'situs_addr' or None if not found

    Example:
        >>> result = lookup_cad_account("3705 DESERT RIDGE DR, Fort Worth TX 76116")
        >>> result['account_num']
        '12345678'
        >>> result['county']
        'Tarrant'
    """
    # Determine primary county
    primary_county = _get_county_from_address(address)

    # Try primary county first
    if primary_county:
        result = _query_county(address, primary_county, timeout)
        if result:
            return result

    # Try all counties if primary failed
    for county in COUNTY_CONFIGS:
        if county == primary_county:
            continue
        result = _query_county(address, county, timeout)
        if result:
            return result

    return None
