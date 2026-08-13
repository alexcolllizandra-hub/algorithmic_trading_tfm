"""Catalogue layer: the study as queryable records rather than loose files.

The artifacts under ``artifacts/`` and ``reports/`` are the scientific evidence
and stay immutable. This package indexes them — families, runs, seeds, folds,
metrics, gates, provenance — so the API can answer questions across the whole
study without re-reading every parquet on every request.

Nothing here is a source of truth. Every row records where it came from and the
hash of the artifact it was read from, so any figure the dashboard shows can be
traced back to the file that produced it.
"""

from __future__ import annotations

from perp_lab.catalog.status import (
    MEASURED_STATUSES,
    TERMINAL_STATUSES,
    ResultStatus,
    has_metrics,
)

__all__ = [
    "MEASURED_STATUSES",
    "TERMINAL_STATUSES",
    "ResultStatus",
    "has_metrics",
]
