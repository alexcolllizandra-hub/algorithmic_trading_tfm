"""Intraday / weekly seasonality and funding-rate summaries."""

from __future__ import annotations

import polars as pl


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
