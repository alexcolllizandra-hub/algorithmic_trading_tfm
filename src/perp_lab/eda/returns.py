"""Return construction and distributional statistics."""

from __future__ import annotations

from typing import Any

import numpy as np
import polars as pl
from scipy import stats

from perp_lab.utils.timeutils import TIMEFRAME_TO_MS

_MS_PER_YEAR_365 = 365 * 24 * 60 * 60 * 1000


def add_log_returns(
    df: pl.DataFrame, price_col: str = "close", out_col: str = "log_return"
) -> pl.DataFrame:
    """Append log returns ``ln(P_t / P_{t-1})``."""
    return df.with_columns(
        (pl.col(price_col).log() - pl.col(price_col).log().shift(1)).alias(out_col)
    )


def add_simple_returns(
    df: pl.DataFrame, price_col: str = "close", out_col: str = "simple_return"
) -> pl.DataFrame:
    """Append simple returns ``P_t / P_{t-1} - 1``."""
    return df.with_columns((pl.col(price_col) / pl.col(price_col).shift(1) - 1).alias(out_col))


def annualization_factor(timeframe: str, days_per_year: int = 365) -> float:
    """Volatility scaling factor ``sqrt(bars_per_year)`` for a 24/7 market."""
    step_ms = TIMEFRAME_TO_MS[timeframe]
    bars_per_year = (days_per_year / 365) * _MS_PER_YEAR_365 / step_ms
    return float(np.sqrt(bars_per_year))


def return_stats(df: pl.DataFrame, col: str = "log_return") -> dict[str, float]:
    """Distributional statistics of a return series (nulls dropped)."""
    values = df.select(pl.col(col)).drop_nulls().to_series().to_numpy()
    if values.size == 0:
        return {}
    jb: Any = stats.jarque_bera(values)
    jb_stat = float(jb.statistic)
    jb_p = float(jb.pvalue)
    return {
        "n": float(values.size),
        "mean": float(np.mean(values)),
        "std": float(np.std(values, ddof=1)),
        "skew": float(stats.skew(values)),
        "excess_kurtosis": float(stats.kurtosis(values, fisher=True)),
        "min": float(np.min(values)),
        "p01": float(np.quantile(values, 0.01)),
        "p05": float(np.quantile(values, 0.05)),
        "median": float(np.median(values)),
        "p95": float(np.quantile(values, 0.95)),
        "p99": float(np.quantile(values, 0.99)),
        "max": float(np.max(values)),
        "jarque_bera": float(jb_stat),
        "jarque_bera_pvalue": float(jb_p),
    }
