"""Engle-Granger cointegration diagnostics for the BTC-ETH pair.

Descriptive machinery for Chapter 5: whether the two log-price series share a
stationary linear combination over the development window, and how unstable
that relationship is across the frozen market-regime windows. This never
selects a trading rule; the cross-asset families of the study register their
own hypotheses separately.
"""

from __future__ import annotations

from datetime import UTC, datetime

import numpy as np
import polars as pl
from statsmodels.tsa.stattools import coint

from perp_lab.eda.regimes import MARKET_REGIMES


def engle_granger(p1: np.ndarray, p2: np.ndarray, *, trend: str = "c") -> dict[str, float]:
    """Engle-Granger two-step cointegration test on two log-price arrays.

    Returns the test statistic, its p-value and the OLS hedge ratio of the
    first series on the second. Small p-values reject "no cointegration".
    """
    a = np.asarray(p1, dtype=float)
    b = np.asarray(p2, dtype=float)
    valid = np.isfinite(a) & np.isfinite(b)
    a, b = a[valid], b[valid]
    stat, pvalue, _ = coint(a, b, trend=trend)
    slope, intercept = np.polyfit(b, a, 1)
    return {
        "stat": float(stat),
        "pvalue": float(pvalue),
        "hedge_ratio": float(slope),
        "intercept": float(intercept),
        "n": float(a.size),
    }


def engle_granger_by_regime(
    btc: pl.DataFrame,
    eth: pl.DataFrame,
    *,
    price_col: str = "close",
    time_col: str = "open_time",
) -> pl.DataFrame:
    """Engle-Granger per frozen market-regime window plus the full sample."""
    joined = (
        btc.select(pl.col(time_col), pl.col(price_col).log().alias("lp_btc"))
        .join(
            eth.select(pl.col(time_col), pl.col(price_col).log().alias("lp_eth")),
            on=time_col,
            how="inner",
        )
        .drop_nulls()
        .sort(time_col)
    )
    windows = [("full_sample", MARKET_REGIMES[0][1], MARKET_REGIMES[-1][2])] + [
        (name, start, end) for name, start, end in MARKET_REGIMES
    ]
    rows = []
    for name, start_s, end_s in windows:
        start = datetime.fromisoformat(start_s).replace(tzinfo=UTC)
        end = datetime.fromisoformat(end_s).replace(tzinfo=UTC)
        sub = joined.filter((pl.col(time_col) >= start) & (pl.col(time_col) < end))
        if sub.height < 500:
            continue
        result = engle_granger(sub["lp_btc"].to_numpy(), sub["lp_eth"].to_numpy())
        rows.append({"window": name, "start": start_s, "end": end_s, **result})
    return pl.DataFrame(rows)
