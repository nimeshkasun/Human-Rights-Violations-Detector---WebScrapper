"""
Main scraping engine.
Orchestrates robots-check → fetch (static or dynamic) → extract → page-save.
Supports configurable scrape depth:
  depth 1 – index/listing page only
  depth 2 – also follow each article link and enrich with full-page content
"""
from typing import Optional
from datetime import datetime, timezone

import config
from scraper import robots_checker, static_scraper, dynamic_scraper, page_saver
from utils.logger import get_logger

logger = get_logger("hrv.scraper.engine")


# ──────────────────────────────────────────────────────────────────────────────
def _fetch(url: str, is_dynamic: bool) -> Optional[object]:
    """Fetch a URL using the appropriate scraper."""
    if is_dynamic:
        return dynamic_scraper.fetch_page(url)
    return static_scraper.fetch_page(url)


def _extract_article_text(soup) -> str:
    """
    Pull the main body text from an individual article page.
    Tries <article> first, then common content div patterns, then <body>.
    """
    # Priority candidates for article body
    for selector in (
        {"name": "article"},
        {"name": "div", "class_": lambda c: c and any(
            kw in c.lower() for kw in ("article-body", "article__body",
                                        "story-body", "entry-content",
                                        "post-content", "content-body",
                                        "article-content", "main-content"))},
        {"name": "main"},
    ):
        tag = soup.find(**selector)
        if tag:
            text = tag.get_text(separator=" ", strip=True)
            if len(text) > 100:
                return text[:2000]  # cap to avoid bloat
    # Fallback: grab all <p> text from the page
    paragraphs = " ".join(p.get_text(strip=True) for p in soup.find_all("p"))
    return paragraphs[:2000]


# ──────────────────────────────────────────────────────────────────────────────
def _print(msg: str, end: str = "\n") -> None:
    """Print to console immediately (unbuffered)."""
    print(msg, end=end, flush=True)


def scrape_source(
    source: dict,
    depth: Optional[int] = None,
    index: int = 0,
    total: int = 0,
) -> list[dict]:
    """
    Scrape a single source entry and return a list of raw article dicts.

    Each dict has: title, url, snippet, raw_html, source_name,
                   source_category, source_url, scraped_at.

    depth overrides the settings value when supplied explicitly.
      1 – index page only
      2 – follow each discovered article link for full content
    """
    settings = config.load_settings()
    if depth is None:
        depth = int(settings.get("scrape_depth", 2))

    url: str = source["url"]
    name: str = source.get("name", url)
    category: str = source.get("category", "")
    is_dynamic: bool = source.get("is_dynamic", False)
    counter = f"[{index}/{total}] " if total else ""
    kind_tag = "[JS]" if is_dynamic else "[static]"

    logger.info("Scraping (depth=%d): %s (%s)", depth, name, url)
    _print(f"  {counter}{kind_tag} {name}")
    _print(f"          URL : {url}")

    # ─ robots.txt check ───────────────────────────────────────────────────────
    if not robots_checker.is_allowed(url):
        logger.warning("Skipping %s – blocked by robots.txt", url)
        _print("          ✗  Blocked by robots.txt – skipping")
        return []

    # ─ Fetch index / listing page ─────────────────────────────────────────────
    _print(f"          Fetching index page… ", end="")
    soup = _fetch(url, is_dynamic)
    if soup is None:
        logger.error("Could not fetch %s", url)
        _print("FAILED")
        return []
    _print("OK")

    page_saver.save_page(url, str(soup))

    if is_dynamic:
        articles = dynamic_scraper.extract_articles(soup, url)
    else:
        articles = static_scraper.extract_articles(soup, url)

    _print(f"          Found {len(articles)} article link(s) on index page")
    scraped_at = datetime.now(timezone.utc).isoformat()

    # ─ Depth-2: follow each article link and enrich snippet ──────────────────
    if depth >= 2 and articles:
        _print(f"          Following {len(articles)} link(s) at depth 2…")
        enriched = 0
        skipped_robots = 0
        failed = 0
        for idx, article in enumerate(articles, 1):
            art_url = article.get("url", "")
            if not art_url or art_url == url:
                continue
            _print(f"            [{idx}/{len(articles)}] {art_url[:80]}… ", end="")
            if not robots_checker.is_allowed(art_url):
                logger.debug("  Depth-2 skip (robots.txt): %s", art_url)
                _print("blocked (robots.txt)")
                skipped_robots += 1
                continue
            art_soup = _fetch(art_url, is_dynamic)
            if art_soup is None:
                _print("FAILED")
                failed += 1
                continue
            full_text = _extract_article_text(art_soup)
            if full_text:
                article["snippet"] = full_text
            page_saver.save_page(art_url, str(art_soup))
            logger.debug("  Depth-2 enriched: %s", art_url)
            _print("OK")
            enriched += 1
        _print(
            f"          Depth-2 done: {enriched} enriched, "
            f"{skipped_robots} blocked, {failed} failed"
        )

    # Attach source metadata
    for article in articles:
        article["source_name"] = name
        article["source_category"] = category
        article["source_url"] = url
        article["scraped_at"] = scraped_at

    logger.info("  → %d articles extracted from %s", len(articles), name)
    _print(f"          ✓  {len(articles)} article(s) collected from {name}")
    return articles


def scrape_all(sources: list[dict]) -> list[dict]:
    """Scrape all enabled sources and return the combined raw articles list."""
    all_articles: list[dict] = []
    total = len(sources)
    _print(f"\n  Scraping {total} source(s)…")
    _print("  " + "─" * 54)
    for i, source in enumerate(sources, 1):
        logger.info("[%d/%d] Scraping: %s", i, total, source.get("name", source["url"]))
        try:
            articles = scrape_source(source, index=i, total=total)
            all_articles.extend(articles)
        except Exception as exc:  # noqa: BLE001
            logger.error("Unexpected error scraping %s: %s", source.get("url"), exc)
            _print(f"          ✗  Unexpected error: {exc}")
        _print("  " + "─" * 54)
    _print(f"  Scraping complete – {len(all_articles)} raw article(s) collected")
    return all_articles
