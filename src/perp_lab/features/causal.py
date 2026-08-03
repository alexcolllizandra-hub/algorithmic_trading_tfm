"""Pure, causal column builders for the feature engine.

Every function here is a small, pure transform that appends one (or, for
cyclical time encodings, two) causal column(s) to a Polars frame and returns a
**new** frame (the input is never mutated in place).

Design rules (enforced by ``tests/unit/test_features_*.py``):

* **No look-ahead.** Every value at row *t* depends only on rows ``<= t``.
  Rolling windows use ``min_samples == window`` (deterministic warm-up nulls)
  and are never centred; differences use ``shift(k)`` (the past).
* **No infinities.** Every ratio guards its denominator: a non-positive or zero
  denominator maps to ``null`` rather than producing ``+/-inf``.
* **Contextual variables are lagged.** ``taker_buy_imbalance`` is only fully
  known once a bar has closed, so it is shifted by ``lag`` (>= 1) before it can
  inform a decision. Close-based indicators are formed at the close of bar *t*;
  the *execution* delay to the open of *t+1* is applied by the backtester, not
  by an extra feature shift.

Orchestration (which columns to build, holdout guard, metadata) lives in
:mod:`perp_lab.features.registry`; these builders stay dependency-light.
"""

from __future__ import annotations

import math

import polars as pl

# Columns the engine may read. ``taker_buy_quote``/``quote_volume`` are only
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


def add_log_return(
    df: pl.DataFrame, *, k: int = 1, price_col: str = "close", out_col: str = "log_return"
) -> pl.DataFrame:
    """Append ``ln(P_t / P_{t-k})`` (causal; ``k`` warm-up nulls)."""
    if k < 1:
        raise ValueError("log-return horizon k must be >= 1.")
    logp = pl.col(price_col).log()
    return df.with_columns((logp - logp.shift(k)).alias(out_col))


def add_momentum(
    df: pl.DataFrame, window: int, *, price_col: str = "close", out_col: str | None = None
) -> pl.DataFrame:
    """Append momentum ``ln(P_t / P_{t-w})`` (causal; ``w`` warm-up nulls)."""
    name = out_col or f"momentum_{window}"
    logp = pl.col(price_col).log()
    return df.with_columns((logp - logp.shift(window)).alias(name))


def add_sma(
    df: pl.DataFrame, window: int, *, price_col: str = "close", out_col: str | None = None
) -> pl.DataFrame:
    """Append a simple moving average ``sma_{w}`` (trailing mean; causal)."""
    name = out_col or f"sma_{window}"
    return df.with_columns(
        pl.col(price_col).rolling_mean(window_size=window, min_samples=window).alias(name)
    )


def add_price_distance_ma(
    df: pl.DataFrame, window: int, *, price_col: str = "close", out_col: str | None = None
) -> pl.DataFrame:
    """Append scale-free distance of price from its trailing SMA.

    ``(P_t - sma_w) / sma_w``. A non-positive moving average maps to null (no
    infinities). Warm-up is ``w - 1`` rows (the SMA warm-up).
    """
    name = out_col or f"price_dist_sma_{window}"
    sma = pl.col(price_col).rolling_mean(window_size=window, min_samples=window)
    expr = pl.when(sma > 0).then(pl.col(price_col) / sma - 1.0).otherwise(None)
    return df.with_columns(expr.alias(name))


def add_zscore(
    df: pl.DataFrame, window: int, *, price_col: str = "close", out_col: str | None = None
) -> pl.DataFrame:
    """Append the trailing price z-score ``(P_t - mean_w) / std_w`` (causal).

    A zero rolling standard deviation (a flat window) maps to null, never an
    infinity. Warm-up is ``w - 1`` rows.
    """
    name = out_col or f"zscore_{window}"
    mean = pl.col(price_col).rolling_mean(window_size=window, min_samples=window)
    std = pl.col(price_col).rolling_std(window_size=window, min_samples=window)
    expr = pl.when(std > 0).then((pl.col(price_col) - mean) / std).otherwise(None)
    return df.with_columns(expr.alias(name))


def add_rolling_volatility(
    df: pl.DataFrame, window: int, *, price_col: str = "close", out_col: str | None = None
) -> pl.DataFrame:
    """Append rolling std of 1-bar log returns ``rvol_{w}`` (causal).

    Computed directly from ``price_col`` so it does not depend on any other
    feature column. Warm-up is ``w`` rows (the first return is null).
    """
    name = out_col or f"rvol_{window}"
    ret = pl.col(price_col).log().diff()
    return df.with_columns(ret.rolling_std(window_size=window, min_samples=window).alias(name))


def add_atr(df: pl.DataFrame, window: int, *, out_col: str | None = None) -> pl.DataFrame:
    """Append the Average True Range (trailing mean of true range; causal).

    True range uses the current bar's high/low and the *previous* close, so it
    is available at the current bar's close. Warm-up is ``w - 1`` rows.
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


def add_true_range_norm(df: pl.DataFrame, *, out_col: str = "range_norm") -> pl.DataFrame:
    """Append the scale-free current-bar range ``(high - low) / close`` (causal).

    Pointwise (no warm-up). A non-positive close maps to null (no infinities).
    """
    expr = (
        pl.when(pl.col("close") > 0)
        .then((pl.col("high") - pl.col("low")) / pl.col("close"))
        .otherwise(None)
    )
    return df.with_columns(expr.alias(out_col))


def add_relative_volume(
    df: pl.DataFrame, window: int, *, vol_col: str = "volume", out_col: str | None = None
) -> pl.DataFrame:
    """Append relative volume ``volume / rolling_mean(volume, w)`` (causal).

    A non-positive rolling average maps to null (never an infinity). Warm-up is
    ``w - 1`` rows.
    """
    name = out_col or f"rel_volume_{window}"
    avg = pl.col(vol_col).rolling_mean(window_size=window, min_samples=window)
    expr = pl.when(avg > 0).then(pl.col(vol_col) / avg).otherwise(None)
    return df.with_columns(expr.alias(name))


def add_volume_zscore(
    df: pl.DataFrame, window: int, *, vol_col: str = "volume", out_col: str | None = None
) -> pl.DataFrame:
    """Append the trailing volume z-score ``(v_t - mean_w) / std_w`` (causal).

    A zero rolling standard deviation maps to null (no infinities). Warm-up is
    ``w - 1`` rows.
    """
    name = out_col or f"volume_zscore_{window}"
    mean = pl.col(vol_col).rolling_mean(window_size=window, min_samples=window)
    std = pl.col(vol_col).rolling_std(window_size=window, min_samples=window)
    expr = pl.when(std > 0).then((pl.col(vol_col) - mean) / std).otherwise(None)
    return df.with_columns(expr.alias(name))


def add_cyclical_time(df: pl.DataFrame, unit: str, *, time_col: str = "open_time") -> pl.DataFrame:
    """Append sine/cosine encodings of a calendar clock (known ex-ante; no lag).

    ``unit`` is ``"hour"`` (period 24) or ``"dow"`` (day of week, period 7).
    These depend only on the bar's own timestamp, which is known in advance, so
    no shift is required and there is no warm-up.
    """
    if unit == "hour":
        raw = pl.col(time_col).dt.hour().cast(pl.Float64)
        period, prefix = 24.0, "hour"
    elif unit == "dow":
        raw = (pl.col(time_col).dt.weekday() - 1).cast(pl.Float64)
        period, prefix = 7.0, "dow"
    else:
        raise ValueError("cyclical time unit must be 'hour' or 'dow'.")
    angle = raw * (2.0 * math.pi / period)
    return df.with_columns(
        angle.sin().alias(f"{prefix}_sin"),
        angle.cos().alias(f"{prefix}_cos"),
    )


def add_taker_buy_imbalance(
    df: pl.DataFrame, *, lag: int = 1, out_col: str = "taker_buy_imbalance"
) -> pl.DataFrame:
    """Append a **lagged** taker-buy imbalance in ``[-1, 1]`` (contextual).

    ``imbalance = 2 * taker_buy_quote / quote_volume - 1``. A non-positive quote
    volume maps to null (never an infinity). The series is shifted by ``lag``
    (>= 1) because it is only known once the bar has closed.
    """
    if lag < 1:
        raise ValueError("taker-buy imbalance lag must be >= 1 (contextual feature).")
    ratio = (
        pl.when(pl.col("quote_volume") > 0)
        .then(pl.col("taker_buy_quote") / pl.col("quote_volume"))
        .otherwise(None)
    )
    return df.with_columns((2.0 * ratio - 1.0).shift(lag).alias(out_col))
