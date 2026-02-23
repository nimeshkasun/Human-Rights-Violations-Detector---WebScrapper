"""
Optional page-saver: persists the raw HTML of scraped pages
to scraped_pages/<sanitised-hostname>/<timestamp>.html.
Can be toggled on/off via settings.json (save_scraped_pages: true/false).
"""
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import config
from utils.logger import get_logger

logger = get_logger("hrv.pagesaver")


def _safe_filename(url: str) -> str:
    parsed = urlparse(url)
    host = re.sub(r"[^\w\-]", "_", parsed.netloc)
    path = re.sub(r"[^\w\-]", "_", parsed.path.strip("/"))[:60]
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    return f"{host}__{path}__{ts}.html"


def save_page(url: str, html_content: str) -> Path | None:
    """
    Save `html_content` to disk if save_scraped_pages is enabled.
    Returns the saved path or None if feature is disabled.
    """
    settings = config.load_settings()
    if not settings.get("save_scraped_pages", False):
        return None

    parsed = urlparse(url)
    host_dir = config.SCRAPED_PAGES_DIR / re.sub(r"[^\w\-]", "_", parsed.netloc)
    host_dir.mkdir(parents=True, exist_ok=True)

    file_path = host_dir / _safe_filename(url)
    file_path.write_text(html_content, encoding="utf-8")
    logger.debug("Page saved: %s", file_path)
    return file_path
