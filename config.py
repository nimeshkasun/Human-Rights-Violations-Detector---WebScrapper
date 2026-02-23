"""
Global configuration for Human Rights Violations Detector.
Edit this file or use the CLI to manage settings.
"""
import os
import json
from pathlib import Path

BASE_DIR = Path(__file__).parent

# ── Paths ──────────────────────────────────────────────────────────────────────
SOURCES_FILE       = BASE_DIR / "sources.json"
SETTINGS_FILE      = BASE_DIR / "settings.json"
DATA_DIR           = BASE_DIR / "data"
EXPORTS_DIR        = DATA_DIR / "exports"
SCRAPED_PAGES_DIR  = BASE_DIR / "scraped_pages"
LOG_FILE           = BASE_DIR / "hrv_trace.log"

# ── Scraping defaults ──────────────────────────────────────────────────────────
REQUEST_TIMEOUT    = 20          # seconds for HTTP requests
SELENIUM_TIMEOUT   = 30          # seconds for Selenium page loads
PAGE_LOAD_DELAY    = 2           # seconds to wait after JS rendering
MAX_RETRIES        = 3
USER_AGENT         = (
    "Mozilla/5.0 (compatible; HRVDetector/1.0; "
    "+https://github.com/hrv-detector)"
)

# ── HRV keyword categories ─────────────────────────────────────────────────────
HRV_KEYWORDS: dict[str, list[str]] = {
    "torture_abuse": [
        "torture", "torturing", "tortured", "cruel treatment",
        "inhumane treatment", "degrading treatment", "abuse",
        "beaten", "beating", "flogging", "electrocution",
    ],
    "arbitrary_detention": [
        "arbitrary detention", "arbitrary arrest", "unlawful detention",
        "political prisoner", "detained without", "held without charge",
        "enforced disappearance", "disappeared", "incommunicado",
    ],
    "extrajudicial_killing": [
        "extrajudicial killing", "extrajudicial execution", "summary execution",
        "unlawful killing", "targeted killing", "assassination",
        "murdered by police", "killed by security", "death squad",
    ],
    "freedom_speech": [
        "censorship", "censored", "silenced", "press freedom",
        "journalist arrested", "journalist killed", "internet shutdown",
        "blocked website", "banned publication",
    ],
    "discrimination": [
        "racial discrimination", "ethnic cleansing", "apartheid",
        "religious persecution", "minority rights", "caste discrimination",
        "gender discrimination", "LGBTQ+ persecution",
    ],
    "refugee_migration": [
        "refugee", "asylum seeker", "forcibly displaced",
        "deportation", "refoulement", "stateless",
    ],
    "child_rights": [
        "child soldier", "child labor", "child marriage",
        "trafficking of children", "child abuse", "child exploitation",
    ],
    "gender_violence": [
        "sexual violence", "rape", "gender-based violence",
        "forced marriage", "female genital mutilation", "femicide",
        "trafficking", "sex trafficking",
    ],
    "war_crimes": [
        "war crime", "crimes against humanity", "genocide",
        "ethnic cleansing", "civilian massacre", "collective punishment",
        "siege", "use of chemical weapons",
    ],
    "general": [
        "human rights violation", "human rights abuse", "rights violation",
        "violated rights", "rights abuses", "oppression", "repression",
        "crackdown", "suppression", "persecution",
    ],
}

# Flat keyword list built from the dict above (used for quick searching)
ALL_HRV_KEYWORDS: list[str] = [
    kw for kws in HRV_KEYWORDS.values() for kw in kws
]

# ── Default settings (written to settings.json on first run) ───────────────────
DEFAULT_SETTINGS: dict = {
    "save_scraped_pages": False,          # feature toggle
    "scheduler": {
        "enabled": False,
        "frequency": "daily",             # daily | weekly | hourly
        "time": "06:00",                  # HH:MM  (24h, used for daily/weekly)
        "day_of_week": "monday",          # used when frequency == weekly
    },
    "chrome_headless": True,
    "respect_robots_txt": True,
    "dedup_window_hours": 24,             # hours to look back when deduping
}


def load_settings() -> dict:
    if not SETTINGS_FILE.exists():
        save_settings(DEFAULT_SETTINGS)
        return dict(DEFAULT_SETTINGS)
    with open(SETTINGS_FILE, encoding="utf-8") as f:
        stored = json.load(f)
    # merge so new keys from DEFAULT_SETTINGS are always present
    merged = {**DEFAULT_SETTINGS, **stored}
    merged["scheduler"] = {**DEFAULT_SETTINGS["scheduler"], **stored.get("scheduler", {})}
    return merged


def save_settings(settings: dict) -> None:
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2)


def ensure_dirs() -> None:
    """Create all required directories if they don't exist."""
    for d in (DATA_DIR, EXPORTS_DIR, SCRAPED_PAGES_DIR):
        d.mkdir(parents=True, exist_ok=True)
