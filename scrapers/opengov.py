#!/usr/bin/env python3
"""
OPENGOV PERMIT SCRAPER (Playwright)
Platform: OpenGov Permitting & Licensing Portal
Covers: Highland Park, Bedford (wealthy DFW suburbs)

Usage:
  python3 scrapers/opengov.py highland_park 100
  python3 scrapers/opengov.py bedford 100
  python3 scrapers/opengov.py --list
"""

import asyncio
import json
import logging
import re
import sys
from datetime import datetime
from pathlib import Path

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

OUTPUT_DIR = Path(__file__).parent.parent / "data" / "raw"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# OpenGov cities with confirmed public access
OPENGOV_CITIES = {
    'highland_park': {
        'name': 'Highland Park',
        'base_url': 'https://highlandparktx.portal.opengov.com',
        'pop': 9000,
        'tier': 'A',  # Ultra-wealthy
    },
    'bedford': {
        'name': 'Bedford',
        'base_url': 'https://bedfordtx.portal.opengov.com',
        'pop': 48000,
        'tier': 'B',
    },
}

# Common street names to search (same as MyGov pattern)
SEARCH_TERMS = [
    'Main', 'Oak', 'Park', 'Hill', 'Lake',
    'Cedar', 'Pine', 'Maple', 'Elm',
    'First', 'Second', 'Third',
    'North', 'South', 'East', 'West',
    'Creek', 'Spring', 'Valley', 'Ridge',
    'Meadow', 'Forest', 'Highland', 'Sunset',
]


async def navigate_to_search(page, city_config: dict) -> bool:
    """
    Navigate to OpenGov portal and find the search interface.

    OpenGov uses Ember.js SPA - we need to wait for app to bootstrap,
    then find the search functionality.

    Returns True if search is accessible, False otherwise.
    """
    base_url = city_config['base_url']
    city_name = city_config['name']

    try:
        logger.info(f"[{city_name}] Navigating to {base_url}")
        await page.goto(base_url, timeout=30000)

        # Wait for Ember app to load (loading spinner disappears)
        await page.wait_for_selector('#main-content, .ember-application', timeout=20000)
        logger.info(f"[{city_name}] App loaded, looking for search...")

        # Give Angular/Ember extra time to render
        await asyncio.sleep(3)

        # Look for search button/link in header
        # Common patterns: "Search" link, magnifying glass icon, search input
        search_selectors = [
            'a:has-text("Search")',
            'button:has-text("Search")',
            '[data-test="search"]',
            '.search-button',
            'input[type="search"]',
            '[placeholder*="Search"]',
        ]

        for selector in search_selectors:
            element = page.locator(selector).first
            if await element.count() > 0:
                logger.info(f"[{city_name}] Found search element: {selector}")
                return True

        # If no search found, try clicking "Permits" or "Records" link
        nav_links = ['Permits', 'Records', 'Applications', 'Public Records']
        for link_text in nav_links:
            link = page.locator(f'a:has-text("{link_text}")').first
            if await link.count() > 0:
                await link.click()
                await asyncio.sleep(2)
                logger.info(f"[{city_name}] Clicked '{link_text}' navigation")
                return True

        logger.warning(f"[{city_name}] Could not find search interface")
        return False

    except PlaywrightTimeout:
        logger.error(f"[{city_name}] Timeout loading portal")
        return False
    except Exception as e:
        logger.error(f"[{city_name}] Error navigating: {e}")
        return False


async def main():
    if len(sys.argv) < 2 or sys.argv[1] == '--list':
        print("OpenGov Multi-City Scraper")
        print()
        print("Available cities:")
        for key, city in sorted(OPENGOV_CITIES.items(), key=lambda x: -x[1]['pop']):
            print(f"  {key:15} - {city['name']:15} (pop: {city['pop']:,})")
        print()
        print("Usage: python3 opengov.py <city> [count]")
        return

    city_key = sys.argv[1].lower()
    target = int(sys.argv[2]) if len(sys.argv) > 2 else 50

    if city_key not in OPENGOV_CITIES:
        print(f"Unknown city: {city_key}")
        print(f"Available: {', '.join(sorted(OPENGOV_CITIES.keys()))}")
        return

    await scrape_city(city_key, target)


async def scrape_city(city_key: str, target_count: int) -> list:
    """Scrape permits for a city."""
    # Placeholder - implemented in Task 2
    print(f"Scraping {city_key} for {target_count} permits...")
    return []


if __name__ == '__main__':
    asyncio.run(main())
