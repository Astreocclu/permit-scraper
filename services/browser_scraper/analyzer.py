"""
Failure Analyzer - Claude Code analyzes Browser-Use failures via screenshots.

This module is designed to be called BY Claude Code (not as standalone).
It provides structured analysis of what went wrong and suggests adjustments.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict


@dataclass
class FailureAnalysis:
    """Structured analysis of a scraping failure."""
    root_cause: str  # What went wrong
    portal_state: str  # What the portal is showing
    suggested_fix: str  # How to adjust the approach
    confidence: float  # 0-1 confidence in analysis
    needs_manual_verification: bool  # Should Claude use Playwright to verify?


def get_latest_screenshots(city: str, n: int = 3) -> List[Path]:
    """Get the N most recent screenshots for a city."""
    screenshots_dir = Path("data/screenshots") / city.lower().replace(" ", "_")
    if not screenshots_dir.exists():
        return []

    pngs = sorted(screenshots_dir.glob("*.png"), key=lambda p: p.stat().st_mtime, reverse=True)
    return pngs[:n]


def get_attempt_context(city: str) -> Dict:
    """Load the most recent attempt context from review queue."""
    review_dir = Path("data/review_queue/pending")
    city_file = review_dir / f"{city.lower()}.json"

    if city_file.exists():
        with open(city_file) as f:
            return json.load(f)
    return {}


def format_analysis_prompt(city: str, error: str, screenshot_paths: List[Path]) -> str:
    """Format a prompt for Claude to analyze the failure.

    Note: This returns a prompt string. The actual analysis happens when
    Claude Code reads the screenshots and this prompt together.
    """
    return f"""## Browser-Use Failure Analysis Request

**City:** {city}
**Error:** {error}

**Screenshots:** {[str(p) for p in screenshot_paths]}

Please analyze these screenshots and the error to determine:
1. **Root Cause**: What specifically went wrong? (e.g., wrong selector, portal changed, date format issue)
2. **Portal State**: What is the portal currently showing?
3. **Suggested Fix**: How should the task template be modified?
4. **Confidence**: How confident are you in this analysis? (0-1)
5. **Manual Verification Needed**: Should we use Playwright to manually test before retrying?

Return your analysis as a FailureAnalysis object.
"""


def save_analysis(city: str, analysis: FailureAnalysis, attempt_num: int):
    """Save analysis to the review queue."""
    analysis_dir = Path("data/review_queue/analyzed")
    analysis_dir.mkdir(parents=True, exist_ok=True)

    output_file = analysis_dir / f"{city.lower()}_attempt_{attempt_num}.json"
    with open(output_file, 'w') as f:
        json.dump(asdict(analysis), f, indent=2)
