"""Tests for the extended causal feature kinds, manifest and predictor rows."""

from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta

import numpy as np
import polars as pl
import pytest

from perp_lab.features import (
    build_feature_manifest,
    build_predictor_rows,
    resolve_feature_set,
)
from perp_lab.features.causal import (
    add_cum_return,
    add_ema,
    add_ma_distance,
    add_rolling_std,
    add_taker_buy_ratio,
    add_true_range,
)
from perp_lab.features.predictors import EXECUTION_TIME, FEATURE_TIME, LABEL_TIME, SIGNAL_TIME
from perp_lab.features.registry import build_feature_frame, feature_columns


def _klines(n: int = 40) -> pl.DataFrame:
    start = datetime(2021, 1, 4, tzinfo=UTC)
    times = [start + timedelta(hours=i) for i in range(n)]
    close = [100.0 + 5.0 * math.sin(i / 4.0) + 0.3 * i for i in range(n)]
    return pl.DataFrame(
        {
            "open_time": times,
            "open": [c - 0.2 for c in close],
            "high": [c + 1.0 for c in close],
            "low": [c - 1.0 for c in close],
            "close": close,
            "volume": [1000.0 + 10 * i for i in range(n)],
            "quote_volume": [(1000.0 + 10 * i) * c for i, c in enumerate(close)],
            "taker_buy_quote": [0.55 * (1000.0 + 10 * i) * c for i, c in enumerate(close)],
        }
    )


def _leading_nulls(s: pl.Series) -> int:
    count = 0
    for is_null in s.is_null().to_list():
        if not is_null:
            break
        count += 1
    return count


# --------------------------------------------------------------------------- #
# New causal builders: warm-up and arithmetic
# --------------------------------------------------------------------------- #
def test_ema_warmup_matches_window_minus_one() -> None:
    df = add_ema(_klines(), 5)
    assert _leading_nulls(df["ema_5"]) == 4


def test_cum_return_first_is_zero_and_matches_log_ratio() -> None:
    df = add_cum_return(_klines())
    vals = df["cum_return"].to_list()
    close = df["close"].to_list()
    assert vals[0] == pytest.approx(0.0)
    assert vals[-1] == pytest.approx(math.log(close[-1] / close[0]))


def test_rolling_std_warmup_and_positive() -> None:
    df = add_rolling_std(_klines(), 6)
    assert _leading_nulls(df["roll_std_6"]) == 5
    assert df["roll_std_6"].drop_nulls().min() >= 0.0  # type: ignore[operator]


def test_true_range_first_row_is_high_low() -> None:
    df = add_true_range(_klines())
    row0 = df.row(0, named=True)
    assert df["true_range"][0] == pytest.approx(row0["high"] - row0["low"])
    assert df["true_range"].is_null().sum() == 0


def test_ma_distance_warmup_and_scale_free() -> None:
    df = add_ma_distance(_klines(), 3, 9)
    assert _leading_nulls(df["ma_distance_3_9"]) == 8
    # manual check on last row
    close = np.array(df["close"].to_list())
    fast = close[-3:].mean()
    slow = close[-9:].mean()
    assert df["ma_distance_3_9"][-1] == pytest.approx(fast / slow - 1.0)


def test_ma_distance_requires_fast_below_slow() -> None:
    with pytest.raises(ValueError, match=r"fast .* < slow"):
        add_ma_distance(_klines(), 9, 3)


def test_taker_buy_ratio_lagged_and_bounded() -> None:
    df = add_taker_buy_ratio(_klines(), lag=1)
    r = df["taker_buy_ratio"]
    assert _leading_nulls(r) == 1
    vals = r.drop_nulls().to_list()
    assert all(0.0 <= v <= 1.0 for v in vals)


def test_new_kinds_are_truncation_invariant() -> None:
    # Causality: earlier feature values must not change when future rows appear.
    full = _klines(48)
    head = full.head(30)
    cases = (
        (add_ema(full, 6)["ema_6"], add_ema(head, 6)["ema_6"]),
        (add_rolling_std(full, 6)["roll_std_6"], add_rolling_std(head, 6)["roll_std_6"]),
        (
            add_ma_distance(full, 3, 9)["ma_distance_3_9"],
            add_ma_distance(head, 3, 9)["ma_distance_3_9"],
        ),
        (add_cum_return(full)["cum_return"], add_cum_return(head)["cum_return"]),
        (add_true_range(full)["true_range"], add_true_range(head)["true_range"]),
    )
    for full_col, head_col in cases:
        assert full_col.to_list()[:30] == pytest.approx(head_col.to_list(), nan_ok=True)


# --------------------------------------------------------------------------- #
# Feature manifest
# --------------------------------------------------------------------------- #
def test_manifest_documents_every_column() -> None:
    from perp_lab.config.experiment import FeatureItem

    items = [
        FeatureItem(kind="log_return"),
        FeatureItem(kind="ema", window=12),
        FeatureItem(kind="ma_distance", window=12, window_slow=48),
        FeatureItem(kind="zscore", window=24),
    ]
    specs = resolve_feature_set(items)
    manifest = build_feature_manifest(specs, symbol="BTCUSDT", timeframe="1h")
    assert manifest["n_features"] == len(specs)
    assert manifest["columns"] == feature_columns(specs)
    for entry in manifest["features"]:  # type: ignore[attr-defined]
        assert entry["formula"]
        assert "missing_data_rule" in entry
        assert "required_source_columns" in entry
    import json

    json.dumps(manifest)  # serialisable


# --------------------------------------------------------------------------- #
# Predictor rows: four separated timestamp roles
# --------------------------------------------------------------------------- #
def test_predictor_rows_keep_timestamp_roles_separated() -> None:
    from perp_lab.config.experiment import FeatureItem

    df = _klines(30)
    specs = resolve_feature_set([FeatureItem(kind="zscore", window=5)], ensure_sma=(3, 6))
    feats, _ = build_feature_frame(df, specs)
    from perp_lab.strategies.momentum import MomentumCrossover

    sig = MomentumCrossover(fast=3, slow=6).signals(feats)
    rows = build_predictor_rows(feats, sig, feature_columns=["zscore_5", "sma_3"])

    assert {FEATURE_TIME, SIGNAL_TIME, EXECUTION_TIME, LABEL_TIME}.issubset(rows.columns)
    # feature_time == signal_time; execution_time is the NEXT bar; label undefined.
    assert rows[FEATURE_TIME].to_list() == rows[SIGNAL_TIME].to_list()
    ft = rows[FEATURE_TIME].to_list()
    et = rows[EXECUTION_TIME].to_list()
    assert et[0] == ft[1]  # execution is next bar's timestamp
    assert et[-1] is None  # last bar has no next execution bar
    assert rows[LABEL_TIME].null_count() == rows.height  # labeling not implemented


def test_predictor_rows_events_only_are_position_changes() -> None:
    from perp_lab.config.experiment import FeatureItem
    from perp_lab.strategies.mean_reversion import MeanReversion

    df = _klines(40)
    specs = resolve_feature_set([FeatureItem(kind="zscore", window=5)])
    feats, _ = build_feature_frame(df, specs)
    sig = MeanReversion(zscore_window=5, entry_z=0.5, exit_z=0.1).signals(feats)
    events = build_predictor_rows(feats, sig, feature_columns=["zscore_5"], events_only=True)
    assert bool(events["is_event"].all())
    assert (events["side"] != 0).all()
