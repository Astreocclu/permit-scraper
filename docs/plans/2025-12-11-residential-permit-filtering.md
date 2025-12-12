# Residential Permit Filtering Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Filter Southlake scraper for residential-only permits and implement Westlake autocomplete harvesting to target residential addresses instead of commercial corridors.

**Architecture:** Southlake uses post-processing filter on existing CSS scraper output (efficient: 1 page load vs multiple type-specific searches). Westlake abandons address guessing for autocomplete harvesting - type street names, capture valid addresses from dropdown, then scrape only verified addresses.

**Tech Stack:** Python 3, Playwright, existing CSS scraper (`citizen_self_service.py`), MyGov scraper (`mygov_westlake.py`)

---

## Task 1: Southlake Post-Processing Filter

**Files:**
- Create: `scrapers/filters.py`
- Test: `tests/test_filters.py`

**Step 1: Write the failing test**

```python
# tests/test_filters.py
import pytest
from scrapers.filters import filter_residential_permits

def test_filter_keeps_residential_permits():
    permits = [
        {'type': 'Residential Remodel', 'address': '123 Oak St'},
        {'type': 'Residential New Construction', 'address': '456 Elm St'},
        {'type': 'Pool/Spa', 'address': '789 Pine St'},
    ]
    result = filter_residential_permits(permits)
    assert len(result) == 3
    assert all('Residential' in p['type'] or 'Pool' in p['type'] for p in result)

def test_filter_excludes_commercial_permits():
    permits = [
        {'type': 'Commercial New Building', 'address': '100 Main St'},
        {'type': 'Commercial Electrical', 'address': '200 Business Blvd'},
        {'type': 'Business Sign', 'address': '300 Corp Dr'},
    ]
    result = filter_residential_permits(permits)
    assert len(result) == 0

def test_filter_mixed_permits():
    permits = [
        {'type': 'Residential Remodel', 'address': '123 Oak St'},
        {'type': 'Commercial New Building', 'address': '100 Main St'},
        {'type': 'Roof Replacement', 'address': '456 Elm St'},
        {'type': 'Certificate of Occupancy', 'address': '789 Pine St'},
    ]
    result = filter_residential_permits(permits)
    assert len(result) == 2
    types = [p['type'] for p in result]
    assert 'Residential Remodel' in types
    assert 'Roof Replacement' in types

def test_filter_handles_missing_type():
    permits = [
        {'address': '123 Oak St'},  # No type field
        {'type': '', 'address': '456 Elm St'},  # Empty type
    ]
    result = filter_residential_permits(permits)
    assert len(result) == 0  # Conservative: exclude if we can't classify
```

**Step 2: Run test to verify it fails**

Run: `cd /home/reid/testhome/permit-scraper && python3 -m pytest tests/test_filters.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'scrapers.filters'"

**Step 3: Write minimal implementation**

```python
# scrapers/filters.py
"""Post-processing filters for permit data."""

def filter_residential_permits(permits: list[dict]) -> list[dict]:
    """
    Filter permits to keep only residential-related types.

    Includes: residential, pool, spa, roof, foundation, accessory, patio, remodel, addition
    Excludes: commercial, business, sign, fire, certificate of occupancy
    """
    residential_keywords = [
        'residential', 'res ', 'pool', 'spa', 'roof',
        'foundation', 'accessory', 'patio', 'remodel', 'addition'
    ]
    commercial_keywords = [
        'commercial', 'business', 'sign', 'fire',
        'certificate of occupancy', 'certificate of compliance'
    ]

    filtered = []
    for permit in permits:
        permit_type = permit.get('type', '').lower()

        # Skip if no type or empty type
        if not permit_type:
            continue

        # Exclude explicit commercial
        if any(keyword in permit_type for keyword in commercial_keywords):
            continue

        # Include explicit residential keywords
        if any(keyword in permit_type for keyword in residential_keywords):
            filtered.append(permit)

    return filtered
```

**Step 4: Run test to verify it passes**

Run: `cd /home/reid/testhome/permit-scraper && python3 -m pytest tests/test_filters.py -v`
Expected: PASS (4 tests)

**Step 5: Commit**

```bash
cd /home/reid/testhome/permit-scraper && git add scrapers/filters.py tests/test_filters.py && git commit -m "feat: add residential permit filter with TDD tests"
```

---

## Task 2: Integrate Filter into Southlake Scraper

**Files:**
- Modify: `scrapers/citizen_self_service.py` (add import and filter call)

**Step 1: Identify integration point**

Read the current scraper to find where permits are saved. Look for the save/export logic.

Run: `cd /home/reid/testhome/permit-scraper && grep -n "save\|write\|export\|json.dump" scrapers/citizen_self_service.py`

**Step 2: Add import at top of file**

Add after existing imports:
```python
from scrapers.filters import filter_residential_permits
```

**Step 3: Add filter before save**

Find the line that saves permits (likely `json.dump` or similar) and add filter call before it:

```python
# Before saving, filter for residential only if city is Southlake
if city.lower() == 'southlake':
    permits = filter_residential_permits(permits)
    print(f"Filtered to {len(permits)} residential permits")
```

**Step 4: Test manually**

Run: `cd /home/reid/testhome/permit-scraper && python3 scrapers/citizen_self_service.py --city southlake --days 30 --dry-run`
Expected: Should show "Filtered to X residential permits" in output

**Step 5: Commit**

```bash
cd /home/reid/testhome/permit-scraper && git add scrapers/citizen_self_service.py && git commit -m "feat: integrate residential filter into Southlake CSS scraper"
```

---

## Task 3: Westlake Autocomplete Spike

**Files:**
- Create: `scrapers/westlake_spike.py` (temporary spike script)

**Step 1: Write spike script to verify autocomplete**

```python
# scrapers/westlake_spike.py
"""
Spike: Verify Westlake MyGov autocomplete endpoint.
Run this to confirm we can harvest addresses from autocomplete.
"""
import asyncio
from playwright.async_api import async_playwright

WESTLAKE_URL = "https://westlaketx.mygovcommunity.com/"

async def spike_autocomplete():
    """Type a street name and capture autocomplete responses."""

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # Visible for debugging
        page = await browser.new_page()

        # Capture network requests
        addresses_found = []

        async def handle_response(response):
            if 'autocomplete' in response.url.lower() or 'search' in response.url.lower():
                try:
                    data = await response.json()
                    print(f"FOUND API: {response.url}")
                    print(f"DATA: {data}")
                    addresses_found.append(data)
                except:
                    pass

        page.on("response", handle_response)

        await page.goto(WESTLAKE_URL)
        await page.wait_for_timeout(2000)

        # Look for address input field
        address_input = page.locator('input[placeholder*="address" i], input[name*="address" i], input#address')

        if await address_input.count() > 0:
            print("Found address input field")
            await address_input.first.fill("Vaquero")
            await page.wait_for_timeout(3000)  # Wait for autocomplete

            # Try to find dropdown options
            options = page.locator('.autocomplete-item, .ui-menu-item, [role="option"], .dropdown-item')
            count = await options.count()
            print(f"Found {count} autocomplete options in DOM")

            for i in range(min(count, 10)):
                text = await options.nth(i).text_content()
                print(f"  Option {i}: {text}")
        else:
            print("Could not find address input field")
            # List all inputs for debugging
            inputs = page.locator('input')
            for i in range(await inputs.count()):
                inp = inputs.nth(i)
                placeholder = await inp.get_attribute('placeholder') or ''
                name = await inp.get_attribute('name') or ''
                print(f"  Input {i}: placeholder='{placeholder}' name='{name}'")

        await browser.close()

        return addresses_found

if __name__ == "__main__":
    results = asyncio.run(spike_autocomplete())
    print(f"\nSPIKE COMPLETE: Found {len(results)} API responses")
```

**Step 2: Run spike**

Run: `cd /home/reid/testhome/permit-scraper && python3 scrapers/westlake_spike.py`
Expected: Either:
- SUCCESS: "FOUND API: ..." with address data
- PARTIAL: "Found X autocomplete options in DOM"
- FAIL: Need to inspect manually and adjust selectors

**Step 3: Document findings**

Based on spike results, update `westlake_investigation.json` with:
- Actual autocomplete endpoint URL (if found)
- DOM selectors for dropdown options
- Any authentication/session requirements

**Step 4: Commit spike (even if partial success)**

```bash
cd /home/reid/testhome/permit-scraper && git add scrapers/westlake_spike.py && git commit -m "spike: verify Westlake MyGov autocomplete endpoint"
```

---

## Task 4: Westlake Address Harvester

**Files:**
- Create: `scrapers/westlake_harvester.py`
- Create: `data/westlake_addresses.json`
- Test: `tests/test_westlake_harvester.py`

**Step 1: Write the failing test**

```python
# tests/test_westlake_harvester.py
import pytest
from scrapers.westlake_harvester import parse_autocomplete_response, RESIDENTIAL_STREETS

def test_residential_streets_defined():
    """Verify we have target streets configured."""
    assert len(RESIDENTIAL_STREETS) >= 5
    assert 'Vaquero' in ' '.join(RESIDENTIAL_STREETS)

def test_parse_autocomplete_response_extracts_addresses():
    """Test parsing autocomplete API response."""
    # Typical MyGov autocomplete response format
    response = [
        {"label": "2204 Vaquero Club Dr", "value": "2204 Vaquero Club Dr"},
        {"label": "2206 Vaquero Club Dr", "value": "2206 Vaquero Club Dr"},
    ]
    addresses = parse_autocomplete_response(response)
    assert len(addresses) == 2
    assert "2204 Vaquero Club Dr" in addresses

def test_parse_autocomplete_handles_empty():
    """Handle empty or invalid responses gracefully."""
    assert parse_autocomplete_response([]) == []
    assert parse_autocomplete_response(None) == []
```

**Step 2: Run test to verify it fails**

Run: `cd /home/reid/testhome/permit-scraper && python3 -m pytest tests/test_westlake_harvester.py -v`
Expected: FAIL with ModuleNotFoundError

**Step 3: Write implementation (adapt based on spike results)**

```python
# scrapers/westlake_harvester.py
"""
Westlake Address Harvester
Collects valid residential addresses via MyGov autocomplete.
"""
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

WESTLAKE_URL = "https://westlaketx.mygovcommunity.com/"
OUTPUT_FILE = Path(__file__).parent.parent / "data" / "westlake_addresses.json"

# High-value residential streets in Westlake
RESIDENTIAL_STREETS = [
    # Vaquero
    "Cedar Elm",
    "Post Oak",
    "Fountain Grass",
    "Wills Ct",
    "White Wing",
    "Vaquero Club",
    "Saddle White",
    "King Fisher",
    # Glenwyck
    "Paigebrooke",
    "Wimbledon",
    # General residential
    "Dove Rd",
    "Ottinger",
    "Sam School",
    "Oak Ridge",
]

def parse_autocomplete_response(response) -> list[str]:
    """Extract addresses from autocomplete API response."""
    if not response:
        return []

    addresses = []
    for item in response:
        if isinstance(item, dict):
            # Try common field names
            addr = item.get('label') or item.get('value') or item.get('address')
            if addr:
                addresses.append(str(addr))
        elif isinstance(item, str):
            addresses.append(item)

    return addresses

async def harvest_addresses_for_street(page, street: str) -> list[str]:
    """Type a street name and collect autocomplete suggestions."""
    addresses = []

    # Find address input (adjust selector based on spike findings)
    address_input = page.locator('input[placeholder*="address" i]').first

    await address_input.clear()
    await address_input.fill(street)
    await page.wait_for_timeout(1500)  # Wait for autocomplete

    # Collect dropdown options (adjust selector based on spike findings)
    options = page.locator('.autocomplete-item, .ui-menu-item, [role="option"]')
    count = await options.count()

    for i in range(count):
        text = await options.nth(i).text_content()
        if text and text.strip():
            addresses.append(text.strip())

    return addresses

async def harvest_all_addresses() -> dict:
    """Harvest addresses for all residential streets."""
    all_addresses = {}

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(WESTLAKE_URL)
        await page.wait_for_timeout(2000)

        for street in RESIDENTIAL_STREETS:
            print(f"Harvesting: {street}")
            addresses = await harvest_addresses_for_street(page, street)
            all_addresses[street] = addresses
            print(f"  Found {len(addresses)} addresses")
            await page.wait_for_timeout(500)  # Rate limit

        await browser.close()

    return all_addresses

def save_addresses(addresses: dict):
    """Save harvested addresses to JSON."""
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(addresses, f, indent=2)
    print(f"Saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    addresses = asyncio.run(harvest_all_addresses())
    save_addresses(addresses)

    total = sum(len(v) for v in addresses.values())
    print(f"\nTotal addresses harvested: {total}")
```

**Step 4: Run test to verify it passes**

Run: `cd /home/reid/testhome/permit-scraper && python3 -m pytest tests/test_westlake_harvester.py -v`
Expected: PASS

**Step 5: Commit**

```bash
cd /home/reid/testhome/permit-scraper && git add scrapers/westlake_harvester.py tests/test_westlake_harvester.py && git commit -m "feat: add Westlake address harvester with autocomplete"
```

---

## Task 5: Update Westlake Scraper to Use Harvested Addresses

**Files:**
- Modify: `scrapers/mygov_westlake.py`

**Step 1: Read current implementation**

Run: `cd /home/reid/testhome/permit-scraper && head -100 scrapers/mygov_westlake.py`

**Step 2: Add address loading from JSON**

Add near top of file:
```python
import json
from pathlib import Path

ADDRESSES_FILE = Path(__file__).parent.parent / "data" / "westlake_addresses.json"

def load_harvested_addresses() -> list[str]:
    """Load pre-harvested addresses instead of guessing."""
    if not ADDRESSES_FILE.exists():
        print(f"WARNING: {ADDRESSES_FILE} not found. Run westlake_harvester.py first.")
        return []

    with open(ADDRESSES_FILE) as f:
        data = json.load(f)

    # Flatten all street addresses into single list
    addresses = []
    for street_addresses in data.values():
        addresses.extend(street_addresses)

    return addresses
```

**Step 3: Replace address generation with loaded addresses**

Find the address iteration loop and replace:
```python
# OLD: addresses = generate_addresses(street, start=1000, end=3500, step=100)
# NEW:
addresses = load_harvested_addresses()
if not addresses:
    print("No harvested addresses. Falling back to brute force.")
    addresses = generate_addresses_brute_force()  # Keep fallback
```

**Step 4: Test manually**

Run: `cd /home/reid/testhome/permit-scraper && python3 scrapers/mygov_westlake.py --dry-run`
Expected: Should show "Loaded X harvested addresses" or fallback message

**Step 5: Commit**

```bash
cd /home/reid/testhome/permit-scraper && git add scrapers/mygov_westlake.py && git commit -m "feat: use harvested addresses in Westlake scraper"
```

---

## Task 6: End-to-End Test

**Step 1: Run Southlake scraper with filter**

Run: `cd /home/reid/testhome/permit-scraper && python3 scrapers/citizen_self_service.py --city southlake --days 30`
Expected:
- Scrapes permits
- Shows "Filtered to X residential permits"
- Saves to `data/raw/southlake_raw.json`

**Step 2: Run Westlake harvester**

Run: `cd /home/reid/testhome/permit-scraper && python3 scrapers/westlake_harvester.py`
Expected:
- Harvests addresses for each street
- Saves to `data/westlake_addresses.json`
- Shows total count

**Step 3: Run Westlake scraper**

Run: `cd /home/reid/testhome/permit-scraper && python3 scrapers/mygov_westlake.py`
Expected:
- Loads harvested addresses
- Scrapes permits for verified addresses only
- Saves to `data/raw/westlake_raw.json`

**Step 4: Verify residential data quality**

Run: `cd /home/reid/testhome/permit-scraper && python3 -c "import json; d=json.load(open('data/raw/southlake_raw.json')); types=set(p.get('type','') for p in d); print('\\n'.join(sorted(types)))"`
Expected: Only residential permit types (no Commercial, Business, Sign, etc.)

**Step 5: Final commit**

```bash
cd /home/reid/testhome/permit-scraper && git add -A && git commit -m "feat: complete residential filtering for Southlake and Westlake"
```

---

## Fallback: Westlake Brute Force (If Autocomplete Fails)

If Task 3 spike reveals autocomplete doesn't work, implement this fallback:

**Files:**
- Modify: `scrapers/mygov_westlake.py`

**Step 1: Get street list from OpenStreetMap**

Run: `cd /home/reid/testhome/permit-scraper && echo "Download Westlake streets from OSM or use manual list"`

**Step 2: Update street list in scraper**

```python
WESTLAKE_RESIDENTIAL_STREETS = [
    ('Cedar Elm Ter', 2000, 2500),      # (street, start_num, end_num)
    ('Post Oak Pl', 2100, 2300),
    ('Vaquero Club Dr', 2200, 2800),
    ('Paigebrooke Dr', 1800, 2200),
    ('Dove Rd', 1000, 3000),
    # ... add more based on research
]
```

**Step 3: Iterate with smaller step size**

```python
for street, start, end in WESTLAKE_RESIDENTIAL_STREETS:
    for num in range(start, end, 10):  # Every 10 instead of 100
        address = f"{num} {street}"
        # ... scrape logic
```

---

## Caveats and Assumptions

1. **Southlake permit type field** - Assumes the `type` field contains descriptive text (e.g., "Residential Remodel"). If it's just "Permit" for everything, filter won't work.

2. **Westlake autocomplete** - Assumes MyGov has working autocomplete. The spike in Task 3 will verify this before committing to the approach.

3. **Rate limiting** - Both scrapers include delays. If sites block us, increase timeouts.

4. **Selectors may change** - MyGov UI updates could break selectors. The spike helps identify current working selectors.
