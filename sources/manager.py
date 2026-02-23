"""
Sources manager – CRUD operations for scraping sources stored in sources.json.

Schema of each source entry:
{
    "id": str,          # UUID
    "name": str,
    "url": str,
    "category": str,    # public_news | government | ngo | public_posts
    "is_dynamic": bool, # True → Selenium; False → requests
    "enabled": bool,
    "notes": str
}
"""
import json
import uuid
from pathlib import Path
from typing import Optional

import config
from utils.logger import get_logger

logger = get_logger("hrv.sources")

VALID_CATEGORIES = {"public_news", "government", "ngo", "public_posts"}


def _load() -> list[dict]:
    if not config.SOURCES_FILE.exists():
        return []
    with open(config.SOURCES_FILE, encoding="utf-8") as f:
        return json.load(f)


def _save(sources: list[dict]) -> None:
    config.SOURCES_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(config.SOURCES_FILE, "w", encoding="utf-8") as f:
        json.dump(sources, f, indent=2)
    logger.debug("sources.json saved (%d entries)", len(sources))


# ── Public API ─────────────────────────────────────────────────────────────────

def list_sources(category: Optional[str] = None, enabled_only: bool = False) -> list[dict]:
    """Return all sources, optionally filtered by category and enabled flag."""
    sources = _load()
    if category:
        sources = [s for s in sources if s.get("category") == category]
    if enabled_only:
        sources = [s for s in sources if s.get("enabled", True)]
    return sources


def add_source(
    name: str,
    url: str,
    category: str,
    is_dynamic: bool = False,
    notes: str = "",
    enabled: bool = True,
) -> dict:
    """Add a new source and persist it. Returns the created entry."""
    if category not in VALID_CATEGORIES:
        raise ValueError(
            f"Invalid category '{category}'. Valid: {sorted(VALID_CATEGORIES)}"
        )
    sources = _load()
    # Prevent duplicate URLs
    if any(s["url"] == url for s in sources):
        raise ValueError(f"A source with URL '{url}' already exists.")

    entry = {
        "id": str(uuid.uuid4()),
        "name": name,
        "url": url,
        "category": category,
        "is_dynamic": is_dynamic,
        "enabled": enabled,
        "notes": notes,
    }
    sources.append(entry)
    _save(sources)
    logger.info("Source added: %s (%s)", name, url)
    return entry


def edit_source(source_id: str, **fields) -> dict:
    """
    Update fields on an existing source by its ID.
    Allowed fields: name, url, category, is_dynamic, enabled, notes.
    """
    sources = _load()
    for src in sources:
        if src["id"] == source_id:
            for key, val in fields.items():
                if key == "id":
                    raise ValueError("Cannot change source id.")
                if key == "category" and val not in VALID_CATEGORIES:
                    raise ValueError(f"Invalid category '{val}'.")
                src[key] = val
            _save(sources)
            logger.info("Source updated: %s", source_id)
            return src
    raise KeyError(f"No source found with id '{source_id}'.")


def delete_source(source_id: str) -> None:
    """Remove a source by ID."""
    sources = _load()
    original_len = len(sources)
    sources = [s for s in sources if s["id"] != source_id]
    if len(sources) == original_len:
        raise KeyError(f"No source found with id '{source_id}'.")
    _save(sources)
    logger.info("Source deleted: %s", source_id)


def get_source(source_id: str) -> dict:
    """
    Fetch a single source by full UUID or unique prefix (min 6 chars).
    Raises KeyError if not found, ValueError if the prefix is ambiguous.
    """
    sources = _load()
    # Exact match first
    for s in sources:
        if s["id"] == source_id:
            return s
    # Prefix match
    matches = [s for s in sources if s["id"].startswith(source_id)]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        ids = ", ".join(s['id'][:12] for s in matches)
        raise ValueError(f"Prefix '{source_id}' is ambiguous: {ids}")
    raise KeyError(f"No source found with id '{source_id}'.")


def seed_default_sources() -> None:
    """Populate sources.json with a small set of well-known public sources."""
    defaults = [
        {
            "name": "Amnesty International – News",
            "url": "https://www.amnesty.org/en/latest/news/",
            "category": "ngo",
            "is_dynamic": False,
            "notes": "Leading human rights NGO",
        },
        {
            "name": "Human Rights Watch",
            "url": "https://www.hrw.org/news",
            "category": "ngo",
            "is_dynamic": False,
            "notes": "",
        },
        {
            "name": "UN Human Rights (OHCHR) – News",
            "url": "https://www.ohchr.org/en/news-and-events/news",
            "category": "government",
            "is_dynamic": False,
            "notes": "UN Office of the High Commissioner for Human Rights",
        },
        {
            "name": "Reuters – World News",
            "url": "https://www.reuters.com/world/",
            "category": "public_news",
            "is_dynamic": True,
            "notes": "Major wire service – JS-rendered",
        },
        {
            "name": "BBC News – World",
            "url": "https://www.bbc.com/news/world",
            "category": "public_news",
            "is_dynamic": True,
            "notes": "",
        },
    ]
    for d in defaults:
        try:
            add_source(**d)
        except ValueError:
            pass  # skip duplicates silently
    logger.info("Default sources seeded.")
