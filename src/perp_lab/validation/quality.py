"""Data-quality reporting for OHLCV klines.

Design principle: this module *reports*, it does not silently mutate data. In
particular, extreme observations are **flagged, never dropped** -- deciding
whether an extreme move is a data error or a real market event is an analysis
step, documented in the EDA.
"""

from __future__ import annotations

from datetime import datetime

import polars as pl
from pydantic import BaseModel

from perp_lab.utils.timeutils import TIMEFRAME_TO_MS, expected_bar_count


class QualityReport(BaseModel):
    """Summary of data-quality checks for a single dataset."""

    symbol: str
    timeframe: str
    row_count: int
    period_start: datetime | None
    period_end: datetime | None
    expected_bars: int
    missing_bars: int
    duplicate_timestamps: int
    is_monotonic: bool
    ohlc_violations: int
    extreme_return_flags: int
    coverage_ratio: float


def find_duplicates(df: pl.DataFrame, time_col: str = "open_time") -> pl.DataFrame:
    """Return the timestamps that appear more than once."""
    return (
        df.group_by(time_col)
        .len()
        .filter(pl.col("len") > 1)
        .rename({"len": "count"})
        .sort(time_col)
    )


def is_monotonic_increasing(df: pl.DataFrame, time_col: str = "open_time") -> bool:
    """True if timestamps are strictly increasing."""
    if df.height <= 1:
        return True
    diffs = df.select(pl.col(time_col).diff().dt.total_milliseconds()).drop_nulls()
    return bool(diffs.select((pl.col(time_col) > 0).all()).item())


def find_gaps(df: pl.DataFrame, timeframe: str, time_col: str = "open_time") -> pl.DataFrame:
    """Return rows where the gap to the previous bar exceeds one step.

    Columns: ``gap_start`` (previous bar), ``gap_end`` (next present bar) and
    ``missing`` (number of absent bars in between).
    """
    step_ms = TIMEFRAME_TO_MS[timeframe]
    if df.height <= 1:
        return pl.DataFrame(
            schema={
                "gap_start": df.schema[time_col],
                "gap_end": df.schema[time_col],
                "missing": pl.Int64,
            }
        )
    sorted_df = df.sort(time_col)
    return (
        sorted_df.select(
            pl.col(time_col).shift(1).alias("gap_start"),
            pl.col(time_col).alias("gap_end"),
            (pl.col(time_col).diff().dt.total_milliseconds() // step_ms - 1)
            .cast(pl.Int64)
            .alias("missing"),
        )
        .drop_nulls()
        .filter(pl.col("missing") > 0)
    )


def check_ohlc_consistency(df: pl.DataFrame) -> pl.DataFrame:
    """Return rows violating OHLC invariants.

    Invariants: ``high >= max(open, close, low)`` and ``low <= min(open, close, high)``.
    """
    return df.filter(
        (pl.col("high") < pl.col("low"))
        | (pl.col("high") < pl.col("open"))
        | (pl.col("high") < pl.col("close"))
        | (pl.col("low") > pl.col("open"))
        | (pl.col("low") > pl.col("close"))
    )


def flag_extreme_returns(
    df: pl.DataFrame,
    sigma: float = 10.0,
    window: int = 96,
    time_col: str = "open_time",
) -> pl.DataFrame:
    """Add ``log_return`` and boolean ``extreme`` columns (never drops rows).

    A bar is flagged when its log return exceeds ``sigma`` rolling standard
    deviations. This surfaces candidates for manual review, not for deletion.
    """
    out = df.sort(time_col).with_columns(
        (pl.col("close").log() - pl.col("close").log().shift(1)).alias("log_return")
    )
    return out.with_columns(
        (
            pl.col("log_return").abs()
            > sigma * pl.col("log_return").rolling_std(window_size=window, min_samples=window // 2)
        )
        .fill_null(False)
        .alias("extreme")
    )


def coverage_summary(
    df: pl.DataFrame,
    timeframe: str,
    start: datetime,
    end: datetime,
    time_col: str = "open_time",
) -> dict[str, float | int]:
    """Rows present vs. expected over ``[start, end)`` for a 24/7 market."""
    expected = expected_bar_count(start, end, timeframe)
    present = df.height
    return {
        "expected_bars": expected,
        "present_bars": present,
        "coverage_ratio": (present / expected) if expected else 0.0,
    }


def quality_report(
    df: pl.DataFrame,
    *,
    symbol: str,
    timeframe: str,
    start: datetime,
    end: datetime,
    extreme_sigma: float = 10.0,
    extreme_window: int = 96,
    time_col: str = "open_time",
) -> QualityReport:
    """Run every check and return a compact :class:`QualityReport`."""
    gaps = find_gaps(df, timeframe, time_col)
    missing = int(gaps.select(pl.col("missing").sum()).item() or 0) if gaps.height else 0
    dupes = find_duplicates(df, time_col)
    ohlc = check_ohlc_consistency(df)
    flagged = flag_extreme_returns(df, extreme_sigma, extreme_window, time_col)
    n_extreme = int(flagged.select(pl.col("extreme").sum()).item() or 0)
    cov = coverage_summary(df, timeframe, start, end, time_col)

    period_start = df.select(pl.col(time_col).min()).item() if df.height else None
    period_end = df.select(pl.col(time_col).max()).item() if df.height else None

    return QualityReport(
        symbol=symbol,
        timeframe=timeframe,
        row_count=df.height,
        period_start=period_start,
        period_end=period_end,
        expected_bars=int(cov["expected_bars"]),
        missing_bars=missing,
        duplicate_timestamps=dupes.height,
        is_monotonic=is_monotonic_increasing(df, time_col),
        ohlc_violations=ohlc.height,
        extreme_return_flags=n_extreme,
        coverage_ratio=float(cov["coverage_ratio"]),
    )
