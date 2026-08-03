"""Rolling distribution moments (volatility, skewness, excess kurtosis).

Computed exactly from rolling means of powers (no sliding-window materialisation),
so it scales to the full development sample. Central moments use the population
convention; windows shorter than ``window`` yield nulls.
"""

from __future__ import annotations

import polars as pl

from perp_lab.eda.returns import annualization_factor


def rolling_moments(
    df: pl.DataFrame,
    window: int,
    *,
    ret_col: str = "log_return",
    timeframe: str | None = None,
    days_per_year: int = 365,
    time_col: str = "open_time",
) -> pl.DataFrame:
    """Append rolling volatility, skewness and excess kurtosis over ``window`` bars.

    Parameters
    ----------
    timeframe:
        When given, ``rolling_vol`` is annualised with the 24/7 factor for that
        timeframe; otherwise it is the per-bar rolling standard deviation.
    """
    out = df.sort(time_col)
    x = pl.col(ret_col)
    out = out.with_columns(
        x.rolling_mean(window_size=window, min_samples=window).alias("_e1"),
        (x**2).rolling_mean(window_size=window, min_samples=window).alias("_e2"),
        (x**3).rolling_mean(window_size=window, min_samples=window).alias("_e3"),
        (x**4).rolling_mean(window_size=window, min_samples=window).alias("_e4"),
    )
    e1, e2, e3, e4 = pl.col("_e1"), pl.col("_e2"), pl.col("_e3"), pl.col("_e4")
    var = (e2 - e1**2).clip(lower_bound=0.0)
    m3 = e3 - 3 * e1 * e2 + 2 * e1**3
    m4 = e4 - 4 * e1 * e3 + 6 * e1**2 * e2 - 3 * e1**4

    factor = annualization_factor(timeframe, days_per_year) if timeframe else 1.0
    out = out.with_columns(
        (var.sqrt() * factor).alias("rolling_vol"),
        pl.when(var > 0).then(m3 / var**1.5).otherwise(None).alias("rolling_skew"),
        pl.when(var > 0).then(m4 / var**2 - 3.0).otherwise(None).alias("rolling_kurt"),
    )
    return out.drop("_e1", "_e2", "_e3", "_e4")
