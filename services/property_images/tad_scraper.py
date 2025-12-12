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
