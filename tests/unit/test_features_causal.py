"""Causality, determinism and numerical tests for the causal feature engine.

Covers the leakage-critical invariants: truncation invariance, future-mutation
invariance, exact-once shifting, deterministic warm-up/null behaviour, absence
of infinities, safe handling of flat/zero/constant windows, alignment
preservation, input immutability, deterministic column order, multi-asset
independence, reproducibility and holdout isolation. Small hand-calculated
fixtures pin the arithmetic; deterministic edge cases complement them.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta

import numpy as np
import polars as pl
import pytest

from perp_lab.eda.datasets import HoldoutLeakageError
from perp_lab.features.registry import build_feature_frame, feature_columns
from perp_lab.features.spec import FeatureSpec, resolve_spec

# (kind, window, lag) triples covering every registered kind with small windows
# so no column is entirely warm-up on the fixtures below.
_SMALL_ITEMS: tuple[tuple[str, int | None, int | None], ...] = (
    ("log_return", None, None),
    ("momentum", 3, None),
    ("sma", 2, None),
    ("sma", 3, None),
    ("price_dist_sma", 3, None),
    ("zscore", 3, None),
    ("rvol", 3, None),
    ("atr", 2, None),
    ("range_norm", None, None),
    ("rel_volume", 3, None),
    ("volume_zscore", 3, None),
    ("hour_cyclical", None, None),
    ("dow_cyclical", None, None),
    ("taker_buy_imbalance", None, 1),
)

_EXPECTED_COLUMNS = [
    "log_return",
    "momentum_3",
    "sma_2",
    "sma_3",
    "price_dist_sma_3",
    "zscore_3",
    "rvol_3",
    "atr_2",
    "range_norm",
    "rel_volume_3",
    "volume_zscore_3",
    "hour_sin",
    "hour_cos",
    "dow_sin",
    "dow_cos",
    "taker_buy_imbalance",
]


def _specs() -> list[FeatureSpec]:
    return [resolve_spec(kind, window=w, lag=lag) for kind, w, lag in _SMALL_ITEMS]


def _klines(n: int = 40, *, start: datetime | None = None) -> pl.DataFrame:
    start = start or datetime(2021, 1, 4, tzinfo=UTC)  # a Monday, hour 0
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


def _build(df: pl.DataFrame, **kw: object) -> pl.DataFrame:
    feats, _ = build_feature_frame(df, _specs(), **kw)  # type: ignore[arg-type]
    return feats


def _leading_nulls(series: pl.Series) -> int:
    mask = series.is_null().to_list()
    count = 0
    for is_null in mask:
        if not is_null:
            break
        count += 1
    return count


# --------------------------------------------------------------------------- #
# 1 & 2: future rows / future mutations cannot change past feature values
# --------------------------------------------------------------------------- #
def test_appending_future_rows_does_not_change_past_values() -> None:
    df = _klines(40)
    full = _build(df)
    for k in (5, 12, 30):
        truncated = _build(df.head(k))
        assert full.head(k).select(_EXPECTED_COLUMNS).equals(truncated.select(_EXPECTED_COLUMNS))


def test_mutating_future_ohlcv_does_not_change_earlier_features() -> None:
    df = _klines(40)
    base = _build(df)
    cut = 20
    mutated_df = df.with_columns(
        pl.when(pl.arange(0, df.height) >= cut)
        .then(pl.col("close") * 3.0)
        .otherwise(pl.col("close"))
        .alias("close"),
        pl.when(pl.arange(0, df.height) >= cut)
        .then(pl.col("high") * 3.0)
        .otherwise(pl.col("high"))
        .alias("high"),
        pl.when(pl.arange(0, df.height) >= cut)
        .then(pl.col("volume") * 5.0)
        .otherwise(pl.col("volume"))
        .alias("volume"),
    )
    mutated = _build(mutated_df)
    assert (
        base.head(cut).select(_EXPECTED_COLUMNS).equals(mutated.head(cut).select(_EXPECTED_COLUMNS))
    )


# --------------------------------------------------------------------------- #
# 3: rolling windows never use future/centred observations (hand calculations)
# --------------------------------------------------------------------------- #
def test_rolling_and_returns_hand_calculations() -> None:
    df = _klines(6)
    feats = _build(df)
    close = df["close"].to_list()

    assert feats["sma_2"].to_list()[0] is None
    assert feats["sma_2"].to_list()[1] == pytest.approx((close[0] + close[1]) / 2)
    assert feats["sma_2"].to_list()[2] == pytest.approx((close[1] + close[2]) / 2)

    assert feats["log_return"].to_list()[0] is None
    assert feats["log_return"].to_list()[1] == pytest.approx(math.log(close[1] / close[0]))

    assert feats["momentum_3"].to_list()[3] == pytest.approx(math.log(close[3] / close[0]))

    # z-score of the linear window [100,101,102] -> (102-101)/1 = 1.0 (sample std).
    assert feats["zscore_3"].to_list()[2] == pytest.approx(1.0)

    # rvol_3: first valid at row 3 spans the returns of rows 1..3 == logret[0:3].
    logret = np.diff(np.log(np.asarray(close)))
    assert feats["rvol_3"].to_list()[3] == pytest.approx(float(np.std(logret[0:3], ddof=1)))

    # atr_2 = mean(TR0, TR1); TR0 = high0-low0 = 2.0; TR1 = max(2, |h1-c0|, |l1-c0|).
    tr0 = df["high"][0] - df["low"][0]
    tr1 = max(
        df["high"][1] - df["low"][1],
        abs(df["high"][1] - close[0]),
        abs(df["low"][1] - close[0]),
    )
    assert feats["atr_2"].to_list()[1] == pytest.approx((tr0 + tr1) / 2)


def test_cyclical_time_is_known_ex_ante() -> None:
    feats = _build(_klines(6))  # starts Monday 00:00 UTC
    assert feats["hour_sin"].to_list()[0] == pytest.approx(0.0)
    assert feats["hour_cos"].to_list()[0] == pytest.approx(1.0)
    assert feats["hour_sin"].to_list()[1] == pytest.approx(math.sin(2 * math.pi / 24))
    # Monday -> (weekday 1 - 1) = 0 -> dow_sin 0, dow_cos 1; no warm-up nulls.
    assert feats["dow_sin"].to_list()[0] == pytest.approx(0.0)
    assert feats["dow_cos"].to_list()[0] == pytest.approx(1.0)
    assert _leading_nulls(feats["hour_sin"]) == 0


# --------------------------------------------------------------------------- #
# 4: any required shift is applied exactly once
# --------------------------------------------------------------------------- #
def test_contextual_shift_applied_exactly_once() -> None:
    df = _klines(6)
    feats = _build(df)
    imb = feats["taker_buy_imbalance"].to_list()
    assert imb[0] is None  # lag 1 -> first row null
    assert imb[1] == pytest.approx(0.2)  # 2*0.6 - 1, from bar 0

    # A lag of 2 must equal the raw series shifted by exactly 2 (not 1, not 3).
    spec2 = resolve_spec("taker_buy_imbalance", lag=2)
    f2, _ = build_feature_frame(df, [spec2])
    raw = (2.0 * (df["taker_buy_quote"] / df["quote_volume"]) - 1.0).to_list()
    got = f2["taker_buy_imbalance"].to_list()
    assert got[:2] == [None, None]
    assert got[2] == pytest.approx(raw[0])
    assert got[3] == pytest.approx(raw[1])


# --------------------------------------------------------------------------- #
# 5 & 6: availability / deterministic warm-up length for every feature
# --------------------------------------------------------------------------- #
def test_declared_warmup_matches_actual_leading_nulls() -> None:
    df = _klines(30)
    specs = _specs()
    feats, _ = build_feature_frame(df, specs)
    for spec in specs:
        for col in spec.columns:
            assert _leading_nulls(feats[col]) == spec.warmup, f"{col}: warm-up mismatch"


def test_availability_metadata_is_consistent() -> None:
    for spec in _specs():
        if spec.kind == "taker_buy_imbalance":
            assert "contextual" in spec.availability
            lag_val = int(spec.params["lag"])
            assert spec.shift == lag_val >= 1
        elif spec.family == "time":
            assert "ex-ante" in spec.availability
            assert spec.shift == 0
        else:
            assert spec.availability == "close t"
            assert spec.shift == 0


# --------------------------------------------------------------------------- #
# 7 & 14: deterministic null handling and reproducibility
# --------------------------------------------------------------------------- #
def test_repeated_build_is_identical() -> None:
    df = _klines(25)
    first = _build(df)
    second = _build(df)
    assert first.equals(second)


# --------------------------------------------------------------------------- #
# 8 & 9: no infinities; flat prices / zero volume / constant windows are safe
# --------------------------------------------------------------------------- #
def test_no_infinities_with_zero_volume_and_flat_prices() -> None:
    n = 20
    times = [datetime(2021, 1, 4, tzinfo=UTC) + timedelta(hours=i) for i in range(n)]
    df = pl.DataFrame(
        {
            "open_time": times,
            "open": [100.0] * n,  # perfectly flat prices
            "high": [100.0] * n,
            "low": [100.0] * n,
            "close": [100.0] * n,
            "volume": [0.0 if i % 4 == 0 else 500.0 for i in range(n)],
            "quote_volume": [0.0 if i % 4 == 0 else 5.0e4 for i in range(n)],
            "taker_buy_base": [0.0] * n,
            "taker_buy_quote": [0.0 if i % 4 == 0 else 3.0e4 for i in range(n)],
        }
    )
    feats = _build(df)
    for col in _EXPECTED_COLUMNS:
        values = feats[col].to_numpy()
        finite = values[~np.isnan(values.astype(float))]
        assert not np.isinf(finite).any(), f"{col} produced an infinity"
    # A flat window has zero dispersion -> z-scores must be null, never +/-inf.
    assert feats["zscore_3"].drop_nulls().to_list() == []
    assert feats["volume_zscore_3"].is_infinite().sum() == 0


def test_flat_prices_give_zero_returns_and_volatility() -> None:
    n = 10
    times = [datetime(2021, 1, 4, tzinfo=UTC) + timedelta(hours=i) for i in range(n)]
    df = pl.DataFrame(
        {
            "open_time": times,
            "open": [50.0] * n,
            "high": [50.0] * n,
            "low": [50.0] * n,
            "close": [50.0] * n,
            "volume": [10.0] * n,
            "quote_volume": [500.0] * n,
            "taker_buy_base": [5.0] * n,
            "taker_buy_quote": [250.0] * n,
        }
    )
    feats, _ = build_feature_frame(df, [resolve_spec("log_return"), resolve_spec("rvol", window=3)])
    assert feats["log_return"].to_list()[1:] == pytest.approx([0.0] * (n - 1))
    assert feats["rvol_3"].to_list()[3:] == pytest.approx([0.0] * (n - 3))


# --------------------------------------------------------------------------- #
# 10 & 12: alignment, timezone and deterministic column names/order preserved
# --------------------------------------------------------------------------- #
def test_alignment_and_column_order_preserved() -> None:
    df = _klines(30)
    specs = _specs()
    feats, resolved = build_feature_frame(df, specs)
    assert feats.height == df.height
    assert feats["open_time"].to_list() == df.sort("open_time")["open_time"].to_list()
    assert feats["open_time"].dtype == df["open_time"].dtype  # tz-aware UTC preserved
    assert feature_columns(resolved) == _EXPECTED_COLUMNS
    # Feature columns appear after the inputs in the declared order.
    assert feats.columns[-len(_EXPECTED_COLUMNS) :] == _EXPECTED_COLUMNS


# --------------------------------------------------------------------------- #
# 11: input frame is not mutated in place
# --------------------------------------------------------------------------- #
def test_input_frame_not_mutated() -> None:
    df = _klines(15)
    snapshot = df.clone()
    _build(df)
    assert df.equals(snapshot)


# --------------------------------------------------------------------------- #
# 13: BTCUSDT and ETHUSDT share the implementation without contamination
# --------------------------------------------------------------------------- #
def test_multi_asset_independence_no_state_contamination() -> None:
    btc = _klines(30)
    eth = _klines(30).with_columns(
        (pl.col("close") * 0.05).alias("close"),
        (pl.col("high") * 0.05).alias("high"),
        (pl.col("low") * 0.05).alias("low"),
        (pl.col("open") * 0.05).alias("open"),
    )
    eth_alone = _build(eth)
    _ = _build(btc)  # build BTC in between
    eth_again = _build(eth)
    assert eth_alone.equals(eth_again)
    # The two assets genuinely differ (so the test is meaningful).
    assert not _build(btc).select(_EXPECTED_COLUMNS).equals(eth_alone.select(_EXPECTED_COLUMNS))


# --------------------------------------------------------------------------- #
# 15: development loading cannot cross the frozen holdout boundary
# --------------------------------------------------------------------------- #
def test_holdout_guard_blocks_future_timestamps() -> None:
    df = _klines(40, start=datetime(2025, 12, 31, tzinfo=UTC))  # crosses into 2026
    holdout_start = datetime(2026, 1, 1, tzinfo=UTC)
    with pytest.raises(HoldoutLeakageError):
        build_feature_frame(df, _specs(), holdout_start=holdout_start)


def test_holdout_guard_allows_pure_development_history() -> None:
    df = _klines(40, start=datetime(2025, 12, 1, tzinfo=UTC))  # stays before 2026
    holdout_start = datetime(2026, 1, 1, tzinfo=UTC)
    feats, _ = build_feature_frame(df, _specs(), holdout_start=holdout_start)
    assert feats.height == df.height


def test_missing_input_column_raises_before_computation() -> None:
    df = _klines(10).drop("taker_buy_quote")
    with pytest.raises(ValueError, match="Missing required input columns"):
        build_feature_frame(df, _specs())
