"""Causal order-flow primitives shared by the Gate S2 families.

Binance klines report ``taker_buy_quote``: the share of the bar's quote volume
that lifted the ask. The complement is quote volume that hit the bid. This gives
an **exact** aggressor side at bar granularity, which is what the Lee-Ready,
tick-rule and bulk-volume-classification literature spends its effort
*estimating*. It is not order-book flow: the canonical Cont-Kukanov-Stoikov OFI
is defined over limit-order arrivals and cancellations at the best quotes, and
those events are not in our data. Everything here is therefore **trade (taker)
imbalance**, never "OFI".

Causality contract
------------------
``docs/methodology/experimental_design.md`` freezes the rule that contemporaneous
flow variables are lagged by at least one bar and are never treated as
contemporaneously predictive. Every builder in this module therefore takes an
explicit ``lag >= 1`` and computes its window over bars ``[t-lag-w+1, t-lag]``,
strictly before the decision bar *t*. The backtester then fills at the open of
*t+1*, so two full bars separate the last observed trade from the fill.

Scale
-----
Amihud-style ratios are left in raw units (log return per unit of quote volume,
so of order 1e-10 on these instruments). Every strategy compares them against
their own trailing quantile, which is scale-free, so rescaling would only invite
a magic constant.
"""

from __future__ import annotations

import numpy as np
import polars as pl

# Raw kline columns these primitives read. Present in every processed frame.
FLOW_COLUMNS: tuple[str, ...] = ("close", "quote_volume", "taker_buy_quote")


def require_flow_columns(features: pl.DataFrame, owner: str) -> None:
    """Fail loudly when the aggressor-side columns are absent."""
    missing = [c for c in ("open_time", *FLOW_COLUMNS) if c not in features.columns]
    if missing:
        raise ValueError(
            f"{owner} requires the raw kline columns {missing}, which carry the taker "
            "aggressor side. This family cannot fall back to a price-only signal: the "
            "aggressor side is the hypothesis."
        )


def _validate(window: int, lag: int) -> None:
    if window < 1:
        raise ValueError("window must be at least one bar.")
    if lag < 1:
        raise ValueError(
            "flow lag must be >= 1 bar: taker volume is only known once the bar has "
            "closed and the frozen methodology forbids treating it as contemporaneously "
            "predictive."
        )


def flow_imbalance(window: int, lag: int) -> pl.Expr:
    """Volume-weighted signed taker imbalance over ``window`` bars, lagged.

    ``(taker_buy - taker_sell) / total`` in quote units, aggregated over the
    window **before** dividing, so a bar with negligible volume cannot swing the
    window average the way a mean of per-bar ratios would. Result lies in
    ``[-1, 1]``; a window with no traded volume yields null, never an infinity.
    """
    _validate(window, lag)
    signed = 2.0 * pl.col("taker_buy_quote") - pl.col("quote_volume")
    net = signed.rolling_sum(window_size=window, min_samples=window)
    total = pl.col("quote_volume").rolling_sum(window_size=window, min_samples=window)
    return pl.when(total > 0).then(net / total).otherwise(None).shift(lag)


def window_log_return(window: int, lag: int) -> pl.Expr:
    """Log price change over the same ``window`` bars the flow is measured on."""
    _validate(window, lag)
    log_close = pl.col("close").log()
    return (log_close - log_close.shift(window)).shift(lag)


def amihud_impact(window: int, lag: int) -> pl.Expr:
    """Amihud-style price impact: |window log return| per unit of quote volume.

    High values mark a move that happened on little traded value -- the classic
    illiquidity reading. Brauneis, Mestel, Riordan & Theissen (2021, *Journal of
    Banking & Finance* 124, 106041) benchmark low-frequency proxies against
    order-book ground truth in crypto and find Amihud among the best for
    liquidity *levels*, which is the use here.
    """
    _validate(window, lag)
    log_close = pl.col("close").log()
    move = (log_close - log_close.shift(window)).abs()
    traded = pl.col("quote_volume").rolling_sum(window_size=window, min_samples=window)
    return pl.when(traded > 0).then(move / traded).otherwise(None).shift(lag)


def trailing_upper_quantile(column: str, rank_window: int, quantile: float) -> pl.Expr:
    """Trailing quantile of ``column`` over past and current bars only."""
    if rank_window <= 1:
        raise ValueError("rank_window must exceed 1 bar for a quantile to exist.")
    if not 0.0 < quantile < 1.0:
        raise ValueError(f"quantile ({quantile}) must lie strictly inside (0, 1).")
    return pl.col(column).rolling_quantile(
        quantile=quantile, window_size=rank_window, min_samples=rank_window
    )


def finite(*arrays: np.ndarray) -> np.ndarray:
    """Boolean mask that is True where every input is finite."""
    mask = np.ones(arrays[0].shape[0], dtype=bool)
    for array in arrays:
        mask &= np.isfinite(array)
    return mask


def as_float(frame: pl.DataFrame, column: str) -> np.ndarray:
    """Column as a float array with nulls mapped to NaN (never silently zero)."""
    return frame[column].cast(pl.Float64).fill_null(float("nan")).to_numpy().astype(float)
