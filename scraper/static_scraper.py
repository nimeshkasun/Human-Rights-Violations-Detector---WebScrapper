"""
Static site scraper using requests + BeautifulSoup.
Used for sites that deliver fully-rendered HTML without JavaScript.
"""
import time
from typing import Optional

import requests
from bs4 import BeautifulSoup

import config
from utils.logger import get_logger

logger = get_logger("hrv.scraper.static")

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": config.USER_AGENT})


def fetch_page(url: str) -> Optional[BeautifulSoup]:
    """
    Fetch `url` with retries. Returns a BeautifulSoup object or None on failure.
    """
    for attempt in range(1, config.MAX_RETRIES + 1):
        try:
            resp = SESSION.get(url, timeout=config.REQUEST_TIMEOUT)
            resp.raise_for_status()
            return BeautifulSoup(resp.text, "html.parser")
        except requests.HTTPError as exc:
            logger.warning("HTTP %s on %s (attempt %d)", exc.response.status_code, url, attempt)
        except requests.RequestException as exc:
            logger.warning("Request error on %s (attempt %d): %s", url, attempt, exc)
        time.sleep(2 ** attempt)  # exponential back-off
    logger.error("Failed to fetch %s after %d attempts.", url, config.MAX_RETRIES)
    return None


def extract_articles(
    soup: BeautifulSoup, source_url: str
) -> list[dict]:
    """
    Generic article extractor. Tries to find common article structures.
    Returns a list of raw dicts with keys: title, url, snippet, raw_html.
    """
    articles: list[dict] = []

    # Heuristic: look for <article>, or common card patterns
    candidates = soup.find_all(
        ["article", "div"],
        class_=lambda c: c and any(
            kw in c.lower() for kw in ("article", "story", "post", "card", "news-item", "entry")
        ),
    ) or soup.find_all("article")

    for elem in candidates:
        title_tag = (
            elem.find(["h1", "h2", "h3", "h4"])
            or elem.find(class_=lambda c: c and "title" in c.lower())
        )
        title = title_tag.get_text(strip=True) if title_tag else ""

        link_tag = elem.find("a", href=True)
        href = link_tag["href"] if link_tag else ""
        if href and not href.startswith("http"):
            from urllib.parse import urljoin
            href = urljoin(source_url, href)

        # snippet: first <p> or meta description
        snippet_tag = elem.find("p")
        snippet = snippet_tag.get_text(strip=True) if snippet_tag else ""

        if not title and not href:
            continue

        articles.append(
            {
                "title": title,
                "url": href or source_url,
                "snippet": snippet,
                "raw_html": str(elem),
            }
        )

    # De-duplicate by URL within this page
    seen: set[str] = set()
    unique = []
    for a in articles:
        if a["url"] not in seen:
            seen.add(a["url"])
            unique.append(a)
    return unique
