"""Meta-label machinery: calibration, validation-only thresholds, explanations."""

from __future__ import annotations

import numpy as np
import pytest

from perp_lab.meta_labeling import (
    MODEL_NAMES,
    build_classifier,
    choose_decision_threshold,
    fit_meta_model,
    shap_feature_importance,
)
from perp_lab.meta_labeling.model import MissingBackendError

SKLEARN_MODELS = ("logistic_regression", "random_forest")


def _learnable_events(
    n: int, *, seed: int, noise: float = 1.0
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Events whose profitability genuinely depends on the first feature."""
    rng = np.random.default_rng(seed)
    features = rng.normal(0.0, 1.0, size=(n, 3))
    score = 1.6 * features[:, 0] + noise * rng.normal(0.0, 1.0, size=n)
    labels = (score > 0).astype(int)
    returns = np.where(labels == 1, 0.01, -0.01) + rng.normal(0.0, 0.001, size=n)
    return features, labels, returns


# --------------------------------------------------------------------------- #
# Classifier construction
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("name", SKLEARN_MODELS)
def test_every_scikit_learn_backend_is_constructible_and_seeded(name: str) -> None:
    first = build_classifier(name, seed=7)
    second = build_classifier(name, seed=7)
    x, y, _ = _learnable_events(120, seed=0)
    first.fit(x, y)
    second.fit(x, y)
    assert np.allclose(first.predict_proba(x), second.predict_proba(x))


def test_the_registry_matches_the_preregistered_model_list() -> None:
    assert MODEL_NAMES == ("logistic_regression", "random_forest", "lightgbm")


def test_an_unknown_backend_is_refused() -> None:
    with pytest.raises(ValueError, match="Unknown meta-label model"):
        build_classifier("xgboost", seed=1)


def test_lightgbm_reports_a_missing_install_instead_of_substituting_a_model() -> None:
    try:
        import lightgbm  # noqa: F401  # pyright: ignore[reportMissingImports]
    except ImportError:
        with pytest.raises(MissingBackendError, match="LightGBM"):
            build_classifier("lightgbm", seed=1)
    else:  # pragma: no cover - only when the optional extra is installed
        assert build_classifier("lightgbm", seed=1) is not None


# --------------------------------------------------------------------------- #
# Decision threshold
# --------------------------------------------------------------------------- #


def test_a_threshold_separates_a_perfectly_ordered_score() -> None:
    labels = np.array([0] * 20 + [1] * 20)
    probabilities = np.concatenate([np.linspace(0.01, 0.45, 20), np.linspace(0.55, 0.99, 20)])
    choice = choose_decision_threshold(labels, probabilities, criterion="f1")
    assert 0.45 < choice.threshold <= 0.55
    assert choice.score == pytest.approx(1.0)
    assert choice.fitted_on == "validation"


def test_the_expected_return_criterion_needs_the_realised_returns() -> None:
    labels = np.array([0, 1] * 10)
    probabilities = np.linspace(0.05, 0.95, 20)
    with pytest.raises(ValueError, match="requires the per-event returns"):
        choose_decision_threshold(labels, probabilities, criterion="expected_return")


def test_the_expected_return_criterion_prefers_the_profitable_tail() -> None:
    probabilities = np.linspace(0.02, 0.98, 40)
    labels = (probabilities > 0.7).astype(int)
    returns = np.where(labels == 1, 0.02, -0.01)
    choice = choose_decision_threshold(
        labels, probabilities, criterion="expected_return", returns=returns, min_signal_rate=0.1
    )
    assert choice.threshold > 0.6
    assert choice.score > 0


def test_a_minimum_signal_rate_blocks_the_degenerate_single_trade_threshold() -> None:
    probabilities = np.linspace(0.01, 0.99, 100)
    labels = (probabilities > 0.98).astype(int)
    choice = choose_decision_threshold(
        labels, probabilities, criterion="precision", min_signal_rate=0.25
    )
    accepted = float((probabilities >= choice.threshold).mean())
    assert accepted >= 0.25


def test_impossible_constraints_fail_loudly_rather_than_defaulting() -> None:
    probabilities = np.linspace(0.01, 0.99, 40)
    labels = np.zeros(40, dtype=int)
    with pytest.raises(ValueError, match="No threshold satisfied"):
        choose_decision_threshold(
            labels, probabilities, criterion="precision", min_precision=0.9, min_signal_rate=0.1
        )


def test_a_threshold_is_refused_on_a_handful_of_samples() -> None:
    with pytest.raises(ValueError, match="not meaningful"):
        choose_decision_threshold(np.array([0, 1, 0]), np.array([0.1, 0.9, 0.2]))


# --------------------------------------------------------------------------- #
# End-to-end fitting
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("name", SKLEARN_MODELS)
def test_a_fitted_model_learns_a_real_relationship(name: str) -> None:
    x_train, y_train, _ = _learnable_events(400, seed=1)
    x_val, y_val, _ = _learnable_events(300, seed=2)
    model = fit_meta_model(
        name,
        features_train=x_train,
        labels_train=y_train,
        features_validation=x_val,
        labels_validation=y_val,
        seed=42,
    )
    assert model.validation_metrics["roc_auc"] > 0.7
    x_test, y_test, _ = _learnable_events(300, seed=3)
    probabilities = model.predict_proba(x_test)
    assert probabilities.shape == (300,)
    assert probabilities.min() >= 0.0
    assert probabilities.max() <= 1.0
    decisions = model.predict(x_test)
    assert set(np.unique(decisions)) <= {0, 1}
    assert float(y_test[decisions == 1].mean()) > float(y_test.mean())


def test_fitting_is_deterministic_for_a_given_seed() -> None:
    x_train, y_train, _ = _learnable_events(300, seed=4)
    x_val, y_val, _ = _learnable_events(200, seed=5)
    kwargs = {
        "features_train": x_train,
        "labels_train": y_train,
        "features_validation": x_val,
        "labels_validation": y_val,
        "seed": 11,
    }
    first = fit_meta_model("random_forest", **kwargs)
    second = fit_meta_model("random_forest", **kwargs)
    assert first.threshold.to_dict() == second.threshold.to_dict()
    assert first.validation_metrics == second.validation_metrics


def test_the_threshold_is_fitted_only_on_the_later_part_of_validation() -> None:
    x_train, y_train, _ = _learnable_events(300, seed=6)
    x_val, y_val, _ = _learnable_events(240, seed=7)
    model = fit_meta_model(
        "logistic_regression",
        features_train=x_train,
        labels_train=y_train,
        features_validation=x_val,
        labels_validation=y_val,
        seed=13,
        calibration_fraction=0.5,
    )
    assert model.n_calibration == 120
    assert model.threshold.n_samples == 120
    assert model.threshold.fitted_on == "validation"
    assert model.to_dict()["threshold"]["fitted_on"] == "validation"  # type: ignore[index]


def test_the_validation_split_is_chronological_not_shuffled() -> None:
    # A validation block whose second half is pure noise must not be rescued by
    # the first half: the threshold sees only the later part.
    x_train, y_train, _ = _learnable_events(300, seed=8)
    x_val, y_val, _ = _learnable_events(240, seed=9)
    scrambled = y_val.copy()
    scrambled[120:] = np.random.default_rng(0).integers(0, 2, size=120)
    ordered = fit_meta_model(
        "logistic_regression",
        features_train=x_train,
        labels_train=y_train,
        features_validation=x_val,
        labels_validation=y_val,
        seed=13,
    )
    corrupted = fit_meta_model(
        "logistic_regression",
        features_train=x_train,
        labels_train=y_train,
        features_validation=x_val,
        labels_validation=scrambled,
        seed=13,
    )
    assert ordered.validation_metrics["roc_auc"] > corrupted.validation_metrics["roc_auc"]

    # The comparison above degrades under any split, shuffled or not, so it does
    # not by itself pin the order down. Corrupting one half at a time does: the
    # reported metrics come from the threshold part, which is the *later* half.
    # Noise confined to the early half must leave them intact, and noise confined
    # to the late half must destroy them. Shuffling first would blend the two
    # cases into the same mediocre score and break this asymmetry.
    early_noise = y_val.copy()
    early_noise[:120] = np.random.default_rng(1).integers(0, 2, size=120)
    late_noise = y_val.copy()
    late_noise[120:] = np.random.default_rng(1).integers(0, 2, size=120)
    common = {
        "features_train": x_train,
        "labels_train": y_train,
        "features_validation": x_val,
        "seed": 13,
    }
    early = fit_meta_model("logistic_regression", labels_validation=early_noise, **common)
    late = fit_meta_model("logistic_regression", labels_validation=late_noise, **common)
    assert early.validation_metrics["roc_auc"] > 0.8
    assert late.validation_metrics["roc_auc"] < 0.65


def test_calibration_improves_the_brier_score_of_an_overconfident_model() -> None:
    # A *small* forest of fully grown trees is the overconfident case: with five
    # trees the vote share can only take six values and is pushed to 0 or 1. The
    # default 300-tree forest is already close to calibrated, so it would not
    # exercise the calibration step at all.
    overconfident = {"n_estimators": 5, "max_depth": None, "min_samples_leaf": 1}
    x_train, y_train, _ = _learnable_events(400, seed=14, noise=1.5)
    x_val, y_val, _ = _learnable_events(400, seed=15, noise=1.5)
    common = {
        "features_train": x_train,
        "labels_train": y_train,
        "features_validation": x_val,
        "labels_validation": y_val,
        "seed": 21,
    }
    calibrated = fit_meta_model("random_forest", calibration="isotonic", **common, **overconfident)
    raw = fit_meta_model("random_forest", calibration="none", **common, **overconfident)
    assert calibrated.n_calibration == 200
    assert raw.n_calibration == 0
    assert calibrated.validation_metrics["brier_score"] < raw.validation_metrics["brier_score"]


def test_sample_weights_are_forwarded_and_change_the_fit() -> None:
    x_train, y_train, _ = _learnable_events(300, seed=16)
    x_val, y_val, _ = _learnable_events(200, seed=17)
    weights = np.linspace(0.1, 3.0, x_train.shape[0])
    common = {
        "features_train": x_train,
        "labels_train": y_train,
        "features_validation": x_val,
        "labels_validation": y_val,
        "seed": 5,
    }
    unweighted = fit_meta_model("logistic_regression", **common)
    weighted = fit_meta_model("logistic_regression", sample_weight_train=weights, **common)
    assert not np.allclose(unweighted.predict_proba(x_val), weighted.predict_proba(x_val))


def test_fitting_refuses_inconsistent_or_degenerate_blocks() -> None:
    x_train, y_train, _ = _learnable_events(200, seed=18)
    x_val, y_val, _ = _learnable_events(120, seed=19)
    with pytest.raises(ValueError, match="single class"):
        fit_meta_model(
            "logistic_regression",
            features_train=x_train,
            labels_train=np.ones_like(y_train),
            features_validation=x_val,
            labels_validation=y_val,
            seed=1,
        )
    with pytest.raises(ValueError, match="disagree on the number of events"):
        fit_meta_model(
            "logistic_regression",
            features_train=x_train,
            labels_train=y_train[:-5],
            features_validation=x_val,
            labels_validation=y_val,
            seed=1,
        )
    with pytest.raises(ValueError, match="same feature columns"):
        fit_meta_model(
            "logistic_regression",
            features_train=x_train,
            labels_train=y_train,
            features_validation=x_val[:, :2],
            labels_validation=y_val,
            seed=1,
        )
    with pytest.raises(ValueError, match="one weight per training event"):
        fit_meta_model(
            "logistic_regression",
            features_train=x_train,
            labels_train=y_train,
            features_validation=x_val,
            labels_validation=y_val,
            seed=1,
            sample_weight_train=np.ones(5),
        )


def test_fit_meta_model_exposes_no_test_or_holdout_argument() -> None:
    import inspect

    parameters = set(inspect.signature(fit_meta_model).parameters)
    forbidden = {p for p in parameters if "test" in p or "holdout" in p}
    assert not forbidden, f"the meta-label fit must not accept evaluation data: {forbidden}"


def test_shap_reports_a_missing_install_instead_of_a_silent_fallback() -> None:
    x_train, y_train, _ = _learnable_events(200, seed=20)
    x_val, y_val, _ = _learnable_events(120, seed=21)
    model = fit_meta_model(
        "logistic_regression",
        features_train=x_train,
        labels_train=y_train,
        features_validation=x_val,
        labels_validation=y_val,
        seed=1,
    )
    names = ("a", "b", "c")
    try:
        import shap  # noqa: F401  # pyright: ignore[reportMissingImports]
    except ImportError:
        with pytest.raises(MissingBackendError, match="SHAP"):
            shap_feature_importance(model, x_val[:20], names)
    else:  # pragma: no cover - only when the optional extra is installed
        frame = shap_feature_importance(model, x_val[:20], names)
        assert frame.columns == ["feature", "mean_abs_shap"]
        assert frame.height == 3
