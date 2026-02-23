"""
Main scraping engine.
Orchestrates robots-check → fetch (static or dynamic) → extract → page-save.
"""
from typing import Optional
from datetime import datetime, timezone

from scraper import robots_checker, static_scraper, dynamic_scraper, page_saver
from utils.logger import get_logger

logger = get_logger("hrv.scraper.engine")


def scrape_source(source: dict) -> list[dict]:
    """
    Scrape a single source entry and return a list of raw article dicts.

    Each dict has: title, url, snippet, raw_html, source_name,
                   source_category, source_url, scraped_at.
    """
    url: str = source["url"]
    name: str = source.get("name", url)
    category: str = source.get("category", "")
    is_dynamic: bool = source.get("is_dynamic", False)

    logger.info("Scraping: %s (%s)", name, url)

    # Compliance: robots.txt check
    if not robots_checker.is_allowed(url):
        logger.warning("Skipping %s – blocked by robots.txt", url)
        return []

    # Fetch page
    soup = None
    if is_dynamic:
        soup = dynamic_scraper.fetch_page(url)
    else:
        soup = static_scraper.fetch_page(url)

    if soup is None:
        logger.error("Could not fetch %s", url)
        return []

    # Optional: save raw HTML
    html_str = str(soup)
    page_saver.save_page(url, html_str)

    # Extract articles
    if is_dynamic:
        articles = dynamic_scraper.extract_articles(soup, url)
    else:
        articles = static_scraper.extract_articles(soup, url)

    scraped_at = datetime.now(timezone.utc).isoformat()

    # Attach source metadata to each article
    for article in articles:
        article["source_name"] = name
        article["source_category"] = category
        article["source_url"] = url
        article["scraped_at"] = scraped_at

    logger.info("  → %d articles extracted from %s", len(articles), name)
    return articles


def scrape_all(sources: list[dict]) -> list[dict]:
    """Scrape all enabled sources and return the combined raw articles list."""
    all_articles: list[dict] = []
    total = len(sources)
    for i, source in enumerate(sources, 1):
        logger.info("[%d/%d] Scraping: %s", i, total, source.get("name", source["url"]))
        try:
            articles = scrape_source(source)
            all_articles.extend(articles)
        except Exception as exc:  # noqa: BLE001
            logger.error("Unexpected error scraping %s: %s", source.get("url"), exc)
    logger.info("Scraping complete. Total raw articles: %d", len(all_articles))
    return all_articles
