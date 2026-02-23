"""Logging setup – writes to hrv_trace.log and console simultaneously."""
import logging
import sys
from pathlib import Path

import config  # noqa: E402 – imported after sys.path is set in main

_initialised = False


def get_logger(name: str = "hrv") -> logging.Logger:
    """Return (and lazily initialise) the root HRV logger."""
    global _initialised
    logger = logging.getLogger(name)

    if _initialised:
        return logger

    logger.setLevel(logging.DEBUG)
    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)-8s] %(name)s – %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # File handler
    config.LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    fh = logging.FileHandler(config.LOG_FILE, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)

    # Console handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)

    logger.addHandler(fh)
    logger.addHandler(ch)
    _initialised = True
    return logger
