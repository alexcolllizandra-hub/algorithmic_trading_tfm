"""Funding-rate alignment and dynamics (leak-free).

Funding is observed on a coarse (nominal 8h) schedule. To attach it to finer
bars we use a strictly *backward* as-of join: each bar receives the most recent
funding value whose ``funding_time`` is at or before the bar's ``open_time``.
This never uses future information. Any change of direction or tolerance must
be declared explicitly by the caller.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import polars as pl
from scipy import stats


def attach_funding(
    bars: pl.DataFrame,
    funding: pl.DataFrame,
    *,
    bar_time: str = "open_time",
    funding_time: str = "funding_time",
    rate_col: str = "funding_rate",
    tolerance: str | None = None,
) -> pl.DataFrame:
    """Attach the last-known funding rate to each bar via a backward as-of join.

    Parameters
    ----------
    tolerance:
        Optional Polars duration string (e.g. ``"8h"``). When set, bars with no
        funding observation within the tolerance receive a null rate rather
        than a stale one. When ``None``, the most recent value is used
        regardless of age (still strictly backward, so leak-free).
    """
    if bars.height == 0:
        return bars.with_columns(pl.lit(None, dtype=pl.Float64).alias(rate_col))

    left = bars.sort(bar_time)
    right = funding.select(funding_time, rate_col).sort(funding_time)
    return left.join_asof(
        right,
        left_on=bar_time,
        right_on=funding_time,
        strategy="backward",
        tolerance=tolerance,
    )


def funding_dynamics(funding: pl.DataFrame, rate_col: str = "funding_rate") -> dict[str, float]:
    """Persistence and sign behaviour of the funding-rate series.

    Reports the share of positive/negative observations, the sign-change
    frequency, the mean absolute rate, the lag-1 autocorrelation (persistence)
    and the average length of consecutive same-sign runs.
    """
    values = funding.select(pl.col(rate_col)).drop_nulls().to_series().to_numpy()
    n = values.size
    if n < 3:
        return {}

    signs = np.sign(values)
    nonzero = signs[signs != 0]
    sign_changes = int(np.sum(nonzero[1:] != nonzero[:-1])) if nonzero.size > 1 else 0
    n_runs = sign_changes + 1 if nonzero.size else 0

    lag1 = float(np.corrcoef(values[1:], values[:-1])[0, 1]) if n > 2 else float("nan")

    return {
        "n": float(n),
        "share_positive": float(np.mean(values > 0)),
        "share_negative": float(np.mean(values < 0)),
        "share_zero": float(np.mean(values == 0)),
        "mean_abs_rate": float(np.mean(np.abs(values))),
        "sign_change_freq": (sign_changes / (nonzero.size - 1))
        if nonzero.size > 1
        else float("nan"),
        "avg_run_length": (nonzero.size / n_runs) if n_runs else float("nan"),
        "acf_lag1": lag1,
    }


def funding_autocorr(
    funding: pl.DataFrame, rate_col: str = "funding_rate", lags: tuple[int, ...] = (1, 3)
) -> dict[str, float]:
    """Autocorrelation of the funding series at the requested lags."""
    values = funding.select(pl.col(rate_col)).drop_nulls().to_series().to_numpy()
    out: dict[str, float] = {}
    for lag in lags:
        if values.size > lag + 1:
            out[f"acf_lag{lag}"] = float(np.corrcoef(values[lag:], values[:-lag])[0, 1])
        else:
            out[f"acf_lag{lag}"] = float("nan")
    return out


def funding_sign_runs(funding: pl.DataFrame, rate_col: str = "funding_rate") -> pl.DataFrame:
    """Length statistics of consecutive positive / negative funding runs."""
    values = funding.select(pl.col(rate_col)).drop_nulls().to_series().to_numpy()
    if values.size == 0:
        return pl.DataFrame(
            schema={
                "sign": pl.Utf8,
                "n_runs": pl.Int64,
                "mean_len": pl.Float64,
                "max_len": pl.Int64,
            }
        )
    signs = np.sign(values)
    change = np.empty(signs.size, dtype=bool)
    change[0] = True
    change[1:] = signs[1:] != signs[:-1]
    run_id = np.cumsum(change)
    frame = pl.DataFrame({"sign": signs, "run": run_id})
    runs = frame.group_by("run").agg(pl.col("sign").first().alias("sign"), pl.len().alias("length"))
    return (
        runs.filter(pl.col("sign") != 0)
        .with_columns(
            pl.when(pl.col("sign") > 0)
            .then(pl.lit("positive"))
            .otherwise(pl.lit("negative"))
            .alias("sign")
        )
        .group_by("sign")
        .agg(
            pl.len().alias("n_runs"),
            pl.col("length").mean().alias("mean_len"),
            pl.col("length").max().alias("max_len"),
        )
        .sort("sign")
    )


def funding_future_return_relation(
    bars: pl.DataFrame,
    funding: pl.DataFrame,
    *,
    horizons: tuple[int, ...] = (1, 3, 8),
    bar_time: str = "open_time",
    price_col: str = "close",
    tolerance: str | None = "8h",
) -> pl.DataFrame:
    """Leak-free relationship between funding known at ``t`` and future returns.

    Funding is attached with a strictly backward as-of join (value known at or
    before ``t``); the forward return over ``h`` bars is ``close[t+h]/close[t]-1``
    (entirely after ``t``). We report the Spearman rank correlation and sample
    size per horizon. A non-zero correlation is descriptive, not a tradable
    signal, and ignores funding costs and execution.
    """
    attached = attach_funding(bars, funding, tolerance=tolerance).sort(bar_time)
    rows: list[dict[str, object]] = []
    for h in horizons:
        d = attached.with_columns(
            (pl.col(price_col).shift(-h) / pl.col(price_col) - 1.0).alias("fwd_ret")
        ).drop_nulls(subset=["funding_rate", "fwd_ret"])
        if d.height < 10:
            rows.append({"horizon_bars": h, "n": d.height, "spearman": float("nan")})
            continue
        f = d["funding_rate"].to_numpy()
        r = d["fwd_ret"].to_numpy()
        if np.std(f) == 0 or np.std(r) == 0:  # spearman undefined for a constant series
            rows.append({"horizon_bars": h, "n": d.height, "spearman": float("nan")})
            continue
        res: Any = stats.spearmanr(f, r)
        rows.append(
            {"horizon_bars": h, "n": d.height, "spearman": round(float(res.correlation), 4)}
        )
    return pl.DataFrame(rows)


def mark_price_basis(
    klines: pl.DataFrame,
    mark: pl.DataFrame,
    *,
    time_col: str = "open_time",
    price_col: str = "close",
) -> pl.DataFrame:
    """Aligned trade-vs-mark basis time series on matched timestamps only.

    Basis is ``basis_bps = 1e4 * (trade_close - mark_close) / mark_close`` and is
    computed only where both streams share a timestamp (inner join). Missing
    mark-price timestamps are never imputed. Rows with a non-positive or null
    mark price are dropped so no infinite basis is produced. The returned frame
    carries ``open_time`` and ``basis_bps`` sorted in time.
    """
    joined = (
        klines.select(time_col, pl.col(price_col).alias("_trade"))
        .join(
            mark.select(time_col, pl.col(price_col).alias("_mark")),
            on=time_col,
            how="inner",
        )
        .drop_nulls()
        .filter(pl.col("_mark") > 0)
        .sort(time_col)
    )
    return joined.with_columns(
        (1e4 * (pl.col("_trade") - pl.col("_mark")) / pl.col("_mark")).alias("basis_bps")
    ).select(time_col, "basis_bps")


def basis_summary(
    klines: pl.DataFrame,
    mark: pl.DataFrame,
    *,
    time_col: str = "open_time",
    price_col: str = "close",
    n_expected: int | None = None,
) -> dict[str, float]:
    """Summarise the trade-vs-mark basis on the shared index (basis points).

    Reports the matched sample size, coverage against ``n_expected`` (the number
    of trade bars, when provided), mean, median, standard deviation and extreme
    quantiles of ``basis_bps``.
    """
    basis = mark_price_basis(klines, mark, time_col=time_col, price_col=price_col)
    if basis.height < 2:
        return {}
    vals = basis["basis_bps"].to_numpy()
    out = {
        "n_matched": float(vals.size),
        "mean_bps": float(np.mean(vals)),
        "median_bps": float(np.median(vals)),
        "std_bps": float(np.std(vals, ddof=1)),
        "p01_bps": float(np.quantile(vals, 0.01)),
        "p05_bps": float(np.quantile(vals, 0.05)),
        "p95_bps": float(np.quantile(vals, 0.95)),
        "p99_bps": float(np.quantile(vals, 0.99)),
    }
    if n_expected:
        out["coverage_pct"] = round(100.0 * vals.size / n_expected, 3)
    return out
