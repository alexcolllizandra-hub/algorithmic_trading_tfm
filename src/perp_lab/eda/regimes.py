"""Preliminary, descriptive market-regime tagging for the EDA.

This is exploratory characterisation (how often is the market trending vs.
ranging, calm vs. volatile), not the modelling-stage regime detector. Because
it is descriptive only, volatility terciles are computed on the full sample;
the modelling phase will use causal, past-only regime features instead.
"""

from __future__ import annotations

import polars as pl


def tag_trend_volatility_regimes(
    df: pl.DataFrame,
    *,
    trend_window: int = 96,
    vol_window: int = 96,
    price_col: str = "close",
    ret_col: str = "log_return",
    flat_band: float = 0.0,
) -> pl.DataFrame:
    """Append ``trend_regime``, ``vol_regime`` and combined ``regime`` columns.

    - trend: price relative to its ``trend_window`` moving average.
    - volatility: rolling std of returns bucketed into low/medium/high by the
      full-sample 33rd and 66th percentiles.
    """
    sma = pl.col(price_col).rolling_mean(window_size=trend_window, min_samples=trend_window)
    rolling_vol = pl.col(ret_col).rolling_std(window_size=vol_window, min_samples=vol_window)

    out = df.sort("open_time").with_columns(
        sma.alias("_sma"),
        rolling_vol.alias("_vol"),
    )

    rel = (pl.col(price_col) - pl.col("_sma")) / pl.col("_sma")
    out = out.with_columns(
        pl.when(rel > flat_band)
        .then(pl.lit("up"))
        .when(rel < -flat_band)
        .then(pl.lit("down"))
        .otherwise(pl.lit("flat"))
        .alias("trend_regime")
    )

    q33 = out.select(pl.col("_vol").quantile(0.33)).item()
    q66 = out.select(pl.col("_vol").quantile(0.66)).item()
    out = out.with_columns(
        pl.when(pl.col("_vol").is_null())
        .then(pl.lit("unknown"))
        .when(pl.col("_vol") <= q33)
        .then(pl.lit("low"))
        .when(pl.col("_vol") <= q66)
        .then(pl.lit("medium"))
        .otherwise(pl.lit("high"))
        .alias("vol_regime")
    )

    return out.with_columns(
        pl.concat_str([pl.col("trend_regime"), pl.col("vol_regime")], separator="_").alias("regime")
    ).drop("_sma", "_vol")
