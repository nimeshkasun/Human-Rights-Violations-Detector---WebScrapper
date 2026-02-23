"""
Normalize raw scraped articles into the unified HRV record schema.

Output schema per record:
{
    "id":               str,   # SHA-256 of url+title
    "title":            str,
    "snippet":          str,
    "url":              str,
    "source_name":      str,
    "source_category":  str,   # public_news | government | ngo | public_posts
    "source_url":       str,   # root URL of the source
    "published_date":   str,   # ISO-8601 if detectable, else ""
    "scraped_at":       str,   # ISO-8601 UTC
    "attribution":      str,   # "Source Name (category)"
    "raw_html":         str,   # kept for reference / page-save link
}
"""
import hashlib
import re
from datetime import datetime, timezone
from typing import Optional

from utils.logger import get_logger

logger = get_logger("hrv.processor.normalizer")

# Very basic date-string patterns (extend as needed)
_DATE_PATTERNS = [
    r"\b(\d{4}-\d{2}-\d{2})\b",
    r"\b(\d{2}/\d{2}/\d{4})\b",
    r"\b(\d{1,2}\s+\w+\s+\d{4})\b",
]


def _try_parse_date(text: str) -> str:
    """Attempt to extract a date string from arbitrary text. Returns '' on failure."""
    for pat in _DATE_PATTERNS:
        m = re.search(pat, text)
        if m:
            return m.group(1)
    return ""


def _build_id(url: str, title: str) -> str:
    raw = f"{url}||{title}".encode()
    return hashlib.sha256(raw).hexdigest()[:16]


def normalize(article: dict) -> dict:
    """Convert a raw scraped article dict into the standard HRV record schema."""
    title = (article.get("title") or "").strip()
    snippet = (article.get("snippet") or "").strip()
    url = (article.get("url") or article.get("source_url") or "").strip()
    source_name = article.get("source_name", "Unknown")
    source_category = article.get("source_category", "")
    source_url = article.get("source_url", "")
    scraped_at = article.get("scraped_at") or datetime.now(timezone.utc).isoformat()
    raw_html = article.get("raw_html", "")

    # Try to extract a date from title or snippet
    published_date = _try_parse_date(title + " " + snippet)

    attribution = f"{source_name} ({source_category})" if source_category else source_name

    return {
        "id": _build_id(url, title),
        "title": title,
        "snippet": snippet,
        "url": url,
        "source_name": source_name,
        "source_category": source_category,
        "source_url": source_url,
        "published_date": published_date,
        "scraped_at": scraped_at,
        "attribution": attribution,
        "raw_html": raw_html,
    }


def normalize_all(articles: list[dict]) -> list[dict]:
    return [normalize(a) for a in articles]
