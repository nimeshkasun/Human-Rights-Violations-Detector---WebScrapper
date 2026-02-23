"""
CSV exporter.
Writes processed/filtered HRV records to data/exports/hrv_<timestamp>.csv.
Includes clear source attribution in every row.
"""
import csv
from datetime import datetime, timezone
from pathlib import Path

import config
from utils.logger import get_logger

logger = get_logger("hrv.exporter")

# Column order in the exported CSV
EXPORT_COLUMNS = [
    "id",
    "title",
    "url",
    "source_name",
    "source_category",
    "attribution",
    "published_date",
    "scraped_at",
    "violation_categories",
    "matched_keywords",
    "snippet",
]


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def export_to_csv(records: list[dict]) -> Path | None:
    """
    Export `records` to a timestamped CSV file.
    Returns the path of the created file, or None if records is empty.
    """
    if not records:
        logger.warning("No records to export.")
        return None

    config.EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    file_path = config.EXPORTS_DIR / f"hrv_{_timestamp()}.csv"

    with open(file_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=EXPORT_COLUMNS,
            extrasaction="ignore",
        )
        writer.writeheader()
        for record in records:
            row = dict(record)
            # Flatten list fields to pipe-separated strings
            for list_field in ("violation_categories", "matched_keywords"):
                val = row.get(list_field, [])
                row[list_field] = " | ".join(val) if isinstance(val, list) else (val or "")
            writer.writerow(row)

    logger.info("Exported %d records → %s", len(records), file_path)
    return file_path
