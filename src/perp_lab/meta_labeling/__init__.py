"""Pre-registered meta-labeling layer (machinery only, not yet applied).

The meta-label answers a narrower question than the primary strategy: *given that
the primary strategy wants to trade in this direction now, should the trade be
taken?* Direction is never predicted here; only whether to act.

This package ships the fitting, calibration, threshold-selection and explanation
machinery. It is deliberately **not** wired into any search, family or promotion
decision: no strategy has been declared eligible for a meta-label yet.
"""

from perp_lab.meta_labeling.diagnostics import (
    MAX_POSITION_SCALE,
    MIN_POSITION_SCALE,
    EconomicComparison,
    compare_primary_and_meta,
    feature_drift,
    meta_position_scale,
    permutation_importance_scores,
    population_stability_index,
)
from perp_lab.meta_labeling.model import (
    MODEL_NAMES,
    FittedMetaModel,
    ThresholdChoice,
    build_classifier,
    choose_decision_threshold,
    fit_meta_model,
    shap_feature_importance,
)

__all__ = [
    "MAX_POSITION_SCALE",
    "MIN_POSITION_SCALE",
    "MODEL_NAMES",
    "EconomicComparison",
    "FittedMetaModel",
    "ThresholdChoice",
    "build_classifier",
    "choose_decision_threshold",
    "compare_primary_and_meta",
    "feature_drift",
    "fit_meta_model",
    "meta_position_scale",
    "permutation_importance_scores",
    "population_stability_index",
    "shap_feature_importance",
]
