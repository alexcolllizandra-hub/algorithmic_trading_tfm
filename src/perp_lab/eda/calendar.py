"""Calendar-style monthly aggregates (returns and realised volatility).

Monthly log returns are summed within each calendar month (log-additivity) and
reported as percentages; monthly realised volatility is the standard deviation
of within-month returns, annualised with the 24/7 convention. Output is a tidy
long frame; the notebook pivots it to a year x month matrix for the heatmap.
"""

from __future__ import annotations

import numpy as np
import polars as pl

from perp_lab.eda.returns import annualization_factor


def monthly_returns(
    df: pl.DataFrame,
    *,
    ret_col: str = "log_return",
    time_col: str = "open_time",
) -> pl.DataFrame:
    """Monthly compounded return (%) from summed log returns."""
    return (
        df.with_columns(
            pl.col(time_col).dt.year().alias("year"),
            pl.col(time_col).dt.month().alias("month"),
        )
        .group_by("year", "month")
        .agg(pl.col(ret_col).sum().alias("_sum_log"), pl.len().alias("n"))
        .with_columns(((pl.col("_sum_log").exp() - 1.0) * 100.0).alias("return_pct"))
        .drop("_sum_log")
        .sort("year", "month")
    )


def monthly_volatility(
    df: pl.DataFrame,
    *,
    ret_col: str = "log_return",
    timeframe: str,
    days_per_year: int = 365,
    time_col: str = "open_time",
) -> pl.DataFrame:
    """Monthly annualised realised volatility from within-month return std."""
    factor = annualization_factor(timeframe, days_per_year)
    return (
        df.with_columns(
            pl.col(time_col).dt.year().alias("year"),
            pl.col(time_col).dt.month().alias("month"),
        )
        .group_by("year", "month")
        .agg((pl.col(ret_col).std() * factor).alias("ann_vol"), pl.len().alias("n"))
        .sort("year", "month")
    )


def to_year_month_matrix(
    monthly: pl.DataFrame, value_col: str, *, year_col: str = "year", month_col: str = "month"
) -> tuple[np.ndarray, list[int]]:
    """Pivot a monthly long frame to a ``(n_years, 12)`` matrix and the year list."""
    years = sorted(monthly[year_col].unique().to_list())
    mat = np.full((len(years), 12), np.nan)
    idx = {y: i for i, y in enumerate(years)}
    for r in monthly.iter_rows(named=True):
        mat[idx[int(r[year_col])], int(r[month_col]) - 1] = r[value_col]
    return mat, years
