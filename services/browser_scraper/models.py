"""Data models for Browser-Use scraper handoff."""
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class ScrapeContext:
    """
    Rich context from a Browser-Use scrape attempt.

    This captures everything needed for Claude Code to review
    and potentially fix a failed scrape.
    """
    city: str
    final_result: Optional[str]  # JSON string if successful
    is_done: bool
    is_successful: Optional[bool]  # None if not done
    errors: list[Optional[str]]  # One error per step, None if no error
    urls: list[str]  # All URLs visited
    actions: list[str]  # Action names taken (click, input_text, etc.)
    screenshots: list[str] = field(default_factory=list)  # Base64 encoded, last N
    screenshot_paths: list[str] = field(default_factory=list)  # Paths to saved PNG files
    task_description: str = ""  # Original task given to agent
    raw_history: Optional[str] = None  # Full history JSON for deep debugging
    extracted_content: list[str] = field(default_factory=list)  # Content from extract actions (saved incrementally)
    extracted_files: list[str] = field(default_factory=list)  # Paths to extracted_content_N.md files

    def needs_review(self) -> bool:
        """Return True if this scrape needs human/Claude review."""
        return self.is_successful is False or self.is_successful is None

    def has_errors(self) -> bool:
        """Return True if any step had an error."""
        return any(e is not None for e in self.errors)

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "ScrapeContext":
        """Create from dictionary (e.g., loaded from JSON)."""
        return cls(**data)


@dataclass
class AttemptRecord:
    """Record of a single scraping attempt."""
    attempt_num: int
    timestamp: str
    success: bool
    error: Optional[str] = None
    screenshot_paths: list[str] = field(default_factory=list)
    actions_taken: list[str] = field(default_factory=list)
    analysis: Optional[str] = None  # Claude's analysis of what went wrong
    adjustment: Optional[str] = None  # What was changed for next attempt


@dataclass
class CityShepherdState:
    """Track shepherding progress for a city."""
    city: str
    status: str  # "pending", "in_progress", "success", "failed", "blocked"
    attempts: list[AttemptRecord] = field(default_factory=list)
    current_task: Optional[str] = None  # The task template being used
    task_adjustments: list[str] = field(default_factory=list)  # History of modifications
    final_result: Optional[str] = None
    permits_extracted: int = 0
