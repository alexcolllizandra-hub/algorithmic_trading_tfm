"""Project logging configured once, rendered with rich (+ optional file logs)."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path

from rich.logging import RichHandler

_CONFIGURED = False


def _configure_root(level: int) -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return
    handler = RichHandler(rich_tracebacks=True, show_path=False, markup=False)
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[handler],
    )
    _CONFIGURED = True


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """Return a namespaced logger with rich formatting configured once."""
    _configure_root(level)
    return logging.getLogger(name)


def add_file_logging(
    log_dir: str | Path = "logs", *, prefix: str = "perp_lab", level: int = logging.INFO
) -> Path:
    """Attach a timestamped UTC file handler to the root logger.

    Returns the path of the created log file. The ``logs/`` directory is
    git-ignored, so run logs stay local. Each call creates a fresh file so runs
    do not overwrite one another.
    """
    _configure_root(level)
    directory = Path(log_dir)
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    path = directory / f"{prefix}_{stamp}.log"
    handler = logging.FileHandler(path, encoding="utf-8")
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logging.getLogger().addHandler(handler)
    return path
