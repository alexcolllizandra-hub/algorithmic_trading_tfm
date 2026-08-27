"""Meta-label classifier, probability calibration and decision threshold.

The pipeline is deliberately split across three disjoint, chronologically
ordered blocks, because each stage would otherwise inherit the optimism of the
previous one:

1. **train** fits the classifier;
2. the first part of **validation** calibrates its probabilities;
3. the second part of **validation** selects the decision threshold.

The test block is never seen by any of the three, and the frozen holdout is never
loaded at all. :func:`fit_meta_model` takes no test or holdout argument, so a
threshold cannot be tuned on evaluation data even by accident.

Raw classifier scores are not probabilities: a random forest's vote share and a
logistic regression's sigmoid are on different, uncalibrated scales, and a
threshold chosen on one is meaningless on the other. Calibrating first makes the
threshold interpretable as "act when the probability of a profitable trade
exceeds p".

Backends
--------
``logistic_regression`` and ``random_forest`` come from scikit-learn, a declared
dependency, so the layer works on a plain ``uv sync --extra dev``. ``lightgbm``
and the SHAP explanations live in the optional ``ml`` extra
(``uv sync --extra ml``) and are imported lazily. When the extra is absent
:func:`build_classifier` raises an explicit, actionable error rather than
silently substituting another model, so a run can never report LightGBM results
that a random forest actually produced.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Protocol, cast

import numpy as np
import polars as pl
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.frozen import FrozenEstimator
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

MODEL_NAMES: tuple[str, ...] = ("logistic_regression", "random_forest", "lightgbm")

CalibrationMethod = Literal["isotonic", "sigmoid", "none"]
ThresholdCriterion = Literal["f1", "precision", "expected_return"]

_MIN_THRESHOLD_SAMPLES = 8


class _SupportsPredictProba(Protocol):
    def fit(self, X: Any, y: Any, **kwargs: Any) -> Any: ...

    def predict_proba(self, X: Any) -> np.ndarray: ...


class MissingBackendError(RuntimeError):
    """A pre-registered model or explainer is not installed in this environment."""


def build_classifier(name: str, *, seed: int, **overrides: Any) -> Any:
    """Instantiate one of the pre-registered meta-label classifiers.

    Every backend is seeded from the caller's seed so a refit is reproducible.
    Logistic regression is wrapped in a standardiser because its regularisation
    is scale dependent; the tree ensembles are not, so they are left bare.
    """
    if name not in MODEL_NAMES:
        raise ValueError(f"Unknown meta-label model {name!r}; expected one of {MODEL_NAMES}.")

    if name == "logistic_regression":
        params: dict[str, Any] = {"max_iter": 1000, "C": 1.0, "solver": "lbfgs"}
        params.update(overrides)
        return Pipeline(
            [
                ("scale", StandardScaler()),
                ("model", LogisticRegression(random_state=seed, **params)),
            ]
        )

    if name == "random_forest":
        params = {
            "n_estimators": 300,
            "max_depth": 4,
            "min_samples_leaf": 20,
            "class_weight": "balanced_subsample",
            "n_jobs": 1,
        }
        params.update(overrides)
        return RandomForestClassifier(random_state=seed, **params)

    try:
        # Optional extra: declared in experiment.yaml, installed on demand.
        import lightgbm  # pyright: ignore[reportMissingImports]
    except ImportError as exc:  # pragma: no cover - depends on the environment
        raise MissingBackendError(
            "LightGBM is pre-registered in experiment.yaml but is not installed. "
            "Install it with `uv add --optional ml lightgbm` (requires network access) "
            "before running the lightgbm backend."
        ) from exc
    params = {
        "n_estimators": 300,
        "num_leaves": 15,
        "min_child_samples": 20,
        "learning_rate": 0.05,
        "verbose": -1,
        "n_jobs": 1,
    }
    params.update(overrides)
    return lightgbm.LGBMClassifier(random_state=seed, **params)


@dataclass(frozen=True)
class ThresholdChoice:
    """The decision threshold and the evidence it was chosen on."""

    threshold: float
    criterion: str
    score: float
    n_samples: int
    fitted_on: str = "validation"

    def to_dict(self) -> dict[str, object]:
        return {
            "threshold": self.threshold,
            "criterion": self.criterion,
            "score": self.score,
            "n_samples": self.n_samples,
            "fitted_on": self.fitted_on,
        }


def _threshold_grid(probabilities: np.ndarray) -> np.ndarray:
    """Candidate thresholds: the observed probabilities plus a coarse backbone.

    Using the observed values means every distinct classification the model can
    produce on this block is considered, instead of an arbitrary lattice that may
    miss the only interesting cut point.
    """
    grid = np.unique(np.concatenate([probabilities, np.linspace(0.05, 0.95, 19)]))
    return grid[(grid > 0.0) & (grid < 1.0)]


def choose_decision_threshold(
    y_true: np.ndarray,
    probabilities: np.ndarray,
    *,
    criterion: ThresholdCriterion = "f1",
    returns: np.ndarray | None = None,
    min_precision: float = 0.0,
    min_signal_rate: float = 0.05,
) -> ThresholdChoice:
    """Pick the probability above which the primary signal is acted on.

    ``criterion``:

    * ``f1`` balances missed trades against false positives;
    * ``precision`` maximises precision subject to still trading at least
      ``min_signal_rate`` of the events, which stops the degenerate solution of
      taking one trade at threshold 0.999;
    * ``expected_return`` maximises the mean of ``returns`` over the accepted
      events, which is the criterion that actually matters economically but
      needs the realised per-event returns.

    This function must only ever be given validation data. It is the single
    place where a number is fitted to labelled outcomes outside the classifier
    itself.
    """
    truth = np.asarray(y_true).astype(int).ravel()
    probs = np.asarray(probabilities, dtype=float).ravel()
    if truth.size != probs.size:
        raise ValueError("y_true and probabilities must have the same length.")
    if truth.size < _MIN_THRESHOLD_SAMPLES:
        raise ValueError(
            f"Choosing a threshold on {truth.size} samples is not meaningful; "
            f"at least {_MIN_THRESHOLD_SAMPLES} are required."
        )
    if criterion == "expected_return":
        if returns is None:
            raise ValueError("criterion='expected_return' requires the per-event returns.")
        realised = np.asarray(returns, dtype=float).ravel()
        if realised.size != truth.size:
            raise ValueError("returns must have the same length as y_true.")
    else:
        realised = np.zeros_like(probs)

    best_threshold = 0.5
    best_score = -np.inf
    for threshold in _threshold_grid(probs):
        accepted = probs >= threshold
        n_accepted = int(accepted.sum())
        if n_accepted == 0 or n_accepted < min_signal_rate * truth.size:
            continue
        true_positive = float((accepted & (truth == 1)).sum())
        precision = true_positive / n_accepted
        positives = float((truth == 1).sum())
        recall = true_positive / positives if positives else 0.0

        if criterion == "f1":
            score = (
                0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)
            )
        elif criterion == "precision":
            score = precision
        else:
            score = float(realised[accepted].mean())
        if precision < min_precision:
            continue
        if score > best_score:
            best_score, best_threshold = score, float(threshold)

    if not np.isfinite(best_score):
        raise ValueError(
            "No threshold satisfied the constraints (min_precision / min_signal_rate). "
            "Relax them explicitly rather than silently defaulting to 0.5."
        )
    return ThresholdChoice(
        threshold=best_threshold,
        criterion=criterion,
        score=float(best_score),
        n_samples=int(truth.size),
    )


@dataclass(frozen=True)
class FittedMetaModel:
    """A fitted, calibrated meta-label model with its validation-fitted threshold."""

    name: str
    estimator: Any
    calibration: str
    threshold: ThresholdChoice
    validation_metrics: dict[str, float]
    n_train: int
    n_calibration: int
    seed: int

    def predict_proba(self, features: np.ndarray) -> np.ndarray:
        """Probability that the primary signal turns into a profitable trade."""
        proba = cast(_SupportsPredictProba, self.estimator).predict_proba(np.asarray(features))
        return np.asarray(proba, dtype=float)[:, 1]

    def predict(self, features: np.ndarray) -> np.ndarray:
        """1 to act on the primary signal, 0 to stand aside."""
        return (self.predict_proba(features) >= self.threshold.threshold).astype(int)

    def to_dict(self) -> dict[str, object]:
        return {
            "model": self.name,
            "calibration": self.calibration,
            "seed": self.seed,
            "n_train": self.n_train,
            "n_calibration": self.n_calibration,
            "threshold": self.threshold.to_dict(),
            "validation_metrics": dict(self.validation_metrics),
        }


def _split_validation(n: int, calibration_fraction: float) -> tuple[slice, slice]:
    if not 0.0 < calibration_fraction < 1.0:
        raise ValueError("calibration_fraction must lie strictly inside (0, 1).")
    cut = round(n * calibration_fraction)
    cut = min(max(cut, 1), n - _MIN_THRESHOLD_SAMPLES)
    if cut < 1:
        raise ValueError(
            f"The validation block ({n} events) is too small to be split into a "
            "calibration part and a threshold part."
        )
    return slice(0, cut), slice(cut, n)


def fit_meta_model(
    name: str,
    *,
    features_train: np.ndarray,
    labels_train: np.ndarray,
    features_validation: np.ndarray,
    labels_validation: np.ndarray,
    seed: int,
    sample_weight_train: np.ndarray | None = None,
    calibration: CalibrationMethod = "isotonic",
    calibration_fraction: float = 0.5,
    threshold_criterion: ThresholdCriterion = "f1",
    returns_validation: np.ndarray | None = None,
    min_signal_rate: float = 0.05,
    **model_overrides: Any,
) -> FittedMetaModel:
    """Fit, calibrate and threshold a meta-label model without touching test data.

    ``features_validation`` must be in chronological order: it is split at
    ``calibration_fraction`` into an earlier calibration part and a later
    threshold part, so the threshold is chosen on data the calibrator has not
    seen either.
    """
    x_train = np.asarray(features_train, dtype=float)
    y_train = np.asarray(labels_train).astype(int).ravel()
    x_val = np.asarray(features_validation, dtype=float)
    y_val = np.asarray(labels_validation).astype(int).ravel()
    if x_train.shape[0] != y_train.size:
        raise ValueError("features_train and labels_train disagree on the number of events.")
    if x_val.shape[0] != y_val.size:
        raise ValueError("features_validation and labels_validation disagree on events.")
    if x_train.shape[1] != x_val.shape[1]:
        raise ValueError("train and validation must share the same feature columns.")
    if np.unique(y_train).size < 2:
        raise ValueError(
            "The training block contains a single class; a meta-label model cannot "
            "learn when to stand aside if it never sees both outcomes."
        )

    base = build_classifier(name, seed=seed, **model_overrides)
    if sample_weight_train is None:
        base.fit(x_train, y_train)
    else:
        weights = np.asarray(sample_weight_train, dtype=float).ravel()
        if weights.size != y_train.size:
            raise ValueError("sample_weight_train must have one weight per training event.")
        fit_key = "model__sample_weight" if isinstance(base, Pipeline) else "sample_weight"
        base.fit(x_train, y_train, **{fit_key: weights})

    calib_slice, threshold_slice = _split_validation(y_val.size, calibration_fraction)
    if calibration == "none":
        estimator: Any = base
        n_calibration = 0
    else:
        y_calib = y_val[calib_slice]
        if np.unique(y_calib).size < 2:
            raise ValueError(
                "The calibration part of the validation block contains a single class; "
                "probability calibration would be undefined."
            )
        calibrator = CalibratedClassifierCV(FrozenEstimator(base), method=calibration)
        calibrator.fit(x_val[calib_slice], y_calib)
        estimator = calibrator
        n_calibration = int(y_calib.size)

    proba_threshold = np.asarray(estimator.predict_proba(x_val[threshold_slice]), dtype=float)[:, 1]
    y_threshold = y_val[threshold_slice]
    returns_slice = (
        None
        if returns_validation is None
        else np.asarray(returns_validation, dtype=float).ravel()[threshold_slice]
    )
    threshold = choose_decision_threshold(
        y_threshold,
        proba_threshold,
        criterion=threshold_criterion,
        returns=returns_slice,
        min_signal_rate=min_signal_rate,
    )

    metrics: dict[str, float] = {
        "brier_score": float(brier_score_loss(y_threshold, proba_threshold)),
        "base_rate": float(y_threshold.mean()),
        "signal_rate": float((proba_threshold >= threshold.threshold).mean()),
    }
    if np.unique(y_threshold).size == 2:
        metrics["roc_auc"] = float(roc_auc_score(y_threshold, proba_threshold))

    return FittedMetaModel(
        name=name,
        estimator=estimator,
        calibration=calibration,
        threshold=threshold,
        validation_metrics=metrics,
        n_train=int(y_train.size),
        n_calibration=n_calibration,
        seed=seed,
    )


def shap_feature_importance(
    model: FittedMetaModel,
    features: np.ndarray,
    feature_names: tuple[str, ...],
) -> pl.DataFrame:
    """Mean absolute SHAP value per feature, descending.

    SHAP is used for interpretation only. It is computed after the model is
    fitted and never feeds back into feature selection, which would turn an
    explanation into another round of in-sample search.
    """
    try:
        # Optional extra: interpretation only, installed on demand.
        import shap  # pyright: ignore[reportMissingImports]
    except ImportError as exc:  # pragma: no cover - depends on the environment
        raise MissingBackendError(
            "SHAP is pre-registered for meta-label interpretation but is not installed. "
            "Install it with `uv add --optional ml shap` (requires network access)."
        ) from exc

    matrix = np.asarray(features, dtype=float)
    if matrix.shape[1] != len(feature_names):
        raise ValueError("feature_names must name every feature column.")
    explainer = shap.Explainer(model.predict_proba, matrix)
    explanation = cast(Any, explainer(matrix))
    values = np.asarray(explanation.values, dtype=float)
    if values.ndim == 3:
        values = values[:, :, -1]
    importance = np.abs(values).mean(axis=0)
    return pl.DataFrame(
        {"feature": list(feature_names), "mean_abs_shap": importance.tolist()}
    ).sort("mean_abs_shap", descending=True)
