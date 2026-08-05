# Strategy-search framework: Random Search vs Genetic Algorithm

This document describes the `perp_lab.search` package: a reproducible, extensible
framework that discovers interpretable strategy configurations and **fairly**
compares two search strategies — deterministic **Random Search (RS)** and a
mixed-type **Genetic Algorithm (GA)** — under identical conditions.

Status legend: **[impl]** implemented · **[test]** unit/integration tested ·
**[smoke]** exercised end to end on synthetic data · **[cfg]** configured but not
yet run on real development data · **[future]** not implemented.

---

## 1. System architecture

```
configs/experiment.yaml  ──►  ExperimentConfig (validated)
        │                          │  (families, costs, walk-forward, fitness)
        ▼                          ▼
configs/search{,_smoke}.yaml ─► SearchRunConfig ──► runner.run_search
                                                        │
   data (validated dev bars | synthetic) ──► features (built once, causal)
                                                        │
              walk-forward folds (purge/embargo) ──► FoldsBundle
                                                        │  (per fold: regime fit on TRAIN only)
                                                        ▼
              ┌──────────────── CandidateEvaluator (shared) ────────────────┐
              │  build strategy via registry → signals → funding-aware       │
              │  backtester → validation metrics → objective (components)    │
              └──────────────────────────────────────────────────────────────┘
                       ▲                                   ▲
              run_random_search                    run_genetic_algorithm
                       └───────────── same space / folds / budget ───────────┘
                                                        │
                       per-fold winner (validation-best) → TEST once → artifacts
```

Key modules:

- `search/space.py` **[impl][test]** — typed parameter system (`IntParam`,
  `FloatParam` incl. log scale, `CategoricalParam`, `BoolParam`), conditional
  parameters, `SearchSpace` with sampling, per-parameter + family repair,
  validation, canonical serialization and stable `candidate_hash`.
- `search/registry.py` **[impl][test]** — builds a `SearchSpace` per family
  (`momentum`, `breakout`, `mean_reversion`) **from validated config**. Adding a
  family = register one builder; neither RS nor GA changes.
- `search/candidate.py` **[impl][test]** — the reproducible `Candidate` record.
- `search/objective.py` **[impl][test]** — component-wise objective + hard
  constraints + deterministic failure penalty.
- `search/evaluator.py` **[impl][test]** — the single leakage-safe evaluator and
  fold builder (`build_folds_data`, `CandidateEvaluator`).
- `search/random_search.py`, `search/genetic_algorithm.py` **[impl][test]**.
- `search/runner.py` **[impl][test][smoke]** — fair comparison + artifacts.
- `search/config.py` **[impl][test]** — strict `SearchRunConfig`.

## 2. Search lifecycle

1. Validate `SearchRunConfig` and load `ExperimentConfig`.
2. Load data (validated development bars, or an explicitly-labelled synthetic
   series for smoke runs) and, if `require_funding`, a funding frame.
3. Build the causal feature frame **once** (stateless, deterministic).
4. Generate expanding walk-forward folds (config purge/embargo) and assert the
   frozen holdout is excluded.
5. For each fold: fit a regime model on **train only** and attach regime labels
   causally to train/val/test.
6. Run RS and/or GA against the shared evaluator; each candidate is scored on
   **validation** across all folds → objective components → scalar fitness.
7. For each fold pick the **validation**-best feasible candidate (the "fold
   winner") and score it **once** on that fold's **test** slice.
8. Aggregate the fold winners' **test** metrics = the out-of-sample comparison
   metric. Write artifacts.

## 3. Fair-budget definition

The *budget* caps the number of **unique objective evaluations** (candidate
backtests). Applied identically to RS and GA:

- **invalid** proposals (failed parameter/family validation) — do **not** consume
  the budget;
- **duplicate** proposals (an already-seen `candidate_hash`) — do **not** consume
  the budget;
- **cached** re-encounters (GA elites / repeated offspring) — do **not** consume
  the budget;
- a candidate that is backtested but violates a hard constraint (**failed**) —
  **does** consume one evaluation (it used the objective).

Consequently the GA can never obtain more objective evaluations than RS at the
same budget. The comparison is decided on aggregated walk-forward **test**
metrics, never on the higher in-sample/validation score.

## 4. Objective and constraints

Computed on per-fold **validation** metrics only:

```
fitness = w_sharpe · mean_val_sharpe
        − w_max_drawdown · mean_val_drawdown
        − w_turnover · mean_val_turnover_per_bar
        − w_fold_instability · std(val_sharpe across folds)
        − w_complexity · max(n_active_params − 2, 0)
```

Weights come from `experiment.fitness.weights` (overridable per run). Every raw
component is stored on the candidate so the score is fully explainable.

Hard constraints (violation ⇒ explicit **failure** status + deterministic
penalty `FAILURE_PENALTY = −1e9`, never a silent attractive score):

- finite metrics only;
- minimum total trades (`min_trades_total`);
- minimum trades per fold (`min_trades_per_fold`);
- maximum permitted drawdown (`max_drawdown_limit`, optional);
- required funding availability when `require_funding` is set.

## 5. Temporal-selection protocol (leakage protections)

- Transformations and regime models are fitted on **train only** and applied
  unchanged to validation and test.
- Candidate ranking / GA evolution use **validation** metrics only.
- Test is touched **once**, for the already-selected fold winner.
- `build_folds_data` calls `assert_folds_exclude_holdout` and raises if any fold
  (or requested holdout boundary) overlaps the frozen holdout.
- The backtester is next-bar (`position = side.shift(1)`); no signal executes at
  its own close.

## 6. Parameter spaces (from config)

| Family | Parameters (types) | Conditional | Repair |
|---|---|---|---|
| momentum | `fast`, `slow`, `direction` (categorical); `use_trend_filter` (bool) → `trend_filter_ma`; `use_regime_gate` (bool) → `regime_gate` | trend/regime gates | force `fast < slow` |
| breakout | `channel_window`, `confirmation_bars`, `direction`; `use_regime_gate` → `regime_gate` | regime gate | — |
| mean_reversion | `zscore_window`, `entry_z`, `exit_z`, `direction`; `use_regime_gate` → `regime_gate` | regime gate | force `exit_z < entry_z` |

Choice lists come from `experiment.strategies.families.*`,
`strategies.allowed_directions` and `strategies.volatility_filter.regime_gate_options`.
Only exits/filters the backtester can execute are offered.

## 7. Random Search behaviour

Deterministic (`numpy.random.default_rng(seed)`): sample → repair → validate →
dedupe by hash → evaluate, until `budget` unique evaluations. Records exact
counters (proposed/invalid/duplicate/cached/evaluated), a monotone convergence
history (best feasible fitness after each evaluation) and the best feasible
candidate.

## 8. Genetic Algorithm operators

Mixed-type operators through the typed parameters:

- **initialisation**: unique sampled population (deterministic);
- **selection**: tournament (`tournament_size`);
- **crossover**: uniform per-gene at `crossover_rate`;
- **mutation**: per-parameter typed mutation at `mutation_rate` (int creep,
  float Gaussian/log-Gaussian, categorical swap, bool flip);
- **repair**: family repair after crossover/mutation (invalid offspring rejected);
- **elitism**: top-`elitism` carried over (cached, free);
- **duplicate handling**: within-population and global de-duplication by hash;
- **early termination** when the evaluation budget is exhausted.

Tracks per-generation best, population diversity (mean pairwise normalised
parameter distance + unique ratio) and full parent→offspring lineage.

## 9. Reproducibility & artifacts

`artifacts/runs/<run_id>/` (git-ignored) contains, where applicable:
`resolved_experiment_config.yaml`, `search_config.json`, `algorithms.json`,
`dataset_manifests.json`, `feature_manifest.json`, `search_space.json`,
`objective.json`, `folds.json` (partitions + per-fold regime params),
`environment.json`, `git_state.json`, `<method>_candidates.parquet`,
`<method>_failed_candidates.json`, `<method>_fold_winners.json`,
`<method>_convergence.json`, `ga_lineage.json`, `ga_diversity.json`,
`<best>_fold{i}_test_equity.parquet` + `_test_trades.parquet`,
`comparison_summary.json`, `comparison_report.md`, `metrics.json`,
`warnings.json`, `logs/`.

## 10. Commands

Installation:

```
uv sync --extra dev
```

Offline smoke run (synthetic data — **not** a research result):

```
uv run perp-lab search --config configs/search_smoke.yaml
```

Research runs (require `perp-lab download` first):

```
uv run perp-lab search --config configs/search.yaml --algorithm random_search
uv run perp-lab search --config configs/search.yaml --algorithm genetic_algorithm
uv run perp-lab search --config configs/search.yaml --algorithm comparison
```

Inspect a completed run:

```
uv run perp-lab search-summary artifacts/runs/<run_id>
```

Results are written under `artifacts/runs/<run_id>/`. Start with
`comparison_report.md` (human) and `comparison_summary.json` (machine); per-method
`_candidates.parquet` holds the full candidate ledger and `_fold_winners.json`
the out-of-sample test metrics.

## 11. Resume / rerun

Runs are deterministic given the seed and config, so re-running reproduces the
candidate ledger and convergence exactly. There is no partial-resume of an
interrupted run yet (**[future]**); rerun the command to regenerate a run.

## 12. Adding a new strategy family / parameter type

1. Implement the strategy (in `perp_lab.strategies`) with `params()`,
   `required_features()` and `signals()`.
2. Add a `SearchSpace` builder in `search/registry.py` (params from config, a
   `repair`, a `validate` and a `build` closure, and the feature items it needs).
3. Register it in `_BUILDERS`. RS, GA, evaluator, objective and artifacts work
   unchanged. New parameter *types* subclass `Param` (sample/is_valid/repair/
   mutate/describe).

## 13. Known limitations

- Breakout channels warm up **within** each validation/test slice (no cross-slice
  continuity), which slightly reduces early-slice breakout signals; this is
  causal and leakage-safe.
- Real development-data runs are **[cfg]** — verified offline on synthetic data;
  a full research run depends on a populated local data lake.
- No distributed execution, Docker, dashboard, paper trading, triple-barrier
  labeling or meta-labeling here (**[future]**).
