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


def _step(n: int, label: str) -> None:
    print(f"\n  ── Step {n}: {label}", flush=True)


def run_pipeline(category: Optional[str] = None) -> Optional[Path]:
    """
    Execute the full HRV pipeline and return the path of the exported CSV,
    or None if there was nothing to export.

    Args:
        category: If provided, only scrape sources of this category.
    """
    cat_label = f" (category: {category})" if category else ""
    print(f"\n{'═' * 56}", flush=True)
    print(f"  HRV Pipeline starting{cat_label}", flush=True)
    print(f"{'═' * 56}", flush=True)
    logger.info("=" * 60)
    logger.info("Pipeline start%s", f" (category={category})" if category else "")

    # 1. Load enabled sources
    _step(1, "Loading sources")
    sources = list_sources(category=category, enabled_only=True)
    if not sources:
        logger.warning("No enabled sources found. Aborting.")
        print("  No enabled sources found. Aborting.", flush=True)
        return None
    print(f"  {len(sources)} source(s) queued", flush=True)
    logger.info("Sources to scrape: %d", len(sources))

    # 2. Scrape
    _step(2, "Scraping")
    raw_articles = scrape_all(sources)

    # 3. Normalize
    _step(3, "Normalising records")
    normalised = normalize_all(raw_articles)
    print(f"  {len(normalised)} record(s) normalised", flush=True)
    logger.info("Normalised records: %d", len(normalised))

    # 4. Filter (HRV-relevant only)
    _step(4, "Filtering for HRV content")
    filtered = filter_records(normalised)
    print(f"  {len(filtered)} record(s) matched HRV keywords", flush=True)

    # 5. Deduplicate
    _step(5, "Deduplicating")
    unique = deduplicate(filtered)
    print(f"  {len(unique)} unique record(s) after deduplication", flush=True)

    # 6. Export
    _step(6, "Exporting to CSV")
    export_path = export_to_csv(unique)

    print(f"\n{'═' * 56}", flush=True)
    if export_path:
        print(f"  ✓ Done — {len(unique)} record(s) exported to:", flush=True)
        print(f"    {export_path}", flush=True)
    else:
        print("  ✓ Done — nothing to export (0 matching records)", flush=True)
    print(f"{'═' * 56}\n", flush=True)

    logger.info(
        "Pipeline complete. Records exported: %d%s",
        len(unique),
        f" → {export_path}" if export_path else " (nothing exported)",
    )
    logger.info("=" * 60)
    return export_path
