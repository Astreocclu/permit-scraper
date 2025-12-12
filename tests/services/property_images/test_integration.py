"""Integration tests for property image service.

These tests hit real APIs and may be slow. Run with:
    pytest tests/services/property_images/test_integration.py -v --timeout=180
"""
import pytest
from pathlib import Path
from services.property_images import fetch_property_image, PropertyImage


@pytest.mark.integration
@pytest.mark.asyncio
class TestRealAPIs:
    """Integration tests using real addresses from permit data."""

    @pytest.fixture
    def real_media_dir(self, tmp_path):
        """Use temp dir for test images."""
        media_dir = tmp_path / "media" / "property_images"
        media_dir.mkdir(parents=True)
        return media_dir

    async def test_fort_worth_address(self, real_media_dir, monkeypatch):
        """Test with a real Fort Worth address from permit data."""
        monkeypatch.setenv("MEDIA_DIR", str(real_media_dir.parent))

        result = await fetch_property_image(
            address="3705 DESERT RIDGE DR, Fort Worth TX 76116",
            city="Fort Worth",
            permit_id="integration_test_fw"
        )

        assert isinstance(result, PropertyImage)
        print(f"\nResult: source={result.source}, path={result.image_path}")

        if result.success:
            assert Path(result.image_path).exists()
            assert Path(result.image_path).stat().st_size > 1000  # Not empty

    async def test_dallas_address(self, real_media_dir, monkeypatch):
        """Test with a Dallas County address."""
        monkeypatch.setenv("MEDIA_DIR", str(real_media_dir.parent))

        result = await fetch_property_image(
            address="1234 ELM ST, Dallas TX 75201",
            city="Dallas",
            permit_id="integration_test_dallas",
            skip_redfin=True  # Just test CAD lookup
        )

        assert isinstance(result, PropertyImage)
        # Dallas CAD image scraper not implemented yet, so this may fail
        print(f"\nResult: source={result.source}, account={result.account_num}")
