---
name: register-experiment-run
description: Record a reproducible development run under artifacts/runs/<run_id>/ with resolved config, dataset hashes, git state, environment, seed, metrics, feature metadata, trades and equity. Use when running or extending the perp-lab development pipeline.
disable-model-invocation: true
---

# Register an experiment run

Owner agent: **architect** (tracking contract) with the pipeline caller.

## Purpose & triggers
Persist a self-describing, reproducible record of one pipeline run. Trigger:
running `perp-lab pipeline development ...` or adding a new pipeline stage.

## Required inputs
- Resolved `ExperimentConfig` and `DataContract`.
- The loaded dataset ids + manifest hashes and the seed.
- Backtest metrics, ledger (equity) and trades; the feature metadata.

## Files it MAY modify
- `src/perp_lab/tracking/*.py`, `src/perp_lab/experiments/*.py`
- `tests/unit/test_tracking*.py`

## Files it MUST NOT modify
- `src/perp_lab/features/`, `src/perp_lab/strategies/`,
  `src/perp_lab/backtesting/` (consume them, do not change them).

## Prerequisites
- `artifacts/` is git-ignored; logs are timestamped and ignored.

## Procedure
1. Generate a run ID that ties together config, data hashes, git state and seed.
2. Create `artifacts/runs/<run_id>/` and write the stable contract:
   `resolved_config.yaml`, `dataset_manifests.json`, `environment.json`,
   `git_state.json`, `metrics.json`, `feature_metadata.json`,
   `trades.parquet`, `equity.parquet`, plus `logs/` and `figures/`.
3. Emit Rich terminal logging per stage; also write a timestamped run log file.
4. Return a non-zero exit code on failure; full tracebacks in debug mode.

## Mandatory invariants
- The run ID connects resolved config, dataset hashes, git commit/state, seed,
  metrics, selected strategy and generated artifacts.
- No secrets, no heavy datasets, no holdout data are written to Git.
- Metrics and artifacts are deterministic for a fixed data/config/seed.

## Required tests
- The artifact contract files are created; `metrics.json` carries the run ID,
  git state and seed; a repeated run with the same inputs yields identical
  metrics; the holdout guard blocks holdout loading.

## Generated artifacts
- The `artifacts/runs/<run_id>/` tree and the run log file.

## Stop conditions
- Dataset manifests/hashes are missing; git state cannot be read (record as
  unknown, do not fabricate); holdout data would be required.

## Completion report (exact)
- The run ID, the artifact paths written, the metrics, and the exact CLI command
  and quality-gate outputs.
