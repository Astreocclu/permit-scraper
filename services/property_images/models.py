"""Data models for property image service."""
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

ImageSource = Literal['tad', 'dcad', 'dentoncad', 'collincad', 'redfin', 'failed']
ImageType = Literal['front', 'back', 'aerial', 'sketch', 'unknown']


@dataclass
class PropertyImage:
    """Result of a property image fetch attempt."""
    permit_id: str
    address: str
    image_path: str  # Local path to saved image, empty if failed
    source: ImageSource
    image_type: ImageType
    fetched_at: datetime
    account_num: str | None = None  # CAD account number if found
    error: str | None = None  # Error message if failed

    @property
    def success(self) -> bool:
        """Return True if image was successfully fetched."""
        return self.source != 'failed' and bool(self.image_path)
