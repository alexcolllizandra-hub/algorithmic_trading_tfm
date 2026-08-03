"""Leakage and determinism tests for the causal feature engine."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import numpy as np
import polars as pl
import pytest

from perp_lab.eda.datasets import HoldoutLeakageError
from perp_lab.features.causal import add_taker_buy_imbalance, build_features


def _klines(n: int = 40, *, start: datetime | None = None) -> pl.DataFrame:
    start = start or datetime(2021, 1, 1, tzinfo=UTC)
    times = [start + timedelta(hours=i) for i in range(n)]
    close = [100.0 + i for i in range(n)]
    open_ = [c - 0.5 for c in close]
    high = [c + 1.0 for c in close]
    low = [c - 1.0 for c in close]
    volume = [1000.0 + 10 * i for i in range(n)]
    quote = [v * c for v, c in zip(volume, close, strict=False)]
    taker_q = [0.6 * q for q in quote]
    return pl.DataFrame(
        {
            "open_time": times,
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
            "quote_volume": quote,
            "taker_buy_base": [0.6 * v for v in volume],
            "taker_buy_quote": taker_q,
        }
    )


_FEATURE_COLS = [
    "log_return",
    "momentum_3",
    "sma_2",
    "sma_3",
    "rvol_2",
    "atr_2",
    "rel_volume_3",
    "taker_buy_imbalance",
]


def _build(df: pl.DataFrame) -> pl.DataFrame:
    return build_features(
        df,
        ma_windows=(2, 3),
        momentum_window=3,
        atr_window=2,
        vol_window=2,
        relvol_window=3,
        context_lag=1,
    )


def test_future_rows_do_not_change_past_feature_values() -> None:
    df = _klines(40)
    full = _build(df)
    for k in (5, 10, 25):
        truncated = _build(df.head(k))
        # First k rows of the full computation must equal the truncated build.
        assert full.head(k).select(_FEATURE_COLS).equals(truncated.select(_FEATURE_COLS))


def test_rolling_uses_only_available_information() -> None:
    df = _klines(10)
    feats = _build(df)
    sma2 = feats["sma_2"].to_list()
    closes = df["close"].to_list()
    assert sma2[0] is None  # warm-up
    assert sma2[1] == pytest.approx((closes[0] + closes[1]) / 2)
    assert sma2[2] == pytest.approx((closes[1] + closes[2]) / 2)


def test_contextual_feature_is_shifted() -> None:
    df = _klines(6)
    feats = _build(df)
    # imbalance is constant 0.2 (0.6 taker ratio -> 2*0.6-1) but LAGGED by 1 bar,
    # so the first row must be null (no prior bar to borrow from).
    imb = feats["taker_buy_imbalance"].to_list()
    assert imb[0] is None
    assert imb[1] == pytest.approx(0.2)


def test_zero_quote_volume_is_null_not_infinite() -> None:
    df = _klines(4).with_columns(
        pl.when(pl.arange(0, 4) == 1)
        .then(0.0)
        .otherwise(pl.col("quote_volume"))
        .alias("quote_volume")
    )
    out = add_taker_buy_imbalance(df, lag=1)
    values = out["taker_buy_imbalance"].to_list()
    # The zero-volume bar (index 1) yields a null raw imbalance; after the 1-bar
    # lag it surfaces at index 2. No value is ever an infinity.
    assert values[2] is None
    assert all(v is None or abs(v) <= 1.0 for v in values)


def test_lag_below_one_is_rejected() -> None:
    with pytest.raises(ValueError, match="lag must be >= 1"):
        add_taker_buy_imbalance(_klines(4), lag=0)


def test_holdout_guard_blocks_future_timestamps() -> None:
    # 40 hourly bars from 2025-12-31 00:00 UTC cross into 2026 (the holdout).
    df = _klines(40, start=datetime(2025, 12, 31, tzinfo=UTC))
    holdout_start = datetime(2026, 1, 1, tzinfo=UTC)
    with pytest.raises(HoldoutLeakageError):
        build_features(df, ma_windows=(2, 3), holdout_start=holdout_start)


def test_warmup_nulls_are_deterministic() -> None:
    df = _klines(20)
    first = _build(df)
    second = _build(df)
    assert first.select(_FEATURE_COLS).equals(second.select(_FEATURE_COLS))
    # sma_3 needs 3 observations: first two rows null.
    assert first["sma_3"].to_list()[:2] == [None, None]


def test_missing_columns_raise() -> None:
    df = _klines(5).drop("taker_buy_quote")
    with pytest.raises(ValueError, match="Missing required input columns"):
        _build(df)


def test_no_infinities_even_with_zero_volume() -> None:
    df = _klines(20).with_columns(
        pl.when(pl.arange(0, 20) % 5 == 0).then(0.0).otherwise(pl.col("volume")).alias("volume"),
        pl.when(pl.arange(0, 20) % 5 == 0)
        .then(0.0)
        .otherwise(pl.col("quote_volume"))
        .alias("quote_volume"),
    )
    feats = _build(df)
    for col in ("rel_volume_3", "taker_buy_imbalance", "log_return", "rvol_2"):
        values = feats[col].to_numpy()
        assert not np.isinf(values[~np.isnan(values)]).any()


def test_timestamp_and_row_alignment_preserved() -> None:
    df = _klines(30)
    feats = _build(df)
    assert feats.height == df.height
    assert feats["open_time"].to_list() == df.sort("open_time")["open_time"].to_list()
