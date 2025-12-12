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
