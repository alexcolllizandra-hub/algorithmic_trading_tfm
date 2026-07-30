"""Volatility estimators."""

from __future__ import annotations

import polars as pl

from perp_lab.eda.returns import annualization_factor


def rolling_volatility(
    df: pl.DataFrame,
    window: int,
    ret_col: str = "log_return",
    out_col: str | None = None,
) -> pl.DataFrame:
    """Append rolling standard deviation of returns over ``window`` bars."""
    out_col = out_col or f"rolling_vol_{window}"
    return df.with_columns(
        pl.col(ret_col).rolling_std(window_size=window, min_samples=window).alias(out_col)
    )


def realized_volatility(
    df: pl.DataFrame,
    window: int,
    ret_col: str = "log_return",
    out_col: str | None = None,
) -> pl.DataFrame:
    """Append realised volatility: sqrt of the rolling sum of squared returns."""
    out_col = out_col or f"realized_vol_{window}"
    return df.with_columns(
        (pl.col(ret_col).pow(2).rolling_sum(window_size=window, min_samples=window))
        .sqrt()
        .alias(out_col)
    )


def annualized_volatility(
    df: pl.DataFrame,
    timeframe: str,
    window: int,
    ret_col: str = "log_return",
    days_per_year: int = 365,
    out_col: str | None = None,
) -> pl.DataFrame:
    """Append annualised rolling volatility (24/7 convention)."""
    out_col = out_col or f"ann_vol_{window}"
    factor = annualization_factor(timeframe, days_per_year)
    return df.with_columns(
        (pl.col(ret_col).rolling_std(window_size=window, min_samples=window) * factor).alias(
            out_col
        )
    )
