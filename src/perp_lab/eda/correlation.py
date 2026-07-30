"""Cross-asset correlation (static and rolling)."""

from __future__ import annotations

import polars as pl


def _aligned(
    left: pl.DataFrame,
    right: pl.DataFrame,
    col: str,
    time_col: str,
    suffixes: tuple[str, str],
) -> pl.DataFrame:
    a, b = suffixes
    return (
        left.select(time_col, pl.col(col).alias(f"{col}{a}"))
        .join(right.select(time_col, pl.col(col).alias(f"{col}{b}")), on=time_col, how="inner")
        .sort(time_col)
    )


def static_correlation(
    left: pl.DataFrame,
    right: pl.DataFrame,
    col: str = "log_return",
    time_col: str = "open_time",
) -> float:
    """Pearson correlation of ``col`` between two assets on their shared index."""
    joined = _aligned(left, right, col, time_col, ("_a", "_b"))
    if joined.height < 2:
        return float("nan")
    return float(joined.select(pl.corr(f"{col}_a", f"{col}_b")).item())


def rolling_correlation(
    left: pl.DataFrame,
    right: pl.DataFrame,
    window: int,
    col: str = "log_return",
    time_col: str = "open_time",
) -> pl.DataFrame:
    """Rolling Pearson correlation of ``col`` over ``window`` bars."""
    joined = _aligned(left, right, col, time_col, ("_a", "_b"))
    return joined.with_columns(
        pl.rolling_corr(
            pl.col(f"{col}_a"), pl.col(f"{col}_b"), window_size=window, min_samples=window
        ).alias(f"rolling_corr_{window}")
    ).select(time_col, f"rolling_corr_{window}")
