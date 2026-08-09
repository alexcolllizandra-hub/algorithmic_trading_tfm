"""Read-only Research Dashboard (v0) for perp-lab search runs.

This package only *consumes* artifacts produced by the search engine
(``perp_lab.search``). It never re-runs backtests or the search itself, and it
must not import the search algorithms. Data loading and transformations live in
:mod:`perp_lab.dashboard.loader` (Streamlit-free, unit tested); the Streamlit UI
lives in :mod:`perp_lab.dashboard.app`.
"""

from perp_lab.dashboard.loader import (
    RunArtifacts,
    RunSummary,
    candidate_ranking,
    candidates_frame,
    classify_run_kind,
    comparison_table,
    convergence_folds,
    convergence_frame,
    dataset_manifest_frame,
    discover_runs,
    diversity_frame,
    equity_frame,
    failed_candidates_frame,
    fair_budget_report,
    fold_winners_frame,
    folds_frame,
    generation_best_frame,
    load_run,
    search_protocol,
    trades_frame,
    warning_messages,
)

__all__ = [
    "RunArtifacts",
    "RunSummary",
    "candidate_ranking",
    "candidates_frame",
    "classify_run_kind",
    "comparison_table",
    "convergence_folds",
    "convergence_frame",
    "dataset_manifest_frame",
    "discover_runs",
    "diversity_frame",
    "equity_frame",
    "failed_candidates_frame",
    "fair_budget_report",
    "fold_winners_frame",
    "folds_frame",
    "generation_best_frame",
    "load_run",
    "search_protocol",
    "trades_frame",
    "warning_messages",
]
