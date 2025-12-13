"""Dallas County Appraisal District (DCAD) property image scraper.

Images are served from files.dcad.org with predictable URLs based on account number.
No browser automation needed - simple direct download.
"""
import asyncio
import logging
import random
from pathlib import Path
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

MIN_DELAY_SECONDS = 3.0
MAX_DELAY_SECONDS = 5.0


async def fetch_dcad_image(
    account_num: str,
    output_dir: Path,
    filename_prefix: str,
    timeout_s: int = 30,
) -> Optional[dict]:
    """
    Fetch property image from DCAD.

    Args:
        account_num: DCAD account number (e.g., '00000123456')
        output_dir: Directory to save the image
        filename_prefix: Prefix for saved filename
        timeout_s: Request timeout in seconds

    Returns:
        Dict with 'image_path' and 'image_type', or None if not found

    Example:
        >>> result = await fetch_dcad_image("00000123456", Path("media/images"), "permit_001")
        >>> result['image_path']
        'media/images/permit_001_dcad.jpg'
    """
    # Ensure output directory exists
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Check cache first
    filename = f"{filename_prefix}_dcad.jpg"
    image_path = output_dir / filename
    if image_path.exists():
        logger.info(f"Using cached DCAD image: {image_path}")
        return {
            'image_path': str(image_path),
            'image_type': 'front',
        }

    # DCAD image URL pattern
    url = f'https://files.dcad.org/propertyimages/{account_num}.jpg'

    try:
        logger.info(f"Fetching DCAD image for account {account_num}")

        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                timeout=timeout_s,
                follow_redirects=True
            )

            if response.status_code == 200:
                # Save image
                image_path.write_bytes(response.content)
                logger.info(f"Saved DCAD image to {image_path}")

                return {
                    'image_path': str(image_path),
                    'image_type': 'front',  # DCAD typically shows front/street view
                }
            else:
                logger.info(f"DCAD image not found for account {account_num} (status: {response.status_code})")
                return None

    except httpx.HTTPError as e:
        logger.warning(f'DCAD image fetch failed for {account_num}: {e}')
        return None

    except Exception as e:
        logger.error(f'Unexpected error fetching DCAD image for {account_num}: {e}')
        return None

    finally:
        # Throttle to avoid rate limiting
        delay = random.uniform(MIN_DELAY_SECONDS, MAX_DELAY_SECONDS)
        logger.debug(f"Throttling for {delay:.2f}s")
        await asyncio.sleep(delay)
