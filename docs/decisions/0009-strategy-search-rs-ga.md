# ADR 0009: Strategy-search framework — Random Search and Genetic Algorithm

- Status: Accepted
- Date: 2026-08-04
- Builds on: ADR 0008 (experimental foundation: features, regimes, strategy
  families, funding-aware backtester, walk-forward)

## Context

The experimental foundation (ADR 0008) provides causal features, fold-fit
regime models, three interpretable strategy families, a funding-aware next-bar
backtester and expanding walk-forward folds. The next step is to *discover*
strategy configurations and to compare two search strategies — Random Search
and a Genetic Algorithm — **fairly**, i.e. under identical spaces, folds,
backtester, objective, budget, seeds and failure handling.

Triple-barrier labeling, meta-labeling, the robustness battery, the dashboard
and paper trading remain out of scope and are not implemented.

## Decision

1. **Shared typed parameter spaces.** `search/space.py` introduces `IntParam`,
   `FloatParam` (optional log scale), `CategoricalParam`, `BoolParam` and
   conditional parameters, wrapped by a `SearchSpace` with deterministic
   sampling, per-parameter + family repair, validation, canonical serialization
   and a stable `candidate_hash`. `search/registry.py` builds one space per
   family **from validated config** (no duplicated constants), so new families
   or parameter types are added without touching either search algorithm.

2. **One reproducible candidate + one evaluator.** `search/candidate.py` records
   everything needed to rebuild and re-score a candidate. `search/evaluator.py`
   builds the causal feature frame once, pre-splits leakage-safe folds (regime
   models fitted on **train only**), and evaluates candidates on **validation**
   for selection and **once** on **test** for the fold winner. It reuses the
   existing funding-aware backtester — no second backtester is introduced — and
   caches per-candidate results within a run only (never across incompatible
   datasets/folds/configs).

3. **Transparent objective + hard constraints.** `search/objective.py` combines
   Sharpe, drawdown, turnover, fold instability and complexity with
   config-driven weights, stores every raw component, and turns constraint
   violations (finite metrics, min trades total/per-fold, max drawdown, required
   funding) into an explicit failure with a deterministic penalty.

4. **Fair-budget definition.** The budget caps **unique objective evaluations**.
   Invalid, duplicate and cached proposals do not consume it; a backtested but
   infeasible candidate does. Applied identically to RS and GA, so the GA can
   never buy extra evaluations. The comparison verdict uses aggregated
   walk-forward **test** metrics of fold winners, not in-sample/validation
   scores.

5. **Deterministic RS and mixed-type GA.** `search/random_search.py` samples,
   repairs, de-duplicates and evaluates until the budget is spent.
   `search/genetic_algorithm.py` adds tournament selection, uniform crossover,
   typed mutation, family repair, elitism, duplicate handling, budget-capped
   early termination, per-generation diversity and full lineage.

6. **Fair comparison + artifacts + CLI.** `search/runner.run_search` executes
   RS and/or GA under matched conditions and writes a run-specific artifact
   directory (candidate ledgers, failed ledgers, fold winners, convergence, GA
   lineage/diversity, fold-winner test outputs, comparison summary + human
   report, warnings). Strict `SearchRunConfig` (`search/config.py`) selects
   algorithm/family/data/geometry and reuses experiment-config budget parity,
   costs, walk-forward and fitness. New CLI commands: `perp-lab search` and
   `perp-lab search-summary`.

## Consequences

- RS and GA are fair by construction (shared space/folds/evaluator/objective/
  budget/seeds), and their comparison is reported on out-of-sample test folds
  with an explicit "exploratory, not final holdout" warning.
- The frozen holdout is never accessed; folds are guarded and the backtester is
  next-bar. All new checks passed the offline quality gate.
- Extensibility is preserved: a new strategy family is one registry builder; a
  new parameter type is one `Param` subclass.

## Alternatives considered

- A single search abstraction with pluggable operators — rejected as
  over-engineered for two algorithms; the shared *space + evaluator + objective*
  already guarantee fairness.
- Selecting winners on aggregate validation fitness only — rejected in favour of
  per-fold validation winners scored once on test, which matches the walk-forward
  out-of-sample protocol.
