"""Pre-registered meta-labeling layer (machinery only, not yet applied).

The meta-label answers a narrower question than the primary strategy: *given that
the primary strategy wants to trade in this direction now, should the trade be
taken?* Direction is never predicted here; only whether to act.

This package ships the fitting, calibration, threshold-selection and explanation
machinery. It is deliberately **not** wired into any search, family or promotion
decision: no strategy has been declared eligible for a meta-label yet.

:mod:`~perp_lab.meta_labeling.synthetic` and :mod:`~perp_lab.meta_labeling.study`
exercise that machinery end to end on generated markets whose ground truth is
known. Those runs are **infrastructure validation only** and say nothing about
BTC or ETH.
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
from perp_lab.meta_labeling.metrics import (
    EconomicMetrics,
    PredictiveMetrics,
    calibration_table,
    economic_metrics,
    expected_calibration_error,
    predictive_metrics,
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
from perp_lab.meta_labeling.study import (
    META_ARM,
    PRIMARY_ARM,
    FoldGeometry,
    FoldResult,
    MarketStudy,
    MetaLabelDataset,
    MetaLabelStudyConfig,
    build_dataset,
    event_block_masks,
    event_signal_series,
    run_meta_label_study,
    study_from_market,
    walk_forward_folds,
)

__all__ = [
    "MAX_POSITION_SCALE",
    "META_ARM",
    "MIN_POSITION_SCALE",
    "MODEL_NAMES",
    "PRIMARY_ARM",
    "EconomicComparison",
    "EconomicMetrics",
    "FittedMetaModel",
    "FoldGeometry",
    "FoldResult",
    "MarketStudy",
    "MetaLabelDataset",
    "MetaLabelStudyConfig",
    "PredictiveMetrics",
    "ThresholdChoice",
    "build_classifier",
    "build_dataset",
    "calibration_table",
    "choose_decision_threshold",
    "compare_primary_and_meta",
    "economic_metrics",
    "event_block_masks",
    "event_signal_series",
    "expected_calibration_error",
    "feature_drift",
    "fit_meta_model",
    "meta_position_scale",
    "permutation_importance_scores",
    "population_stability_index",
    "predictive_metrics",
    "run_meta_label_study",
    "shap_feature_importance",
    "study_from_market",
    "walk_forward_folds",
]
