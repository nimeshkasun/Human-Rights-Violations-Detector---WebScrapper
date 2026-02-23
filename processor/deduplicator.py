"""
Duplicate record removal.

Two deduplication strategies are applied in sequence:
1. Exact:     same computed `id` (SHA-256 of url+title).
2. Near-dup:  same URL (regardless of title differences).

Optionally compares against recently exported records within a configurable
time window (dedup_window_hours) so re-runs don't re-export the same news.
"""
import csv
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

import config
from utils.logger import get_logger

logger = get_logger("hrv.processor.dedup")


def _load_recent_ids(window_hours: int) -> set[str]:
    """
    Load record IDs from any CSV export produced within the last `window_hours`.
    """
    if not config.EXPORTS_DIR.exists():
        return set()

    cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)
    seen: set[str] = set()

    for csv_path in sorted(config.EXPORTS_DIR.glob("hrv_*.csv"), reverse=True):
        try:
            mtime = datetime.fromtimestamp(csv_path.stat().st_mtime, tz=timezone.utc)
            if mtime < cutoff:
                break  # files are in reverse-time order; older files can be skipped
            with open(csv_path, encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row_id := row.get("id"):
                        seen.add(row_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not read %s for dedup: %s", csv_path, exc)
    return seen


def deduplicate(records: list[dict]) -> list[dict]:
    """
    Remove duplicate records within the current batch and against recent exports.
    Returns a deduplicated list.
    """
    settings = config.load_settings()
    window_hours: int = settings.get("dedup_window_hours", 24)

    recent_ids = _load_recent_ids(window_hours)

    seen_ids: set[str] = set(recent_ids)
    seen_urls: set[str] = set()
    unique: list[dict] = []

    for record in records:
        rid = record.get("id", "")
        url = record.get("url", "")

        if rid in seen_ids:
            continue
        if url and url in seen_urls:
            continue

        seen_ids.add(rid)
        if url:
            seen_urls.add(url)
        unique.append(record)

    removed = len(records) - len(unique)
    logger.info(
        "Deduplication: %d unique / %d total (%d removed, window=%dh)",
        len(unique), len(records), removed, window_hours,
    )
    return unique
