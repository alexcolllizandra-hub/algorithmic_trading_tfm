"""Pre-registered meta-labeling layer (machinery only, not yet applied).

The meta-label answers a narrower question than the primary strategy: *given that
the primary strategy wants to trade in this direction now, should the trade be
taken?* Direction is never predicted here; only whether to act.

This package ships the fitting, calibration, threshold-selection and explanation
machinery. It is deliberately **not** wired into any search, family or promotion
decision: no strategy has been declared eligible for a meta-label yet.
"""

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
    "MODEL_NAMES",
    "FittedMetaModel",
    "ThresholdChoice",
    "build_classifier",
    "choose_decision_threshold",
    "fit_meta_model",
    "shap_feature_importance",
]
