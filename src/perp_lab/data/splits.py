"""Chronological splitting and the frozen final holdout.

Research-integrity rules:
- Splits are strictly chronological. There are NO random train/test splits.
- The holdout is the final contiguous block before the cutoff. It is frozen and
  never used for EDA-driven decisions or parameter selection.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

import polars as pl

from perp_lab.config.models import DataContract
from perp_lab.utils.timeutils import floor_to_timeframe


@dataclass(frozen=True)
class ChronoSplit:
    """A development / holdout partition of a dataset."""

    development: pl.DataFrame
    holdout: pl.DataFrame
    holdout_start: datetime


def resolve_holdout_start(contract: DataContract) -> datetime:
    """Holdout start as a tz-aware UTC datetime, snapped to the base bar."""
    start_date = contract.holdout.start_date(contract.cutoff_date)
    dt = datetime(start_date.year, start_date.month, start_date.day, tzinfo=UTC)
    return floor_to_timeframe(dt, contract.base_timeframe)


def split_by_holdout(
    df: pl.DataFrame,
    holdout_start: datetime,
    *,
    time_col: str = "open_time",
) -> ChronoSplit:
    """Partition ``df`` into development (< holdout_start) and holdout (>=)."""
    if holdout_start.tzinfo is None:
        holdout_start = holdout_start.replace(tzinfo=UTC)
    development = df.filter(pl.col(time_col) < holdout_start).sort(time_col)
    holdout = df.filter(pl.col(time_col) >= holdout_start).sort(time_col)
    return ChronoSplit(development=development, holdout=holdout, holdout_start=holdout_start)


def tag_holdout(
    df: pl.DataFrame,
    holdout_start: datetime,
    *,
    time_col: str = "open_time",
) -> pl.DataFrame:
    """Return ``df`` with a boolean ``is_holdout`` column."""
    if holdout_start.tzinfo is None:
        holdout_start = holdout_start.replace(tzinfo=UTC)
    return df.with_columns((pl.col(time_col) >= holdout_start).alias("is_holdout"))
