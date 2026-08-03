"""Volatility estimators."""

from __future__ import annotations

import math

import polars as pl

from perp_lab.eda.returns import annualization_factor

_ONE_OVER_4LN2 = 1.0 / (4.0 * math.log(2.0))
_GK_C = 2.0 * math.log(2.0) - 1.0


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


def parkinson_volatility(
    df: pl.DataFrame,
    window: int,
    high_col: str = "high",
    low_col: str = "low",
    out_col: str | None = None,
) -> pl.DataFrame:
    """Append the Parkinson (high-low range) realised-volatility estimator.

    ``sigma = sqrt( (1 / 4 ln2) * mean( ln(H/L)^2 ) )`` over ``window`` bars.
    More efficient than close-to-close when intrabar range is informative; it
    assumes continuous trading and ignores overnight/opening gaps.
    """
    out_col = out_col or f"parkinson_vol_{window}"
    term = (_ONE_OVER_4LN2 * (pl.col(high_col) / pl.col(low_col)).log().pow(2)).alias("_pk")
    return (
        df.with_columns(term)
        .with_columns(
            pl.col("_pk").rolling_mean(window_size=window, min_samples=window).sqrt().alias(out_col)
        )
        .drop("_pk")
    )


def garman_klass_volatility(
    df: pl.DataFrame,
    window: int,
    open_col: str = "open",
    high_col: str = "high",
    low_col: str = "low",
    close_col: str = "close",
    out_col: str | None = None,
) -> pl.DataFrame:
    """Append the Garman-Klass OHLC realised-volatility estimator.

    ``sigma^2 = mean( 0.5 ln(H/L)^2 - (2 ln2 - 1) ln(C/O)^2 )`` over ``window``.
    Uses the full OHLC bar and is more efficient than close-to-close when bars
    are well formed.
    """
    out_col = out_col or f"garman_klass_vol_{window}"
    hl = (pl.col(high_col) / pl.col(low_col)).log().pow(2)
    co = (pl.col(close_col) / pl.col(open_col)).log().pow(2)
    term = (0.5 * hl - _GK_C * co).alias("_gk")
    return (
        df.with_columns(term)
        .with_columns(
            pl.col("_gk")
            .rolling_mean(window_size=window, min_samples=window)
            .clip(lower_bound=0.0)
            .sqrt()
            .alias(out_col)
        )
        .drop("_gk")
    )
