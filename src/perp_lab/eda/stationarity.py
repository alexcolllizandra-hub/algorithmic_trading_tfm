"""Stationarity and dependence diagnostic tests.

Thin, defensive wrappers around statsmodels tests that return plain dicts /
Polars frames and cope with the very large samples in this project. All tests
are computed on development data only.

Caveat carried through to the notebook: unit-root and stationarity tests are
low-powered under structural breaks and heteroskedasticity. A rejection here
does not prove stable behaviour, and a significant autocorrelation is a
statistical fact, not evidence of an economically exploitable effect.
"""

from __future__ import annotations

import warnings
from typing import Any, Literal

import numpy as np
import polars as pl
from statsmodels.stats.diagnostic import acorr_ljungbox, het_arch
from statsmodels.tsa.stattools import adfuller, kpss


def _clean(values: np.ndarray) -> np.ndarray:
    arr = np.asarray(values, dtype=float)
    return arr[np.isfinite(arr)]


def adf_test(values: np.ndarray, *, autolag: str = "AIC") -> dict[str, float]:
    """Augmented Dickey-Fuller test (null: a unit root / non-stationary)."""
    arr = _clean(values)
    if arr.size < 20:
        return {}
    res: Any = adfuller(arr, autolag=autolag)
    return {
        "stat": float(res[0]),
        "pvalue": float(res[1]),
        "usedlag": float(res[2]),
        "nobs": float(res[3]),
    }


def kpss_test(values: np.ndarray, *, regression: Literal["c", "ct"] = "c") -> dict[str, float]:
    """KPSS test (null: stationary around a constant/trend)."""
    arr = _clean(values)
    if arr.size < 20:
        return {}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # p-value interpolation warnings are expected
        res: Any = kpss(arr, regression=regression, nlags="auto")
    return {"stat": float(res[0]), "pvalue": float(res[1]), "usedlag": float(res[2])}


def arch_lm_test(values: np.ndarray, *, nlags: int = 12) -> dict[str, float]:
    """Engle's ARCH-LM test for conditional heteroskedasticity (ARCH effects)."""
    arr = _clean(values)
    if arr.size < nlags + 5:
        return {}
    res: Any = het_arch(arr, nlags=nlags)
    return {
        "lm_stat": float(res[0]),
        "lm_pvalue": float(res[1]),
        "f_stat": float(res[2]),
        "f_pvalue": float(res[3]),
    }


def ljung_box(values: np.ndarray, *, lags: int = 20) -> dict[str, float]:
    """Ljung-Box test at a single lag horizon; returns statistic and p-value."""
    arr = _clean(values)
    if arr.size < lags + 5:
        return {}
    res = acorr_ljungbox(arr, lags=[lags], return_df=True)
    return {
        "lb_stat": float(res["lb_stat"].iloc[-1]),
        "lb_pvalue": float(res["lb_pvalue"].iloc[-1]),
    }


def stationarity_report(
    df: pl.DataFrame,
    *,
    symbol: str,
    price_col: str = "close",
    ret_col: str = "log_return",
    ljung_lags: int = 20,
    arch_lags: int = 12,
) -> pl.DataFrame:
    """Compact stationarity/dependence report for one asset.

    Runs ADF and KPSS on log price and log returns, Ljung-Box on raw and
    squared returns, and ARCH-LM on returns. Returns one row per test.
    """
    log_price = df.select(pl.col(price_col).log()).drop_nulls().to_series().to_numpy()
    ret = df.select(pl.col(ret_col)).drop_nulls().to_series().to_numpy()

    adf_p = adf_test(log_price)
    adf_r = adf_test(ret)
    kpss_p = kpss_test(log_price)
    kpss_r = kpss_test(ret)
    lb_r = ljung_box(ret, lags=ljung_lags)
    lb_sq = ljung_box(ret**2, lags=ljung_lags)
    arch = arch_lm_test(ret, nlags=arch_lags)

    rows = [
        {
            "symbol": symbol,
            "test": "ADF",
            "series": "log_price",
            "statistic": adf_p.get("stat"),
            "pvalue": adf_p.get("pvalue"),
            "null": "unit root (non-stationary)",
        },
        {
            "symbol": symbol,
            "test": "ADF",
            "series": "log_return",
            "statistic": adf_r.get("stat"),
            "pvalue": adf_r.get("pvalue"),
            "null": "unit root (non-stationary)",
        },
        {
            "symbol": symbol,
            "test": "KPSS",
            "series": "log_price",
            "statistic": kpss_p.get("stat"),
            "pvalue": kpss_p.get("pvalue"),
            "null": "stationary",
        },
        {
            "symbol": symbol,
            "test": "KPSS",
            "series": "log_return",
            "statistic": kpss_r.get("stat"),
            "pvalue": kpss_r.get("pvalue"),
            "null": "stationary",
        },
        {
            "symbol": symbol,
            "test": f"Ljung-Box(l={ljung_lags})",
            "series": "log_return",
            "statistic": lb_r.get("lb_stat"),
            "pvalue": lb_r.get("lb_pvalue"),
            "null": "no autocorrelation",
        },
        {
            "symbol": symbol,
            "test": f"Ljung-Box(l={ljung_lags})",
            "series": "squared_return",
            "statistic": lb_sq.get("lb_stat"),
            "pvalue": lb_sq.get("lb_pvalue"),
            "null": "no autocorrelation",
        },
        {
            "symbol": symbol,
            "test": f"ARCH-LM(l={arch_lags})",
            "series": "log_return",
            "statistic": arch.get("lm_stat"),
            "pvalue": arch.get("lm_pvalue"),
            "null": "no ARCH effects",
        },
    ]
    return pl.DataFrame(rows)
