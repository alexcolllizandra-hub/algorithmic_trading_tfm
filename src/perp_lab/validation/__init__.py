"""Validation: data-quality (schemas / reports) and temporal walk-forward CV."""

from perp_lab.validation.quality import (
    QualityReport,
    check_ohlc_consistency,
    coverage_summary,
    find_duplicates,
    find_gaps,
    flag_extreme_returns,
    quality_report,
)
from perp_lab.validation.schemas import validate_funding, validate_klines
from perp_lab.validation.walk_forward import (
    WalkForwardFold,
    assert_folds_exclude_holdout,
    generate_folds,
    generate_walk_forward,
    split_fold,
)

__all__ = [
    "QualityReport",
    "WalkForwardFold",
    "assert_folds_exclude_holdout",
    "check_ohlc_consistency",
    "coverage_summary",
    "find_duplicates",
    "find_gaps",
    "flag_extreme_returns",
    "generate_folds",
    "generate_walk_forward",
    "quality_report",
    "split_fold",
    "validate_funding",
    "validate_klines",
]
