"""
Robots.txt compliance checker.
Caches parsed robots.txt per host to avoid repeated network calls.
"""
from urllib.robotparser import RobotFileParser
from urllib.parse import urlparse
from functools import lru_cache

import config
from utils.logger import get_logger

logger = get_logger("hrv.robots")


@lru_cache(maxsize=256)
def _get_parser(robots_url: str) -> RobotFileParser:
    rp = RobotFileParser()
    rp.set_url(robots_url)
    try:
        rp.read()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not read robots.txt at %s: %s", robots_url, exc)
    return rp


def robots_url_for(url: str) -> str:
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}/robots.txt"


def is_allowed(url: str, user_agent: str = config.USER_AGENT) -> bool:
    """
    Return True if scraping `url` is permitted according to robots.txt.
    If respect_robots_txt is disabled in settings, always returns True.
    """
    from config import load_settings  # avoid circular at module level

    settings = load_settings()
    if not settings.get("respect_robots_txt", True):
        return True

    robots_url = robots_url_for(url)
    parser = _get_parser(robots_url)
    allowed = parser.can_fetch(user_agent, url)
    if not allowed:
        logger.warning("robots.txt DISALLOWS: %s", url)
    return allowed
