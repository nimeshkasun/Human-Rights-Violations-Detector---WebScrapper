# Human Rights Violations Detector

A Python + Selenium web scraper that collects news articles from multiple
source types, filters for human-rights-violation content, deduplicates results,
and exports clean CSV reports.

---

## Features

| Feature | Detail |
|---|---|
| Source categories | Public news, Government portals, NGO articles, Public posts |
| Source management | Add / edit / delete / seed via CLI; persisted in `sources.json` |
| Static scraping | `requests` + `BeautifulSoup` for plain HTML sites |
| Dynamic scraping | Selenium (Chrome) for JS-heavy pages |
| HRV keyword filter | 10+ violation categories, 80+ keywords |
| Deduplication | Exact ID + URL dedup; cross-session window (configurable hours) |
| CSV export | `data/exports/hrv_<timestamp>.csv` with source attribution |
| Page saving | Optional: save raw HTML to `scraped_pages/` (toggle in settings) |
| Logging | Dual output – console + `hrv_trace.log` |
| One-time run | `python main.py run` |
| Scheduled run | `python main.py schedule` (daily / weekly / hourly via settings) |
| Compliance | robots.txt respect, user-agent declaration, approved sources only |

---

## Requirements

- Python 3.10+
- Google Chrome installed (for Selenium/dynamic scraping)

---

## Setup

```bash
# 1. Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS / Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Seed default sources (optional – adds Amnesty, HRW, OHCHR, Reuters, BBC)
python main.py sources seed
```

---

## Usage

### One-time scrape run
```bash
python main.py run
python main.py run --category ngo          # single category
```

### Scheduled run
```bash
# Enable and configure the scheduler first
python main.py settings set scheduler.enabled true
python main.py settings set scheduler.frequency daily
python main.py settings set scheduler.time 06:00

# Start (blocks; Ctrl-C to stop)
python main.py schedule
```

### Manage sources
```bash
python main.py sources list
python main.py sources list --category government
python main.py sources add                 # interactive prompt
python main.py sources edit <source-id>   # interactive prompt
python main.py sources delete <source-id>
python main.py sources seed
```

### Settings
```bash
python main.py settings show

# Toggle page saving
python main.py settings set save_scraped_pages true

# Adjust deduplication window (hours)
python main.py settings set dedup_window_hours 48

# Disable robots.txt enforcement (not recommended)
python main.py settings set respect_robots_txt false

# Run Chrome with a visible window (for debugging)
python main.py settings set chrome_headless false
```

---

## Project structure

```
Simple-Web-Scrapper/
├── main.py                  # CLI entry point
├── config.py                # Paths, keywords, settings helpers
├── requirements.txt
├── sources.json             # Persisted sources (auto-created)
├── settings.json            # App settings (auto-created)
├── hrv_trace.log            # Run log (auto-created)
│
├── sources/
│   └── manager.py           # CRUD for sources.json
│
├── scraper/
│   ├── engine.py            # Orchestrates scraping of all sources
│   ├── static_scraper.py    # requests + BeautifulSoup
│   ├── dynamic_scraper.py   # Selenium (Chrome)
│   ├── robots_checker.py    # robots.txt compliance
│   └── page_saver.py        # Optional HTML page storage
│
├── processor/
│   ├── normalizer.py        # Unified record schema
│   ├── filter.py            # HRV keyword detection & annotation
│   └── deduplicator.py      # Cross-batch deduplication
│
├── exporter/
│   └── csv_exporter.py      # data/exports/hrv_<timestamp>.csv
│
├── runner/
│   ├── pipeline.py          # Full pipeline (scrape→normalize→filter→dedup→export)
│   ├── one_time.py          # Single run
│   └── scheduler.py        # schedule-based loop
│
├── utils/
│   └── logger.py            # Dual file+console logger
│
├── data/
│   └── exports/             # CSV output files
└── scraped_pages/           # Raw HTML saves (when enabled)
```

---

## Exported CSV columns

| Column | Description |
|---|---|
| `id` | Unique record hash (SHA-256 of url+title) |
| `title` | Article title |
| `url` | Article URL |
| `source_name` | Human-readable source name |
| `source_category` | `public_news` / `government` / `ngo` / `public_posts` |
| `attribution` | `"Source Name (category)"` – for legal/compliance use |
| `published_date` | Extracted date (best-effort) or blank |
| `scraped_at` | UTC ISO-8601 timestamp of scrape |
| `violation_categories` | Pipe-separated detected violation types |
| `matched_keywords` | Pipe-separated keywords that triggered the match |
| `snippet` | Short text excerpt |

---

## Compliance notes

- Only sources explicitly listed in `sources.json` are scraped.
- `robots.txt` is checked for every URL before fetching (disable only with explicit setting).
- The `User-Agent` header identifies the tool.
- All exported records include `attribution` and `source_url` for traceability.
- Static HTML pages can optionally be archived for audit purposes.
