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
  /** Temporal contract the run was produced under (ADR 0012). */
  protocol: string;
  /** True when candidate selection could see other outer folds. */
  contaminated: boolean;
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
  /** Unique evaluations per outer fold. */
  budget: number | null;
  n_folds_searched: number | null;
  proposed: number | null;
  invalid: number | null;
  duplicate: number | null;
  cached: number | null;
  /** Total across all outer folds. */
  evaluated: number | null;
  unique_candidates: number | null;
  /** The engine reached the target in every outer fold. */
  within_budget: boolean | null;
}

export interface FairBudget {
  budget: number | null;
  n_folds: number | null;
  parity_level: string | null;
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
  search_protocol: string | null;
  contaminated: boolean;
  methods: MethodComparison[];
  fair_budget: FairBudget;
}

export interface CandidateModel {
  candidate_id: string;
  family: string | null;
  /** Outer fold whose isolated search produced this candidate. */
  fold_index: number | null;
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
  /** Hash of the winner, recorded before its test slice was scored. */
  selection_fingerprint: string | null;
  frozen_before_test: boolean | null;
  params: Record<string, unknown>;
}

export interface FoldsResponse {
  run_id: string;
  regime_inputs: string[];
  folds: FoldModel[];
  winners: Record<string, FoldWinnerModel[]>;
}

export interface ConvergencePoint {
  /** Each outer fold is searched independently and has its own trace. */
  fold: number;
  evaluation: number;
  best_fitness: number | null;
}

export interface GaGenerationDiversity {
  generation: number;
  fold: number | null;
  param_diversity: number | null;
  unique_ratio: number | null;
}

export interface SearchAnalyticsResponse {
  run_id: string;
  search_protocol: string | null;
  convergence_folds: number[];
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

// --------------------------------------------------------------------------- //
// Study closure — the whole study rather than a single run
// --------------------------------------------------------------------------- //

/** One of the six R3 promotion criteria, as scored across seeds. */
export interface StudyCriterion {
  key: string;
  label: string;
  passed: number;
  of: number;
  required: number;
  met: boolean;
}

/** One family on one asset, without its curves. */
export interface StudyFamilySummary {
  /** `family|SYMBOL` — contains a pipe, so encode it before putting it in a URL. */
  key: string;
  family: string;
  /** R2 | R3 | S1 | S2 */
  gate: string;
  symbol: string;
  thesis: string;
  n_seeds: number;
  n_bars: number;
  total_return: number;
  sharpe: number;
  max_drawdown: number;
  p_value: number | null;
  holm_adjusted_p: number | null;
  bh_adjusted_p: number | null;
  survives_correction: boolean;
  verdict: string;
  gate_note: string | null;
  criteria: StudyCriterion[] | null;
  buy_and_hold_return: number | null;
}

export interface StudyEquityPoint {
  t: string;
  equity: number;
}

export interface StudySeedResult {
  seed: number;
  total_return: number;
  sharpe: number;
  max_drawdown: number;
  n_bars: number;
  equity: StudyEquityPoint[];
}

export interface StudyMonteCarloTerminal {
  observed_total_return: number;
  p05: number;
  p25: number;
  p50: number;
  p75: number;
  p95: number;
  probability_positive: number;
}

/**
 * Resampling fan over the family's own returns. `measures` is part of the
 * contract, not decoration: the fan quantifies PATH RISK and cannot establish
 * that the mean is real, because resampling the observed series carries the
 * observed mean with it.
 */
export interface StudyMonteCarlo {
  method: string;
  n_paths: number;
  expected_block_bars: number;
  seed: number;
  /** e.g. `path_risk_not_significance` */
  measures: string;
  checkpoint_index: number[];
  bands: Record<string, number[]>;
  observed: number[];
  terminal: StudyMonteCarloTerminal;
}

/** Served as `dict[str, Any]`; the keys the closure report writes. */
export interface StudyMinTradesVeto {
  passed?: number;
  of?: number;
  triggered?: boolean;
}

export interface StudyFamilyDetail extends StudyFamilySummary {
  equity: StudyEquityPoint[];
  seeds: StudySeedResult[];
  monte_carlo: StudyMonteCarlo;
  min_trades_veto: StudyMinTradesVeto | null;
}

/** Served as `dict[str, Any]`; shape of the Holm / BH blocks. */
export interface StudyAdjustment {
  n_rejected?: number;
  adjusted_p_values?: Record<string, number>;
}

/** Served as `dict[str, Any]`; probability of backtest overfitting. */
export interface StudyPbo {
  available?: boolean;
  pbo?: number | null;
  n_splits?: number;
  n_partitions?: number;
  n_observations?: number;
  n_configurations?: number;
}

export interface StudyDeflatedSharpeEntry {
  n_trials?: number;
  observed_sharpe_per_observation?: number;
  benchmark_sharpe_per_observation?: number;
  deflated_sharpe?: number;
  probability_best_is_spurious?: number;
}

export interface StudySensitivityRow {
  n_tests?: number;
  bonferroni_threshold?: number;
  smallest_raw_p_value?: number;
  any_survive?: boolean;
}

export interface StudyCorrections {
  n_families: number;
  n_units: number;
  n_configurations_evaluated: number;
  alpha: number;
  best_family: string;
  holm: StudyAdjustment;
  benjamini_hochberg: StudyAdjustment;
  pbo: StudyPbo;
  /** Keyed by trial-counting rule (e.g. `family_selection`). */
  deflated_sharpe: Record<string, StudyDeflatedSharpeEntry>;
  /** Keyed by counting rule (e.g. `family_x_asset`). */
  sensitivity: Record<string, StudySensitivityRow>;
  criteria_by_gate: Record<string, string>;
  conclusion: string;
  source_commit: string | null;
}

export interface StudySummaryResponse {
  generated_at: string;
  schema_version: number;
  primary_symbol: string;
  secondary_symbol: string;
  primary_engine: string;
  timeframe: string;
  study: StudyCorrections;
  families: StudyFamilySummary[];
  holdout_opened: boolean;
}

/** Served as `dict[str, Any]`; one family x regime cell. */
export interface StudyRegimeCell {
  family?: string;
  gate?: string;
  dimension?: string;
  regime?: string;
  n_bars?: number;
  share_of_bars?: number;
  mean_bar_return?: number;
  total_return?: number;
  sharpe_annualised?: number;
  p_value?: number | null;
}

/** Served as `dict[str, Any]`; the correction applied inside the regime block. */
export interface StudyRegimeCorrection {
  alpha?: number;
  n_cells?: number;
  n_testable_cells?: number;
  n_excluded_small_cells?: number;
  min_cell_bars?: number;
  holm_bonferroni?: StudyAdjustment;
  benjamini_hochberg?: StudyAdjustment;
  survivors?: unknown[];
}

/** Exploratory by construction; the flag travels with the data. */
export interface StudyRegimesResponse {
  exploratory: boolean;
  cells: StudyRegimeCell[];
  correction: StudyRegimeCorrection;
  candidate: Record<string, unknown> | null;
  conclusion: string | null;
}

/** Served as `dict[str, Any]`; the metric block written by the backtester. */
export interface StudyHoldoutMetrics {
  n_bars?: number;
  total_return?: number;
  ann_return?: number;
  ann_volatility?: number;
  sharpe?: number;
  sortino?: number;
  max_drawdown?: number;
  calmar?: number;
  time_in_drawdown?: number;
  ulcer_index?: number;
  exposure?: number;
  hit_rate?: number;
  turnover?: number;
  n_trades?: number;
  funding_total?: number;
  gross_return_total?: number;
}

export interface StudyHoldoutMember {
  seed?: number;
  selection_fingerprint?: string | null;
  metrics?: StudyHoldoutMetrics;
}

export interface StudyHoldoutResult {
  combined?: StudyHoldoutMetrics;
  costs_paid?: { fees_and_slippage?: number; funding?: number; total?: number };
  per_member?: StudyHoldoutMember[];
  n_bars?: number;
  window?: { start?: string | null; end?: string | null };
}

export interface StudyHoldoutProvenance {
  opened_at?: string;
  partition_evaluated?: string;
  is_research_result?: boolean;
  git?: {
    commit?: string;
    branch?: string;
    worktree_clean?: boolean;
    dirty_paths?: string[];
  };
  candidate?: {
    family?: string;
    symbol?: string;
    timeframe?: string;
    engine?: string;
    fold?: number;
    n_members?: number;
  };
  dataset_hashes?: Record<string, { sha256?: string; rows?: number; role?: string }>;
  costs?: {
    fee_bps_per_side?: number;
    slippage_bps_per_side?: number;
    funding_treatment?: string;
    provisional?: boolean;
  };
  annualization_days?: number;
}

/**
 * State of the frozen partition. The reading is UNAUDITED, so the payload is
 * locked: `provenance`, `result` and `buy_and_hold` must never be rendered,
 * whether or not they arrive populated.
 */
export interface StudyHoldoutResponse {
  /** Expected `HOLDOUT_LOCKED`; part of the shared status vocabulary. */
  status: string;
  opened: boolean;
  /** Reserved window, described but not evaluated in the UI. */
  period: string | null;
  /** Why the partition stays isolated. */
  reason: string | null;
  /** What must be verified before any holdout number may be published. */
  requirements: string[];
  /** Present in the contract; deliberately never displayed. */
  provenance: StudyHoldoutProvenance | null;
  /** Present in the contract; deliberately never displayed. */
  result: StudyHoldoutResult | null;
  /** Present in the contract; deliberately never displayed. */
  buy_and_hold: StudyHoldoutMetrics | null;
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
