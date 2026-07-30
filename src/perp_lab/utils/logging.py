"""Project logging configured once, rendered with rich."""

from __future__ import annotations

import logging

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
