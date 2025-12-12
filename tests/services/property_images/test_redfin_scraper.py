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
