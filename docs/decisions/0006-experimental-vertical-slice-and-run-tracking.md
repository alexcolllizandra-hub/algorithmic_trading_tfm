# ADR 0006: First experimental vertical slice and run-tracking contract

- Status: Accepted
- Date: 2026-08-03

> **Nota de estado añadida el 2026-08-16 — el cuerpo del ADR no se modifica.**
> La consecuencia «the frozen holdout remains untouched» describe el estado del
> 2026-08-03 y el comportamiento por defecto del cargador, que sigue siendo el
> descrito. La partición se abrió una vez el 2026-08-13 por la ruta explícita de
> Fase H; véase [holdout_audit_status.md](../methodology/holdout_audit_status.md).

## Context

Chapter 5 needs an executable, auditable pipeline built as small verified
slices, not a monolith. The methodology (`docs/methodology/`) specifies causal
features, next-bar execution, walk-forward validation, search and robustness.
Before any of the heavy components (walk-forward, Random Search, the Genetic
Algorithm, triple-barrier labeling, meta-labeling, holdout evaluation), we need
a minimal end-to-end path plus a reproducible record of every run.

## Decision

1. **Bounded vertical slice** under `src/perp_lab/`:
   - `config/experiment.py`: strict, frozen `ExperimentConfig` with cross-field
     validation (dates/holdout isolation, feature windows, strategy parameter
     bounds, RS/GA budget parity, derived purge/embargo).
   - `features/`: a small justified causal feature set with leakage tests.
   - `strategies/`: one interpretable momentum (MA-crossover) baseline.
   - `backtesting/`: next-bar, cost-aware engine (fees + adverse slippage on
     position changes) and 365-day annualised metrics.
   - `experiments/pipeline.py`: the orchestration; notebooks/CLI only consume it.
2. **Execution semantics.** A signal formed at the close of bar *t* is executed
   at the open of *t+1* (`position = side.shift(1)`, open-to-open return). Never
   the same-bar close. Slippage is charged on traded position change (adverse
   for both buys and sells). Funding is deferred (documented), not faked.
3. **Local run-tracking contract** (`tracking/`, `artifacts/runs/<run_id>/`):
   `resolved_config.yaml`, `dataset_manifests.json`, `environment.json`,
   `git_state.json`, `metrics.json`, `feature_metadata.json`, `trades.parquet`,
   `equity.parquet`, plus `logs/` and `figures/`. The run id ties resolved
   config, dataset hashes, git state, seed, metrics, selected strategy and
   artifacts. `artifacts/` is git-ignored. This precedes (and will later feed)
   MLflow rather than competing with it.
4. **CLI.** `perp-lab pipeline development` reuses the existing argparse + Rich
   logging; timestamped file logs; non-zero exit on failure.

## Consequences

- Development runs are reproducible and auditable from day one.
- The frozen holdout remains untouched: development loading defaults to the
  development partition and is guarded three times (load, feature build,
  pipeline); a separate explicit path will be required for final evaluation.
- Not implemented here (deliberately): walk-forward, Random Search, the GA,
  triple-barrier labeling, meta-labeling, robustness battery, holdout
  evaluation, dashboard. Costs remain provisional (ADR 0005).
- The in-sample slice metric is a smoke/illustrative baseline, **not** a thesis
  result; conclusions await walk-forward validation.
