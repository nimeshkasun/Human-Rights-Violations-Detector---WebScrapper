"""
HRV keyword filter.
Scans the title + snippet of each normalised record for human-rights-violation
keywords and annotates matching records with matched_keywords and
violation_categories.  Non-matching records are dropped.
"""
import re
from typing import Optional

import config
from utils.logger import get_logger

logger = get_logger("hrv.processor.filter")


def _find_matches(text: str) -> dict[str, list[str]]:
    """
    Return a dict of {category: [matched_keyword, ...]} for all keyword hits
    found in `text` (case-insensitive).
    """
    text_lower = text.lower()
    hits: dict[str, list[str]] = {}
    for category, keywords in config.HRV_KEYWORDS.items():
        for kw in keywords:
            if re.search(r"\b" + re.escape(kw) + r"\b", text_lower):
                hits.setdefault(category, []).append(kw)
    return hits


def filter_record(record: dict) -> Optional[dict]:
    """
    Return an annotated copy of `record` if HRV keywords are found,
    or None if the record is not relevant.
    """
    search_text = f"{record.get('title', '')} {record.get('snippet', '')}"
    matches = _find_matches(search_text)
    if not matches:
        return None

    annotated = dict(record)
    annotated["matched_keywords"] = sorted(
        {kw for kws in matches.values() for kw in kws}
    )
    annotated["violation_categories"] = sorted(matches.keys())
    return annotated


def filter_records(records: list[dict]) -> list[dict]:
    """Filter a list of records; return only HRV-relevant ones, annotated."""
    relevant = []
    for r in records:
        filtered = filter_record(r)
        if filtered is not None:
            relevant.append(filtered)
    discarded = len(records) - len(relevant)
    logger.info(
        "HRV filter: %d relevant / %d total (%d discarded)",
        len(relevant), len(records), discarded,
    )
    return relevant
