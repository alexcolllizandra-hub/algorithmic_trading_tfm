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
};

const warning =
  "EXPLORATORY fixture result (synthetic). Not real BTC/ETH performance and not final holdout.";

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
    fair_budget: {
      budget: 12,
      definition: "budget caps UNIQUE objective evaluations; invalid/duplicate/cached excluded",
      ok: true,
      rows: [
        {
          method: "random_search",
          budget: 12,
          proposed: 14,
          invalid: 1,
          duplicate: 1,
          cached: 0,
          evaluated: 12,
          unique_candidates: 12,
          within_budget: true,
        },
        {
          method: "genetic_algorithm",
          budget: 12,
          proposed: 12,
          invalid: 1,
          duplicate: 1,
          cached: 0,
          evaluated: 10,
          unique_candidates: 10,
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
    convergence: {
      random_search: [
        { evaluation: 1, best_fitness: -0.2 },
        { evaluation: 2, best_fitness: -0.1 },
      ],
      genetic_algorithm: [
        { evaluation: 1, best_fitness: -0.1 },
        { evaluation: 2, best_fitness: 0.3 },
      ],
    },
    ga_diversity: [
      { generation: 0, param_diversity: 0.8, unique_ratio: 1.0 },
      { generation: 1, param_diversity: 0.5, unique_ratio: 0.75 },
    ],
    ga_generation_best: [{ generation: 0, best_candidate_id: "momentum-ga-0", best_fitness: 0.3 }],
    ga_lineage: [{ generation: 1, child: "momentum-ga-1", parents: ["momentum-ga-0"] }],
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
