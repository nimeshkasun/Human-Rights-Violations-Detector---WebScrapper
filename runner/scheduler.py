"""
Scheduled runner using the `schedule` library.
Reads schedule configuration from settings.json and keeps running until
the process is killed (Ctrl-C or SIGTERM).

Supported frequencies:
  - daily   → runs once per day at HH:MM
  - weekly  → runs once per week on day_of_week at HH:MM
  - hourly  → runs every hour (ignores the time field)
"""
import time
import signal
import sys
from typing import Optional

import schedule

import config
from runner.pipeline import run_pipeline
from utils.logger import get_logger

logger = get_logger("hrv.runner.scheduler")

_stop_flag = False


def _signal_handler(sig, frame):
    global _stop_flag
    logger.info("Shutdown signal received. Stopping scheduler.")
    _stop_flag = True


def _job(category: Optional[str] = None) -> None:
    logger.info("Scheduled job triggered.")
    try:
        run_pipeline(category=category)
    except Exception as exc:  # noqa: BLE001
        logger.error("Scheduled job failed: %s", exc)


def start_scheduler(category: Optional[str] = None) -> None:
    """
    Configure and start the scheduler loop.
    Reads frequency/time from settings.json.
    Blocks until the process is stopped.
    """
    global _stop_flag
    _stop_flag = False

    settings = config.load_settings()
    sched_cfg = settings.get("scheduler", {})

    if not sched_cfg.get("enabled", False):
        logger.warning(
            "Scheduler is disabled in settings.json. "
            "Set scheduler.enabled = true to activate."
        )
        print("Scheduler is disabled. Enable it with: python main.py settings scheduler.enabled true")
        return

    frequency: str = sched_cfg.get("frequency", "daily")
    run_time: str   = sched_cfg.get("time", "06:00")
    day_of_week: str = sched_cfg.get("day_of_week", "monday").lower()

    schedule.clear()

    if frequency == "hourly":
        schedule.every().hour.do(_job, category=category)
        logger.info("Scheduler: every hour")
    elif frequency == "weekly":
        getattr(schedule.every(), day_of_week).at(run_time).do(_job, category=category)
        logger.info("Scheduler: every %s at %s", day_of_week, run_time)
    else:  # daily (default)
        schedule.every().day.at(run_time).do(_job, category=category)
        logger.info("Scheduler: every day at %s", run_time)

    # Graceful shutdown on SIGINT / SIGTERM
    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    print(f"Scheduler running ({frequency}). Press Ctrl-C to stop.")
    logger.info("Scheduler started.")

    while not _stop_flag:
        schedule.run_pending()
        time.sleep(30)

    logger.info("Scheduler stopped.")
    print("Scheduler stopped.")
