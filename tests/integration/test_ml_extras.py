"""The optional ``ml`` extra: LightGBM and SHAP actually work end to end.

These are integration tests in the narrow sense that they exercise a third-party
backend rather than our own arithmetic. They stay small and seeded so they add
seconds, not minutes, and they skip cleanly when the extra is not installed —
``uv sync --extra dev`` alone must keep the suite green.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pytest

from perp_lab.meta_labeling import (
    build_classifier,
    fit_meta_model,
    permutation_importance_scores,
    shap_feature_importance,
)

lightgbm = pytest.importorskip("lightgbm", reason="optional 'ml' extra is not installed")
shap = pytest.importorskip("shap", reason="optional 'ml' extra is not installed")

FEATURE_NAMES = ("signal", "noise_a", "noise_b")


def _events(n: int, *, seed: int) -> tuple[np.ndarray, np.ndarray]:
    """Only the first feature carries information; the other two are noise."""
    rng = np.random.default_rng(seed)
    features = rng.normal(0.0, 1.0, size=(n, 3))
    score = 1.8 * features[:, 0] + rng.normal(0.0, 1.0, size=n)
    return features, (score > 0).astype(int)


# --------------------------------------------------------------------------- #
# LightGBM
# --------------------------------------------------------------------------- #


def test_lightgbm_is_built_with_the_frozen_defaults_and_the_caller_seed() -> None:
    model = build_classifier("lightgbm", seed=17)
    params = model.get_params()
    assert params["random_state"] == 17
    assert params["n_estimators"] == 300
    assert params["num_leaves"] == 15
    assert params["min_child_samples"] == 20
    # Single-threaded, or the suite stops being reproducible across machines.
    assert params["n_jobs"] == 1


def test_lightgbm_learns_the_relationship_and_is_reproducible() -> None:
    x_train, y_train = _events(600, seed=30)
    x_val, y_val = _events(400, seed=31)
    kwargs: dict[str, Any] = {
        "features_train": x_train,
        "labels_train": y_train,
        "features_validation": x_val,
        "labels_validation": y_val,
        "seed": 5,
        # A small forest keeps the test fast without changing what it checks.
        "n_estimators": 40,
    }
    first = fit_meta_model("lightgbm", **kwargs)
    second = fit_meta_model("lightgbm", **kwargs)

    assert first.validation_metrics["roc_auc"] > 0.7
    assert np.allclose(first.predict_proba(x_val), second.predict_proba(x_val))


def test_lightgbm_probabilities_stay_in_the_unit_interval_after_calibration() -> None:
    x_train, y_train = _events(500, seed=32)
    x_val, y_val = _events(300, seed=33)
    model = fit_meta_model(
        "lightgbm",
        features_train=x_train,
        labels_train=y_train,
        features_validation=x_val,
        labels_validation=y_val,
        seed=9,
        n_estimators=40,
    )
    probabilities = model.predict_proba(x_val)
    assert probabilities.min() >= 0.0
    assert probabilities.max() <= 1.0
    assert 0.0 < model.threshold.threshold < 1.0


def test_permutation_importance_ranks_lightgbm_features_correctly() -> None:
    x_train, y_train = _events(600, seed=34)
    x_val, y_val = _events(400, seed=35)
    estimator = build_classifier("lightgbm", seed=3, n_estimators=40)
    estimator.fit(x_train, y_train)
    scores = permutation_importance_scores(
        estimator, x_val, y_val, FEATURE_NAMES, seed=3, n_repeats=5
    )
    assert scores["feature"][0] == "signal"


# --------------------------------------------------------------------------- #
# SHAP
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("backend", ["logistic_regression", "random_forest", "lightgbm"])
def test_shap_attributes_the_prediction_to_the_informative_feature(backend: str) -> None:
    x_train, y_train = _events(400, seed=36)
    x_val, y_val = _events(200, seed=37)
    overrides: dict[str, Any] = {"n_estimators": 40} if backend != "logistic_regression" else {}
    model = fit_meta_model(
        backend,
        features_train=x_train,
        labels_train=y_train,
        features_validation=x_val,
        labels_validation=y_val,
        seed=4,
        **overrides,
    )
    frame = shap_feature_importance(model, x_val[:60], FEATURE_NAMES)

    assert frame.columns == ["feature", "mean_abs_shap"]
    assert frame.height == 3
    assert frame["feature"][0] == "signal"
    # Descending order is part of the contract callers rely on.
    values = frame["mean_abs_shap"].to_list()
    assert values == sorted(values, reverse=True)
    assert all(v >= 0.0 for v in values)


def test_shap_is_deterministic_for_a_fixed_model_and_sample() -> None:
    x_train, y_train = _events(400, seed=38)
    x_val, y_val = _events(200, seed=39)
    model = fit_meta_model(
        "random_forest",
        features_train=x_train,
        labels_train=y_train,
        features_validation=x_val,
        labels_validation=y_val,
        seed=6,
        n_estimators=30,
    )
    first = shap_feature_importance(model, x_val[:50], FEATURE_NAMES)
    second = shap_feature_importance(model, x_val[:50], FEATURE_NAMES)
    assert first.equals(second)
