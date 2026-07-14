from __future__ import annotations

import logging
import sys
from pathlib import Path


def setup_logger(
    name: str = "prana_elex",
    level: str = "INFO",
    console_level: str | None = None,
    log_file: str | Path | None = None,
) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    if not logger.handlers:
        stream = sys.stdout if sys.stdout is not None else sys.stderr
        console = logging.StreamHandler(stream)
        console.setFormatter(fmt)
        if console_level:
            console.setLevel(getattr(logging, console_level.upper(), logging.WARNING))
        logger.addHandler(console)

        if log_file:
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            fh = logging.FileHandler(str(log_path), encoding="utf-8")
            fh.setFormatter(fmt)
            logger.addHandler(fh)

    return logger


def get_logger(name: str = "prana_elex") -> logging.Logger:
    return logging.getLogger(name)
