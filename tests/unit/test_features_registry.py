"""Tests for the feature contract, registry resolution and config-driven set."""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from perp_lab.config import load_experiment_config
from perp_lab.config.experiment import ExperimentConfig, FeatureItem
from perp_lab.features.registry import feature_columns, resolve_feature_set
from perp_lab.features.spec import (
    KIND_REGISTRY,
    known_kinds,
    resolve_spec,
    validate_feature_item,
)

_PERIODS = {
    "development_start": "2020-01-01T00:00:00Z",
    "development_end_exclusive": "2026-01-01T00:00:00Z",
    "holdout_start": "2026-01-01T00:00:00Z",
    "cutoff_exclusive": "2026-07-01T00:00:00Z",
}


# --------------------------------------------------------------------------- #
# Contract completeness and serialisability
# --------------------------------------------------------------------------- #
def test_every_kind_resolves_and_serialises() -> None:
    required_keys = {
        "name",
        "kind",
        "family",
        "columns",
        "inputs",
        "asset_dependency",
        "timeframe_dependency",
        "params",
        "lookback",
        "availability",
        "shift",
        "warmup",
        "null_policy",
        "inf_policy",
        "consumers",
        "leakage_risk",
        "output_dtype",
        "impl_version",
    }
    for kind, kd in KIND_REGISTRY.items():
        window = 12 if kd.requires_window else None
        lag = 1 if kd.requires_lag else None
        spec = resolve_spec(kind, window=window, lag=lag)
        payload = spec.to_dict()
        assert required_keys.issubset(payload.keys())
        json.dumps(payload)  # must be JSON-serialisable
        assert spec.columns  # at least one output column


def test_known_kinds_cover_all_families() -> None:
    families = {KIND_REGISTRY[k].family for k in known_kinds()}
    assert {
        "returns",
        "momentum",
        "trend",
        "volatility",
        "range",
        "volume",
        "time",
        "order_flow",
    } <= (families)


# --------------------------------------------------------------------------- #
# Validation rejects malformed requests before any computation
# --------------------------------------------------------------------------- #
def test_unknown_kind_rejected() -> None:
    with pytest.raises(ValueError, match="Unknown feature kind"):
        validate_feature_item("teleportation", window=3)


def test_missing_window_rejected() -> None:
    with pytest.raises(ValueError, match="requires a strictly positive window"):
        validate_feature_item("sma")


def test_superfluous_window_rejected() -> None:
    with pytest.raises(ValueError, match="does not take a window"):
        validate_feature_item("range_norm", window=3)


def test_invalid_lag_rejected() -> None:
    with pytest.raises(ValueError, match="requires an integer lag"):
        validate_feature_item("taker_buy_imbalance", lag=0)


def test_unknown_source_rejected() -> None:
    with pytest.raises(ValueError, match="does not accept source"):
        validate_feature_item("sma", window=3, source="volume")


# --------------------------------------------------------------------------- #
# resolve_feature_set: ordering, de-duplication and SMA injection
# --------------------------------------------------------------------------- #
def test_resolve_feature_set_injects_missing_sma_windows() -> None:
    items = [FeatureItem(kind="log_return"), FeatureItem(kind="sma", window=24)]
    specs = resolve_feature_set(items, ensure_sma=(24, 96))
    cols = feature_columns(specs)
    assert cols == ["log_return", "sma_24", "sma_96"]  # 24 not duplicated, 96 injected


def test_resolve_feature_set_dedupes_repeated_requests() -> None:
    items = [FeatureItem(kind="sma", window=24), FeatureItem(kind="sma", window=24)]
    specs = resolve_feature_set(items)
    assert feature_columns(specs) == ["sma_24"]


# --------------------------------------------------------------------------- #
# Config-driven selection through ExperimentConfig
# --------------------------------------------------------------------------- #
def test_repo_experiment_yaml_feature_set_resolves() -> None:
    cfg = load_experiment_config("configs/experiment.yaml")
    specs = resolve_feature_set(cfg.features.feature_set, ensure_sma=(24, 96))
    cols = feature_columns(specs)
    assert "log_return" in cols
    assert "hour_sin" in cols and "hour_cos" in cols
    assert "taker_buy_imbalance" in cols
    assert len(cols) == len(set(cols))  # no duplicates
    assert 10 <= len(cols) <= 16  # bounded feature set


def test_config_rejects_unknown_feature_kind() -> None:
    payload: dict[str, object] = {
        "periods": dict(_PERIODS),
        "features": {"feature_set": [{"kind": "does_not_exist"}]},
    }
    with pytest.raises(ValidationError, match="Unknown feature kind"):
        ExperimentConfig.model_validate(payload)


def test_config_rejects_bad_feature_params() -> None:
    payload: dict[str, object] = {
        "periods": dict(_PERIODS),
        "features": {"feature_set": [{"kind": "sma"}]},  # missing window
    }
    with pytest.raises(ValidationError, match="requires a strictly positive window"):
        ExperimentConfig.model_validate(payload)


def test_config_rejects_duplicate_feature_columns() -> None:
    payload: dict[str, object] = {
        "periods": dict(_PERIODS),
        "features": {"feature_set": [{"kind": "sma", "window": 24}, {"kind": "sma", "window": 24}]},
    }
    with pytest.raises(ValidationError, match="Duplicate feature column"):
        ExperimentConfig.model_validate(payload)
