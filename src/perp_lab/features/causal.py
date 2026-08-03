"""Causal feature construction from OHLCV klines.

Design rules (enforced by tests in ``tests/unit/test_features_causal.py``):

* **No look-ahead.** Every column at row *t* depends only on rows ``<= t``.
  Rolling windows use ``min_samples == window`` (deterministic warm-up nulls)
  and are never centred; differences use ``shift(1)`` (the past).
* **Contextual features are lagged.** ``taker_buy_imbalance`` is only known once
  a bar has closed, so it is shifted by ``lag`` (>= 1) before it can inform a
  decision. Moving averages and returns are computed from closes and are used to
  form a signal at the close of bar *t*; the *execution* delay to the open of
  *t+1* is applied by the backtester, not by an extra feature shift.
* **Holdout isolation.** When ``holdout_start`` is provided, a guard raises if
  any input row is on or after the holdout boundary.
"""

from __future__ import annotations

from datetime import datetime

import polars as pl

from perp_lab.eda.datasets import assert_no_holdout

# Columns the feature engine reads. ``taker_buy_quote``/``quote_volume`` are only
# needed for the contextual order-flow feature.
FEATURE_INPUT_COLUMNS: tuple[str, ...] = (
    "open_time",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "quote_volume",
    "taker_buy_quote",
)


def _require_columns(df: pl.DataFrame, columns: tuple[str, ...]) -> None:
    missing = [c for c in columns if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required input columns: {missing}")


def add_log_return(
    df: pl.DataFrame, *, price_col: str = "close", out_col: str = "log_return"
) -> pl.DataFrame:
    """Append 1-bar log return ``ln(P_t / P_{t-1})`` (causal; warm-up null)."""
    return df.with_columns(
        (pl.col(price_col).log() - pl.col(price_col).log().shift(1)).alias(out_col)
    )


def add_momentum(
    df: pl.DataFrame, window: int, *, price_col: str = "close", out_col: str | None = None
) -> pl.DataFrame:
    """Append medium-horizon momentum ``ln(P_t / P_{t-w})`` (causal; warm-up null)."""
    name = out_col or f"momentum_{window}"
    return df.with_columns(
        (pl.col(price_col).log() - pl.col(price_col).log().shift(window)).alias(name)
    )


def add_relative_volume(
    df: pl.DataFrame, window: int, *, vol_col: str = "volume", out_col: str | None = None
) -> pl.DataFrame:
    """Append relative volume ``volume / rolling_mean(volume, w)`` (causal).

    The rolling mean uses ``min_samples == window``; a zero average maps to null
    (never an infinity).
    """
    name = out_col or f"rel_volume_{window}"
    avg = pl.col(vol_col).rolling_mean(window_size=window, min_samples=window)
    expr = pl.when(avg > 0).then(pl.col(vol_col) / avg).otherwise(None)
    return df.with_columns(expr.alias(name))


def add_moving_averages(
    df: pl.DataFrame, windows: tuple[int, ...], *, price_col: str = "close"
) -> pl.DataFrame:
    """Append simple moving averages ``sma_{w}`` for each window (causal)."""
    exprs = [
        pl.col(price_col).rolling_mean(window_size=w, min_samples=w).alias(f"sma_{w}")
        for w in windows
    ]
    return df.with_columns(exprs)


def add_atr(df: pl.DataFrame, window: int, *, out_col: str | None = None) -> pl.DataFrame:
    """Append Average True Range (rolling mean of true range, causal).

    True range uses the current bar's high/low and the *previous* close, so it
    is available at the current bar's close.
    """
    name = out_col or f"atr_{window}"
    prev_close = pl.col("close").shift(1)
    true_range = pl.max_horizontal(
        pl.col("high") - pl.col("low"),
        (pl.col("high") - prev_close).abs(),
        (pl.col("low") - prev_close).abs(),
    )
    return df.with_columns(
        true_range.rolling_mean(window_size=window, min_samples=window).alias(name)
    )


def add_rolling_volatility(
    df: pl.DataFrame, window: int, *, ret_col: str = "log_return", out_col: str | None = None
) -> pl.DataFrame:
    """Append rolling standard deviation of returns ``rvol_{w}`` (causal)."""
    name = out_col or f"rvol_{window}"
    return df.with_columns(
        pl.col(ret_col).rolling_std(window_size=window, min_samples=window).alias(name)
    )


def add_taker_buy_imbalance(
    df: pl.DataFrame, *, lag: int = 1, out_col: str = "taker_buy_imbalance"
) -> pl.DataFrame:
    """Append a **lagged** taker-buy imbalance in ``[-1, 1]`` (contextual).

    ``imbalance = 2 * taker_buy_quote / quote_volume - 1``. A zero quote volume
    maps to null (never an infinity). The series is shifted by ``lag`` (>= 1)
    because it is only known once the bar has closed.
    """
    if lag < 1:
        raise ValueError("taker-buy imbalance lag must be >= 1 (contextual feature).")
    ratio = (
        pl.when(pl.col("quote_volume") > 0)
        .then(pl.col("taker_buy_quote") / pl.col("quote_volume"))
        .otherwise(None)
    )
    return df.with_columns((2.0 * ratio - 1.0).shift(lag).alias(out_col))


def build_features(
    df: pl.DataFrame,
    *,
    ma_windows: tuple[int, ...] = (24, 96),
    momentum_window: int = 24,
    atr_window: int = 24,
    vol_window: int = 96,
    relvol_window: int = 24,
    context_lag: int = 1,
    holdout_start: datetime | None = None,
    time_col: str = "open_time",
) -> pl.DataFrame:
    """Build the initial causal feature frame for a single symbol/timeframe.

    Parameters mirror ``configs/experiment.yaml`` defaults for a momentum
    baseline. The result is sorted by ``time_col`` and contains the input
    columns plus the small justified causal set: ``log_return``,
    ``momentum_{momentum_window}``, ``sma_{w}`` (per ``ma_windows``),
    ``rvol_{vol_window}``, ``atr_{atr_window}``, ``rel_volume_{relvol_window}``
    and a **lagged** ``taker_buy_imbalance`` (contextual). All are causal and,
    for contextual inputs, shifted; the next-bar execution delay is added by the
    backtester.
    """
    _require_columns(df, FEATURE_INPUT_COLUMNS)
    if holdout_start is not None:
        assert_no_holdout(df, holdout_start, time_col=time_col)

    out = df.sort(time_col)
    out = add_log_return(out)
    out = add_momentum(out, momentum_window)
    out = add_moving_averages(out, ma_windows)
    out = add_rolling_volatility(out, vol_window)
    out = add_atr(out, atr_window)
    out = add_relative_volume(out, relvol_window)
    out = add_taker_buy_imbalance(out, lag=context_lag)
    return out


def feature_metadata(
    *,
    ma_windows: tuple[int, ...] = (24, 96),
    momentum_window: int = 24,
    atr_window: int = 24,
    vol_window: int = 96,
    relvol_window: int = 24,
    context_lag: int = 1,
) -> list[dict[str, object]]:
    """Describe the features produced by :func:`build_features` (for run records).

    Each entry documents the column name, formula, lookback, availability, the
    required shift and the missing-value policy, so a run's ``feature_metadata``
    artifact is self-describing and matches the feature catalogue.
    """
    meta: list[dict[str, object]] = [
        {
            "name": "log_return",
            "formula": "ln(close_t / close_{t-1})",
            "lookback": 1,
            "availability": "close t",
            "shift": 0,
            "missing_policy": "warm-up null",
        },
        {
            "name": f"momentum_{momentum_window}",
            "formula": "ln(close_t / close_{t-w})",
            "lookback": momentum_window,
            "availability": "close t",
            "shift": 0,
            "missing_policy": "warm-up null",
        },
    ]
    meta += [
        {
            "name": f"sma_{w}",
            "formula": "rolling mean(close, w)",
            "lookback": w,
            "availability": "close t",
            "shift": 0,
            "missing_policy": "warm-up null",
        }
        for w in ma_windows
    ]
    meta += [
        {
            "name": f"rvol_{vol_window}",
            "formula": "rolling std(log_return, w)",
            "lookback": vol_window,
            "availability": "close t",
            "shift": 0,
            "missing_policy": "warm-up null",
        },
        {
            "name": f"atr_{atr_window}",
            "formula": "rolling mean(true_range, w)",
            "lookback": atr_window,
            "availability": "close t",
            "shift": 0,
            "missing_policy": "warm-up null",
        },
        {
            "name": f"rel_volume_{relvol_window}",
            "formula": "volume / rolling_mean(volume, w)",
            "lookback": relvol_window,
            "availability": "close t",
            "shift": 0,
            "missing_policy": "warm-up null; mean=0 -> null",
        },
        {
            "name": "taker_buy_imbalance",
            "formula": "2*(taker_buy_quote/quote_volume) - 1, lagged",
            "lookback": 1,
            "availability": "close t (contextual)",
            "shift": context_lag,
            "missing_policy": "denom=0 -> null (no inf); lag warm-up null",
        },
    ]
    return meta
