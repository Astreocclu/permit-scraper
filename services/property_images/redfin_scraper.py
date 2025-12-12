"""Redfin property image scraper (backup source).

Uses Playwright to search Redfin and extract property images.
Redfin has aggressive anti-scraping, so use with caution and rate limiting.

IMPORTANT:
- Add 3-5 second delays between requests
- Maximum 50 properties per session
- Stop immediately if blocked
"""
import asyncio
import logging
import random
import re
from pathlib import Path
from typing import Optional

import httpx
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
from playwright_stealth import Stealth

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
                locale="en-US",
                timezone_id="America/Chicago",
            )
            page = await context.new_page()

            # Apply stealth to avoid detection
            stealth = Stealth()
            await stealth.apply_stealth_async(page)

            # Navigate to Redfin with faster wait strategy
            logger.info(f"Searching Redfin for: {search_query}")

            try:
                await page.goto(REDFIN_BASE_URL, wait_until="domcontentloaded", timeout=timeout_ms)
                # Wait for search box to appear (confirms page is interactive)
                await page.wait_for_selector('input[placeholder*="Search"]', timeout=10000)
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
                # Wait for navigation, not network idle
                await page.wait_for_load_state("domcontentloaded", timeout=timeout_ms)
                # Wait for either property page or search results
                await page.wait_for_selector(
                    'img[src*="photo"], .HomeCard, [data-rf-test-id="home-card"], .searchResults',
                    timeout=15000
                )
            except PlaywrightTimeout:
                logger.warning("Timeout waiting for search results")
                return None

            # Check for blocking again
            if await _is_blocked(page):
                logger.error("Redfin blocked after search - stopping")
                return None

            # Brief pause for any redirects
            await asyncio.sleep(1)

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
