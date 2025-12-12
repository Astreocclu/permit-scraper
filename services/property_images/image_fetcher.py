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
