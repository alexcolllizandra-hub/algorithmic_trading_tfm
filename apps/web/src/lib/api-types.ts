// TypeScript mirror of the API v1 Pydantic response models
// (src/perp_lab/api/models.py). Kept in strict sync; a contract test
// (src/test/contract.test.ts) checks the field sets against the live OpenAPI
// schema when an API base is available.

export type RunKind = "synthetic-smoke" | "development" | "final-holdout" | "unknown";

export interface PageMeta {
  total: number;
  limit: number;
  offset: number;
  returned: number;
}

export interface HealthResponse {
  status: string;
  service: string;
  api_version: string;
  environment: string;
  artifact_root_exists: boolean;
  runs_available: number;
}

export interface RunSummary {
  run_id: string;
  kind: RunKind;
  label: string;
  family: string;
  algorithm: string;
  symbol: string;
  timeframe: string;
  seed: number | null;
  budget: number | null;
  n_folds: number | null;
  best_method: string | null;
  has_comparison: boolean;
}

export interface RunListResponse {
  items: RunSummary[];
  meta: PageMeta;
}

export interface RunDetailResponse {
  run_id: string;
  kind: RunKind;
  summary: Record<string, unknown> | null;
  config: Record<string, unknown> | null;
  environment: Record<string, unknown> | null;
  git_state: Record<string, unknown> | null;
  available_methods: string[];
  artifact_files: string[];
  warnings: string[];
}

export interface MethodComparison {
  method: string;
  evaluated: number | null;
  feasible: number | null;
  best_val_fitness: number | null;
  mean_test_sharpe: number | null;
  mean_test_total_return: number | null;
  mean_test_max_drawdown: number | null;
  mean_test_ann_return: number | null;
  mean_test_n_trades: number | null;
  n_fold_winners: number | null;
}

export interface FairBudgetRow {
  method: string;
  budget: number | null;
  proposed: number | null;
  invalid: number | null;
  duplicate: number | null;
  cached: number | null;
  evaluated: number | null;
  unique_candidates: number | null;
  within_budget: boolean | null;
}

export interface FairBudget {
  budget: number | null;
  definition: string | null;
  ok: boolean;
  rows: FairBudgetRow[];
}

export interface ComparisonResponse {
  run_id: string;
  kind: RunKind;
  family: string;
  symbol: string;
  timeframe: string;
  budget: number | null;
  comparison_metric: string | null;
  best_out_of_sample_method: string | null;
  warning: string | null;
  methods: MethodComparison[];
  fair_budget: FairBudget;
}

export interface CandidateModel {
  candidate_id: string;
  family: string | null;
  status: string | null;
  fitness: number | null;
  failure_reason: string | null;
  step: number | null;
  n_active_params: number | null;
  mean_val_sharpe: number | null;
  params: Record<string, unknown>;
  objective_components: Record<string, number>;
}

export interface CandidatesResponse {
  run_id: string;
  method: string;
  items: CandidateModel[];
  meta: PageMeta;
}

export interface FoldModel {
  fold: number | null;
  train_start: string | null;
  train_end: string | null;
  val_start: string | null;
  val_end: string | null;
  test_start: string | null;
  test_end: string | null;
  purge_bars: number | null;
  embargo_bars: number | null;
}

export interface FoldWinnerModel {
  fold: number | null;
  winner: string | null;
  val_sharpe: number | null;
  test_sharpe: number | null;
  test_total_return: number | null;
  test_max_drawdown: number | null;
  test_ann_return: number | null;
  test_n_trades: number | null;
  params: Record<string, unknown>;
}

export interface FoldsResponse {
  run_id: string;
  regime_inputs: string[];
  folds: FoldModel[];
  winners: Record<string, FoldWinnerModel[]>;
}

export interface ConvergencePoint {
  evaluation: number;
  best_fitness: number | null;
}

export interface GaGenerationDiversity {
  generation: number;
  param_diversity: number | null;
  unique_ratio: number | null;
}

export interface SearchAnalyticsResponse {
  run_id: string;
  convergence: Record<string, ConvergencePoint[]>;
  ga_diversity: GaGenerationDiversity[];
  ga_generation_best: Record<string, unknown>[];
  ga_lineage: Record<string, unknown>[];
}

export interface PerformanceFold {
  method: string;
  fold: number;
  n_points: number;
  final_equity: number | null;
  max_drawdown: number | null;
  n_trades: number;
  candidate_id: string | null;
  period_start: string | null;
  period_end: string | null;
}

export interface PerformanceResponse {
  run_id: string;
  kind: RunKind;
  warning: string | null;
  aggregate: Record<string, Record<string, number>>;
  folds: PerformanceFold[];
  best_method: string | null;
}

export interface EquitySeriesSummary {
  n_points_total: number;
  final_equity: number | null;
  max_drawdown: number | null;
  period_start: string | null;
  period_end: string | null;
  candidate_id: string | null;
}

export interface EquityPoint {
  open_time: string;
  equity: number | null;
  drawdown: number | null;
}

export interface EquityResponse {
  run_id: string;
  method: string;
  fold: number;
  points: EquityPoint[];
  meta: PageMeta;
  summary: EquitySeriesSummary;
}

export interface TradeModel {
  trade_id: number | null;
  entry_time: string | null;
  exit_time: string | null;
  n_bars: number | null;
  position: number | null;
  net_return: number | null;
  funding: number | null;
  cost: number | null;
  exit_reason: string | null;
}

export interface TradesResponse {
  run_id: string;
  method: string;
  fold: number;
  items: TradeModel[];
  meta: PageMeta;
}

export interface ArtifactsResponse {
  run_id: string;
  dataset_manifests: Record<string, unknown> | null;
  feature_manifest: Record<string, unknown> | null;
  search_space: Record<string, unknown> | null;
  objective: Record<string, unknown> | null;
  environment: Record<string, unknown> | null;
  git_state: Record<string, unknown> | null;
  warnings: string[];
  failed_candidates: Record<string, Record<string, unknown>[]>;
  files: string[];
}

export interface DatasetCoverage {
  dataset_id: string;
  classification: string;
  provider: string;
  symbol: string | null;
  timeframe: string | null;
  stream: string | null;
  row_count: number | null;
  min_timestamp: string | null;
  max_timestamp: string | null;
  duplicate_timestamps: number | null;
  missing_intervals: number | null;
  crosses_holdout: boolean | null;
  checksum_matches: boolean | null;
}

export interface MarketCoverageResponse {
  holdout_start: string;
  development_end_max: string | null;
  datasets: DatasetCoverage[];
}

export interface OhlcvBar {
  open_time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface OhlcvResponse {
  symbol: string;
  timeframe: string;
  partition: string;
  holdout_excluded: boolean;
  bars: OhlcvBar[];
  meta: PageMeta;
}

export interface ResearchSummaryResponse {
  holdout_start: string;
  runs_total: number;
  runs_development: number;
  runs_synthetic: number;
  pilot_run_id: string | null;
  pilot_symbol: string | null;
  pilot_timeframe: string | null;
  pilot_interval: string | null;
  pilot_budget: number | null;
  pilot_evaluated: Record<string, number | null>;
  pilot_folds: number | null;
  pilot_seed: number | null;
  pilot_fraction_of_dev_days: number | null;
  artifact_root_exists: boolean;
}

export interface TimelineFold {
  index: number;
  train_start: string | null;
  train_end: string | null;
  val_start: string | null;
  val_end: string | null;
  test_start: string | null;
  test_end: string | null;
  purge_bars: number | null;
  embargo_bars: number | null;
}

export interface TimelineResponse {
  run_id: string;
  symbol: string;
  timeframe: string;
  holdout_start: string;
  development_start: string | null;
  development_end: string | null;
  development_bars: number | null;
  pilot_used_start: string | null;
  pilot_used_end: string | null;
  pilot_used_days: number | null;
  pilot_used_pct_of_dev: number | null;
  pilot_unused_pct_of_dev: number | null;
  n_folds: number;
  folds: TimelineFold[];
}

export interface ValidityCheck {
  id: string;
  label_es: string;
  status: "pass" | "warn" | "fail";
  detail_es: string;
}

export interface ValidityWarning {
  code: string;
  severity: "info" | "warn" | "error";
  message_es: string;
}

export interface RunValidityResponse {
  run_id: string;
  kind: RunKind;
  checks: ValidityCheck[];
  warnings: ValidityWarning[];
  budget: number | null;
  random_search_evaluated: number | null;
  genetic_algorithm_evaluated: number | null;
  equal_effective_evaluations: boolean | null;
}

export interface EdaFigureModel {
  figure_id: string;
  theme: string;
  theme_label_es: string;
  title_es: string;
  caption_en: string;
  research_question_es: string;
  finding_es: string;
  interpretation_es: string;
  implication_es: string;
  period: string | null;
  notebook: string | null;
  is_key_finding: boolean;
  has_pdf: boolean;
}

export interface EdaSummaryResponse {
  holdout_start: string;
  development_period: string | null;
  n_figures: number;
  n_key_findings: number;
  themes: string[];
}

export interface EdaFiguresResponse {
  items: EdaFigureModel[];
  meta: PageMeta;
}

export interface FeatureDocModel {
  name: string;
  family: string;
  formula: string;
  inputs: string[];
  lag_bars: number | null;
  warmup_bars: number | null;
  interpretation_es: string;
}

export interface StrategyDocModel {
  family: string;
  name_es: string;
  hypothesis_es: string;
  status: string;
  parameters: string[];
}

export interface MethodologyResponse {
  features: FeatureDocModel[];
  strategies: StrategyDocModel[];
  source_run_id: string | null;
}

/** Shared selection context for Results views — must stay synchronized. */
export interface FoldSelection {
  runId: string;
  method: string;
  fold: number;
  candidateId: string | null;
  periodStart: string | null;
  periodEnd: string | null;
}
