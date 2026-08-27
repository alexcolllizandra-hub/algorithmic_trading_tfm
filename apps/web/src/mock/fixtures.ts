// Clearly-labelled SYNTHETIC fixtures used only for standalone frontend runs
// and Playwright E2E (no Python API required). The run id and label both shout
// "fixture/synthetic" so these can never be mistaken for real results.

const RUN_ID = "fixture_synthetic_momentum_e2e_run01";

const runSummary = {
  run_id: RUN_ID,
  kind: "synthetic-smoke" as const,
  label: "fixture_synthetic_NOT_a_research_result",
  family: "momentum",
  algorithm: "comparison",
  symbol: "BTCUSDT",
  timeframe: "1h",
  seed: 7,
  budget: 12,
  n_folds: 2,
  best_method: "genetic_algorithm",
  has_comparison: true,
  protocol: "independent_search_per_outer_fold",
  contaminated: false,
};

const warning =
  "EXPLORATORY fixture result (synthetic). Not real BTC/ETH performance and not final holdout.";

const FIXTURE_TAG = "FIXTURE SINTÉTICO — no es un resultado de investigación";

/** Deterministic curve so the fixtures never change between runs. */
function studyCurve(n: number, drift: number, wobble: number, offset: number) {
  const points: { t: string; equity: number }[] = [];
  let equity = 1;
  for (let i = 0; i < n; i += 1) {
    equity *= 1 + drift + wobble * Math.sin(i * 0.9 + offset);
    points.push({
      t: new Date(Date.UTC(2024, 0, 1 + i)).toISOString(),
      equity: Number(equity.toFixed(6)),
    });
  }
  return points;
}

function studyFan(drift: number, offset: number) {
  const n = 12;
  const checkpoint_index: number[] = [];
  const bands: Record<string, number[]> = { p05: [], p25: [], p50: [], p75: [], p95: [] };
  const observed: number[] = [];
  for (let i = 0; i < n; i += 1) {
    const t = i / (n - 1);
    const center = 1 + drift * i;
    const width = 0.02 + 0.12 * t;
    checkpoint_index.push(i * 24);
    bands.p05.push(Number((center - 2 * width).toFixed(6)));
    bands.p25.push(Number((center - width).toFixed(6)));
    bands.p50.push(Number(center.toFixed(6)));
    bands.p75.push(Number((center + width).toFixed(6)));
    bands.p95.push(Number((center + 2 * width).toFixed(6)));
    observed.push(Number((center + 0.4 * width * Math.sin(i + offset)).toFixed(6)));
  }
  return { checkpoint_index, bands, observed };
}

function studySeeds(seeds: number[], drift: number) {
  return seeds.map((seed, i) => {
    const equity = studyCurve(24, drift + (i - 1) * 0.004, 0.006, seed % 7);
    const last = equity[equity.length - 1].equity;
    return {
      seed,
      total_return: Number((last - 1).toFixed(6)),
      sharpe: Number((-0.4 + i * 0.35).toFixed(4)),
      max_drawdown: Number((-0.05 - i * 0.03).toFixed(4)),
      n_bars: 24,
      equity,
    };
  });
}

const fixtureCriteria = [
  {
    key: "positive_total_return",
    label: "C1 positive return",
    passed: 6,
    of: 10,
    required: 6,
    met: true,
  },
  {
    key: "bootstrap_sharpe_ci_excludes_zero",
    label: "C2 bootstrap Sharpe CI",
    passed: 1,
    of: 10,
    required: 6,
    met: false,
  },
  {
    key: "survives_double_costs",
    label: "C3 survives 2x costs",
    passed: 3,
    of: 10,
    required: 6,
    met: false,
  },
  {
    key: "beats_buy_and_hold",
    label: "C4 beats buy-and-hold",
    passed: 2,
    of: 10,
    required: 6,
    met: false,
  },
  {
    key: "survives_drop_top_trades",
    label: "C5 drop top 5 trades",
    passed: 0,
    of: 10,
    required: 6,
    met: false,
  },
  {
    key: "not_confined_to_one_fold",
    label: "C6 fold locality",
    passed: 7,
    of: 10,
    required: 6,
    met: true,
  },
];

interface StudyFixtureFamily {
  key: string;
  family: string;
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
  criteria: typeof fixtureCriteria | null;
  buy_and_hold_return: number | null;
  equity: { t: string; equity: number }[];
  seeds: ReturnType<typeof studySeeds>;
  monte_carlo: Record<string, unknown>;
  min_trades_veto: { passed: number; of: number; triggered: boolean } | null;
}

function studyFamily(
  overrides: Partial<StudyFixtureFamily> & {
    family: string;
    gate: string;
    symbol: string;
    total_return: number;
  }
): StudyFixtureFamily {
  const drift = overrides.total_return / 24;
  const fan = studyFan(drift, overrides.symbol === "ETHUSDT" ? 2 : 0);
  return {
    key: `${overrides.family}|${overrides.symbol}`,
    thesis: `${FIXTURE_TAG}: hipótesis de ejemplo para ${overrides.family}.`,
    n_seeds: 3,
    n_bars: 24,
    sharpe: -0.5,
    max_drawdown: -0.18,
    p_value: 0.42,
    holm_adjusted_p: 1.0,
    bh_adjusted_p: 0.99,
    survives_correction: false,
    verdict: "REJECTED",
    gate_note: null,
    criteria: null,
    buy_and_hold_return: 0.1234,
    equity: studyCurve(24, drift, 0.004, overrides.symbol === "ETHUSDT" ? 1.5 : 0),
    seeds: studySeeds([101, 202, 303], drift),
    monte_carlo: {
      method: "stationary_bootstrap",
      n_paths: 100,
      expected_block_bars: 24,
      seed: 20260813,
      measures: "path_risk_not_significance",
      ...fan,
      terminal: {
        observed_total_return: overrides.total_return,
        p05: Number((overrides.total_return - 0.3).toFixed(4)),
        p25: Number((overrides.total_return - 0.12).toFixed(4)),
        p50: Number((overrides.total_return + 0.01).toFixed(4)),
        p75: Number((overrides.total_return + 0.15).toFixed(4)),
        p95: Number((overrides.total_return + 0.42).toFixed(4)),
        probability_positive: 0.51,
      },
    },
    min_trades_veto: null,
    ...overrides,
  };
}

const STUDY_FAMILIES: StudyFixtureFamily[] = [
  studyFamily({
    family: "volatility_breakout",
    gate: "R3",
    symbol: "BTCUSDT",
    total_return: 0.0421,
    sharpe: 0.18,
    p_value: 0.312,
    holm_adjusted_p: 1.0,
    bh_adjusted_p: 0.984,
    gate_note: "partial non-robust signal (not promotion-eligible)",
    criteria: fixtureCriteria,
    min_trades_veto: { passed: 9, of: 10, triggered: false },
  }),
  studyFamily({
    family: "taker_flow_extreme",
    gate: "S2",
    symbol: "BTCUSDT",
    total_return: 0.0087,
    sharpe: 0.05,
    p_value: 0.463,
  }),
  studyFamily({
    family: "momentum",
    gate: "R2",
    symbol: "BTCUSDT",
    total_return: -0.1533,
    sharpe: -0.24,
    p_value: 0.671,
  }),
  studyFamily({
    family: "volatility_breakout",
    gate: "R3",
    symbol: "ETHUSDT",
    total_return: -0.2718,
    sharpe: -0.63,
    p_value: 0.905,
    holm_adjusted_p: null,
    bh_adjusted_p: null,
    criteria: fixtureCriteria,
    min_trades_veto: { passed: 10, of: 10, triggered: false },
  }),
];

const STUDY_FAMILY_BY_KEY: Record<string, StudyFixtureFamily> = Object.fromEntries(
  STUDY_FAMILIES.map((f) => [f.key, f])
);

const adjusted = (value: number) => ({
  volatility_breakout: value,
  taker_flow_extreme: value,
  momentum: value,
});

const studySummaryFixture = {
  generated_at: "2026-08-13T10:00:00+00:00",
  schema_version: 1,
  primary_symbol: "BTCUSDT",
  secondary_symbol: "ETHUSDT",
  primary_engine: "random_search",
  timeframe: "1h",
  study: {
    n_families: 3,
    n_units: 22,
    n_configurations_evaluated: 12345,
    alpha: 0.05,
    best_family: "volatility_breakout",
    holm: { n_rejected: 0, adjusted_p_values: adjusted(1.0) },
    benjamini_hochberg: { n_rejected: 0, adjusted_p_values: adjusted(0.984) },
    pbo: {
      available: true,
      pbo: 0.472,
      n_splits: 70,
      n_partitions: 8,
      n_observations: 24,
      n_configurations: 3,
    },
    deflated_sharpe: {
      family_selection: {
        n_trials: 3,
        observed_sharpe_per_observation: 0.0019,
        benchmark_sharpe_per_observation: 0.0071,
        deflated_sharpe: 0.1421,
        probability_best_is_spurious: 0.8579,
      },
      all_configurations_evaluated: {
        n_trials: 12345,
        observed_sharpe_per_observation: 0.0019,
        benchmark_sharpe_per_observation: 0.0198,
        deflated_sharpe: 0.0012,
        probability_best_is_spurious: 0.9988,
      },
    },
    sensitivity: {
      families: {
        n_tests: 3,
        bonferroni_threshold: 0.0166,
        smallest_raw_p_value: 0.312,
        any_survive: false,
      },
      family_x_asset: {
        n_tests: 4,
        bonferroni_threshold: 0.0125,
        smallest_raw_p_value: 0.312,
        any_survive: false,
      },
    },
    criteria_by_gate: {
      R2: `${FIXTURE_TAG}: criterio de ejemplo para la ronda R2.`,
      R3: `${FIXTURE_TAG}: criterio de ejemplo para la ronda R3.`,
      S2: `${FIXTURE_TAG}: criterio de ejemplo para la ronda S2.`,
    },
    conclusion: `${FIXTURE_TAG}. Ninguna familia de este fixture sobrevive a la corrección; los valores son inventados para probar la interfaz.`,
    source_commit: "0000000fixture",
  },
  // Mirrors the API, which strips curves, seeds and the fan from the summary.
  families: STUDY_FAMILIES.map((f) => ({
    key: f.key,
    family: f.family,
    gate: f.gate,
    symbol: f.symbol,
    thesis: f.thesis,
    n_seeds: f.n_seeds,
    n_bars: f.n_bars,
    total_return: f.total_return,
    sharpe: f.sharpe,
    max_drawdown: f.max_drawdown,
    p_value: f.p_value,
    holm_adjusted_p: f.holm_adjusted_p,
    bh_adjusted_p: f.bh_adjusted_p,
    survives_correction: f.survives_correction,
    verdict: f.verdict,
    gate_note: f.gate_note,
    criteria: f.criteria,
    buy_and_hold_return: f.buy_and_hold_return,
  })),
  holdout_opened: false,
};

const studyRegimesFixture = {
  exploratory: true,
  cells: [
    {
      family: "volatility_breakout",
      gate: "R3",
      dimension: "volatility",
      regime: "high",
      n_bars: 900,
      share_of_bars: 0.18,
      mean_bar_return: -0.00002,
      total_return: -0.041,
      sharpe_annualised: -0.52,
      p_value: 0.72,
    },
    {
      family: "volatility_breakout",
      gate: "R3",
      dimension: "trend",
      regime: "up",
      n_bars: 2600,
      share_of_bars: 0.52,
      mean_bar_return: 0.00001,
      total_return: 0.031,
      sharpe_annualised: 0.28,
      p_value: 0.34,
    },
    {
      family: "momentum",
      gate: "R2",
      dimension: "volatility",
      regime: "low",
      n_bars: 2100,
      share_of_bars: 0.42,
      mean_bar_return: -0.00003,
      total_return: -0.078,
      sharpe_annualised: -0.61,
      p_value: 0.81,
    },
    {
      family: "momentum",
      gate: "R2",
      dimension: "trend",
      regime: "down",
      n_bars: 1900,
      share_of_bars: 0.38,
      mean_bar_return: -0.00004,
      total_return: -0.112,
      sharpe_annualised: -0.94,
      p_value: 0.93,
    },
  ],
  correction: {
    alpha: 0.05,
    n_cells: 4,
    n_testable_cells: 4,
    n_excluded_small_cells: 0,
    min_cell_bars: 500,
    holm_bonferroni: {
      n_rejected: 0,
      adjusted_p_values: {
        "volatility_breakout|volatility|high": 1.0,
        "volatility_breakout|trend|up": 1.0,
        "momentum|volatility|low": 1.0,
        "momentum|trend|down": 1.0,
      },
    },
    benjamini_hochberg: {
      n_rejected: 0,
      adjusted_p_values: {
        "volatility_breakout|volatility|high": 0.93,
        "volatility_breakout|trend|up": 0.93,
        "momentum|volatility|low": 0.93,
        "momentum|trend|down": 0.93,
      },
    },
    survivors: [],
  },
  candidate: null,
  conclusion: `${FIXTURE_TAG}: ninguna celda de ejemplo sobrevive a la corrección dentro de este bloque exploratorio.`,
};

// The frozen partition is UNAUDITED: the locked payload carries no metrics at
// all, and the UI must not render provenance/result/buy_and_hold even if sent.
const studyHoldoutFixture = {
  status: "HOLDOUT_LOCKED",
  opened: false,
  period: "2026-01-01 .. 2026-06-30 (ventana reservada, FIXTURE)",
  reason: `${FIXTURE_TAG}: la partición congelada permanece aislada porque su evaluación no ha sido auditada.`,
  requirements: [
    "Auditoría independiente del pipeline de evaluación del holdout.",
    "Verificación de que el candidato quedó congelado antes de abrir la partición.",
    "Comprobación de hashes SHA-256 de los datasets usados en la evaluación.",
    "Registro de commit, entorno y configuración resuelta en el momento de la apertura.",
  ],
  provenance: null,
  result: null,
  buy_and_hold: null,
};

/**
 * FIXTURE SINTÉTICO — a locked holdout payload that DOES carry a reading.
 *
 * The contract allows `provenance`, `result` and `buy_and_hold` to arrive
 * populated while the partition is still unaudited, and no view may render
 * them. Every value here is a recognisable sentinel so a leak test can assert
 * that none of it reaches the DOM. It is exported for tests only and is
 * deliberately NOT served by `resolveFixture`.
 */
export const HOLDOUT_LEAK_PROBE = {
  status: "HOLDOUT_LOCKED",
  opened: false,
  period: `${FIXTURE_TAG}: ventana reservada (sonda de fuga)`,
  reason: `${FIXTURE_TAG}: la partición congelada sigue sin auditar.`,
  requirements: [`${FIXTURE_TAG}: requisito de ejemplo para la sonda.`],
  provenance: {
    opened_at: "2026-07-01T00:00:00+00:00",
    partition_evaluated: "PROBE_final_holdout_do_not_render",
    is_research_result: false,
    git: { commit: "deadbeefcafe4242", branch: "probe", worktree_clean: true, dirty_paths: [] },
    candidate: {
      family: "PROBE_family_do_not_render",
      symbol: "BTCUSDT",
      timeframe: "1h",
      engine: "random_search",
      fold: 3,
      n_members: 2,
    },
    dataset_hashes: { probe: { sha256: "deadbeefcafe4242", rows: 987654, role: "holdout" } },
    costs: {
      fee_bps_per_side: 42.42,
      slippage_bps_per_side: 31.31,
      funding_treatment: "PROBE_funding_do_not_render",
      provisional: true,
    },
    annualization_days: 365,
  },
  result: {
    combined: {
      n_bars: 987654,
      total_return: 424.242,
      sharpe: 313.131,
      max_drawdown: -98.7654,
      n_trades: 987654,
    },
    costs_paid: { fees_and_slippage: 42.42, funding: 31.31, total: 98.7654 },
    per_member: [
      {
        seed: 4242,
        selection_fingerprint: "deadbeefcafe4242",
        metrics: { total_return: 424.242, sharpe: 313.131 },
      },
    ],
    n_bars: 987654,
    window: { start: "2026-01-01T00:00:00+00:00", end: "2026-06-30T23:00:00+00:00" },
  },
  buy_and_hold: { total_return: 313.131, sharpe: 42.42 },
};

/**
 * Digit runs and tokens that must never appear where a holdout is locked. Both
 * the raw values and their es-ES rendering are listed, because a leak would
 * surface formatted ("424,24 %") rather than raw.
 */
export const HOLDOUT_LEAK_SENTINELS = [
  "4242",
  "3131",
  "9876",
  "424,24",
  "313,13",
  "98,77",
  "987.654",
  "deadbeefcafe",
  "PROBE_final_holdout_do_not_render",
  "PROBE_family_do_not_render",
  "PROBE_funding_do_not_render",
];

export const FIXTURES: Record<string, unknown> = {
  "/health": {
    status: "ok",
    service: "perp-lab-api (MOCK)",
    api_version: "v1",
    environment: "mock",
    artifact_root_exists: true,
    runs_available: 1,
  },
  "/runs": { items: [runSummary], meta: { total: 1, limit: 200, offset: 0, returned: 1 } },
  [`/runs/${RUN_ID}`]: {
    run_id: RUN_ID,
    kind: "synthetic-smoke",
    summary: { warning },
    config: { family: "momentum", synthetic: true },
    environment: { python_version: "3.12" },
    git_state: { commit: "mock", dirty: true },
    available_methods: ["random_search", "genetic_algorithm"],
    artifact_files: ["comparison_summary.json", "folds.json"],
    warnings: [warning],
  },
  [`/runs/${RUN_ID}/comparison`]: {
    run_id: RUN_ID,
    kind: "synthetic-smoke",
    family: "momentum",
    symbol: "BTCUSDT",
    timeframe: "1h",
    budget: 12,
    comparison_metric: "aggregate OOS test sharpe of per-fold winners",
    best_out_of_sample_method: "genetic_algorithm",
    warning,
    methods: [
      {
        method: "random_search",
        evaluated: 12,
        feasible: 10,
        best_val_fitness: -0.1,
        mean_test_sharpe: -0.4,
        mean_test_total_return: -0.02,
        mean_test_max_drawdown: -0.2,
        mean_test_ann_return: -0.05,
        mean_test_n_trades: 22,
        n_fold_winners: 2,
      },
      {
        method: "genetic_algorithm",
        evaluated: 10,
        feasible: 8,
        best_val_fitness: 0.3,
        mean_test_sharpe: 0.25,
        mean_test_total_return: 0.03,
        mean_test_max_drawdown: -0.15,
        mean_test_ann_return: 0.06,
        mean_test_n_trades: 18,
        n_fold_winners: 2,
      },
    ],
    search_protocol: "independent_search_per_outer_fold",
    contaminated: false,
    fair_budget: {
      budget: 12,
      n_folds: 2,
      parity_level: "per outer fold",
      definition:
        "budget caps UNIQUE objective evaluations and is spent in full inside EVERY outer fold; invalid/duplicate/cached excluded",
      ok: true,
      rows: [
        {
          method: "random_search",
          budget: 12,
          n_folds_searched: 2,
          proposed: 28,
          invalid: 2,
          duplicate: 2,
          cached: 0,
          evaluated: 24,
          unique_candidates: 24,
          within_budget: true,
        },
        {
          method: "genetic_algorithm",
          budget: 12,
          n_folds_searched: 2,
          proposed: 26,
          invalid: 1,
          duplicate: 1,
          cached: 0,
          evaluated: 24,
          unique_candidates: 24,
          within_budget: true,
        },
      ],
    },
  },
  [`/runs/${RUN_ID}/folds`]: {
    run_id: RUN_ID,
    regime_inputs: ["rvol_96"],
    folds: [
      {
        fold: 0,
        train_start: "2020-01-01",
        train_end: "2021-12-31",
        val_start: "2022-01-01",
        val_end: "2022-03-31",
        test_start: "2022-04-01",
        test_end: "2022-06-30",
        purge_bars: 24,
        embargo_bars: 12,
      },
      {
        fold: 1,
        train_start: "2020-01-01",
        train_end: "2022-03-31",
        val_start: "2022-04-01",
        val_end: "2022-06-30",
        test_start: "2022-07-01",
        test_end: "2022-09-30",
        purge_bars: 24,
        embargo_bars: 12,
      },
    ],
    winners: {
      genetic_algorithm: [
        {
          fold: 0,
          winner: "momentum-ga-0",
          val_sharpe: 0.6,
          test_sharpe: 0.3,
          test_total_return: 0.04,
          test_max_drawdown: -0.12,
          test_ann_return: 0.08,
          test_n_trades: 20,
          params: { fast: 6, slow: 96 },
        },
        {
          fold: 1,
          winner: "momentum-ga-1",
          val_sharpe: 0.4,
          test_sharpe: 0.2,
          test_total_return: 0.02,
          test_max_drawdown: -0.18,
          test_ann_return: 0.04,
          test_n_trades: 16,
          params: { fast: 8, slow: 72 },
        },
      ],
    },
  },
  [`/runs/${RUN_ID}/candidates`]: {
    run_id: RUN_ID,
    method: "genetic_algorithm",
    items: [
      {
        candidate_id: "momentum-ga-0",
        family: "momentum",
        status: "evaluated",
        fitness: 0.3,
        failure_reason: null,
        step: 1,
        n_active_params: 2,
        mean_val_sharpe: 0.6,
        params: { fast: 6, slow: 96 },
        objective_components: { sharpe: 0.6 },
      },
      {
        candidate_id: "momentum-ga-1",
        family: "momentum",
        status: "evaluated",
        fitness: 0.2,
        failure_reason: null,
        step: 2,
        n_active_params: 2,
        mean_val_sharpe: 0.4,
        params: { fast: 8, slow: 72 },
        objective_components: { sharpe: 0.4 },
      },
    ],
    meta: { total: 2, limit: 50, offset: 0, returned: 2 },
  },
  [`/runs/${RUN_ID}/analytics`]: {
    run_id: RUN_ID,
    search_protocol: "independent_search_per_outer_fold",
    convergence_folds: [0, 1],
    convergence: {
      random_search: [
        { fold: 0, evaluation: 1, best_fitness: -0.2 },
        { fold: 0, evaluation: 2, best_fitness: -0.1 },
        { fold: 1, evaluation: 1, best_fitness: -0.4 },
        { fold: 1, evaluation: 2, best_fitness: -0.05 },
      ],
      genetic_algorithm: [
        { fold: 0, evaluation: 1, best_fitness: -0.1 },
        { fold: 0, evaluation: 2, best_fitness: 0.3 },
        { fold: 1, evaluation: 1, best_fitness: -0.3 },
        { fold: 1, evaluation: 2, best_fitness: 0.1 },
      ],
    },
    ga_diversity: [
      { generation: 0, fold: 0, param_diversity: 0.8, unique_ratio: 1.0 },
      { generation: 1, fold: 0, param_diversity: 0.5, unique_ratio: 0.75 },
    ],
    ga_generation_best: [
      { generation: 0, fold: 0, best_candidate_id: "momentum-ga-0", best_fitness: 0.3 },
    ],
    ga_lineage: [{ generation: 1, fold: 0, child: "momentum-ga-1", parents: ["momentum-ga-0"] }],
  },
  [`/runs/${RUN_ID}/performance`]: {
    run_id: RUN_ID,
    kind: "synthetic-smoke",
    warning,
    aggregate: { genetic_algorithm: { mean_test_sharpe: 0.25, n_fold_winners: 2 } },
    folds: [
      {
        method: "genetic_algorithm",
        fold: 0,
        n_points: 3,
        final_equity: 1.04,
        max_drawdown: -0.12,
        n_trades: 2,
        candidate_id: "momentum-ga-0",
        period_start: "2022-04-01T00:00:00Z",
        period_end: "2022-04-03T00:00:00Z",
      },
    ],
    best_method: "genetic_algorithm",
  },
  [`/runs/${RUN_ID}/equity`]: {
    run_id: RUN_ID,
    method: "genetic_algorithm",
    fold: 0,
    points: [
      { open_time: "2022-04-01T00:00:00Z", equity: 1.0, drawdown: 0.0 },
      { open_time: "2022-04-02T00:00:00Z", equity: 1.02, drawdown: -0.01 },
      { open_time: "2022-04-03T00:00:00Z", equity: 1.04, drawdown: 0.0 },
    ],
    meta: { total: 3, limit: 5000, offset: 0, returned: 3 },
    summary: {
      n_points_total: 3,
      final_equity: 1.04,
      max_drawdown: -0.12,
      period_start: "2022-04-01T00:00:00Z",
      period_end: "2022-04-03T00:00:00Z",
      candidate_id: "momentum-ga-0",
    },
  },
  [`/runs/${RUN_ID}/trades`]: {
    run_id: RUN_ID,
    method: "genetic_algorithm",
    fold: 0,
    items: [
      {
        trade_id: 1,
        entry_time: "2022-04-01T00:00:00Z",
        exit_time: "2022-04-02T00:00:00Z",
        n_bars: 24,
        position: 1,
        net_return: 0.02,
        funding: -0.001,
        cost: 0.0002,
        exit_reason: "signal",
      },
    ],
    meta: { total: 1, limit: 100, offset: 0, returned: 1 },
  },
  [`/runs/${RUN_ID}/artifacts`]: {
    run_id: RUN_ID,
    dataset_manifests: { synthetic: { row_count: 1500, sha256: null } },
    feature_manifest: { symbol: "BTCUSDT", timeframe: "1h", n_features: 5 },
    search_space: { family: "momentum", params: [{ name: "fast", kind: "int" }] },
    objective: { weights: { sharpe: 1.0 } },
    environment: { python_version: "3.12" },
    git_state: { commit: "mock", dirty: true },
    warnings: [warning],
    failed_candidates: { random_search: [], genetic_algorithm: [] },
    files: ["comparison_summary.json", "folds.json", "genetic_algorithm_candidates.parquet"],
  },
  "/market/coverage": {
    holdout_start: "2026-01-01T00:00:00+00:00",
    development_end_max: "2025-12-31T23:00:00+00:00",
    datasets: [
      {
        dataset_id: "binance_um_BTCUSDT_klines_1h_development",
        classification: "REAL_HISTORICAL",
        provider: "binance_vision",
        symbol: "BTCUSDT",
        timeframe: "1h",
        stream: "klines",
        row_count: 52608,
        min_timestamp: "2020-01-01T00:00:00+00:00",
        max_timestamp: "2025-12-31T23:00:00+00:00",
        duplicate_timestamps: 0,
        missing_intervals: 0,
        crosses_holdout: false,
        checksum_matches: true,
      },
    ],
  },
  "/market/ohlcv": {
    symbol: "BTCUSDT",
    timeframe: "1h",
    partition: "development",
    holdout_excluded: true,
    bars: Array.from({ length: 60 }, (_, i) => {
      const base = 30000 + i * 50;
      return {
        open_time: new Date(Date.UTC(2020, 0, 1 + i)).toISOString(),
        open: base,
        high: base + 120,
        low: base - 100,
        close: base + (i % 2 === 0 ? 60 : -40),
        volume: 1000 + i,
      };
    }),
    meta: { total: 60, limit: 1500, offset: 0, returned: 60 },
  },
  "/research/summary": {
    holdout_start: "2026-01-01T00:00:00+00:00",
    runs_total: 1,
    runs_development: 0,
    runs_synthetic: 1,
    pilot_run_id: RUN_ID,
    pilot_symbol: "BTCUSDT",
    pilot_timeframe: "1h",
    pilot_interval: "2022-04-01 .. 2022-06-30",
    pilot_budget: 18,
    pilot_evaluated: { random_search: 18, genetic_algorithm: 16 },
    pilot_folds: 3,
    pilot_seed: 7,
    pilot_fraction_of_dev_days: 8.5,
    artifact_root_exists: true,
  },
  "/research/timeline": {
    run_id: RUN_ID,
    symbol: "BTCUSDT",
    timeframe: "1h",
    holdout_start: "2026-01-01T00:00:00+00:00",
    development_start: "2020-01-01T00:00:00+00:00",
    development_end: "2025-12-31T23:00:00+00:00",
    development_bars: 52608,
    pilot_used_start: "2022-04-01T00:00:00+00:00",
    pilot_used_end: "2022-06-30T00:00:00+00:00",
    pilot_used_days: 90,
    pilot_used_pct_of_dev: 8.5,
    pilot_unused_pct_of_dev: 91.5,
    n_folds: 3,
    folds: [
      {
        index: 0,
        train_start: "2020-01-01T00:00:00+00:00",
        train_end: "2021-12-01T00:00:00+00:00",
        val_start: "2021-12-15T00:00:00+00:00",
        val_end: "2022-03-15T00:00:00+00:00",
        test_start: "2022-04-01T00:00:00+00:00",
        test_end: "2022-06-30T00:00:00+00:00",
        purge_bars: 96,
        embargo_bars: 118,
      },
    ],
  },
  "/eda/summary": {
    holdout_start: "2026-01-01T00:00:00+00:00",
    development_period: "2020-01-01 .. 2025-12-31 (development)",
    n_figures: 25,
    n_key_findings: 6,
    themes: ["Calidad y cobertura de datos", "Precios y retornos"],
  },
  "/eda/figures": {
    items: [
      {
        figure_id: "f05_return_distribution_shape",
        theme: "precios_retornos",
        theme_label_es: "Precios y retornos",
        title_es: "Forma de la distribución de retornos",
        caption_en: "Return distribution shape (fixture)",
        research_question_es: "¿Los retornos son gaussianos?",
        finding_es: "Colas pesadas en BTC y ETH.",
        interpretation_es: "Ejemplo sintético para pruebas.",
        implication_es: "Usar medidas de riesgo empíricas.",
        period: "development",
        notebook: "01_comprehensive_exploratory_data_analysis",
        is_key_finding: true,
        has_pdf: true,
      },
    ],
    meta: { total: 1, limit: 100, offset: 0, returned: 1 },
  },
  "/methodology/features": {
    features: [
      {
        name: "log_return_1",
        family: "returns",
        formula: "ln(P_t / P_{t-1})",
        inputs: ["close"],
        lag_bars: 1,
        warmup_bars: 1,
        interpretation_es: "Retorno logarítmico causal.",
      },
    ],
    strategies: [
      {
        family: "momentum",
        name_es: "Momentum (cruce de medias)",
        hypothesis_es: "Persistencia direccional.",
        status: "implementada",
        parameters: ["fast", "slow"],
      },
    ],
    source_run_id: RUN_ID,
  },
  [`/runs/${RUN_ID}/validity`]: {
    run_id: RUN_ID,
    kind: "synthetic-smoke",
    checks: [
      {
        id: "equal_effective_evaluations",
        label_es: "Evaluaciones efectivas RS vs GA",
        status: "warn",
        detail_es: "RS: 18; GA: 16. Conteo desigual (fixture).",
      },
    ],
    warnings: [
      {
        code: "synthetic_fixture",
        severity: "error",
        message_es: "Ejecución con datos sintéticos: no usar como evidencia empírica.",
      },
    ],
    budget: 18,
    random_search_evaluated: 18,
    genetic_algorithm_evaluated: 16,
    equal_effective_evaluations: false,
  },
  "/study/summary": studySummaryFixture,
  "/study/regimes": studyRegimesFixture,
  "/study/holdout": studyHoldoutFixture,
  ...Object.fromEntries(STUDY_FAMILIES.map((f) => [`/study/families/${f.key}`, f])),
};

export function resolveFixture(pathname: string, searchParams?: URLSearchParams): unknown {
  const withoutQuery = pathname.split("?")[0] ?? pathname;
  const path = withoutQuery.replace(/\/$/, "") || "/";
  let data: unknown = null;
  if (FIXTURES[path] !== undefined) data = FIXTURES[path];
  else if (path.startsWith("/runs/") && path.endsWith("/validity"))
    data = FIXTURES[`/runs/${RUN_ID}/validity`];
  else if (path.startsWith("/runs/") && path.endsWith("/equity"))
    data = FIXTURES[`/runs/${RUN_ID}/equity`];
  else if (path.startsWith("/runs/") && path.endsWith("/performance"))
    data = FIXTURES[`/runs/${RUN_ID}/performance`];
  else if (path.startsWith("/methodology/")) data = FIXTURES["/methodology/features"];
  else if (path.startsWith("/study/families/")) {
    // The family key contains a pipe and arrives percent-decoded by the router.
    const key = decodeURIComponent(path.slice("/study/families/".length));
    data = STUDY_FAMILY_BY_KEY[key] ?? null;
  }

  if (path === "/eda/figures" && data && searchParams?.get("key_only") === "true") {
    const body = data as {
      items: Array<{ is_key_finding?: boolean }>;
      meta: { total?: number; limit?: number; offset?: number; returned?: number };
    };
    const filtered = body.items.filter((f) => f.is_key_finding);
    return {
      items: filtered,
      meta: { ...body.meta, total: filtered.length, returned: filtered.length },
    };
  }
  return data;
}
