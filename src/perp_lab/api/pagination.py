"""Small pagination helpers shared by list endpoints."""

from __future__ import annotations

from dataclasses import dataclass

from perp_lab.api.models import PageMeta


@dataclass(frozen=True)
class PageParams:
    limit: int
    offset: int


def paginate[T](items: list[T], params: PageParams) -> tuple[list[T], PageMeta]:
    """Return the requested slice plus pagination metadata."""
    total = len(items)
    start = min(params.offset, total)
    end = min(start + params.limit, total)
    window = items[start:end]
    meta = PageMeta(total=total, limit=params.limit, offset=params.offset, returned=len(window))
    return window, meta
