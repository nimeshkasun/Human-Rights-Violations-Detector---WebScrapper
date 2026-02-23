"""
Human Rights Violations Detector – CLI entry point.

Usage examples:
  python main.py run                              # one-time run
  python main.py run --category ngo              # run for one category
  python main.py schedule                        # start scheduler loop
  python main.py sources list
  python main.py sources add
  python main.py sources edit <id>
  python main.py sources delete <id>
  python main.py sources seed                    # add built-in defaults
  python main.py settings show
  python main.py settings set save_scraped_pages true
  python main.py settings set scheduler.enabled true
  python main.py settings set scheduler.frequency daily
  python main.py settings set scheduler.time 07:00
"""
import argparse
import json
import sys
from pathlib import Path

# ── bootstrap path so sub-packages can import each other ──────────────────────
sys.path.insert(0, str(Path(__file__).parent))

import config
config.ensure_dirs()

from utils.logger import get_logger
from sources.manager import (
    list_sources, add_source, edit_source, delete_source,
    get_source, seed_default_sources, VALID_CATEGORIES,
)

logger = get_logger("hrv.main")


# ══════════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════════

def _yn(prompt: str, default: bool = True) -> bool:
    hint = "[Y/n]" if default else "[y/N]"
    ans = input(f"{prompt} {hint}: ").strip().lower()
    if not ans:
        return default
    return ans.startswith("y")


def _prompt(label: str, default: str = "") -> str:
    val = input(f"{label} [{default}]: ").strip() if default else input(f"{label}: ").strip()
    return val or default


def _print_source(s: dict) -> None:
    status = "✓ enabled" if s.get("enabled", True) else "✗ disabled"
    kind = "dynamic (JS)" if s.get("is_dynamic") else "static"
    print(
        f"  [{s['id'][:8]}…]  {s['name']}\n"
        f"    URL      : {s['url']}\n"
        f"    Category : {s['category']}  |  Type: {kind}  |  {status}\n"
        f"    Notes    : {s.get('notes','')}"
    )


# ══════════════════════════════════════════════════════════════════════════════
# Sources sub-commands
# ══════════════════════════════════════════════════════════════════════════════

def cmd_sources_list(args):
    sources = list_sources(category=args.category)
    if not sources:
        print("No sources found.")
        return
    print(f"\n{'─'*60}")
    for s in sources:
        _print_source(s)
        print(f"{'─'*60}")
    print(f"Total: {len(sources)}")


def cmd_sources_add(args):
    print("\nAdd a new source")
    name = _prompt("Name")
    url  = _prompt("URL (must start with http/https)")
    
    print(f"Categories: {', '.join(sorted(VALID_CATEGORIES))}")
    category = _prompt("Category")
    is_dynamic = _yn("Is this a JavaScript-heavy site (needs Selenium)?", default=False)
    notes = _prompt("Notes (optional)", default="")
    enabled = _yn("Enable immediately?", default=True)

    try:
        src = add_source(
            name=name, url=url, category=category,
            is_dynamic=is_dynamic, notes=notes, enabled=enabled,
        )
        print(f"\n✓ Source added (id: {src['id'][:8]}…)")
    except (ValueError, Exception) as exc:
        print(f"\n✗ Error: {exc}")


def cmd_sources_edit(args):
    try:
        src = get_source(args.id)
    except KeyError as exc:
        print(f"✗ {exc}")
        return

    print(f"\nEditing: {src['name']} (id: {src['id'][:8]}…)")
    print("Press Enter to keep current value.\n")

    name     = _prompt("Name", src["name"])
    url      = _prompt("URL", src["url"])
    print(f"Categories: {', '.join(sorted(VALID_CATEGORIES))}")
    category = _prompt("Category", src["category"])
    is_dynamic = _yn("JavaScript-heavy site?", default=src.get("is_dynamic", False))
    notes    = _prompt("Notes", src.get("notes", ""))
    enabled  = _yn("Enabled?", default=src.get("enabled", True))

    try:
        updated = edit_source(
            args.id,
            name=name, url=url, category=category,
            is_dynamic=is_dynamic, notes=notes, enabled=enabled,
        )
        print(f"\n✓ Source updated.")
    except (KeyError, ValueError) as exc:
        print(f"\n✗ Error: {exc}")


def cmd_sources_delete(args):
    try:
        src = get_source(args.id)
    except KeyError as exc:
        print(f"✗ {exc}")
        return

    if _yn(f"Delete source '{src['name']}'?", default=False):
        try:
            delete_source(args.id)
            print("✓ Source deleted.")
        except KeyError as exc:
            print(f"✗ {exc}")
    else:
        print("Aborted.")


def cmd_sources_seed(_args):
    seed_default_sources()
    print("✓ Default sources seeded.")


# ══════════════════════════════════════════════════════════════════════════════
# Settings sub-commands
# ══════════════════════════════════════════════════════════════════════════════

def cmd_settings_show(_args):
    settings = config.load_settings()
    print(json.dumps(settings, indent=2))


def _set_nested(d: dict, key_path: str, raw_value: str) -> None:
    """Set a nested dict value using dot-notation key path."""
    parts = key_path.split(".")
    for part in parts[:-1]:
        d = d.setdefault(part, {})
    last = parts[-1]

    # Type coercion
    if raw_value.lower() in ("true", "yes", "1"):
        d[last] = True
    elif raw_value.lower() in ("false", "no", "0"):
        d[last] = False
    else:
        try:
            d[last] = int(raw_value)
        except ValueError:
            try:
                d[last] = float(raw_value)
            except ValueError:
                d[last] = raw_value


def cmd_settings_set(args):
    settings = config.load_settings()
    _set_nested(settings, args.key, args.value)
    config.save_settings(settings)
    print(f"✓ {args.key} = {args.value}")


# ══════════════════════════════════════════════════════════════════════════════
# Run / Schedule sub-commands
# ══════════════════════════════════════════════════════════════════════════════

def cmd_run(args):
    from runner.one_time import run_once
    run_once(category=args.category if hasattr(args, "category") else None)


def cmd_schedule(args):
    from runner.scheduler import start_scheduler
    category = args.category if hasattr(args, "category") else None
    start_scheduler(category=category)


# ══════════════════════════════════════════════════════════════════════════════
# Argument parser
# ══════════════════════════════════════════════════════════════════════════════

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hrv",
        description="Human Rights Violations Detector – web scraper & analyser",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # ── run ───────────────────────────────────────────────────────────────────
    p_run = sub.add_parser("run", help="Run the scraper pipeline once")
    p_run.add_argument(
        "--category",
        choices=sorted(VALID_CATEGORIES),
        default=None,
        help="Limit run to a specific source category",
    )
    p_run.set_defaults(func=cmd_run)

    # ── schedule ──────────────────────────────────────────────────────────────
    p_sched = sub.add_parser("schedule", help="Start the scheduler loop")
    p_sched.add_argument(
        "--category",
        choices=sorted(VALID_CATEGORIES),
        default=None,
        help="Limit scheduled runs to a specific source category",
    )
    p_sched.set_defaults(func=cmd_schedule)

    # ── sources ───────────────────────────────────────────────────────────────
    p_src = sub.add_parser("sources", help="Manage scraping sources")
    src_sub = p_src.add_subparsers(dest="src_command", required=True)

    p_list = src_sub.add_parser("list", help="List all sources")
    p_list.add_argument("--category", choices=sorted(VALID_CATEGORIES), default=None)
    p_list.set_defaults(func=cmd_sources_list)

    p_add = src_sub.add_parser("add", help="Add a new source (interactive)")
    p_add.set_defaults(func=cmd_sources_add)

    p_edit = src_sub.add_parser("edit", help="Edit an existing source")
    p_edit.add_argument("id", help="Full UUID or unique prefix (min 6 chars)")
    p_edit.set_defaults(func=cmd_sources_edit)

    p_del = src_sub.add_parser("delete", help="Delete a source")
    p_del.add_argument("id", help="Full UUID or unique prefix")
    p_del.set_defaults(func=cmd_sources_delete)

    p_seed = src_sub.add_parser("seed", help="Seed built-in default sources")
    p_seed.set_defaults(func=cmd_sources_seed)

    # ── menu ──────────────────────────────────────────────────────────────────
    p_menu = sub.add_parser("menu", help="Launch the interactive menu (default)")
    p_menu.set_defaults(func=cmd_menu)

    # ── settings ──────────────────────────────────────────────────────────────
    p_cfg = sub.add_parser("settings", help="View / change app settings")
    cfg_sub = p_cfg.add_subparsers(dest="cfg_command", required=True)

    p_show = cfg_sub.add_parser("show", help="Print current settings as JSON")
    p_show.set_defaults(func=cmd_settings_show)

    p_set = cfg_sub.add_parser("set", help="Set a setting value (dot-notation)")
    p_set.add_argument(
        "key",
        help=(
            "Dot-notation key, e.g. save_scraped_pages, "
            "scheduler.enabled, scheduler.frequency, scheduler.time, "
            "scheduler.day_of_week, chrome_headless, respect_robots_txt, "
            "dedup_window_hours"
        ),
    )
    p_set.add_argument("value", help="Value to set (true/false/number/string)")
    p_set.set_defaults(func=cmd_settings_set)

    return parser


# ══════════════════════════════════════════════════════════════════════════════
# Interactive menu
# ══════════════════════════════════════════════════════════════════════════════

MENU_WIDTH = 58


def _clear():
    import os
    os.system("cls" if os.name == "nt" else "clear")


def _header():
    print("╔" + "═" * MENU_WIDTH + "╗")
    print("║" + " Human Rights Violations Detector ".center(MENU_WIDTH) + "║")
    print("║" + " Web Scraper & Analyser ".center(MENU_WIDTH) + "║")
    print("╚" + "═" * MENU_WIDTH + "╝")
    print()


def _section(title: str):
    print("\n  " + "-" * (MENU_WIDTH - 2))
    print(f"  {title}")
    print("  " + "-" * (MENU_WIDTH - 2))


def _pick(prompt: str, choices: list[str], allow_back: bool = True) -> str | None:
    """Show a numbered list and return the chosen value, or None for back/exit."""
    for i, c in enumerate(choices, 1):
        print(f"    [{i}] {c}")
    if allow_back:
        print(f"    [0] Back")
    while True:
        raw = input(f"\n  {prompt}: ").strip()
        if raw == "0" and allow_back:
            return None
        if raw.isdigit() and 1 <= int(raw) <= len(choices):
            return choices[int(raw) - 1]
        print("  Invalid choice – try again.")


# ── Sources submenu ────────────────────────────────────────────────────────────

def _menu_sources():
    while True:
        _clear()
        _header()
        _section("Manage Sources")
        options = [
            "List all sources",
            "List by category",
            "Add a new source",
            "Edit a source",
            "Delete a source",
            "Seed default sources",
        ]
        choice = _pick("Select option", options)
        if choice is None:
            return

        if choice == "List all sources":
            print()
            cmd_sources_list(argparse.Namespace(category=None))
            input("\n  Press Enter to continue…")

        elif choice == "List by category":
            print()
            cat = _pick("Select category", sorted(VALID_CATEGORIES))
            if cat:
                print()
                cmd_sources_list(argparse.Namespace(category=cat))
                input("\n  Press Enter to continue…")

        elif choice == "Add a new source":
            print()
            cmd_sources_add(argparse.Namespace())
            input("\n  Press Enter to continue…")

        elif choice == "Edit a source":
            print()
            sources = list_sources()
            if not sources:
                print("  No sources found.")
                input("\n  Press Enter to continue…")
                continue
            labels = [f"{s['name']}  [{s['id'][:8]}…]" for s in sources]
            sel = _pick("Select source to edit", labels)
            if sel:
                idx = labels.index(sel)
                cmd_sources_edit(argparse.Namespace(id=sources[idx]["id"]))
                input("\n  Press Enter to continue…")

        elif choice == "Delete a source":
            print()
            sources = list_sources()
            if not sources:
                print("  No sources found.")
                input("\n  Press Enter to continue…")
                continue
            labels = [f"{s['name']}  [{s['id'][:8]}…]" for s in sources]
            sel = _pick("Select source to delete", labels)
            if sel:
                idx = labels.index(sel)
                cmd_sources_delete(argparse.Namespace(id=sources[idx]["id"]))
                input("\n  Press Enter to continue…")

        elif choice == "Seed default sources":
            print()
            cmd_sources_seed(argparse.Namespace())
            input("\n  Press Enter to continue…")


# ── Settings submenu ───────────────────────────────────────────────────────────

_SETTINGS_KEYS = [
    ("save_scraped_pages",   "Save raw HTML pages  (true/false)"),
    ("dedup_window_hours",   "Deduplication window in hours  (number)"),
    ("respect_robots_txt",   "Respect robots.txt  (true/false)"),
    ("chrome_headless",      "Run Chrome headless  (true/false)"),
    ("scheduler.enabled",    "Scheduler enabled  (true/false)"),
    ("scheduler.frequency",  "Scheduler frequency  (hourly/daily/weekly)"),
    ("scheduler.time",       "Scheduler time  (HH:MM)"),
    ("scheduler.day_of_week","Scheduler day of week  (monday…sunday)"),
]


def _menu_settings():
    while True:
        _clear()
        _header()
        _section("Settings")
        settings = config.load_settings()
        options = [
            f"{label}  →  current: {_nested_get(settings, key)}"
            for key, label in _SETTINGS_KEYS
        ]
        options.append("Show full settings (JSON)")
        choice = _pick("Select setting to change", options)
        if choice is None:
            return

        if choice == "Show full settings (JSON)":
            print()
            cmd_settings_show(argparse.Namespace())
            input("\n  Press Enter to continue…")
            continue

        idx = options.index(choice)
        key, label = _SETTINGS_KEYS[idx]
        current = _nested_get(settings, key)
        print(f"\n  Current value of '{key}': {current}")
        new_val = input(f"  New value: ").strip()
        if new_val:
            cmd_settings_set(argparse.Namespace(key=key, value=new_val))
        input("\n  Press Enter to continue…")


def _nested_get(d: dict, key_path: str):
    parts = key_path.split(".")
    for p in parts:
        if not isinstance(d, dict):
            return "–"
        d = d.get(p, "–")
    return d


# ── Main menu ──────────────────────────────────────────────────────────────────

def cmd_menu(_args=None):
    while True:
        _clear()
        _header()
        _section("Main Menu")
        options = [
            "Run scraper  (all sources)",
            "Run scraper  (choose category)",
            "Start scheduler loop",
            "Manage sources",
            "Settings",
            "Exit",
        ]
        choice = _pick("Select option", options, allow_back=False)
        if choice is None or choice == "Exit":
            print("\n  Goodbye.\n")
            sys.exit(0)

        elif choice == "Run scraper  (all sources)":
            print()
            cmd_run(argparse.Namespace(category=None))
            input("\n  Press Enter to return to menu…")

        elif choice == "Run scraper  (choose category)":
            print()
            cat = _pick("Select category", sorted(VALID_CATEGORIES))
            if cat:
                cmd_run(argparse.Namespace(category=cat))
                input("\n  Press Enter to return to menu…")

        elif choice == "Start scheduler loop":
            print()
            print("  Starting scheduler – press Ctrl-C to stop and return to menu.")
            try:
                cmd_schedule(argparse.Namespace(category=None))
            except KeyboardInterrupt:
                print("\n  Scheduler stopped.")
            input("\n  Press Enter to return to menu…")

        elif choice == "Manage sources":
            _menu_sources()

        elif choice == "Settings":
            _menu_settings()


# ══════════════════════════════════════════════════════════════════════════════
# Entry
# ══════════════════════════════════════════════════════════════════════════════

def main():
    # No arguments → launch interactive menu
    if len(sys.argv) == 1:
        cmd_menu()
        return

    parser = build_parser()
    args = parser.parse_args()
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
