# Redfin Scraper Fixes Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix the Redfin property image scraper to reduce timeouts and improve anti-detection.

**Architecture:** Replace `networkidle` waits with `domcontentloaded` + explicit selectors, add playwright-stealth for anti-detection, implement retry logic with exponential backoff.

**Tech Stack:** Python 3.10+, Playwright, playwright-stealth (already installed), httpx

---

## Task 1: Add Stealth and Replace networkidle on Homepage Load

**Files:**
- Modify: `services/property_images/redfin_scraper.py:1-90`
- Test: `tests/services/property_images/test_redfin_scraper.py`

**Step 1: Add stealth import and update browser launch**

Edit `services/property_images/redfin_scraper.py` - add import at top (after line 19):

```python
from playwright_stealth import stealth_async
```

**Step 2: Apply stealth to page and change homepage wait strategy**

Replace lines 68-85 (browser launch through homepage load):

```python
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
            await stealth_async(page)

            # Navigate to Redfin with faster wait strategy
            logger.info(f"Searching Redfin for: {search_query}")

            try:
                await page.goto(REDFIN_BASE_URL, wait_until="domcontentloaded", timeout=timeout_ms)
                # Wait for search box to appear (confirms page is interactive)
                await page.wait_for_selector('input[placeholder*="Search"]', timeout=10000)
            except PlaywrightTimeout:
                logger.warning("Timeout loading Redfin homepage")
                return None
```

**Step 3: Run existing tests to verify no regression**

Run: `cd /home/reid/testhome/permit-scraper && pytest tests/services/property_images/test_redfin_scraper.py -v --timeout=120`

Expected: Tests pass (or skip gracefully if Redfin blocks)

**Step 4: Commit**

```bash
cd /home/reid/testhome/permit-scraper && git add services/property_images/redfin_scraper.py
git commit -m "feat(redfin): add stealth and replace networkidle on homepage"
```

---

## Task 2: Replace networkidle After Search Submit

**Files:**
- Modify: `services/property_images/redfin_scraper.py:114-135`

**Step 1: Replace search submit wait strategy**

Replace lines 119-133 (after keyboard press through URL check):

```python
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
```

**Step 2: Run tests**

Run: `cd /home/reid/testhome/permit-scraper && pytest tests/services/property_images/test_redfin_scraper.py -v --timeout=120`

Expected: Tests pass

**Step 3: Commit**

```bash
cd /home/reid/testhome/permit-scraper && git add services/property_images/redfin_scraper.py
git commit -m "feat(redfin): replace networkidle after search submit"
```

---

## Task 3: Replace networkidle on Result Click

**Files:**
- Modify: `services/property_images/redfin_scraper.py:150-165`

**Step 1: Replace result click wait strategy**

Replace lines 150-165 (result clicking loop):

```python
            for selector in result_selectors:
                try:
                    first_result = await page.query_selector(selector)
                    if first_result:
                        await first_result.click()
                        # Wait for property page to load
                        await page.wait_for_load_state("domcontentloaded", timeout=timeout_ms)
                        # Wait for images to appear
                        try:
                            await page.wait_for_selector(
                                'img[src*="photo"], .PhotoCarousel, .HomeMainMedia',
                                timeout=10000
                            )
                        except PlaywrightTimeout:
                            pass  # Continue anyway, images might still be there

                        if await _is_blocked(page):
                            return None

                        return await _extract_property_images(
                            page, output_dir, filename_prefix, prefer_backyard
                        )
                except Exception as e:
                    logger.debug(f"Error clicking result: {e}")
                    continue
```

**Step 2: Run tests**

Run: `cd /home/reid/testhome/permit-scraper && pytest tests/services/property_images/test_redfin_scraper.py -v --timeout=120`

Expected: Tests pass

**Step 3: Commit**

```bash
cd /home/reid/testhome/permit-scraper && git add services/property_images/redfin_scraper.py
git commit -m "feat(redfin): replace networkidle on result click"
```

---

## Task 4: Add Retry Logic with Exponential Backoff

**Files:**
- Modify: `services/property_images/redfin_scraper.py` (add new function, wrap main function)
- Test: `tests/services/property_images/test_redfin_scraper.py`

**Step 1: Write failing test for retry behavior**

Add to `tests/services/property_images/test_redfin_scraper.py`:

```python
    @pytest.mark.asyncio
    async def test_retry_constants_exist(self):
        """Test that retry configuration is available."""
        from services.property_images import redfin_scraper
        assert hasattr(redfin_scraper, 'MAX_RETRIES')
        assert hasattr(redfin_scraper, 'RETRY_BASE_DELAY')
        assert redfin_scraper.MAX_RETRIES >= 2
        assert redfin_scraper.RETRY_BASE_DELAY >= 1.0
```

**Step 2: Run test to verify it fails**

Run: `cd /home/reid/testhome/permit-scraper && pytest tests/services/property_images/test_redfin_scraper.py::TestRedfinScraper::test_retry_constants_exist -v`

Expected: FAIL with "AttributeError: module 'services.property_images.redfin_scraper' has no attribute 'MAX_RETRIES'"

**Step 3: Add retry constants**

Add after line 27 (after MAX_DELAY_SECONDS) in `redfin_scraper.py`:

```python
# Retry configuration
MAX_RETRIES = 3
RETRY_BASE_DELAY = 2.0  # Exponential: 2s, 4s, 8s
```

**Step 4: Run test to verify it passes**

Run: `cd /home/reid/testhome/permit-scraper && pytest tests/services/property_images/test_redfin_scraper.py::TestRedfinScraper::test_retry_constants_exist -v`

Expected: PASS

**Step 5: Commit**

```bash
cd /home/reid/testhome/permit-scraper && git add services/property_images/redfin_scraper.py tests/services/property_images/test_redfin_scraper.py
git commit -m "feat(redfin): add retry constants"
```

---

## Task 5: Implement Retry Wrapper Function

**Files:**
- Modify: `services/property_images/redfin_scraper.py`

**Step 1: Create internal implementation function**

Rename `fetch_redfin_image` to `_fetch_redfin_image_impl` (change line 38):

```python
async def _fetch_redfin_image_impl(
```

**Step 2: Create new fetch_redfin_image with retry logic**

Add before `_fetch_redfin_image_impl` (after the constants):

```python
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
    Fetch property image from Redfin with retry logic.

    Wraps _fetch_redfin_image_impl with exponential backoff retries.
    """
    last_error = None

    for attempt in range(MAX_RETRIES):
        try:
            result = await _fetch_redfin_image_impl(
                address=address,
                city=city,
                state=state,
                output_dir=output_dir,
                filename_prefix=filename_prefix,
                prefer_backyard=prefer_backyard,
                timeout_ms=timeout_ms,
            )

            # Success or graceful "not found" (None is valid)
            return result

        except PlaywrightTimeout as e:
            last_error = e
            if attempt < MAX_RETRIES - 1:
                delay = RETRY_BASE_DELAY * (2 ** attempt)
                logger.warning(f"Redfin attempt {attempt + 1} timed out, retrying in {delay}s...")
                await asyncio.sleep(delay)
            else:
                logger.error(f"Redfin failed after {MAX_RETRIES} attempts: {e}")

        except Exception as e:
            last_error = e
            logger.error(f"Redfin unexpected error: {e}")
            break  # Don't retry on unexpected errors

    return None
```

**Step 3: Run all Redfin tests**

Run: `cd /home/reid/testhome/permit-scraper && pytest tests/services/property_images/test_redfin_scraper.py -v --timeout=180`

Expected: Tests pass

**Step 4: Commit**

```bash
cd /home/reid/testhome/permit-scraper && git add services/property_images/redfin_scraper.py
git commit -m "feat(redfin): add retry wrapper with exponential backoff"
```

---

## Task 6: Add Integration Test for Stealth

**Files:**
- Modify: `tests/services/property_images/test_redfin_scraper.py`

**Step 1: Add stealth verification test**

Add new test to `test_redfin_scraper.py`:

```python
    @pytest.mark.asyncio
    async def test_stealth_is_applied(self, temp_media_dir):
        """Test that stealth measures are imported and available."""
        # Verify stealth import works
        from playwright_stealth import stealth_async
        assert callable(stealth_async)

        # Verify it's used in our scraper (check import)
        import services.property_images.redfin_scraper as scraper
        import inspect
        source = inspect.getsource(scraper)
        assert 'stealth_async' in source, "stealth_async should be used in redfin_scraper"
```

**Step 2: Run test**

Run: `cd /home/reid/testhome/permit-scraper && pytest tests/services/property_images/test_redfin_scraper.py::TestRedfinScraper::test_stealth_is_applied -v`

Expected: PASS

**Step 3: Commit**

```bash
cd /home/reid/testhome/permit-scraper && git add tests/services/property_images/test_redfin_scraper.py
git commit -m "test(redfin): add stealth verification test"
```

---

## Task 7: Final Verification and Cleanup

**Files:**
- All modified files

**Step 1: Run full test suite**

Run: `cd /home/reid/testhome/permit-scraper && pytest tests/services/property_images/ -v --timeout=180`

Expected: All tests pass

**Step 2: Run a manual integration test**

Run: `cd /home/reid/testhome/permit-scraper && python3 -m services.property_images.image_fetcher "3705 Desert Ridge Dr, Fort Worth TX 76116" "Fort Worth" "test_manual"`

Expected: Either fetches image or fails gracefully with informative logging

**Step 3: Update SESSION-NOTES.md with fixes applied**

Add to SESSION-NOTES.md under "### Notes":

```markdown
- **Redfin scraper hardened (2025-12-12):**
  - Added playwright-stealth for anti-detection
  - Replaced networkidle with domcontentloaded + explicit waits
  - Added retry with exponential backoff (3 attempts: 2s, 4s, 8s)
```

**Step 4: Final commit**

```bash
cd /home/reid/testhome/permit-scraper && git add -A
git commit -m "docs: update session notes with redfin fixes"
```

---

## Summary of Changes

| File | Change |
|------|--------|
| `services/property_images/redfin_scraper.py` | Add stealth, replace networkidle (3 places), add retry wrapper |
| `tests/services/property_images/test_redfin_scraper.py` | Add retry constants test, stealth verification test |
| `SESSION-NOTES.md` | Document fixes applied |

## Risk Notes

- **Stealth is not foolproof** - Redfin may still detect and block after N requests
- **Accept partial success rate** - Some properties won't have Redfin images
- **Rate limiting still applies** - 3-5 second delays between requests remain in place
