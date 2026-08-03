"""Coverage and per-dataset data-quality summaries for the EDA.

These helpers wrap the primitive checks in :mod:`perp_lab.validation.quality`
into the compact, presentation-ready tables the notebook needs: a full
per-dataset quality row, a monthly coverage matrix for calendar-style heatmaps,
and a longest-gap descriptor. Everything is reported, never mutated.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import polars as pl

from perp_lab.utils.timeutils import TIMEFRAME_TO_MS, expected_bar_count
from perp_lab.validation.quality import (
    check_ohlc_consistency,
    find_duplicates,
    find_gaps,
    is_monotonic_increasing,
)

_CRITICAL = ("open", "high", "low", "close", "volume")


def longest_gap(df: pl.DataFrame, timeframe: str, time_col: str = "open_time") -> dict[str, float]:
    """Return the number, size and duration of missing-candle gaps.

    ``max_gap_bars`` is the largest number of consecutive absent bars and
    ``max_gap_hours`` the same expressed in clock time.
    """
    gaps = find_gaps(df, timeframe, time_col)
    if gaps.height == 0:
        return {"n_gaps": 0.0, "total_missing_bars": 0.0, "max_gap_bars": 0.0, "max_gap_hours": 0.0}
    missing = gaps["missing"].to_numpy()
    step_h = TIMEFRAME_TO_MS[timeframe] / 3.6e6
    return {
        "n_gaps": float(gaps.height),
        "total_missing_bars": float(missing.sum()),
        "max_gap_bars": float(missing.max()),
        "max_gap_hours": float(missing.max()) * step_h,
    }


def dataset_quality_row(
    df: pl.DataFrame,
    *,
    symbol: str,
    timeframe: str,
    time_col: str = "open_time",
) -> dict[str, object]:
    """Compute a complete data-quality row for one asset/timeframe frame.

    Reuses the primitive checks (gaps, duplicates, OHLC validity, monotonicity)
    and adds null/negative/zero-volume counts and the observed/expected span.
    """
    if df.height == 0:
        return {"symbol": symbol, "timeframe": timeframe, "observed": 0}

    start = df.select(pl.col(time_col).min()).item()
    last = df.select(pl.col(time_col).max()).item()
    end_excl = last + timedelta(milliseconds=TIMEFRAME_TO_MS[timeframe])
    expected = expected_bar_count(start, end_excl, timeframe)

    gaps = longest_gap(df, timeframe, time_col)
    invalid_ohlc = check_ohlc_consistency(df).height
    n_null = int(df.select(list(_CRITICAL)).null_count().to_numpy().sum())
    n_neg = df.filter(
        (pl.col("open") < 0)
        | (pl.col("high") < 0)
        | (pl.col("low") < 0)
        | (pl.col("close") < 0)
        | (pl.col("volume") < 0)
    ).height
    n_zero_vol = df.filter(pl.col("volume") == 0).height

    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "start": str(start),
        "end": str(last),
        "observed": df.height,
        "expected": expected,
        "coverage_pct": round(100.0 * df.height / expected, 4) if expected else 0.0,
        "missing": int(gaps["total_missing_bars"]),
        "duplicates": find_duplicates(df, time_col).height,
        "invalid_ohlc": invalid_ohlc,
        "null_critical": n_null,
        "negative_values": n_neg,
        "zero_volume": n_zero_vol,
        "longest_gap_bars": int(gaps["max_gap_bars"]),
        "monotonic": is_monotonic_increasing(df, time_col),
    }


def monthly_coverage(
    df: pl.DataFrame,
    timeframe: str,
    time_col: str = "open_time",
) -> pl.DataFrame:
    """Observed vs. expected bar counts per calendar month (for a heatmap).

    Expected counts are clipped to the actual data span at the first and last
    partial months, so a fully present month yields ``coverage = 1.0``.
    """
    if df.height == 0:
        return pl.DataFrame(
            schema={
                "year": pl.Int32,
                "month": pl.Int8,
                "observed": pl.UInt32,
                "expected": pl.Int64,
                "coverage": pl.Float64,
            }
        )

    step_ms = TIMEFRAME_TO_MS[timeframe]
    data_start: datetime = df.select(pl.col(time_col).min()).item()
    data_end_excl: datetime = df.select(pl.col(time_col).max()).item() + timedelta(
        milliseconds=step_ms
    )

    observed = (
        df.with_columns(
            pl.col(time_col).dt.year().alias("year"),
            pl.col(time_col).dt.month().alias("month"),
        )
        .group_by("year", "month")
        .agg(pl.len().alias("observed"))
    )

    rows: list[dict[str, object]] = []
    for r in observed.iter_rows(named=True):
        y, m = int(r["year"]), int(r["month"])
        month_start = datetime(y, m, 1, tzinfo=data_start.tzinfo)
        month_end = datetime(y + (m == 12), (m % 12) + 1, 1, tzinfo=data_start.tzinfo)
        lo = max(month_start, data_start)
        hi = min(month_end, data_end_excl)
        expected = expected_bar_count(lo, hi, timeframe) if hi > lo else 0
        rows.append(
            {
                "year": y,
                "month": m,
                "observed": int(r["observed"]),
                "expected": expected,
                "coverage": round(int(r["observed"]) / expected, 5) if expected else 0.0,
            }
        )
    return pl.DataFrame(rows).sort("year", "month")
