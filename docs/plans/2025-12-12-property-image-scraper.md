# Property Image Scraper Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a service that fetches property images from CAD portals (primary) and Redfin (backup) for the pool visualizer pipeline.

**Architecture:** Uses existing CAD enrichment to get account numbers, then fetches images via Playwright. Falls back to Redfin search if CAD has no image. Returns structured PropertyImage dataclass with local file path.

**Tech Stack:** Python 3.11+, Playwright (browser automation), httpx (image download), existing CAD ArcGIS integration from `scripts/enrich_cad.py`

---

## Prerequisites

The existing `scripts/enrich_cad.py` already provides:
- ArcGIS API queries for Tarrant, Dallas, Denton, Collin counties
- Returns `account_num` (CAD account ID) for each property
- Address parsing and normalization utilities
- ZIP/city to county mapping

We will REUSE these functions rather than duplicate them.

---

## Task 1: Create Module Structure and Data Model

**Files:**
- Create: `services/__init__.py`
- Create: `services/property_images/__init__.py`
- Create: `services/property_images/models.py`

**Step 1: Create services directory structure**

```bash
mkdir -p services/property_images
```

**Step 2: Create empty `__init__.py` files**

Create `services/__init__.py`:
```python
"""Services module for permit-scraper."""
```

Create `services/property_images/__init__.py`:
```python
"""Property image fetching service for pool visualizer pipeline."""
from .models import PropertyImage
from .image_fetcher import fetch_property_image

__all__ = ['PropertyImage', 'fetch_property_image']
```

**Step 3: Write the data model**

Create `services/property_images/models.py`:
```python
"""Data models for property image service."""
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

ImageSource = Literal['tad', 'dcad', 'dentoncad', 'collincad', 'redfin', 'failed']
ImageType = Literal['front', 'back', 'aerial', 'sketch', 'unknown']


@dataclass
class PropertyImage:
    """Result of a property image fetch attempt."""
    permit_id: str
    address: str
    image_path: str  # Local path to saved image, empty if failed
    source: ImageSource
    image_type: ImageType
    fetched_at: datetime
    account_num: str | None = None  # CAD account number if found
    error: str | None = None  # Error message if failed

    @property
    def success(self) -> bool:
        """Return True if image was successfully fetched."""
        return self.source != 'failed' and bool(self.image_path)
```

**Step 4: Run Python to verify syntax**

```bash
cd /home/reid/testhome/permit-scraper && python3 -c "from services.property_images.models import PropertyImage; print('OK')"
```

Expected: `OK`

**Step 5: Commit**

```bash
git add services/
git commit -m "feat: add property image service module structure and data model"
```

---

## Task 2: Create CAD Account Lookup Utility

**Files:**
- Create: `services/property_images/cad_lookup.py`

**Purpose:** Extract and expose the CAD lookup functionality from `scripts/enrich_cad.py` for reuse.

**Step 1: Write the failing test**

Create `tests/services/__init__.py`:
```python
"""Tests for services module."""
```

Create `tests/services/property_images/__init__.py`:
```python
"""Tests for property image service."""
```

Create `tests/services/property_images/test_cad_lookup.py`:
```python
"""Tests for CAD account lookup."""
import pytest
from services.property_images.cad_lookup import lookup_cad_account


class TestCADLookup:
    """Test CAD account lookup functionality."""

    def test_lookup_tarrant_address(self):
        """Test lookup for a known Tarrant County address."""
        # Use a real Fort Worth address from permit data
        result = lookup_cad_account("3705 DESERT RIDGE DR, Fort Worth TX 76116")

        assert result is not None
        assert result['county'] == 'Tarrant'
        assert result['account_num'] is not None
        assert len(result['account_num']) > 0

    def test_lookup_invalid_address(self):
        """Test lookup for an invalid address returns None."""
        result = lookup_cad_account("99999 FAKE STREET, Nowhere TX 00000")

        assert result is None

    def test_lookup_returns_expected_fields(self):
        """Test that lookup returns all expected fields."""
        result = lookup_cad_account("3705 DESERT RIDGE DR, Fort Worth TX 76116")

        if result:  # May fail if API is down
            assert 'account_num' in result
            assert 'county' in result
            assert 'situs_addr' in result
```

**Step 2: Run test to verify it fails**

```bash
cd /home/reid/testhome/permit-scraper && python3 -m pytest tests/services/property_images/test_cad_lookup.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'services.property_images.cad_lookup'`

**Step 3: Write the implementation**

Create `services/property_images/cad_lookup.py`:
```python
"""CAD account lookup service.

Wraps the ArcGIS CAD API queries from scripts/enrich_cad.py for use
in the property image fetcher.
"""
import re
from typing import Optional

import requests

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

    # Build WHERE clause
    if county == 'tarrant':
        where = f"Situs_Addr LIKE '{house_num} %{street_core}%'"
    elif county == 'dallas':
        where = f"SITEADDRESS LIKE '{house_num} %{street_core}%'"
    elif county == 'denton':
        where = f"situs_num = '{house_num}' AND situs_street LIKE '%{street_core}%'"
    elif county == 'collin':
        where = f"GIS_DBO_AD_Entity_situs_num = '{house_num}' AND GIS_DBO_AD_Entity_situs_street LIKE '%{street_core}%'"
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
```

**Step 4: Run test to verify it passes**

```bash
cd /home/reid/testhome/permit-scraper && python3 -m pytest tests/services/property_images/test_cad_lookup.py -v
```

Expected: PASS (or skip if API is down)

**Step 5: Commit**

```bash
git add services/property_images/cad_lookup.py tests/services/
git commit -m "feat: add CAD account lookup service wrapping ArcGIS APIs"
```

---

## Task 3: Create TAD Image Scraper

**Files:**
- Create: `services/property_images/tad_scraper.py`
- Create: `tests/services/property_images/test_tad_scraper.py`

**Step 1: Write the failing test**

Create `tests/services/property_images/test_tad_scraper.py`:
```python
"""Tests for TAD image scraper."""
import pytest
from pathlib import Path
from services.property_images.tad_scraper import fetch_tad_image


class TestTADScraper:
    """Test TAD property image fetching."""

    @pytest.fixture
    def temp_media_dir(self, tmp_path):
        """Create temp media directory."""
        media_dir = tmp_path / "media" / "property_images"
        media_dir.mkdir(parents=True)
        return media_dir

    @pytest.mark.asyncio
    async def test_fetch_with_valid_account(self, temp_media_dir):
        """Test fetching image with a valid TAD account number."""
        # Account 40123324 is from TAD.org example
        result = await fetch_tad_image(
            account_num="40123324",
            output_dir=temp_media_dir,
            filename_prefix="test"
        )

        # May return None if no image on this property
        if result:
            assert Path(result['image_path']).exists()
            assert result['image_type'] in ('front', 'back', 'aerial', 'sketch', 'unknown')

    @pytest.mark.asyncio
    async def test_fetch_with_invalid_account(self, temp_media_dir):
        """Test that invalid account returns None."""
        result = await fetch_tad_image(
            account_num="00000000",
            output_dir=temp_media_dir,
            filename_prefix="test"
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_creates_output_directory(self, tmp_path):
        """Test that output directory is created if missing."""
        output_dir = tmp_path / "new_dir" / "images"

        # Should not raise even if dir doesn't exist
        result = await fetch_tad_image(
            account_num="40123324",
            output_dir=output_dir,
            filename_prefix="test"
        )

        assert output_dir.exists()
```

**Step 2: Run test to verify it fails**

```bash
cd /home/reid/testhome/permit-scraper && python3 -m pytest tests/services/property_images/test_tad_scraper.py -v
```

Expected: FAIL with `ModuleNotFoundError`

**Step 3: Write the implementation**

Create `services/property_images/tad_scraper.py`:
```python
"""Tarrant Appraisal District (TAD) property image scraper.

Uses Playwright to navigate TAD.org and extract property images.
TAD blocks simple HTTP requests, so browser automation is required.

Property URL format: https://www.tad.org/property?account={account_num}
"""
import asyncio
import logging
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin

import httpx
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

logger = logging.getLogger(__name__)

TAD_BASE_URL = "https://www.tad.org"
TAD_PROPERTY_URL = "https://www.tad.org/property"

# Rate limiting
REQUEST_DELAY_SECONDS = 2.0


async def fetch_tad_image(
    account_num: str,
    output_dir: Path,
    filename_prefix: str,
    timeout_ms: int = 30000,
) -> Optional[dict]:
    """
    Fetch property image from TAD.org for a given account number.

    Args:
        account_num: TAD account number (e.g., "40123324")
        output_dir: Directory to save the image
        filename_prefix: Prefix for saved filename
        timeout_ms: Page load timeout in milliseconds

    Returns:
        Dict with 'image_path' and 'image_type', or None if no image found

    Example:
        >>> result = await fetch_tad_image("40123324", Path("media/images"), "permit_001")
        >>> result['image_path']
        'media/images/permit_001_tad.jpg'
    """
    # Ensure output directory exists
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    property_url = f"{TAD_PROPERTY_URL}?account={account_num}"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        try:
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()

            logger.info(f"Navigating to TAD property page: {property_url}")

            try:
                await page.goto(property_url, wait_until="networkidle", timeout=timeout_ms)
            except PlaywrightTimeout:
                logger.warning(f"Timeout loading TAD page for account {account_num}")
                return None

            # Wait for page to fully render
            await asyncio.sleep(1)

            # Look for property images on the page
            # TAD typically shows images in a specific container
            image_selectors = [
                # Main property photo
                'img[src*="property"]',
                'img[src*="photo"]',
                'img[src*="image"]',
                # Sketch/aerial view
                'img[src*="sketch"]',
                'img[src*="aerial"]',
                # Generic property images
                '.property-image img',
                '.photo-container img',
                '[class*="image"] img',
                # Fallback: any large image
                'img[width][height]',
            ]

            image_url = None
            image_type = 'unknown'

            for selector in image_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    for element in elements:
                        src = await element.get_attribute('src')
                        if not src:
                            continue

                        # Skip tiny icons and logos
                        width = await element.get_attribute('width')
                        height = await element.get_attribute('height')

                        # Try to get actual rendered size if attributes not set
                        if not width or not height:
                            box = await element.bounding_box()
                            if box:
                                width = box['width']
                                height = box['height']

                        # Skip small images (likely icons)
                        if width and height:
                            try:
                                if float(width) < 100 or float(height) < 100:
                                    continue
                            except (ValueError, TypeError):
                                pass

                        # Skip known non-property images
                        skip_patterns = ['logo', 'icon', 'banner', 'header', 'footer', 'avatar']
                        if any(pattern in src.lower() for pattern in skip_patterns):
                            continue

                        # Found a candidate image
                        image_url = src if src.startswith('http') else urljoin(TAD_BASE_URL, src)

                        # Determine image type from URL/alt
                        alt = await element.get_attribute('alt') or ''
                        combined = f"{src} {alt}".lower()

                        if 'aerial' in combined:
                            image_type = 'aerial'
                        elif 'sketch' in combined:
                            image_type = 'sketch'
                        elif 'back' in combined or 'rear' in combined:
                            image_type = 'back'
                        elif 'front' in combined:
                            image_type = 'front'
                        else:
                            image_type = 'front'  # Default assumption for main photo

                        logger.info(f"Found image: {image_url} (type: {image_type})")
                        break

                    if image_url:
                        break

                except Exception as e:
                    logger.debug(f"Error checking selector {selector}: {e}")
                    continue

            if not image_url:
                logger.info(f"No property image found for TAD account {account_num}")
                return None

            # Download the image
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        image_url,
                        headers={"Referer": property_url},
                        timeout=30.0,
                        follow_redirects=True
                    )
                    response.raise_for_status()

                    # Determine file extension from content type
                    content_type = response.headers.get('content-type', '')
                    if 'jpeg' in content_type or 'jpg' in content_type:
                        ext = '.jpg'
                    elif 'png' in content_type:
                        ext = '.png'
                    elif 'gif' in content_type:
                        ext = '.gif'
                    elif 'webp' in content_type:
                        ext = '.webp'
                    else:
                        # Guess from URL
                        ext = Path(image_url.split('?')[0]).suffix or '.jpg'

                    filename = f"{filename_prefix}_tad{ext}"
                    image_path = output_dir / filename

                    image_path.write_bytes(response.content)
                    logger.info(f"Saved TAD image to {image_path}")

                    return {
                        'image_path': str(image_path),
                        'image_type': image_type,
                    }

            except httpx.HTTPError as e:
                logger.error(f"Failed to download image: {e}")
                return None

        finally:
            await browser.close()
            # Rate limiting
            await asyncio.sleep(REQUEST_DELAY_SECONDS)
```

**Step 4: Run test to verify it passes**

```bash
cd /home/reid/testhome/permit-scraper && python3 -m pytest tests/services/property_images/test_tad_scraper.py -v --timeout=60
```

Expected: Tests should pass (may be slow due to browser automation)

**Step 5: Commit**

```bash
git add services/property_images/tad_scraper.py tests/services/property_images/test_tad_scraper.py
git commit -m "feat: add TAD property image scraper using Playwright"
```

---

## Task 4: Create Redfin Backup Scraper

**Files:**
- Create: `services/property_images/redfin_scraper.py`
- Create: `tests/services/property_images/test_redfin_scraper.py`

**Step 1: Write the failing test**

Create `tests/services/property_images/test_redfin_scraper.py`:
```python
"""Tests for Redfin backup image scraper."""
import pytest
from pathlib import Path
from services.property_images.redfin_scraper import fetch_redfin_image


class TestRedfinScraper:
    """Test Redfin property image fetching."""

    @pytest.fixture
    def temp_media_dir(self, tmp_path):
        """Create temp media directory."""
        media_dir = tmp_path / "media" / "property_images"
        media_dir.mkdir(parents=True)
        return media_dir

    @pytest.mark.asyncio
    async def test_fetch_with_valid_address(self, temp_media_dir):
        """Test fetching image with a real address."""
        result = await fetch_redfin_image(
            address="3705 Desert Ridge Dr",
            city="Fort Worth",
            state="TX",
            output_dir=temp_media_dir,
            filename_prefix="test",
            prefer_backyard=True
        )

        # May return None if property not on Redfin
        if result:
            assert Path(result['image_path']).exists()
            assert result['image_type'] in ('front', 'back', 'aerial', 'unknown')

    @pytest.mark.asyncio
    async def test_fetch_with_invalid_address(self, temp_media_dir):
        """Test that invalid address returns None gracefully."""
        result = await fetch_redfin_image(
            address="99999 Fake Street",
            city="Nowhere",
            state="TX",
            output_dir=temp_media_dir,
            filename_prefix="test"
        )

        assert result is None
```

**Step 2: Run test to verify it fails**

```bash
cd /home/reid/testhome/permit-scraper && python3 -m pytest tests/services/property_images/test_redfin_scraper.py -v
```

Expected: FAIL with `ModuleNotFoundError`

**Step 3: Write the implementation**

Create `services/property_images/redfin_scraper.py`:
```python
"""Redfin property image scraper (backup source).

Uses Playwright to search Redfin and extract property images.
Redfin has aggressive anti-scraping, so use with caution and rate limiting.

IMPORTANT:
- Add 3-5 second delays between requests
- Maximum 50 properties per session
- Stop immediately if blocked
"""
import asyncio
import json
import logging
import random
import re
from pathlib import Path
from typing import Optional

import httpx
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

logger = logging.getLogger(__name__)

REDFIN_BASE_URL = "https://www.redfin.com"

# Rate limiting (conservative)
MIN_DELAY_SECONDS = 3.0
MAX_DELAY_SECONDS = 5.0

# User agents to rotate
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
]


async def fetch_redfin_image(
    address: str,
    city: str,
    state: str,
    output_dir: Path,
    filename_prefix: str,
    prefer_backyard: bool = True,
    timeout_ms: int = 45000,
) -> Optional[dict]:
    """
    Fetch property image from Redfin for a given address.

    Args:
        address: Street address (e.g., "3705 Desert Ridge Dr")
        city: City name (e.g., "Fort Worth")
        state: State abbreviation (e.g., "TX")
        output_dir: Directory to save the image
        filename_prefix: Prefix for saved filename
        prefer_backyard: If True, try to find backyard/aerial photos
        timeout_ms: Page load timeout in milliseconds

    Returns:
        Dict with 'image_path' and 'image_type', or None if not found
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Build search query
    search_query = f"{address}, {city}, {state}"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        try:
            context = await browser.new_context(
                user_agent=random.choice(USER_AGENTS),
                viewport={"width": 1920, "height": 1080},
            )
            page = await context.new_page()

            # Navigate to Redfin
            logger.info(f"Searching Redfin for: {search_query}")

            try:
                await page.goto(REDFIN_BASE_URL, wait_until="networkidle", timeout=timeout_ms)
            except PlaywrightTimeout:
                logger.warning("Timeout loading Redfin homepage")
                return None

            # Check for blocking
            if await _is_blocked(page):
                logger.error("Redfin is blocking requests - stopping")
                return None

            # Find and use search box
            search_selectors = [
                'input[data-rf-test-id="search-box-input"]',
                'input[placeholder*="Address"]',
                'input[placeholder*="Search"]',
                '#search-box-input',
                '.SearchBox input',
            ]

            search_input = None
            for selector in search_selectors:
                try:
                    search_input = await page.wait_for_selector(selector, timeout=5000)
                    if search_input:
                        break
                except:
                    continue

            if not search_input:
                logger.warning("Could not find Redfin search box")
                return None

            # Enter search query
            await search_input.fill(search_query)
            await asyncio.sleep(1)  # Wait for autocomplete

            # Submit search
            await page.keyboard.press("Enter")

            try:
                await page.wait_for_load_state("networkidle", timeout=timeout_ms)
            except PlaywrightTimeout:
                logger.warning("Timeout waiting for search results")
                return None

            # Check for blocking again
            if await _is_blocked(page):
                logger.error("Redfin blocked after search - stopping")
                return None

            # Wait for potential redirect to property page
            await asyncio.sleep(2)

            current_url = page.url

            # If we're on a property page, extract images
            if '/home/' in current_url or '/property/' in current_url:
                return await _extract_property_images(
                    page, output_dir, filename_prefix, prefer_backyard
                )

            # If on search results, try to click first result
            result_selectors = [
                '.HomeCard a',
                '[data-rf-test-id="home-card"] a',
                '.searchResults a[href*="/home/"]',
            ]

            for selector in result_selectors:
                try:
                    first_result = await page.query_selector(selector)
                    if first_result:
                        await first_result.click()
                        await page.wait_for_load_state("networkidle", timeout=timeout_ms)

                        if await _is_blocked(page):
                            return None

                        return await _extract_property_images(
                            page, output_dir, filename_prefix, prefer_backyard
                        )
                except Exception as e:
                    logger.debug(f"Error clicking result: {e}")
                    continue

            logger.info(f"No property found on Redfin for: {search_query}")
            return None

        finally:
            await browser.close()
            # Rate limiting
            delay = random.uniform(MIN_DELAY_SECONDS, MAX_DELAY_SECONDS)
            await asyncio.sleep(delay)


async def _is_blocked(page) -> bool:
    """Check if Redfin is blocking us."""
    content = await page.content()
    blocked_indicators = [
        'Access Denied',
        'blocked',
        'captcha',
        'verify you are human',
        'too many requests',
    ]
    content_lower = content.lower()
    return any(indicator.lower() in content_lower for indicator in blocked_indicators)


async def _extract_property_images(
    page,
    output_dir: Path,
    filename_prefix: str,
    prefer_backyard: bool
) -> Optional[dict]:
    """Extract and download property images from a Redfin property page."""

    # Try to find image data in page scripts (Redfin embeds JSON)
    try:
        scripts = await page.query_selector_all('script')
        for script in scripts:
            content = await script.inner_text()
            if 'photos' in content.lower() and '{' in content:
                # Try to parse JSON from script
                try:
                    # Look for image URLs in the content
                    image_urls = re.findall(
                        r'https://[^"\']+(?:jpg|jpeg|png|webp)[^"\']*',
                        content,
                        re.I
                    )
                    if image_urls:
                        # Filter for property photos (not icons)
                        photo_urls = [
                            url for url in image_urls
                            if 'photo' in url.lower() or 'image' in url.lower()
                        ]
                        if photo_urls:
                            # Pick best photo
                            best_url = _select_best_image(photo_urls, prefer_backyard)
                            return await _download_image(
                                best_url, output_dir, filename_prefix, prefer_backyard
                            )
                except:
                    pass
    except:
        pass

    # Fallback: Find images in DOM
    image_selectors = [
        '.PhotoCarousel img',
        '[data-rf-test-id="photo-carousel"] img',
        '.listing-hero img',
        '.HomeMainMedia img',
        'img[src*="photo"]',
        'img[src*="redfin"]',
    ]

    for selector in image_selectors:
        try:
            images = await page.query_selector_all(selector)
            image_urls = []

            for img in images:
                src = await img.get_attribute('src')
                if src and ('jpg' in src or 'jpeg' in src or 'png' in src or 'webp' in src):
                    # Skip thumbnails
                    if 'thumb' not in src.lower():
                        image_urls.append(src)

            if image_urls:
                best_url = _select_best_image(image_urls, prefer_backyard)
                return await _download_image(best_url, output_dir, filename_prefix, prefer_backyard)

        except Exception as e:
            logger.debug(f"Error with selector {selector}: {e}")
            continue

    logger.info("No images found on Redfin property page")
    return None


def _select_best_image(urls: list[str], prefer_backyard: bool) -> str:
    """Select the best image URL from a list."""
    if not urls:
        return ""

    if prefer_backyard:
        # Look for backyard/aerial keywords
        backyard_keywords = ['back', 'rear', 'yard', 'aerial', 'drone', 'pool']
        for url in urls:
            if any(kw in url.lower() for kw in backyard_keywords):
                return url

    # Return first (usually main photo)
    return urls[0]


async def _download_image(
    url: str,
    output_dir: Path,
    filename_prefix: str,
    prefer_backyard: bool
) -> Optional[dict]:
    """Download an image and return result dict."""
    if not url:
        return None

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers={
                    "User-Agent": random.choice(USER_AGENTS),
                    "Referer": REDFIN_BASE_URL,
                },
                timeout=30.0,
                follow_redirects=True
            )
            response.raise_for_status()

            # Determine extension
            content_type = response.headers.get('content-type', '')
            if 'jpeg' in content_type or 'jpg' in content_type:
                ext = '.jpg'
            elif 'png' in content_type:
                ext = '.png'
            elif 'webp' in content_type:
                ext = '.webp'
            else:
                ext = '.jpg'

            filename = f"{filename_prefix}_redfin{ext}"
            image_path = output_dir / filename

            image_path.write_bytes(response.content)
            logger.info(f"Saved Redfin image to {image_path}")

            # Determine image type from URL
            url_lower = url.lower()
            if any(kw in url_lower for kw in ['back', 'rear', 'yard']):
                image_type = 'back'
            elif any(kw in url_lower for kw in ['aerial', 'drone']):
                image_type = 'aerial'
            else:
                image_type = 'front'

            return {
                'image_path': str(image_path),
                'image_type': image_type,
            }

    except httpx.HTTPError as e:
        logger.error(f"Failed to download Redfin image: {e}")
        return None
```

**Step 4: Run test to verify it passes**

```bash
cd /home/reid/testhome/permit-scraper && python3 -m pytest tests/services/property_images/test_redfin_scraper.py -v --timeout=120
```

Expected: Tests should pass (may be slow, may skip if Redfin blocks)

**Step 5: Commit**

```bash
git add services/property_images/redfin_scraper.py tests/services/property_images/test_redfin_scraper.py
git commit -m "feat: add Redfin backup image scraper with rate limiting"
```

---

## Task 5: Create Main Orchestrator

**Files:**
- Create: `services/property_images/image_fetcher.py`
- Create: `tests/services/property_images/test_image_fetcher.py`

**Step 1: Write the failing test**

Create `tests/services/property_images/test_image_fetcher.py`:
```python
"""Tests for main image fetcher orchestrator."""
import pytest
from pathlib import Path
from services.property_images import fetch_property_image, PropertyImage


class TestImageFetcher:
    """Test the main image fetcher orchestrator."""

    @pytest.fixture
    def temp_media_dir(self, tmp_path):
        """Create temp media directory."""
        media_dir = tmp_path / "media" / "property_images"
        media_dir.mkdir(parents=True)
        return media_dir

    @pytest.mark.asyncio
    async def test_fetch_returns_property_image(self, temp_media_dir, monkeypatch):
        """Test that fetch returns a PropertyImage object."""
        # Patch the media dir
        monkeypatch.setenv("MEDIA_DIR", str(temp_media_dir.parent))

        result = await fetch_property_image(
            address="3705 DESERT RIDGE DR, Fort Worth TX 76116",
            city="Fort Worth",
            permit_id="PP25-21334",
        )

        assert isinstance(result, PropertyImage)
        assert result.permit_id == "PP25-21334"
        assert result.address == "3705 DESERT RIDGE DR, Fort Worth TX 76116"
        # Source should be one of the valid options
        assert result.source in ('tad', 'dcad', 'dentoncad', 'collincad', 'redfin', 'failed')

    @pytest.mark.asyncio
    async def test_failed_fetch_has_error_message(self, temp_media_dir, monkeypatch):
        """Test that failed fetch includes error message."""
        monkeypatch.setenv("MEDIA_DIR", str(temp_media_dir.parent))

        result = await fetch_property_image(
            address="99999 FAKE STREET, Nowhere TX 00000",
            city="Nowhere",
            permit_id="FAKE001",
        )

        assert isinstance(result, PropertyImage)
        assert result.source == 'failed'
        assert result.error is not None
```

**Step 2: Run test to verify it fails**

```bash
cd /home/reid/testhome/permit-scraper && python3 -m pytest tests/services/property_images/test_image_fetcher.py -v
```

Expected: FAIL with `ModuleNotFoundError`

**Step 3: Write the implementation**

Create `services/property_images/image_fetcher.py`:
```python
"""Main orchestrator for property image fetching.

Coordinates between CAD lookup, TAD scraper, and Redfin backup
to fetch property images for the pool visualizer pipeline.

Usage:
    from services.property_images import fetch_property_image

    result = await fetch_property_image(
        address="3705 DESERT RIDGE DR, Fort Worth TX 76116",
        city="Fort Worth",
        permit_id="PP25-21334"
    )

    if result.success:
        print(f"Image saved to: {result.image_path}")
    else:
        print(f"Failed: {result.error}")

CLI:
    python -m services.property_images.image_fetcher "123 Main St, Fort Worth TX 76116" "Fort Worth" "permit_001"
"""
import asyncio
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from .models import PropertyImage, ImageSource, ImageType
from .cad_lookup import lookup_cad_account
from .tad_scraper import fetch_tad_image
from .redfin_scraper import fetch_redfin_image

logger = logging.getLogger(__name__)

# Default media directory
DEFAULT_MEDIA_DIR = Path("media/property_images")


def _get_media_dir() -> Path:
    """Get media directory from environment or default."""
    env_dir = os.environ.get("MEDIA_DIR")
    if env_dir:
        return Path(env_dir) / "property_images"
    return DEFAULT_MEDIA_DIR


def _extract_state(address: str) -> str:
    """Extract state from address, default to TX."""
    if ' TX ' in address.upper() or address.upper().endswith(' TX'):
        return 'TX'
    # Could add more states, but this is DFW-focused
    return 'TX'


async def fetch_property_image(
    address: str,
    city: str,
    permit_id: str,
    prefer_backyard: bool = True,
    skip_redfin: bool = False,
) -> PropertyImage:
    """
    Fetch a property image from available sources.

    Priority:
    1. Tarrant CAD (if Tarrant County)
    2. Dallas CAD (if Dallas County)
    3. Denton CAD (if Denton County)
    4. Collin CAD (if Collin County)
    5. Redfin (backup, unless skip_redfin=True)
    6. Return failed status if all sources fail

    Args:
        address: Full property address (e.g., "3705 DESERT RIDGE DR, Fort Worth TX 76116")
        city: City name (e.g., "Fort Worth")
        permit_id: Permit ID for filename prefix
        prefer_backyard: If True, prefer backyard/aerial images
        skip_redfin: If True, don't try Redfin (to avoid rate limits)

    Returns:
        PropertyImage with result details

    Example:
        >>> result = await fetch_property_image(
        ...     "3705 DESERT RIDGE DR, Fort Worth TX 76116",
        ...     "Fort Worth",
        ...     "PP25-21334"
        ... )
        >>> result.success
        True
        >>> result.image_path
        'media/property_images/PP25-21334_tad.jpg'
    """
    now = datetime.now()
    media_dir = _get_media_dir()
    state = _extract_state(address)

    # Step 1: Look up CAD account number
    logger.info(f"Looking up CAD account for: {address}")
    cad_result = lookup_cad_account(address)

    if cad_result:
        account_num = cad_result['account_num']
        county = cad_result['county']
        logger.info(f"Found CAD account: {account_num} ({county} County)")

        # Step 2: Fetch image from appropriate CAD portal
        if county == 'Tarrant':
            # TAD has images on their website
            tad_result = await fetch_tad_image(
                account_num=account_num,
                output_dir=media_dir,
                filename_prefix=permit_id
            )

            if tad_result:
                return PropertyImage(
                    permit_id=permit_id,
                    address=address,
                    image_path=tad_result['image_path'],
                    source='tad',
                    image_type=tad_result['image_type'],
                    fetched_at=now,
                    account_num=account_num,
                )

            logger.info("TAD had no image, trying Redfin backup...")

        # TODO: Add DCAD, Denton CAD, Collin CAD image scrapers
        # For now, fall through to Redfin for non-Tarrant counties
        else:
            logger.info(f"{county} CAD image scraper not implemented, trying Redfin...")
    else:
        logger.info("CAD lookup failed, trying Redfin backup...")

    # Step 3: Try Redfin as backup
    if not skip_redfin:
        # Extract street address (before comma)
        street_address = address.split(',')[0].strip()

        redfin_result = await fetch_redfin_image(
            address=street_address,
            city=city,
            state=state,
            output_dir=media_dir,
            filename_prefix=permit_id,
            prefer_backyard=prefer_backyard
        )

        if redfin_result:
            return PropertyImage(
                permit_id=permit_id,
                address=address,
                image_path=redfin_result['image_path'],
                source='redfin',
                image_type=redfin_result['image_type'],
                fetched_at=now,
                account_num=cad_result['account_num'] if cad_result else None,
            )

    # Step 4: All sources failed
    return PropertyImage(
        permit_id=permit_id,
        address=address,
        image_path='',
        source='failed',
        image_type='unknown',
        fetched_at=now,
        account_num=cad_result['account_num'] if cad_result else None,
        error="No image found from any source (CAD or Redfin)"
    )


async def main():
    """CLI entry point."""
    if len(sys.argv) < 4:
        print("Usage: python -m services.property_images.image_fetcher ADDRESS CITY PERMIT_ID")
        print('Example: python -m services.property_images.image_fetcher "3705 DESERT RIDGE DR, Fort Worth TX 76116" "Fort Worth" "PP25-21334"')
        sys.exit(1)

    address = sys.argv[1]
    city = sys.argv[2]
    permit_id = sys.argv[3]

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print(f"Fetching image for: {address}")
    print(f"City: {city}")
    print(f"Permit ID: {permit_id}")
    print()

    result = await fetch_property_image(address, city, permit_id)

    print("Result:")
    print(f"  permit_id: {result.permit_id!r}")
    print(f"  address: {result.address!r}")
    print(f"  image_path: {result.image_path!r}")
    print(f"  source: {result.source!r}")
    print(f"  image_type: {result.image_type!r}")
    print(f"  account_num: {result.account_num!r}")
    print(f"  fetched_at: {result.fetched_at}")
    print(f"  success: {result.success}")
    if result.error:
        print(f"  error: {result.error!r}")


if __name__ == "__main__":
    asyncio.run(main())
```

**Step 4: Update the `__init__.py` exports**

Update `services/property_images/__init__.py`:
```python
"""Property image fetching service for pool visualizer pipeline."""
from .models import PropertyImage
from .image_fetcher import fetch_property_image

__all__ = ['PropertyImage', 'fetch_property_image']
```

**Step 5: Run test to verify it passes**

```bash
cd /home/reid/testhome/permit-scraper && python3 -m pytest tests/services/property_images/test_image_fetcher.py -v --timeout=120
```

Expected: PASS

**Step 6: Commit**

```bash
git add services/property_images/
git commit -m "feat: add main image fetcher orchestrator with CAD + Redfin fallback"
```

---

## Task 6: Create Media Directory and Integration Test

**Files:**
- Create: `media/property_images/.gitkeep`
- Modify: `tests/services/property_images/test_integration.py`

**Step 1: Create media directory**

```bash
mkdir -p media/property_images
touch media/property_images/.gitkeep
```

**Step 2: Write integration test**

Create `tests/services/property_images/test_integration.py`:
```python
"""Integration tests for property image service.

These tests hit real APIs and may be slow. Run with:
    pytest tests/services/property_images/test_integration.py -v --timeout=180
"""
import pytest
from pathlib import Path
from services.property_images import fetch_property_image, PropertyImage


@pytest.mark.integration
@pytest.mark.asyncio
class TestRealAPIs:
    """Integration tests using real addresses from permit data."""

    @pytest.fixture
    def real_media_dir(self, tmp_path):
        """Use temp dir for test images."""
        media_dir = tmp_path / "media" / "property_images"
        media_dir.mkdir(parents=True)
        return media_dir

    async def test_fort_worth_address(self, real_media_dir, monkeypatch):
        """Test with a real Fort Worth address from permit data."""
        monkeypatch.setenv("MEDIA_DIR", str(real_media_dir.parent))

        result = await fetch_property_image(
            address="3705 DESERT RIDGE DR, Fort Worth TX 76116",
            city="Fort Worth",
            permit_id="integration_test_fw"
        )

        assert isinstance(result, PropertyImage)
        print(f"\nResult: source={result.source}, path={result.image_path}")

        if result.success:
            assert Path(result.image_path).exists()
            assert Path(result.image_path).stat().st_size > 1000  # Not empty

    async def test_dallas_address(self, real_media_dir, monkeypatch):
        """Test with a Dallas County address."""
        monkeypatch.setenv("MEDIA_DIR", str(real_media_dir.parent))

        result = await fetch_property_image(
            address="1234 ELM ST, Dallas TX 75201",
            city="Dallas",
            permit_id="integration_test_dallas",
            skip_redfin=True  # Just test CAD lookup
        )

        assert isinstance(result, PropertyImage)
        # Dallas CAD image scraper not implemented yet, so this may fail
        print(f"\nResult: source={result.source}, account={result.account_num}")
```

**Step 3: Run integration test**

```bash
cd /home/reid/testhome/permit-scraper && python3 -m pytest tests/services/property_images/test_integration.py -v --timeout=180 -m integration
```

Expected: Tests should run and show results

**Step 4: Add pytest marker config**

Add to `pytest.ini` (create if needed):
```ini
[pytest]
markers =
    integration: marks tests as integration tests (may be slow, hits real APIs)
asyncio_mode = auto
```

**Step 5: Commit**

```bash
git add media/ tests/services/property_images/test_integration.py pytest.ini
git commit -m "feat: add integration tests and media directory"
```

---

## Task 7: Add CLI Verification Script

**Files:**
- Modify: `services/property_images/image_fetcher.py` (already has CLI, verify it works)

**Step 1: Test CLI directly**

```bash
cd /home/reid/testhome/permit-scraper && python3 -m services.property_images.image_fetcher "3705 DESERT RIDGE DR, Fort Worth TX 76116" "Fort Worth" "cli_test_001"
```

Expected output:
```
Fetching image for: 3705 DESERT RIDGE DR, Fort Worth TX 76116
City: Fort Worth
Permit ID: cli_test_001

Result:
  permit_id: 'cli_test_001'
  address: '3705 DESERT RIDGE DR, Fort Worth TX 76116'
  image_path: 'media/property_images/cli_test_001_tad.jpg'
  source: 'tad'
  image_type: 'front'
  ...
```

**Step 2: Verify image was saved**

```bash
ls -la media/property_images/
```

Expected: Should see `cli_test_001_tad.jpg` or similar

**Step 3: Commit final state**

```bash
git add .
git commit -m "feat: complete property image scraper service"
```

---

## Verification Checklist

Run these commands to verify the implementation:

```bash
# 1. Unit tests pass
cd /home/reid/testhome/permit-scraper
python3 -m pytest tests/services/property_images/ -v --ignore=tests/services/property_images/test_integration.py

# 2. CLI works
python3 -m services.property_images.image_fetcher "3705 DESERT RIDGE DR, Fort Worth TX 76116" "Fort Worth" "verify_001"

# 3. Image was saved
ls -la media/property_images/

# 4. Module imports correctly
python3 -c "from services.property_images import fetch_property_image, PropertyImage; print('OK')"
```

---

## Success Criteria Checklist

- [ ] Can fetch image from TAD given an address
- [ ] Falls back to Redfin if CAD fails
- [ ] Saves image locally with descriptive filename
- [ ] Returns structured result with source and type
- [ ] Handles "no image found" gracefully
- [ ] Rate limiting prevents blocking

---

## Future Enhancements (Not in scope)

1. Add Dallas CAD (DCAD) image scraper
2. Add Denton CAD image scraper
3. Add Collin CAD image scraper
4. Batch processing for multiple addresses
5. Image caching to avoid re-fetching
6. Database tracking of fetched images
