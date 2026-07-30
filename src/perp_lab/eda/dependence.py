"""Temporal-dependence diagnostics: autocorrelation and Ljung-Box."""

from __future__ import annotations

import numpy as np
import polars as pl
from statsmodels.stats.diagnostic import acorr_ljungbox
from statsmodels.tsa.stattools import acf


def _clean_series(df: pl.DataFrame, col: str) -> np.ndarray:
    return df.select(pl.col(col)).drop_nulls().to_series().to_numpy()


def autocorrelation(
    df: pl.DataFrame,
    col: str = "log_return",
    max_lag: int = 100,
    transform: str = "identity",
) -> pl.DataFrame:
    """Autocorrelation function up to ``max_lag``.

    ``transform`` in {"identity", "abs", "square"} lets you probe volatility
    clustering (dependence in ``|r|`` or ``r^2``) versus linear dependence in
    raw returns.
    """
    values = _clean_series(df, col)
    if transform == "abs":
        values = np.abs(values)
    elif transform == "square":
        values = values**2
    elif transform != "identity":
        raise ValueError(f"Unknown transform {transform!r}")

    if values.size <= max_lag + 1:
        max_lag = max(1, values.size - 2)
    coeffs = np.asarray(acf(values, nlags=max_lag, fft=True))
    return pl.DataFrame({"lag": list(range(len(coeffs))), "acf": coeffs.tolist()})


def ljung_box_pvalue(
    df: pl.DataFrame, col: str = "log_return", lags: int = 20, transform: str = "identity"
) -> float:
    """Ljung-Box p-value at ``lags`` (small p => significant autocorrelation)."""
    values = _clean_series(df, col)
    if transform == "abs":
        values = np.abs(values)
    elif transform == "square":
        values = values**2
    result = acorr_ljungbox(values, lags=[lags], return_df=True)
    return float(result["lb_pvalue"].iloc[-1])
