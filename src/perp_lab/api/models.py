"""Versioned (v1) Pydantic response models — the frontend contract.

These models are the single source of truth for the API schema. The frontend's
TypeScript types must match them (see ``apps/web/src/lib/api-types.ts``, which is
kept aligned with these definitions and checked by a contract test).
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "perp-lab-api"
    api_version: str
    environment: str
    artifact_root_exists: bool
    runs_available: int


class PageMeta(BaseModel):
    total: int
    limit: int
    offset: int
    returned: int


class RunSummaryModel(BaseModel):
    run_id: str
    kind: str = Field(description="synthetic-smoke | development | final-holdout | unknown")
    label: str
    family: str
    algorithm: str
    symbol: str
    timeframe: str
    seed: int | None = None
    budget: int | None = None
    n_folds: int | None = None
    best_method: str | None = None
    has_comparison: bool


class RunListResponse(BaseModel):
    items: list[RunSummaryModel]
    meta: PageMeta


class RunDetailResponse(BaseModel):
    run_id: str
    kind: str
    summary: dict[str, Any] | None
    config: dict[str, Any] | None
    environment: dict[str, Any] | None
    git_state: dict[str, Any] | None
    available_methods: list[str]
    artifact_files: list[str]
    warnings: list[str]


class MethodComparison(BaseModel):
    method: str
    evaluated: int | None = None
    feasible: int | None = None
    best_val_fitness: float | None = None
    mean_test_sharpe: float | None = None
    mean_test_total_return: float | None = None
    mean_test_max_drawdown: float | None = None
    mean_test_ann_return: float | None = None
    mean_test_n_trades: float | None = None
    n_fold_winners: int | None = None


class FairBudgetRow(BaseModel):
    method: str
    budget: int | None = None
    proposed: int | None = None
    invalid: int | None = None
    duplicate: int | None = None
    cached: int | None = None
    evaluated: int | None = None
    unique_candidates: int | None = None
    within_budget: bool | None = None


class FairBudget(BaseModel):
    budget: int | None = None
    definition: str | None = None
    ok: bool
    rows: list[FairBudgetRow]


class ComparisonResponse(BaseModel):
    run_id: str
    kind: str
    family: str
    symbol: str
    timeframe: str
    budget: int | None = None
    comparison_metric: str | None = None
    best_out_of_sample_method: str | None = None
    warning: str | None = None
    methods: list[MethodComparison]
    fair_budget: FairBudget


class CandidateModel(BaseModel):
    candidate_id: str
    family: str | None = None
    status: str | None = None
    fitness: float | None = None
    failure_reason: str | None = None
    step: int | None = None
    n_active_params: int | None = None
    mean_val_sharpe: float | None = None
    params: dict[str, Any] = Field(default_factory=dict)
    objective_components: dict[str, float] = Field(default_factory=dict)


class CandidatesResponse(BaseModel):
    run_id: str
    method: str
    items: list[CandidateModel]
    meta: PageMeta


class FoldModel(BaseModel):
    fold: int | None = None
    train_start: str | None = None
    train_end: str | None = None
    val_start: str | None = None
    val_end: str | None = None
    test_start: str | None = None
    test_end: str | None = None
    purge_bars: int | None = None
    embargo_bars: int | None = None


class FoldWinnerModel(BaseModel):
    fold: int | None = None
    winner: str | None = None
    val_sharpe: float | None = None
    test_sharpe: float | None = None
    test_total_return: float | None = None
    test_max_drawdown: float | None = None
    test_ann_return: float | None = None
    test_n_trades: float | None = None
    params: dict[str, Any] = Field(default_factory=dict)


class FoldsResponse(BaseModel):
    run_id: str
    regime_inputs: list[str]
    folds: list[FoldModel]
    winners: dict[str, list[FoldWinnerModel]]


class GaGenerationDiversity(BaseModel):
    generation: int
    param_diversity: float | None = None
    unique_ratio: float | None = None


class ConvergencePoint(BaseModel):
    evaluation: int
    best_fitness: float | None = None


class SearchAnalyticsResponse(BaseModel):
    run_id: str
    convergence: dict[str, list[ConvergencePoint]]
    ga_diversity: list[GaGenerationDiversity]
    ga_generation_best: list[dict[str, Any]]
    ga_lineage: list[dict[str, Any]]


class EquityPoint(BaseModel):
    open_time: str
    equity: float | None = None
    drawdown: float | None = None


class PerformanceFold(BaseModel):
    method: str
    fold: int
    n_points: int
    final_equity: float | None = None
    max_drawdown: float | None = None
    n_trades: int
    candidate_id: str | None = None
    period_start: str | None = None
    period_end: str | None = None


class PerformanceResponse(BaseModel):
    run_id: str
    kind: str
    warning: str | None = None
    aggregate: dict[str, dict[str, float | int]]
    folds: list[PerformanceFold]
    best_method: str | None = None


class EquitySeriesSummary(BaseModel):
    """Metrics computed from the full equity series (not the paginated window)."""

    n_points_total: int
    final_equity: float | None = None
    max_drawdown: float | None = None
    period_start: str | None = None
    period_end: str | None = None
    candidate_id: str | None = None


class EquityResponse(BaseModel):
    run_id: str
    method: str
    fold: int
    points: list[EquityPoint]
    meta: PageMeta
    summary: EquitySeriesSummary


class TradeModel(BaseModel):
    trade_id: int | None = None
    entry_time: str | None = None
    exit_time: str | None = None
    n_bars: int | None = None
    position: float | None = None
    net_return: float | None = None
    funding: float | None = None
    cost: float | None = None
    exit_reason: str | None = None


class TradesResponse(BaseModel):
    run_id: str
    method: str
    fold: int
    items: list[TradeModel]
    meta: PageMeta


class ArtifactsResponse(BaseModel):
    run_id: str
    dataset_manifests: dict[str, Any] | None
    feature_manifest: dict[str, Any] | None
    search_space: dict[str, Any] | None
    objective: dict[str, Any] | None
    environment: dict[str, Any] | None
    git_state: dict[str, Any] | None
    warnings: list[str]
    failed_candidates: dict[str, list[dict[str, Any]]]
    files: list[str]


class DatasetCoverage(BaseModel):
    dataset_id: str
    classification: str
    provider: str
    symbol: str | None = None
    timeframe: str | None = None
    stream: str | None = None
    row_count: int | None = None
    min_timestamp: str | None = None
    max_timestamp: str | None = None
    duplicate_timestamps: int | None = None
    missing_intervals: int | None = None
    crosses_holdout: bool | None = None
    checksum_matches: bool | None = None


class MarketCoverageResponse(BaseModel):
    holdout_start: str
    development_end_max: str | None = None
    datasets: list[DatasetCoverage]


class OhlcvBar(BaseModel):
    open_time: str
    open: float
    high: float
    low: float
    close: float
    volume: float


class OhlcvResponse(BaseModel):
    symbol: str
    timeframe: str
    partition: str = "development"
    holdout_excluded: bool
    bars: list[OhlcvBar]
    meta: PageMeta


class ErrorResponse(BaseModel):
    error: str
    detail: str
    request_id: str | None = None


# ---------------------------------------------------------------------------
# Research dashboard (narrative layer)
# ---------------------------------------------------------------------------


class ResearchSummaryResponse(BaseModel):
    holdout_start: str
    runs_total: int
    runs_development: int
    runs_synthetic: int
    pilot_run_id: str | None = None
    pilot_symbol: str | None = None
    pilot_timeframe: str | None = None
    pilot_interval: str | None = None
    pilot_budget: int | None = None
    pilot_evaluated: dict[str, int | None] = Field(default_factory=dict)
    pilot_folds: int | None = None
    pilot_seed: int | None = None
    pilot_fraction_of_dev_days: float | None = None
    artifact_root_exists: bool


class TimelineFold(BaseModel):
    index: int
    train_start: str | None = None
    train_end: str | None = None
    val_start: str | None = None
    val_end: str | None = None
    test_start: str | None = None
    test_end: str | None = None
    purge_bars: int | None = None
    embargo_bars: int | None = None


class TimelineResponse(BaseModel):
    run_id: str
    symbol: str
    timeframe: str
    holdout_start: str
    development_start: str | None = None
    development_end: str | None = None
    development_bars: int | None = None
    pilot_used_start: str | None = None
    pilot_used_end: str | None = None
    pilot_used_days: int | None = None
    pilot_used_pct_of_dev: float | None = None
    pilot_unused_pct_of_dev: float | None = None
    n_folds: int
    folds: list[TimelineFold]


class ValidityCheck(BaseModel):
    id: str
    label_es: str
    status: Literal["pass", "warn", "fail"]
    detail_es: str


class ValidityWarning(BaseModel):
    code: str
    severity: Literal["info", "warn", "error"]
    message_es: str


class RunValidityResponse(BaseModel):
    run_id: str
    kind: str
    checks: list[ValidityCheck]
    warnings: list[ValidityWarning]
    budget: int | None = None
    random_search_evaluated: int | None = None
    genetic_algorithm_evaluated: int | None = None
    equal_effective_evaluations: bool | None = None


class EdaFigureModel(BaseModel):
    figure_id: str
    theme: str
    theme_label_es: str
    title_es: str
    caption_en: str
    research_question_es: str = ""
    finding_es: str = ""
    interpretation_es: str = ""
    implication_es: str = ""
    period: str | None = None
    notebook: str | None = None
    is_key_finding: bool
    has_pdf: bool


class EdaSummaryResponse(BaseModel):
    holdout_start: str
    development_period: str | None = None
    n_figures: int
    n_key_findings: int
    themes: list[str]


class EdaFiguresResponse(BaseModel):
    items: list[EdaFigureModel]
    meta: PageMeta


class FeatureDocModel(BaseModel):
    name: str
    family: str
    formula: str
    inputs: list[str]
    lag_bars: int | None = None
    warmup_bars: int | None = None
    interpretation_es: str = ""


class StrategyDocModel(BaseModel):
    family: str
    name_es: str
    hypothesis_es: str
    status: str
    parameters: list[str] = Field(default_factory=list)


class MethodologyResponse(BaseModel):
    features: list[FeatureDocModel]
    strategies: list[StrategyDocModel]
    source_run_id: str | None = None
