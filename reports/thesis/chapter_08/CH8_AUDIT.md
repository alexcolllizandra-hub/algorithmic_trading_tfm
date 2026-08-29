# CH8 audit — what exists, what was frozen, what is new (2026-08-29)

Audit performed before computing anything. Paths are repo-relative.

## 1. Existing chapter-8 code, protocols and executed simulations

| Asset | Path | Status |
|---|---|---|
| Monte Carlo module | `src/perp_lab/evaluation/montecarlo.py` | Implemented and tested: `bar_net_returns`, `path_metrics`, `percentile_of`, `suggest_block_length` (ACF heuristic), `_stationary_indices` (Politis–Romano), `iid_trade_bootstrap`, `permutation_paths`, `stationary_bar_bootstrap`, `null_circular_shifts`, `cost_multiplier_sweep`, `breakeven_multiplier`, `PropFirmRules` + `prop_firm_pass_probability` + `coin_flip_pass_probability` |
| Executed MC analysis | `notebooks/07_monte_carlo_nula.ipynb` (builder `scripts/build_montecarlo_notebook.py`) | EXECUTED for volatility_breakout BTCUSDT / random_search (the closure's best family): median-by-return seed (rule fixed before reading results), stationary bootstrap at ACF-derived block, 1,000 resamples, notebook seed 42; IID trade bootstrap; order permutation; circular-shift null; cost-multiplier sweep; prop-firm account simulation |
| Executed MC artifacts | `reports/figures/montecarlo/k01..k05`, `reports/tables/montecarlo/t01..t05`, `reports/metadata/montecarlo/` | Reproducible via `build_montecarlo_notebook.py` + `run_notebooks.py 07`; deterministic (verified in the release gates) |
| Block-size precedent | `src/perp_lab/evaluation/study_robustness.py` (`BLOCK_SIZES = (24, 168, 720)`, C2 gate reads block_168, 500 resamples) | Frozen with the promotion contract |
| Web-explorer MC | `scripts/export_strategy_explorer.py` (stationary, block 168, 500 paths, seed 42, median-return seed) | Executed 2026-08-28 for all 15 families |
| Bench convention | `src/perp_lab/evaluation/baselines.py::_evaluate` (funded always-long perp) | Frozen; reconciled in ch7 (`INFORME_DISCREPANCIAS.md` §1) |

## 2. Frozen before results vs new retrospective analysis

**Frozen (usable as contract):** stationary block bootstrap as the resampling
family; ACF-heuristic block selection (`suggest_block_length`, documented as a
heuristic, ACF reported alongside); block-length trio 24/168/720 (C2 gate);
median-by-return seed selection rule; notebook seed 42; IID-trade /
permutation / circular-shift secondaries; cost multiplier sweep; prop-firm
rule configurations (published sources, in notebook 07); funded benchmark.

**New retrospective (declared post-hoc diagnostic analysis in every output):**
per-seed path-uncertainty layer for all 10 seeds; the hierarchical
seed-then-path scheme; the exposure-multiplier grid 0.25–2.00 with absorption
rule; capital-barrier/breach probabilities (90/80/70/50%); drawdown-duration
and recovery metrics (not computed anywhere in the code base); circular
moving-block bootstrap as method sensitivity; Monte Carlo convergence audit;
larger path budgets; master seed 20260829 for the new streams.

## 3. Candidate data availability

Every full-study family (R2, R3×5, CRT×9, S3) × symbol × seed has, per run
dir (paths in `ch7_results_units.csv` column `run_dir`):

- **Complete hourly OOS ledgers**: `random_search_fold{0..14}_test_equity.parquet`
  — 15 folds, 32,385 bars concatenated, columns include `open_time`,
  `raw_signal`, `target_position`, `position`, `execution_price`, `oo_return`,
  `gross_return`, `fee`, `slippage`, `cost`, `funding_rate_in_bar`, `funding`,
  `net_return`, `turnover`, `equity`, `drawdown`, `trade_id`, `exit_reason`,
  regime columns.
- **Complete trade ledgers**: `random_search_fold{0..14}_test_trades.parquet`
  — columns `trade_id`, `entry_time`, `exit_time`, `n_bars`, `position`,
  `net_return`, `funding`, `cost`, `exit_reason`. NOT persisted per trade:
  entry/exit prices, separate fees vs slippage (only combined `cost`),
  equity before/after, initial stop, risk distance, R-multiple. `exit_reason`
  is the ENGINE's label (e.g. `signal_close`); CRT-internal reasons
  (stop/target/time) are not persisted. Trade unit = engine episode of
  non-zero position; in the sampled pdl ledgers positions are 1.0 at the
  trade-record level (CRT partials do not appear as fractional trade rows).

## 4. Definitions in code

- Drawdown: `path_metrics` uses `equity/cummax − 1`, **negative** sign; its
  `max_drawdown` is the minimum (most negative). Chapter 8 reports the
  positive magnitude and says so.
- Time under water: share of bars with drawdown < 0 (`path_metrics`).
- Drawdown duration / recovery / capital-gap ("ruina"): **not defined
  anywhere in the code** — chapter-8 definitions are new (retrospective) and
  are stated in `ch8_method_contract.md`.
- Ruin in the account simulator: breaching a loss limit
  (`PropFirmRules`/`_phase_outcome`); unrelated to the new absorption rule.

## 5. Declared simulation parameters found

Notebook 07: `n_resamples = 1000`, seed 42, stationary bootstrap, block from
`suggest_block_length` (floor 6, ceiling 168, 2/sqrt(n) band). C2 gate: 500
resamples, blocks 24/168/720. Web export: 500 paths, block 168, seed 42.
No pre-existing exposure grid, barrier set, or path budget for a chapter-8
package: those are set now and declared retrospective.

## 6. Contract decision

A valid prior protocol EXISTS for the resampling core (stationary bootstrap,
ACF-derived block, median-seed rule, secondaries). It is adopted as the
primary specification. Everything listed as retrospective above is labelled
**post-hoc diagnostic analysis** in the method contract, tables and brief.
The account-threshold table (8.7) only cites the ALREADY EXECUTED notebook-07
prop-firm results for volatility_breakout (frozen configs); no new account
rules are introduced, and pdl_reclaim_long is declared NOT EVALUATED under
that scenario.
