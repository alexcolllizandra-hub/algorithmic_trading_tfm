"""Data-quality validation: schemas and reporting."""

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

__all__ = [
    "QualityReport",
    "check_ohlc_consistency",
    "coverage_summary",
    "find_duplicates",
    "find_gaps",
    "flag_extreme_returns",
    "quality_report",
    "validate_funding",
    "validate_klines",
]
