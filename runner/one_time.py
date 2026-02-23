"""One-time run: executes the pipeline once and exits."""
from typing import Optional
from runner.pipeline import run_pipeline
from utils.logger import get_logger

logger = get_logger("hrv.runner.onetime")


def run_once(category: Optional[str] = None) -> None:
    """Trigger a single pipeline run."""
    logger.info("One-time run triggered.")
    result = run_pipeline(category=category)
    if result:
        print(f"\n✓ Export saved to: {result}")
    else:
        print("\n⚠  No records were exported (no matches or no sources).")
