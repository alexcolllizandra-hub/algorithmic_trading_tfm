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


def hurst_rs(values: np.ndarray, *, min_chunk: int = 16, n_scales: int = 12) -> float:
    """Hurst exponent via rescaled-range (R/S) analysis.

    The series is split into non-overlapping chunks at each scale; the slope of
    log(mean R/S) against log(scale) is the Hurst exponent. 0.5 is a memoryless
    process, above persistence, below anti-persistence.
    """
    arr = np.asarray(values, dtype=float)
    arr = arr[np.isfinite(arr)]
    n = arr.size
    if n < 4 * min_chunk:
        raise ValueError("Series too short for R/S analysis.")
    scales = np.unique(np.logspace(np.log10(min_chunk), np.log10(n // 4), n_scales).astype(int))
    log_scale, log_rs = [], []
    for s in scales:
        chunks = arr[: (n // s) * s].reshape(-1, s)
        centered = chunks - chunks.mean(axis=1, keepdims=True)
        z = np.cumsum(centered, axis=1)
        r = z.max(axis=1) - z.min(axis=1)
        sd = chunks.std(axis=1, ddof=1)
        valid = sd > 0
        if not valid.any():
            continue
        log_scale.append(np.log(s))
        log_rs.append(np.log((r[valid] / sd[valid]).mean()))
    slope = np.polyfit(log_scale, log_rs, 1)[0]
    return float(slope)


def rolling_hurst(
    df: pl.DataFrame,
    col: str = "log_return",
    *,
    window: int = 4320,
    step: int = 168,
    time_col: str = "open_time",
) -> pl.DataFrame:
    """Hurst exponent over a rolling window (default 180 days of 1h bars, weekly step)."""
    values = df.select(pl.col(col)).to_series().to_numpy()
    times = df.select(pl.col(time_col)).to_series().to_list()
    rows = []
    for end in range(window, len(values) + 1, step):
        chunk = values[end - window : end]
        chunk = chunk[np.isfinite(chunk)]
        if chunk.size < window // 2:
            continue
        rows.append({"time": times[end - 1], "hurst": hurst_rs(chunk)})
    return pl.DataFrame(rows)


def variance_ratio(values: np.ndarray, q: int) -> dict[str, float]:
    """Lo-MacKinlay variance ratio at horizon ``q`` with the robust z-statistic.

    VR(q) compares the variance of overlapping q-period returns against q times
    the one-period variance; under a random walk VR = 1. ``z_robust`` is the
    heteroskedasticity-consistent statistic (Lo & MacKinlay 1988, M2), the one
    that stays valid under the volatility clustering this data exhibits.
    """
    x = np.asarray(values, dtype=float)
    x = x[np.isfinite(x)]
    n = x.size
    if n <= q + 1:
        raise ValueError("Series too short for this horizon.")
    mu = x.mean()
    dev = x - mu
    var_1 = float(np.sum(dev**2)) / (n - 1)
    # Overlapping q-period sums, unbiased normalisation (Lo-MacKinlay eq. 12).
    q_sums = np.convolve(x, np.ones(q), mode="valid") - q * mu
    # The q factor is inside m (Lo-MacKinlay eq. 12), so VR = var_q / var_1.
    m = q * (n - q + 1) * (1 - q / n)
    var_q = float(np.sum(q_sums**2)) / m
    vr = var_q / var_1

    # Heteroskedasticity-robust asymptotic variance of VR(q).
    theta = 0.0
    denom = float(np.sum(dev**2)) ** 2
    for j in range(1, q):
        delta = n * float(np.sum(dev[j:] ** 2 * dev[:-j] ** 2)) / denom
        theta += (2 * (q - j) / q) ** 2 * delta
    z = (vr - 1.0) / np.sqrt(theta / n) if theta > 0 else np.nan
    return {"q": float(q), "vr": float(vr), "z_robust": float(z), "n": float(n)}


def variance_ratio_profile(values: np.ndarray, horizons: list[int]) -> pl.DataFrame:
    """Variance-ratio statistics over a list of horizons, as a tidy frame."""
    return pl.DataFrame([variance_ratio(values, q) for q in horizons])


def leverage_effect(
    df: pl.DataFrame,
    col: str = "log_return",
    *,
    forward_bars: int = 24,
) -> dict[str, float]:
    """Correlation between the return at t and realized volatility over t+1..t+h.

    In equities this is reliably negative (the "leverage effect"); the crypto
    literature reports it weak or inverted, which is why the chapter treats the
    sign as an empirical question rather than an assumption.
    """
    r = df.select(pl.col(col)).to_series().to_numpy()
    r = np.where(np.isfinite(r), r, 0.0)
    sq = r**2
    # Forward realized volatility: sqrt of the sum of squared returns over the
    # next ``forward_bars`` bars, excluding t itself.
    csum = np.concatenate([[0.0], np.cumsum(sq)])
    fwd = csum[1 + forward_bars :] - csum[1:-forward_bars]
    fwd_vol = np.sqrt(fwd)
    now = r[: fwd_vol.size]
    valid = np.isfinite(now) & np.isfinite(fwd_vol)
    corr = float(np.corrcoef(now[valid], fwd_vol[valid])[0, 1])
    return {"corr": corr, "forward_bars": float(forward_bars), "n": float(valid.sum())}
