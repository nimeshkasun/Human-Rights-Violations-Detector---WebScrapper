"""
Core pipeline: scrape → normalize → filter → deduplicate → export.
Shared by both the one-time runner and the scheduler.
"""
from pathlib import Path
from typing import Optional

from sources.manager import list_sources
from scraper.engine import scrape_all
from processor.normalizer import normalize_all
from processor.filter import filter_records
from processor.deduplicator import deduplicate
from exporter.csv_exporter import export_to_csv
from utils.logger import get_logger

logger = get_logger("hrv.runner.pipeline")


def run_pipeline(category: Optional[str] = None) -> Optional[Path]:
    """
    Execute the full HRV pipeline and return the path of the exported CSV,
    or None if there was nothing to export.

    Args:
        category: If provided, only scrape sources of this category.
    """
    logger.info("=" * 60)
    logger.info("Pipeline start%s", f" (category={category})" if category else "")

    # 1. Load enabled sources
    sources = list_sources(category=category, enabled_only=True)
    if not sources:
        logger.warning("No enabled sources found. Aborting.")
        return None
    logger.info("Sources to scrape: %d", len(sources))

    # 2. Scrape
    raw_articles = scrape_all(sources)

    # 3. Normalize
    normalised = normalize_all(raw_articles)
    logger.info("Normalised records: %d", len(normalised))

    # 4. Filter (HRV-relevant only)
    filtered = filter_records(normalised)

    # 5. Deduplicate
    unique = deduplicate(filtered)

    # 6. Export
    export_path = export_to_csv(unique)

    logger.info(
        "Pipeline complete. Records exported: %d%s",
        len(unique),
        f" → {export_path}" if export_path else " (nothing exported)",
    )
    logger.info("=" * 60)
    return export_path
