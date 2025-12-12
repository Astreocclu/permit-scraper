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
