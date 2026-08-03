"""Intraday / weekly seasonality and funding-rate summaries."""

from __future__ import annotations

from typing import Any

import polars as pl
from scipy import stats

_PART_EXPR = {
    "hour": lambda tc: pl.col(tc).dt.hour(),
    "weekday": lambda tc: pl.col(tc).dt.weekday(),
}


def seasonality_kruskal(
    df: pl.DataFrame,
    value_col: str,
    by: str = "hour",
    time_col: str = "open_time",
) -> dict[str, float]:
    """Kruskal-Wallis test of whether ``value_col`` differs across groups.

    Non-parametric (rank-based), so robust to the heavy-tailed returns here.
    ``by`` is ``"hour"`` or ``"weekday"``. Reports the H statistic, p-value,
    the number of groups and the total sample size. A small p-value indicates
    the group distributions are not all equal; it says nothing about economic
    magnitude or causality.
    """
    if by not in _PART_EXPR:
        raise ValueError(f"Unknown seasonality dimension {by!r}; use 'hour' or 'weekday'.")
    tagged = df.with_columns(_PART_EXPR[by](time_col).alias(by)).select(by, value_col).drop_nulls()
    groups = [g[value_col].to_numpy() for _, g in tagged.group_by(by, maintain_order=True)]
    groups = [g for g in groups if g.size > 0]
    if len(groups) < 2:
        return {}
    res: Any = stats.kruskal(*groups)
    return {
        "H": float(res.statistic),
        "pvalue": float(res.pvalue),
        "n_groups": float(len(groups)),
        "n": float(tagged.height),
    }


def seasonality_stats(
    df: pl.DataFrame,
    value_col: str,
    by: str = "hour",
    time_col: str = "open_time",
) -> pl.DataFrame:
    """Grouped mean with count and standard error for a seasonality dimension.

    ``by`` is ``"hour"`` (UTC hour 0-23) or ``"weekday"`` (ISO 1-7). The
    standard error ``std / sqrt(n)`` supports uncertainty bands; do not read a
    seasonal mean as significant without accounting for it.
    """
    if by not in _PART_EXPR:
        raise ValueError(f"Unknown seasonality dimension {by!r}; use 'hour' or 'weekday'.")
    part = _PART_EXPR[by](time_col).alias(by)
    return (
        df.with_columns(part)
        .group_by(by)
        .agg(
            pl.len().alias("count"),
            pl.col(value_col).mean().alias("mean"),
            pl.col(value_col).std().alias("std"),
        )
        .with_columns((pl.col("std") / pl.col("count").sqrt()).alias("stderr"))
        .sort(by)
    )


def seasonality_by_hour(
    df: pl.DataFrame,
    value_col: str = "volume",
    time_col: str = "open_time",
    agg: str = "mean",
) -> pl.DataFrame:
    """Aggregate ``value_col`` by UTC hour of day (0-23)."""
    expr = getattr(pl.col(value_col), agg)()
    return (
        df.with_columns(pl.col(time_col).dt.hour().alias("hour"))
        .group_by("hour")
        .agg(expr.alias(value_col))
        .sort("hour")
    )


def seasonality_by_weekday(
    df: pl.DataFrame,
    value_col: str = "volume",
    time_col: str = "open_time",
    agg: str = "mean",
) -> pl.DataFrame:
    """Aggregate ``value_col`` by ISO weekday (1=Mon .. 7=Sun)."""
    expr = getattr(pl.col(value_col), agg)()
    return (
        df.with_columns(pl.col(time_col).dt.weekday().alias("weekday"))
        .group_by("weekday")
        .agg(expr.alias(value_col))
        .sort("weekday")
    )


def funding_summary(funding: pl.DataFrame, rate_col: str = "funding_rate") -> dict[str, float]:
    """Summary statistics of the funding-rate series."""
    values = funding.select(pl.col(rate_col)).drop_nulls()
    if values.height == 0:
        return {}
    stats = values.select(
        pl.col(rate_col).mean().alias("mean"),
        pl.col(rate_col).std().alias("std"),
        pl.col(rate_col).min().alias("min"),
        pl.col(rate_col).max().alias("max"),
        (pl.col(rate_col) > 0).mean().alias("share_positive"),
        pl.col(rate_col).sum().alias("cumulative"),
    ).to_dicts()[0]
    return {k: (float(v) if v is not None else float("nan")) for k, v in stats.items()}
