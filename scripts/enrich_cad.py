#!/usr/bin/env python3
"""
Standalone CAD Enrichment Script for permit-scraper.
Ported from contractor-auditor/clients/management/commands/enrich_cad.py

Enriches permit data with property information from County Appraisal Districts:
- Tarrant CAD (TAD)
- Denton CAD
- Dallas CAD (DCAD)
- Collin CAD
- Kaufman CAD
- Rockwall CAD

Usage:
    python3 scripts/enrich_cad.py --limit 10      # Test run
    python3 scripts/enrich_cad.py                  # Full run
    python3 scripts/enrich_cad.py --retry-failed   # Retry previously failed
    python3 scripts/enrich_cad.py --db path/to/db  # Custom database path
"""

import argparse
import json
import logging
import os
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, Generator
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

from dotenv import load_dotenv
load_dotenv()

import psycopg2

import requests

# =============================================================================
# CONFIGURATION
# =============================================================================

# Database connection via DATABASE_URL environment variable

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


# =============================================================================
# COUNTY CONFIGURATIONS
# =============================================================================

COUNTY_CONFIGS = {
    'tarrant': {
        'name': 'Tarrant',
        'url': 'https://tad.newedgeservices.com/arcgis/rest/services/TAD/ParcelView/MapServer/1/query',
        'address_field': 'Situs_Addr',
        'fields': [
            "Situs_Addr", "Owner_Name", "Owner_Addr", "Owner_City", "Owner_Zip",
            "Total_Valu", "Land_Value", "Improvemen", "Year_Built", "Living_Are",
            "Land_Acres", "Account_Nu"
        ],
        'field_map': {
            'owner_name': 'Owner_Name',
            'situs_addr': 'Situs_Addr',
            'owner_addr': 'Owner_Addr',
            'owner_city': 'Owner_City',
            'owner_zip': 'Owner_Zip',
            'market_value': 'Total_Valu',
            'land_value': 'Land_Value',
            'improvement_value': 'Improvemen',
            'year_built': 'Year_Built',
            'square_feet': 'Living_Are',
            'lot_size': 'Land_Acres',
            'account_num': 'Account_Nu',
        }
    },
    'denton': {
        'name': 'Denton',
        'url': 'https://gis.dentoncounty.gov/arcgis/rest/services/CAD/MapServer/0/query',
        'address_field': 'situs_num',
        'fields': [
            "owner_name", "situs_num", "situs_street", "situs_street_sufix",
            "situs_city", "situs_zip", "addr_line1", "addr_city", "addr_zip",
            "cert_mkt_val", "main_imprv_val", "yr_blt", "living_area",
            "legal_acreage", "prop_id"
        ],
        'field_map': {
            'owner_name': 'owner_name',
            'situs_num': 'situs_num',
            'situs_street': 'situs_street',
            'situs_suffix': 'situs_street_sufix',
            'situs_city': 'situs_city',
            'situs_zip': 'situs_zip',
            'owner_addr': 'addr_line1',
            'owner_city': 'addr_city',
            'owner_zip': 'addr_zip',
            'market_value': 'cert_mkt_val',
            'improvement_value': 'main_imprv_val',
            'year_built': 'yr_blt',
            'square_feet': 'living_area',
            'lot_size': 'legal_acreage',
            'account_num': 'prop_id',
        }
    },
    'dallas': {
        'name': 'Dallas',
        'url': 'https://maps.dcad.org/prdwa/rest/services/Property/ParcelQuery/MapServer/4/query',
        'address_field': 'SITEADDRESS',
        'fields': [
            "OWNERNME1", "SITEADDRESS", "PSTLADDRESS", "PSTLCITY", "PSTLSTATE",
            "PSTLZIP5", "CNTASSDVAL", "LNDVALUE", "IMPVALUE", "RESYRBLT",
            "BLDGAREA", "PARCELID"
        ],
        'field_map': {
            'owner_name': 'OWNERNME1',
            'situs_addr': 'SITEADDRESS',
            'owner_addr': 'PSTLADDRESS',
            'owner_city': 'PSTLCITY',
            'owner_zip': 'PSTLZIP5',
            'market_value': 'CNTASSDVAL',
            'land_value': 'LNDVALUE',
            'improvement_value': 'IMPVALUE',
            'year_built': 'RESYRBLT',
            'square_feet': 'BLDGAREA',
            'account_num': 'PARCELID',
        }
    },
    'collin': {
        'name': 'Collin',
        'url': 'https://gismaps.cityofallen.org/arcgis/rest/services/ReferenceData/Collin_County_Appraisal_District_Parcels/MapServer/1/query',
        'address_field': 'GIS_DBO_AD_Entity_situs_num',
        'fields': [
            "GIS_DBO_AD_Entity_file_as_name", "GIS_DBO_AD_Entity_situs_num",
            "GIS_DBO_AD_Entity_situs_street", "GIS_DBO_AD_Entity_situs_display",
            "GIS_DBO_AD_Entity_addr_line1", "GIS_DBO_AD_Entity_addr_city",
            "GIS_DBO_AD_Entity_addr_state", "GIS_DBO_AD_Entity_addr_zip",
            "GIS_DBO_AD_Entity_cert_market", "GIS_DBO_AD_Entity_cert_land_hst",
            "GIS_DBO_AD_Entity_cert_imprv_hs", "GIS_DBO_AD_Entity_yr_blt",
            "GIS_DBO_AD_Entity_living_area", "GIS_DBO_AD_Entity_legal_acreage",
            "GIS_DBO_Parcel_PROP_ID"
        ],
        'field_map': {
            'owner_name': 'GIS_DBO_AD_Entity_file_as_name',
            'situs_num': 'GIS_DBO_AD_Entity_situs_num',
            'situs_street': 'GIS_DBO_AD_Entity_situs_street',
            'situs_addr': 'GIS_DBO_AD_Entity_situs_display',
            'owner_addr': 'GIS_DBO_AD_Entity_addr_line1',
            'owner_city': 'GIS_DBO_AD_Entity_addr_city',
            'owner_zip': 'GIS_DBO_AD_Entity_addr_zip',
            'market_value': 'GIS_DBO_AD_Entity_cert_market',
            'land_value': 'GIS_DBO_AD_Entity_cert_land_hst',
            'improvement_value': 'GIS_DBO_AD_Entity_cert_imprv_hs',
            'year_built': 'GIS_DBO_AD_Entity_yr_blt',
            'square_feet': 'GIS_DBO_AD_Entity_living_area',
            'lot_size': 'GIS_DBO_AD_Entity_legal_acreage',
            'account_num': 'GIS_DBO_Parcel_PROP_ID',
        }
    },
    'kaufman': {
        'name': 'Kaufman',
        'url': 'https://services9.arcgis.com/26s7bQ5Q51Gt4J2Q/arcgis/rest/services/KaufmanCADWebService/FeatureServer/0/query',
        'address_field': 'situs_num',
        'fields': [
            "file_as_name", "situs_num", "situs_street", "situs_city",
            "market", "land_val", "imprv_val", "legal_acreage", "prop_id"
        ],
        'field_map': {
            'owner_name': 'file_as_name',
            'situs_num': 'situs_num',
            'situs_street': 'situs_street',
            'situs_city': 'situs_city',
            'market_value': 'market',
            'land_value': 'land_val',
            'improvement_value': 'imprv_val',
            'lot_size': 'legal_acreage',
            'account_num': 'prop_id',
        }
    },
    'rockwall': {
        'name': 'Rockwall',
        'url': 'https://gis.rockwallcad.com/arcgis/rest/services/Parcels/MapServer/0/query',
        'address_field': 'SITUS_ADDRESS',
        'fields': [
            "SITUS_ADDRESS", "ACCOUNT_NUM"
        ],
        'field_map': {
            'situs_addr': 'SITUS_ADDRESS',
            'account_num': 'ACCOUNT_NUM',
        }
    },
}


# =============================================================================
# ZIP CODE TO COUNTY MAPPING (DFW Area - Complete)
# =============================================================================

ZIP_TO_COUNTY = {
    # Tarrant County
    '76101': 'tarrant', '76102': 'tarrant', '76103': 'tarrant', '76104': 'tarrant',
    '76105': 'tarrant', '76106': 'tarrant', '76107': 'tarrant', '76108': 'tarrant',
    '76109': 'tarrant', '76110': 'tarrant', '76111': 'tarrant', '76112': 'tarrant',
    '76113': 'tarrant', '76114': 'tarrant', '76115': 'tarrant', '76116': 'tarrant',
    '76117': 'tarrant', '76118': 'tarrant', '76119': 'tarrant', '76120': 'tarrant',
    '76121': 'tarrant', '76122': 'tarrant', '76123': 'tarrant', '76124': 'tarrant',
    '76126': 'tarrant', '76127': 'tarrant', '76129': 'tarrant', '76130': 'tarrant',
    '76131': 'tarrant', '76132': 'tarrant', '76133': 'tarrant', '76134': 'tarrant',
    '76135': 'tarrant', '76136': 'tarrant', '76137': 'tarrant', '76140': 'tarrant',
    '76148': 'tarrant', '76155': 'tarrant', '76161': 'tarrant', '76162': 'tarrant',
    '76163': 'tarrant', '76164': 'tarrant', '76166': 'tarrant', '76177': 'tarrant',
    '76179': 'tarrant', '76180': 'tarrant', '76181': 'tarrant', '76182': 'tarrant',
    '76185': 'tarrant', '76191': 'tarrant', '76192': 'tarrant', '76193': 'tarrant',
    '76195': 'tarrant', '76196': 'tarrant', '76197': 'tarrant', '76198': 'tarrant',
    '76199': 'tarrant', '76244': 'tarrant', '76248': 'tarrant',
    # North Richland Hills, Hurst, Bedford, Euless, Grapevine, Colleyville, Southlake
    '76021': 'tarrant', '76022': 'tarrant', '76034': 'tarrant', '76039': 'tarrant',
    '76040': 'tarrant', '76051': 'tarrant', '76053': 'tarrant', '76054': 'tarrant',
    '76092': 'tarrant', '76094': 'tarrant', '76095': 'tarrant', '76099': 'tarrant',
    # Arlington, Mansfield
    '76001': 'tarrant', '76002': 'tarrant', '76003': 'tarrant', '76004': 'tarrant',
    '76005': 'tarrant', '76006': 'tarrant', '76010': 'tarrant', '76011': 'tarrant',
    '76012': 'tarrant', '76013': 'tarrant', '76014': 'tarrant', '76015': 'tarrant',
    '76016': 'tarrant', '76017': 'tarrant', '76018': 'tarrant', '76019': 'tarrant',
    '76060': 'tarrant', '76063': 'tarrant',

    # Denton County
    '76201': 'denton', '76202': 'denton', '76203': 'denton', '76204': 'denton',
    '76205': 'denton', '76206': 'denton', '76207': 'denton', '76208': 'denton',
    '76209': 'denton', '76210': 'denton', '76226': 'denton', '76227': 'denton',
    '76234': 'denton', '76247': 'denton', '76249': 'denton', '76258': 'denton',
    '76259': 'denton', '76262': 'denton', '76266': 'denton', '76272': 'denton',
    # Lewisville, Flower Mound, Highland Village, The Colony, Little Elm
    '75006': 'denton', '75007': 'denton', '75010': 'denton', '75019': 'denton',
    '75022': 'denton', '75027': 'denton', '75028': 'denton', '75029': 'denton',
    '75034': 'denton', '75056': 'denton', '75057': 'denton', '75065': 'denton',
    '75067': 'denton', '75068': 'denton', '75077': 'denton',
    # Frisco (split between Denton/Collin), Aubrey, Pilot Point, Sanger
    '75033': 'denton', '75036': 'denton',
    '76023': 'denton', '76052': 'denton', '76078': 'denton',

    # Dallas County
    '75201': 'dallas', '75202': 'dallas', '75203': 'dallas', '75204': 'dallas',
    '75205': 'dallas', '75206': 'dallas', '75207': 'dallas', '75208': 'dallas',
    '75209': 'dallas', '75210': 'dallas', '75211': 'dallas', '75212': 'dallas',
    '75214': 'dallas', '75215': 'dallas', '75216': 'dallas', '75217': 'dallas',
    '75218': 'dallas', '75219': 'dallas', '75220': 'dallas', '75221': 'dallas',
    '75222': 'dallas', '75223': 'dallas', '75224': 'dallas', '75225': 'dallas',
    '75226': 'dallas', '75227': 'dallas', '75228': 'dallas', '75229': 'dallas',
    '75230': 'dallas', '75231': 'dallas', '75232': 'dallas', '75233': 'dallas',
    '75234': 'dallas', '75235': 'dallas', '75236': 'dallas', '75237': 'dallas',
    '75238': 'dallas', '75239': 'dallas', '75240': 'dallas', '75241': 'dallas',
    '75242': 'dallas', '75243': 'dallas', '75244': 'dallas', '75246': 'dallas',
    '75247': 'dallas', '75248': 'dallas', '75249': 'dallas', '75250': 'dallas',
    '75251': 'dallas', '75252': 'dallas', '75253': 'dallas', '75254': 'dallas',
    # Irving, Grand Prairie, Mesquite, Garland (partial)
    '75038': 'dallas', '75039': 'dallas', '75060': 'dallas', '75061': 'dallas',
    '75062': 'dallas', '75063': 'dallas', '75050': 'dallas', '75051': 'dallas',
    '75052': 'dallas', '75053': 'dallas', '75054': 'dallas', '75149': 'dallas',
    '75150': 'dallas', '75180': 'dallas', '75181': 'dallas', '75182': 'dallas',

    # Collin County (Allen, McKinney, Plano, Frisco, etc.)
    '75002': 'collin', '75009': 'collin', '75013': 'collin', '75023': 'collin',
    '75024': 'collin', '75025': 'collin', '75026': 'collin', '75030': 'collin',
    '75034': 'collin', '75035': 'collin', '75048': 'collin', '75069': 'collin',
    '75070': 'collin', '75071': 'collin', '75072': 'collin', '75074': 'collin',
    '75075': 'collin', '75078': 'collin', '75080': 'collin', '75081': 'collin',
    '75082': 'collin', '75086': 'collin', '75093': 'collin',
    '75094': 'collin', '75097': 'collin', '75098': 'collin', '75121': 'collin',
    '75164': 'collin', '75166': 'collin', '75173': 'collin', '75407': 'collin',
    '75409': 'collin', '75424': 'collin', '75442': 'collin', '75454': 'collin',

    # Kaufman County (Forney, Terrell, Kaufman)
    '75126': 'kaufman', '75142': 'kaufman', '75160': 'kaufman', '75161': 'kaufman',

    # Rockwall County (Rockwall, Royse City, Heath, Fate)
    '75032': 'rockwall', '75087': 'rockwall', '75189': 'rockwall',

    # Parker County (Aledo, Weatherford) - no API, will be skipped
    '76008': 'parker', '76087': 'parker', '76085': 'parker', '76086': 'parker',
    '76088': 'parker',

    # Johnson County (Crowley, Burleson area) - no API, will be skipped
    '76028': 'johnson', '76036': 'johnson', '76058': 'johnson', '76031': 'johnson',
    '76044': 'johnson', '76050': 'johnson', '76059': 'johnson', '76093': 'johnson',
    '76097': 'johnson',
}


# =============================================================================
# CITY TO COUNTY MAPPING (Fallback when zip fails)
# =============================================================================

CITY_TO_COUNTY = {
    # Collin County cities
    'frisco': 'collin',
    'allen': 'collin',
    'mckinney': 'collin',
    'plano': 'collin',
    'prosper': 'collin',
    'celina': 'collin',
    'anna': 'collin',
    'princeton': 'collin',
    'melissa': 'collin',
    'fairview': 'collin',
    'lucas': 'collin',
    'murphy': 'collin',
    'wylie': 'collin',
    'sachse': 'collin',

    # Denton County cities
    'denton': 'denton',
    'lewisville': 'denton',
    'flower mound': 'denton',
    'highland village': 'denton',
    'the colony': 'denton',
    'little elm': 'denton',
    'corinth': 'denton',
    'aubrey': 'denton',
    'pilot point': 'denton',
    'sanger': 'denton',
    'argyle': 'denton',
    'bartonville': 'denton',
    'trophy club': 'denton',

    # Tarrant County cities
    'fort worth': 'tarrant',
    'arlington': 'tarrant',
    'north richland hills': 'tarrant',
    'hurst': 'tarrant',
    'bedford': 'tarrant',
    'euless': 'tarrant',
    'grapevine': 'tarrant',
    'colleyville': 'tarrant',
    'southlake': 'tarrant',
    'keller': 'tarrant',
    'watauga': 'tarrant',
    'haltom city': 'tarrant',
    'richland hills': 'tarrant',
    'mansfield': 'tarrant',

    # Dallas County cities
    'dallas': 'dallas',
    'irving': 'dallas',
    'grand prairie': 'dallas',
    'mesquite': 'dallas',
    'garland': 'dallas',
    'richardson': 'dallas',
    'carrollton': 'dallas',
    'farmers branch': 'dallas',
    'coppell': 'dallas',
    'desoto': 'dallas',
    'duncanville': 'dallas',
    'cedar hill': 'dallas',
    'lancaster': 'dallas',
    'rowlett': 'dallas',

    # Kaufman County cities
    'forney': 'kaufman',
    'terrell': 'kaufman',
    'kaufman': 'kaufman',

    # Rockwall County cities
    'rockwall': 'rockwall',
    'royse city': 'rockwall',
    'heath': 'rockwall',
    'fate': 'rockwall',
}


# =============================================================================
# DATABASE SETUP
# =============================================================================

def get_db_connection():
    """Get PostgreSQL connection from DATABASE_URL."""
    url = os.environ.get('DATABASE_URL')
    if not url:
        raise ValueError("DATABASE_URL environment variable not set")
    return psycopg2.connect(url)


# =============================================================================
# ADDRESS PARSING HELPERS
# =============================================================================

def get_county_from_zip(address: str) -> Optional[str]:
    """Extract zip code and determine county."""
    if not address:
        return None
    # Look for 5-digit zip after state abbreviation
    match = re.search(r'\b(TX|TEXAS)\s+(\d{5})(?:-\d{4})?(?:\s|$)', address, re.I)
    if match:
        zip_code = match.group(2)
        return ZIP_TO_COUNTY.get(zip_code)
    # Fallback: last 5-digit sequence in address
    matches = re.findall(r'(\d{5})', address)
    if matches:
        zip_code = matches[-1]
        return ZIP_TO_COUNTY.get(zip_code)
    return None


def get_county_from_city(city: str) -> Optional[str]:
    """Get county from city name."""
    if not city:
        return None
    return CITY_TO_COUNTY.get(city.lower().strip())


def normalize_address(address: str) -> str:
    """Normalize address for comparison."""
    if not address:
        return ""
    addr = address.upper()
    addr = re.sub(r'[^\w\s]', '', addr)
    addr = re.sub(r'\s+', ' ', addr)
    return addr.strip()


def extract_street_address(full_address: str) -> Optional[str]:
    """
    Extract just the street address from a full address.
    Input: "5429 HUNTLY DR, Fort Worth TX 76109"
    Output: "5429 HUNTLY DR"

    Also handles addresses with prefixes like:
    - "Iron Plow Restaurant 105 W Main St" -> "105 W Main St"
    - "Creekside Ph 1B 2805 Spring Side Dr" -> "2805 Spring Side Dr"
    - "Twin Pines 4609 Pine Ridge Lane" -> "4609 Pine Ridge Lane"
    """
    if not full_address:
        return None

    # Remove everything after comma
    if ',' in full_address:
        full_address = full_address.split(',')[0]

    # Remove city/state/zip if no comma
    dfw_cities = (
        r'Fort Worth|Dallas|Arlington|Irving|Plano|Garland|Frisco|McKinney|'
        r'Denton|Lewisville|Allen|Carrollton|Richardson|Mesquite|Grand Prairie|'
        r'Keller|Southlake|Grapevine|Flower Mound|Euless|Bedford|Hurst|'
        r'Colleyville|Coppell|Rowlett|Wylie|Murphy|Sachse|Lucas|Prosper|'
        r'Celina|Anna|Princeton|Melissa|Fairview|Highland Village|The Colony|'
        r'Trophy Club|Westlake|Roanoke|Northlake|Argyle|Lantana|Corinth|'
        r'Little Elm|Oak Point|Double Oak|Bartonville|Copper Canyon|Hickory Creek|'
        r'Royse City|Fate|Rockwall|Heath|Rowlett|Forney|Terrell|Kaufman'
    )
    full_address = re.sub(rf'\s+({dfw_cities}|TX|TEXAS|\d{{5}}).*$', '', full_address, flags=re.I)

    addr = full_address.strip()

    # If address doesn't start with a number, try to find where the house number starts
    # This handles prefixes like business names, subdivision names, etc.
    # Examples: "Iron Plow Restaurant 105 W Main St" -> "105 W Main St"
    #           "Creekside Ph 1B 2805 Spring Side Dr" -> "2805 Spring Side Dr"
    if not re.match(r'^\d', addr):
        # Find a house number pattern (3-5 digit number followed by space and letters)
        # Use the LAST occurrence of a house number pattern to handle "Ph 1B 2805" cases
        matches = list(re.finditer(r'(\d{2,5})\s+([A-Za-z])', addr))
        if matches:
            # Take the last match that looks like a real house number (3+ digits preferred)
            for match in reversed(matches):
                potential_num = match.group(1)
                # Skip if it looks like a phase number (1-2 digits right after "Ph")
                start_pos = match.start()
                prefix = addr[:start_pos].strip().upper()
                if prefix.endswith('PH') or prefix.endswith('PHASE'):
                    continue
                # Found a good house number
                addr = addr[start_pos:]
                break

    return addr.strip()


def parse_address_for_query(address: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Parse address into house number and street name for CAD query.
    Returns (house_num, street_core) or (None, None) if can't parse.
    """
    street_addr = extract_street_address(address)
    if not street_addr:
        return None, None

    street_addr = street_addr.upper().strip()

    # Remove unit/apt numbers (STE requires period or space+number to avoid matching "STEPHIE", "STERLING", etc.)
    street_addr = re.sub(r'\s+(APT|UNIT|SUITE|#)\s*\S*', '', street_addr, flags=re.I)
    street_addr = re.sub(r'\s+STE\.?\s+\S+', '', street_addr, flags=re.I)  # STE must be followed by space then unit

    # Extract house number and street
    match = re.match(r'^(\d+)\s+(.+)$', street_addr)
    if not match:
        return None, None

    house_num = match.group(1)
    street = match.group(2).strip()

    # Extract core street name (remove ST, AVE, DR, etc. for broader matching)
    street_core = re.sub(
        r'\s+(ST|AVE|DR|RD|LN|CT|BLVD|WAY|PL|CIR|PKWY|HWY|TRAIL|TRL|DRIVE|STREET|AVENUE|ROAD|LANE|COURT)\.?$',
        '', street, flags=re.I
    )
    street_core = street_core.strip()

    # If we stripped too much, use original
    if len(street_core) < 3:
        street_core = street

    return house_num, street_core


def generate_address_variants(address: str) -> Generator[str, None, None]:
    """
    Generate progressively simpler address variants for retry.

    Example: "5429 HUNTLY DR, Fort Worth TX 76109"
    Yields:
      1. "5429 HUNTLY DR" (original, cleaned)
      2. "5429 HUNTLY" (strip street type)
      3. If has directional: same without N/S/E/W
    """
    if not address:
        return

    street_addr = extract_street_address(address)
    if not street_addr:
        return

    street_addr = street_addr.upper().strip()

    # Remove unit/apt/suite numbers first (STE requires space then unit to avoid matching STENNETT, STERLING, etc.)
    street_addr = re.sub(r'\s+(APT|UNIT|SUITE|#)\s*\S*', '', street_addr, flags=re.I)
    street_addr = re.sub(r'\s+STE\.?\s+\S+', '', street_addr, flags=re.I)
    street_addr = street_addr.strip()

    # Pattern for street suffixes
    STREET_SUFFIXES = r'(DR|DRIVE|ST|STREET|AVE|AVENUE|BLVD|BOULEVARD|LN|LANE|CT|COURT|CIR|CIRCLE|RD|ROAD|PL|PLACE|WAY|PKWY|PARKWAY|HWY|HIGHWAY|TRAIL|TRL|TERR|TERRACE)\.?'

    # Pattern for directionals
    DIRECTIONALS = r'(N|S|E|W|NE|NW|SE|SW|NORTH|SOUTH|EAST|WEST)'

    # Variant 1: Original cleaned address (with street suffix)
    yield street_addr

    # Variant 2: Strip street suffix
    addr_no_suffix = re.sub(rf'\s+{STREET_SUFFIXES}$', '', street_addr, flags=re.I).strip()
    if addr_no_suffix != street_addr and len(addr_no_suffix) > 3:
        yield addr_no_suffix

    # Variant 3: Also remove directional prefix (e.g., "1234 N MAIN" -> "1234 MAIN")
    match = re.match(rf'^(\d+)\s+{DIRECTIONALS}\s+(.+)$', addr_no_suffix, flags=re.I)
    if match:
        house_num = match.group(1)
        street_name = match.group(3)
        addr_no_direction = f"{house_num} {street_name}".strip()
        if addr_no_direction != addr_no_suffix:
            yield addr_no_direction

    # Variant 4: Check for trailing directional
    match = re.match(rf'^(\d+)\s+(.+?)\s+{DIRECTIONALS}$', addr_no_suffix, flags=re.I)
    if match:
        house_num = match.group(1)
        street_name = match.group(2)
        addr_no_direction = f"{house_num} {street_name}".strip()
        if addr_no_direction != addr_no_suffix:
            yield addr_no_direction


# =============================================================================
# ABSENTEE OWNER DETECTION
# =============================================================================

def normalize_street_suffix(addr: str) -> str:
    """Normalize street suffixes for comparison."""
    if not addr:
        return ''
    addr = addr.upper()
    replacements = [
        ('STREET', 'ST'), ('DRIVE', 'DR'), ('AVENUE', 'AVE'), ('ROAD', 'RD'),
        ('LANE', 'LN'), ('COURT', 'CT'), ('CIRCLE', 'CIR'), ('BOULEVARD', 'BLVD'),
        ('PLACE', 'PL'), ('TERRACE', 'TER'), ('TRAIL', 'TRL'), ('PARKWAY', 'PKWY'),
        ('HIGHWAY', 'HWY'), ('WAY', 'WY'),
    ]
    for full, abbr in replacements:
        addr = re.sub(rf'\b{full}\b', abbr, addr)
    return addr


def extract_street_for_comparison(addr: str) -> str:
    """
    Extract just street address for comparison (house number + street name).
    Handles directional prefixes like "836 S HAVENWOOD LN" vs "836 HAVENWOOD LN S"
    """
    if not addr:
        return ''

    # First split on comma to get just the street portion
    street = addr.upper().split(',')[0].strip()

    # Remove unit/apt designators
    street = re.sub(r'\s*(#|UNIT|APT|STE|SUITE|BLDG)\s*\w*', '', street)

    # Normalize street suffixes
    street = normalize_street_suffix(street)

    # Remove all punctuation
    street = re.sub(r'[^\w\s]', '', street)
    street = re.sub(r'\s+', ' ', street).strip()

    # Extract components
    parts = street.split()
    if not parts:
        return ''

    house_num = parts[0] if parts else ''
    street_words = parts[1:] if len(parts) > 1 else []

    # Remove directionals and sort remaining words
    directionals = {'N', 'S', 'E', 'W', 'NE', 'NW', 'SE', 'SW', 'NORTH', 'SOUTH', 'EAST', 'WEST'}
    core_words = [w for w in street_words if w not in directionals]

    return f"{house_num} {' '.join(core_words)}"


def is_absentee_owner(situs_addr: str, mailing_addr: str) -> Optional[bool]:
    """Check if owner is absentee (mailing address differs from property)."""
    if not situs_addr or not mailing_addr:
        return None

    situs_street = extract_street_for_comparison(situs_addr)
    mailing_street = extract_street_for_comparison(mailing_addr)

    if not situs_street or not mailing_street:
        return None

    return situs_street != mailing_street


# =============================================================================
# CAD API QUERIES
# =============================================================================

def query_county_cad(address: str, county: str, timeout: int = 30) -> Tuple[Optional[dict], Optional[str]]:
    """
    Query a county's CAD ArcGIS API for property data.
    Returns (normalized_data, county_name) or (None, None) if not found.
    """
    if county not in COUNTY_CONFIGS:
        return None, None

    config = COUNTY_CONFIGS[county]
    house_num, street_core = parse_address_for_query(address)
    if not house_num or not street_core:
        return None, None

    # Build query based on county
    if county == 'tarrant':
        where_clause = f"Situs_Addr LIKE '{house_num} %{street_core}%'"
    elif county == 'denton':
        where_clause = f"situs_num = '{house_num}' AND situs_street LIKE '%{street_core}%'"
    elif county == 'dallas':
        where_clause = f"SITEADDRESS LIKE '{house_num} %{street_core}%'"
    elif county == 'collin':
        where_clause = f"GIS_DBO_AD_Entity_situs_num = '{house_num}' AND GIS_DBO_AD_Entity_situs_street LIKE '%{street_core}%'"
    elif county == 'kaufman':
        where_clause = f"situs_num = '{house_num}' AND situs_street LIKE '%{street_core}%'"
    elif county == 'rockwall':
        where_clause = f"SITUS_ADDRESS LIKE '{house_num} %{street_core}%'"
    else:
        return None, None

    params = {
        "where": where_clause,
        "outFields": ",".join(config['fields']),
        "f": "json",
        "resultRecordCount": 10
    }

    try:
        response = requests.get(config['url'], params=params, timeout=timeout)
        response.raise_for_status()

        data = response.json()
        features = data.get("features", [])

        if not features:
            return None, None

        raw_data = features[0]["attributes"]
        fm = config['field_map']

        # Build situs address (varies by county)
        if county == 'denton':
            situs_num = raw_data.get(fm.get('situs_num', ''), '') or ''
            situs_street = raw_data.get(fm.get('situs_street', ''), '') or ''
            situs_suffix = raw_data.get(fm.get('situs_suffix', ''), '') or ''
            situs_addr = f"{situs_num} {situs_street} {situs_suffix}".strip()
        elif county == 'kaufman':
            situs_num = raw_data.get(fm.get('situs_num', ''), '') or ''
            situs_street = raw_data.get(fm.get('situs_street', ''), '') or ''
            situs_city = raw_data.get(fm.get('situs_city', ''), '') or ''
            situs_addr = f"{situs_num} {situs_street}".strip()
            if situs_city:
                situs_addr = f"{situs_addr}, {situs_city}".strip(', ')
        elif county == 'collin':
            situs_addr = raw_data.get(fm.get('situs_addr', ''), '') or ''
            if not situs_addr:
                situs_num = raw_data.get(fm.get('situs_num', ''), '') or ''
                situs_street = raw_data.get(fm.get('situs_street', ''), '') or ''
                situs_addr = f"{situs_num} {situs_street}".strip()
        else:
            situs_addr = raw_data.get(fm.get('situs_addr', ''), '') or ''

        normalized = {
            'owner_name': raw_data.get(fm.get('owner_name', ''), ''),
            'situs_addr': situs_addr,
            'owner_addr': raw_data.get(fm.get('owner_addr', ''), ''),
            'owner_city': raw_data.get(fm.get('owner_city', ''), ''),
            'owner_zip': raw_data.get(fm.get('owner_zip', ''), ''),
            'market_value': raw_data.get(fm.get('market_value', '')),
            'land_value': raw_data.get(fm.get('land_value', '')),
            'improvement_value': raw_data.get(fm.get('improvement_value', '')),
            'year_built': raw_data.get(fm.get('year_built', '')),
            'square_feet': raw_data.get(fm.get('square_feet', '')),
            'lot_size': raw_data.get(fm.get('lot_size', '')),
            'account_num': raw_data.get(fm.get('account_num', '')),
        }

        return normalized, config['name']

    except requests.RequestException as e:
        logger.debug(f"API request failed for {config['name']}: {e}")
        return None, None
    except (KeyError, ValueError) as e:
        logger.debug(f"Failed to parse {config['name']} response: {e}")
        return None, None


def query_denton_by_street(street_name: str, city_filter: str = None, limit: int = 100) -> list:
    """
    Query Denton CAD for all properties on a street.
    Used for The Colony permits which only have street names.

    Args:
        street_name: Street name without number (e.g., "BAKER" or "BAKER DR")
        city_filter: Optional city name to filter (e.g., "THE COLONY")
        limit: Max results to return

    Returns:
        List of property records with full addresses
    """
    config = COUNTY_CONFIGS['denton']

    # Strip any trailing suffix for broader match
    street_core = re.sub(
        r'\s+(DR|DRIVE|ST|STREET|AVE|AVENUE|BLVD|LN|LANE|CT|COURT|CIR|RD|ROAD|WAY|PL)\.?$',
        '', street_name.upper(), flags=re.I
    ).strip()

    # Build query - search by street name only
    where_clause = f"situs_street LIKE '%{street_core}%'"
    if city_filter:
        where_clause += f" AND situs_city LIKE '%{city_filter.upper()}%'"

    params = {
        "where": where_clause,
        "outFields": ",".join(config['fields']),
        "f": "json",
        "resultRecordCount": limit
    }

    try:
        response = requests.get(config['url'], params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        features = data.get("features", [])

        results = []
        fm = config['field_map']

        for feature in features:
            raw = feature.get("attributes", {})

            # Build full situs address
            situs_num = str(raw.get(fm.get('situs_num', ''), '') or '').strip()
            situs_street = str(raw.get(fm.get('situs_street', ''), '') or '').strip()
            situs_suffix = str(raw.get(fm.get('situs_suffix', ''), '') or '').strip()
            situs_city = str(raw.get(fm.get('situs_city', ''), '') or '').strip()

            full_addr = f"{situs_num} {situs_street} {situs_suffix}".strip()

            results.append({
                'situs_addr': full_addr,
                'situs_city': situs_city,
                'owner_name': raw.get(fm.get('owner_name', ''), ''),
                'market_value': raw.get(fm.get('market_value', '')),
                'year_built': raw.get(fm.get('year_built', '')),
                'account_num': raw.get(fm.get('account_num', '')),
            })

        return results

    except Exception as e:
        logger.warning(f"Denton CAD query failed: {e}")
        return []


def query_cad_with_retry(address: str, county: str, timeout: int = 30) -> Tuple[Optional[dict], Optional[str], Optional[str]]:
    """
    Try progressively simpler address variants until one succeeds.
    Returns (normalized_data, county_name, variant_used) or (None, None, None).
    """
    tried_queries = set()

    for variant in generate_address_variants(address):
        house_num, street_core = parse_address_for_query(variant)
        if not house_num or not street_core:
            continue

        query_key = f"{house_num}|{street_core}"
        if query_key in tried_queries:
            continue
        tried_queries.add(query_key)

        try:
            result, county_name = query_county_cad(variant, county, timeout)
            if result:
                return result, county_name, variant
        except Exception:
            pass

    return None, None, None


def query_cad_multi_county(address: str, timeout: int = 15, skip_fallback: bool = True) -> Tuple[Optional[dict], Optional[str], Optional[str]]:
    """
    Try to find property in multiple counties.
    First tries the county based on zip code, then falls back to others.
    Returns (normalized_data, county_name, variant_used) or (None, None, None).

    Args:
        skip_fallback: If True and we know the county from zip, don't try other counties.
                       This is much faster but may miss some edge cases.
    """
    primary_county = get_county_from_zip(address)
    supported_counties = ['tarrant', 'denton', 'dallas', 'collin', 'kaufman', 'rockwall']

    # If we know the county and it's supported, try it first
    if primary_county and primary_county in supported_counties:
        result, county_name, variant = query_cad_with_retry(address, primary_county, timeout)
        if result:
            return result, county_name, variant
        # If skip_fallback is True and we knew the county, don't try others
        if skip_fallback:
            return None, None, None

    # If primary county failed or isn't supported, try others
    for county in supported_counties:
        if county == primary_county:
            continue
        result, county_name, variant = query_cad_with_retry(address, county, timeout)
        if result:
            return result, county_name, variant

    return None, None, None


def process_single_address(address: str, delay: float = 0.1) -> dict:
    """
    Process a single address for CAD enrichment.
    Returns a dict with result info for the main thread to handle DB writes.
    """
    result = {
        'address': address,
        'status': None,  # 'success', 'failed', 'skip'
        'data': None,
        'county': None,
        'variant': None,
        'error': None
    }

    # Detect county for display
    detected_county = get_county_from_zip(address)

    # Check if county is unsupported
    if detected_county and detected_county not in COUNTY_CONFIGS:
        result['status'] = 'skip'
        result['error'] = f'No API for {detected_county.title()} County'
        return result

    # Parse address
    house_num, street_core = parse_address_for_query(address)
    if not house_num:
        result['status'] = 'skip'
        result['error'] = 'Cannot parse address'
        return result

    try:
        # Query CAD with multi-county support (skip fallback for speed)
        cad_data, county_name, variant_used = query_cad_multi_county(address, timeout=15, skip_fallback=True)

        if not cad_data:
            result['status'] = 'failed'
            result['error'] = 'Not found in CAD'
            return result

        result['status'] = 'success'
        result['data'] = cad_data
        result['county'] = county_name
        result['variant'] = variant_used

    except Exception as e:
        result['status'] = 'failed'
        result['error'] = str(e)

    time.sleep(delay)  # Rate limit
    return result


# =============================================================================
# VALUE PARSING HELPERS
# =============================================================================

def parse_float(val) -> Optional[float]:
    """Parse a value to float, returning None on failure."""
    if val is None:
        return None
    try:
        return float(str(val).strip())
    except (ValueError, TypeError):
        return None


def parse_int(val) -> Optional[int]:
    """Parse a value to int, returning None on failure."""
    if val is None:
        return None
    try:
        return int(float(str(val).strip()))
    except (ValueError, TypeError):
        return None


# =============================================================================
# MAIN EXECUTION
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Enrich permits with CAD property data (Tarrant, Denton, Dallas, Collin, Kaufman, Rockwall)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python3 scripts/enrich_cad.py --limit 10      # Test run on 10 permits
    python3 scripts/enrich_cad.py                  # Full run
    python3 scripts/enrich_cad.py --retry-failed   # Retry previously failed
        """
    )
    parser.add_argument('--limit', type=int, default=None, help='Limit number of permits to process')
    parser.add_argument('--force', action='store_true', help='Re-enrich even if already enriched')
    parser.add_argument('--retry-failed', action='store_true', help='Retry previously failed enrichments')
    parser.add_argument('--delay', type=float, default=1.0, help='Delay between API requests (default: 1.0s)')
    parser.add_argument('--workers', type=int, default=10, help='Number of parallel workers (default: 10)')
    parser.add_argument('--recent', action='store_true', help='Only process permits from last 90 days')
    parser.add_argument('--fresh', action='store_true', help='Only process fresh valuable permits (60 days, exclude junk types)')
    parser.add_argument('--never-tried', action='store_true', help='Only process addresses that have never been tried (no property record)')
    parser.add_argument('--bin', default='active',
                        help='Processing bin to target (active, archive, all). Default: active')
    args = parser.parse_args()

    # Connect to PostgreSQL
    try:
        conn = get_db_connection()
    except ValueError as e:
        print(f"ERROR: {e}")
        return

    print("=== MULTI-COUNTY CAD ENRICHMENT ===")
    print("Supported counties: Tarrant, Denton, Dallas, Collin, Kaufman, Rockwall\n")

    # Build query based on options
    recent_filter = ""
    if args.recent:
        recent_filter = "AND (p.issued_date IS NULL OR p.issued_date > NOW() - INTERVAL '90 days')"
        print("Filtering to recent permits (last 90 days)\n")

    # Fresh filter: 60 days + exclude junk permit types
    fresh_filter = ""
    if args.fresh:
        fresh_filter = """
            AND p.issued_date > NOW() - INTERVAL '60 days'
            AND COALESCE(p.permit_type, '') NOT ILIKE '%%Licensed Professional%%'
            AND COALESCE(p.permit_type, '') NOT ILIKE '%%Change of%%'
            AND COALESCE(p.permit_type, '') NOT ILIKE '%%Temporary Health%%'
            AND COALESCE(p.permit_type, '') NOT ILIKE '%%Certificate of Occupancy%%'
            AND COALESCE(p.permit_type, '') NOT ILIKE '%%Extension%%'
            AND COALESCE(p.permit_type, '') NOT ILIKE '%%Backflow%%'
            AND COALESCE(p.permit_type, '') NOT ILIKE '%%Right of Way%%'
            AND COALESCE(p.permit_type, '') NOT ILIKE '%%Investigation%%'
            AND COALESCE(p.permit_type, '') NOT ILIKE '%%Discontinued%%'
            AND COALESCE(p.permit_type, '') NOT ILIKE '%%Renewal%%'
            AND COALESCE(p.permit_type, '') NOT ILIKE '%%Sign %%'
            AND COALESCE(p.permit_type, '') NOT ILIKE '%%Fence%%'
            AND COALESCE(p.permit_type, '') NOT ILIKE '%%Demolition%%'
            AND COALESCE(p.permit_type, '') NOT ILIKE '%%Sidewalk%%'
            AND COALESCE(p.permit_type, '') NOT ILIKE '%%Drive Approach%%'
            AND COALESCE(p.permit_type, '') NOT ILIKE '%%Fire Alarm%%'
            AND COALESCE(p.permit_type, '') NOT ILIKE '%%Fire Sprinkler%%'
            AND COALESCE(p.permit_type, '') NOT ILIKE '%%Fire Prevention%%'
            AND COALESCE(p.permit_type, '') NOT ILIKE '%%Irrigation%%'
            AND COALESCE(p.permit_type, '') NOT ILIKE '%%Tent%%'
            AND COALESCE(p.permit_type, '') NOT ILIKE '%%Liquor%%'
            AND COALESCE(p.permit_type, '') NOT ILIKE '%%Pre Development%%'
            AND COALESCE(p.permit_type, '') NOT ILIKE '%%Access Control%%'
            AND COALESCE(p.permit_type, '') NOT ILIKE '%%Address Assignment%%'
            AND COALESCE(p.permit_type, '') NOT IN ('CO', 'SI')
        """
        print("Filtering to fresh valuable permits (60 days, excluding junk types)\n")

    # Bin filter: only process active permits by default
    bin_filter = ""
    if args.bin != 'all':
        bin_filter = f"AND p.processing_bin = '{args.bin}'"
        print(f"Filtering to '{args.bin}' bin\n")

    if args.force:
        sql = f"SELECT DISTINCT property_address FROM leads_permit p WHERE property_address IS NOT NULL {recent_filter} {fresh_filter} {bin_filter}"
    elif args.retry_failed:
        sql = """
            SELECT property_address FROM leads_property
            WHERE enrichment_status = 'failed'
        """
    elif args.never_tried:
        # Only addresses with NO record in leads_property (never attempted)
        sql = f"""
            SELECT DISTINCT p.property_address
            FROM leads_permit p
            LEFT JOIN leads_property prop ON p.property_address = prop.property_address
            WHERE p.property_address IS NOT NULL
              AND prop.property_address IS NULL
              {recent_filter}
              {fresh_filter}
              {bin_filter}
        """
        print("Processing only never-tried addresses\n")
    else:
        sql = f"""
            SELECT DISTINCT p.property_address
            FROM leads_permit p
            LEFT JOIN leads_property prop ON p.property_address = prop.property_address
            WHERE p.property_address IS NOT NULL
              AND (prop.property_address IS NULL OR prop.enrichment_status != 'success')
              {recent_filter}
              {fresh_filter}
              {bin_filter}
        """

    with conn.cursor() as cur:
        cur.execute(sql)
        addresses = [row[0] for row in cur.fetchall() if row[0]]

    if args.limit:
        addresses = addresses[:args.limit]

    total = len(addresses)
    print(f"Found {total} addresses to enrich\n")

    if total == 0:
        print("No permits need enrichment. Use --force to re-enrich or --retry-failed.")
        conn.close()
        return

    success_count = 0
    fail_count = 0
    skip_count = 0
    county_counts = {}

    # Pre-filter: skip commercial/multi-unit addresses (unenrichable)
    def is_commercial_address(addr: str) -> bool:
        """Check if address is likely commercial/multi-unit (won't have CAD record)."""
        addr_upper = addr.upper()
        # Commercial indicators
        if any(x in addr_upper for x in ['SHELL', 'SUITE ', 'STE ', ' BLDG', 'UNIT:', 'UNIT ',
                                          'TRLR ', 'TRAILER', 'LOT ', '#']):
            return True
        # Suite numbers at end (e.g., "123 MAIN ST 200")
        if re.search(r'\s+\d{3,4}$', addr_upper):
            return True
        # Highway addresses
        if re.search(r'INTERSTATE|I-\d+|US \d+|HWY|HIGHWAY|EXPRESSWAY|EXPY|PKWY|LOOP \d+', addr_upper):
            return True
        return False

    # Filter out commercial addresses
    original_count = len(addresses)
    addresses = [a for a in addresses if not is_commercial_address(a)]
    filtered_count = original_count - len(addresses)
    if filtered_count > 0:
        print(f"Filtered out {filtered_count} commercial/multi-unit addresses")

    total = len(addresses)
    print(f"Processing {total} residential addresses\n")

    # Process addresses in parallel
    print(f"Using {args.workers} parallel workers with {args.delay}s delay\n")

    def save_result_to_db(result: dict, conn) -> str:
        """Save a single result to database. Returns status for counting."""
        address = result['address']

        if result['status'] == 'skip':
            return 'skip'

        if result['status'] == 'failed':
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO leads_property (property_address, homestead_exempt, enrichment_status, enriched_at)
                    VALUES (%s, false, 'failed', %s)
                    ON CONFLICT (property_address) DO UPDATE SET
                        enrichment_status = 'failed',
                        enriched_at = EXCLUDED.enriched_at
                """, (address, datetime.now()))
            conn.commit()
            return 'failed'

        # Success - extract and save data
        cad_data = result['data']
        county_name = result['county']

        owner_name = (cad_data.get('owner_name') or '').strip()
        market_value = parse_float(cad_data.get('market_value'))
        land_value = parse_float(cad_data.get('land_value'))
        improvement_value = parse_float(cad_data.get('improvement_value'))
        year_built = parse_int(cad_data.get('year_built'))
        square_feet = parse_int(cad_data.get('square_feet'))
        lot_size = parse_float(cad_data.get('lot_size'))
        situs_addr = cad_data.get('situs_addr', '')
        account_num = cad_data.get('account_num')

        owner_addr = (cad_data.get('owner_addr') or '').strip()
        owner_city = (cad_data.get('owner_city') or '').strip()
        owner_zip = (cad_data.get('owner_zip') or '').strip()
        mailing_address = f"{owner_addr}, {owner_city} {owner_zip}".strip(", ")

        absentee = is_absentee_owner(situs_addr, mailing_address) if owner_addr else None

        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO leads_property (
                    property_address, cad_account_id, county, owner_name,
                    mailing_address, market_value, land_value, improvement_value,
                    year_built, square_feet, lot_size, is_absentee, homestead_exempt,
                    enrichment_status, enriched_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, false, 'success', %s)
                ON CONFLICT (property_address) DO UPDATE SET
                    cad_account_id = EXCLUDED.cad_account_id,
                    county = EXCLUDED.county,
                    owner_name = EXCLUDED.owner_name,
                    mailing_address = EXCLUDED.mailing_address,
                    market_value = EXCLUDED.market_value,
                    land_value = EXCLUDED.land_value,
                    improvement_value = EXCLUDED.improvement_value,
                    year_built = EXCLUDED.year_built,
                    square_feet = EXCLUDED.square_feet,
                    lot_size = EXCLUDED.lot_size,
                    is_absentee = EXCLUDED.is_absentee,
                    enrichment_status = 'success',
                    enriched_at = EXCLUDED.enriched_at
            """, (
                address, account_num, county_name.lower(), owner_name,
                mailing_address if mailing_address else None,
                market_value, land_value, improvement_value,
                year_built, square_feet, lot_size,
                absentee,
                datetime.now()
            ))
        conn.commit()
        return 'success', county_name, market_value, owner_name, absentee

    # Run parallel processing
    processed = 0
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        # Submit all tasks
        future_to_addr = {
            executor.submit(process_single_address, addr, args.delay): addr
            for addr in addresses
        }

        # Process results as they complete
        for future in as_completed(future_to_addr):
            processed += 1
            result = future.result()
            address = result['address']
            detected_county = get_county_from_zip(address)
            county_display = detected_county.upper() if detected_county else '???'

            # Save to DB (single-threaded to avoid connection issues)
            db_result = save_result_to_db(result, conn)

            if result['status'] == 'skip':
                print(f"[{processed}/{total}] [{county_display}] {address[:50]}... -> SKIP: {result['error']}")
                skip_count += 1
            elif result['status'] == 'failed':
                print(f"[{processed}/{total}] [{county_display}] {address[:50]}... -> NOT FOUND")
                fail_count += 1
            else:
                _, county_name, market_value, owner_name, absentee = db_result
                county_counts[county_name] = county_counts.get(county_name, 0) + 1
                value_str = f"${market_value:,.0f}" if market_value else "N/A"
                absentee_str = " [ABSENTEE]" if absentee else ""
                print(f"[{processed}/{total}] [{county_name}] {address[:50]}... -> {owner_name[:30]} | {value_str}{absentee_str}")
                success_count += 1

    # Summary
    print('\n' + '=' * 50)
    print(f"Success: {success_count}")
    print(f"Failed: {fail_count}")
    print(f"Skipped: {skip_count}")
    print(f"Total: {success_count + fail_count + skip_count}")

    if county_counts:
        print("\nBy County:")
        for county, count in sorted(county_counts.items()):
            print(f"  {county}: {count}")

    conn.close()


if __name__ == "__main__":
    main()
