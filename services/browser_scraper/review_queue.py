"""Review queue for failed Browser-Use scrapes."""
import json
from datetime import datetime
from pathlib import Path
from typing import Optional
from .models import ScrapeContext


class ReviewQueue:
    """
    File-based queue for scrapes that need Claude Code review.

    Structure:
        queue_dir/
            pending/      <- Scrapes waiting for review
            reviewed/     <- Scrapes that have been reviewed
    """

    def __init__(self, queue_dir: Path | str = "data/review_queue"):
        self.queue_dir = Path(queue_dir)
        self.pending_dir = self.queue_dir / "pending"
        self.reviewed_dir = self.queue_dir / "reviewed"

        # Ensure directories exist
        self.pending_dir.mkdir(parents=True, exist_ok=True)
        self.reviewed_dir.mkdir(parents=True, exist_ok=True)

    def add(self, context: ScrapeContext) -> Path:
        """
        Add a ScrapeContext to the review queue.

        Returns the path to the created file.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{context.city.lower().replace(' ', '_')}.json"
        filepath = self.pending_dir / filename

        data = context.to_dict()
        data["queued_at"] = datetime.now().isoformat()

        filepath.write_text(json.dumps(data, indent=2))
        return filepath

    def get_pending(self, limit: int = 10) -> list[ScrapeContext]:
        """Get pending contexts, oldest first."""
        files = sorted(self.pending_dir.glob("*.json"))[:limit]
        contexts = []
        for f in files:
            data = json.loads(f.read_text())
            # Remove queue metadata before creating context
            data.pop("queued_at", None)
            data.pop("_filepath", None)
            ctx = ScrapeContext.from_dict(data)
            # Store filepath for mark_reviewed
            ctx._filepath = f  # type: ignore
            contexts.append(ctx)
        return contexts

    def mark_reviewed(
        self,
        context: ScrapeContext,
        resolution: str,
        notes: str = ""
    ) -> Path:
        """
        Mark a context as reviewed and move to reviewed directory.

        Args:
            context: The context to mark
            resolution: One of 'fixed', 'manual_fix', 'skip', 'permanent_block'
            notes: Any notes about the resolution

        Returns the path to the reviewed file.
        """
        # Get original filepath
        source = getattr(context, '_filepath', None)
        if not source or not source.exists():
            raise ValueError("Context was not loaded from queue")

        # Load and update data
        data = json.loads(source.read_text())
        data["reviewed_at"] = datetime.now().isoformat()
        data["resolution"] = resolution
        data["notes"] = notes

        # Move to reviewed
        dest = self.reviewed_dir / source.name
        dest.write_text(json.dumps(data, indent=2))
        source.unlink()

        return dest

    def pending_count(self) -> int:
        """Number of items waiting for review."""
        return len(list(self.pending_dir.glob("*.json")))
