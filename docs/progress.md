# Project Progress

## Phase 1 - Foundation, Data Contract and EDA

**Status: IMPLEMENTED AND VERIFIED (offline gate green).**
The full quality gate passes locally. The only check still pending is the
opt-in network test (`pytest -m network`), which performs a real
`data.binance.vision` download and can be run on demand.

_Last updated: 2026-07-30 (EDA notebook restructured to 14 sections; order-flow,
mark-price basis and market-context analyses added; deterministically rebuilt and
executed)._

### Comprehensive EDA notebook (Chapter 4) - final 14-section version

`notebooks/01_comprehensive_exploratory_data_analysis.ipynb` is now generated
deterministically by `scripts/build_eda_notebook.py` (which also ruff-formats its
output) and reorganised into exactly 14 sections:

1. Executive summary and reproducibility
2. Configuration and data loading (centralised config; holdout guard;
   expected-vs-observed count gate that stops on any mismatch)
3. Data sources and analytical scope (Summary Table 1 - dataset inventory)
4. Data integrity and coverage (Summary Table 2 - data-quality assessment;
   resampling consistency incl. trade-count; monthly coverage heatmap)
5. Price dynamics and market episodes (price/drawdown, monthly-returns calendar,
   and a NEW documented-events overlay with a price-only market-stress proxy)
6. Return distributions and tail risk (Summary Table 3 - distribution + VaR/ES)
7. Volatility and temporal dependence (Summary Table 4 - ADF/KPSS/Ljung-Box/ARCH)
8. Market activity, order flow and seasonality (NEW taker-buy imbalance analysis)
9. Funding rates and mark-price basis (NEW matched-timestamp trade-vs-mark basis)
10. BTC-ETH dependence
11. Multi-timeframe comparison (Summary Table 5) with explicit 1h selection
12. Preliminary market-regime analysis (regime figure redesigned as consolidated
    contiguous daily episodes - no per-bar barcode)
13. Main findings and methodological implications (Summary Table 6)
14. Appendix diagnostics (empty gap timeline, return box plots, volume/trade-count
    distributions, hour x weekday heatmap)

Figures are regenerated with the continuous scheme `f01`..`f20` (plus `f21`
market-context and `fa2` appendix heatmap). Two genuinely new analyses were added:
taker-buy order-flow imbalance (`f14`) and trade-vs-mark price basis (`f15`).
Corrected interpretations: gaps are reported as "no gaps detected" (no venue-outage
claim); market activity is positively associated with contemporaneous |return|
(rho~0.41 BTC / 0.40 ETH) but not monotonically with rolling annualised volatility
(rho~-0.01). Extreme returns are never winsorised; histogram axes are clipped for
readability only, with the excluded count reported.

New tested modules: `src/perp_lab/eda/orderflow.py` (taker-buy imbalance),
`src/perp_lab/eda/events.py` (curated documented events + price-only stress proxy),
plus `mark_price_basis` in `funding.py`, `regime_intervals` in `regimes.py` and a
`REGIME_COLORS`/`regime_color` house-style palette. 8 new unit tests added.

Execution: end-to-end from a clean kernel, 0 error cells; 22 PNG + 22 PDF figures
and 41 CSV/Markdown tables exported. Observed counts match the contract exactly:
BTC/ETH 5m 631,296; 15m 210,432; 1h 52,608; funding 6,576 per asset. Date range
2020-01-01 .. 2025-12-31 23:55 UTC; no 2026 observation is loaded or exported.

#### Previous 12-section version (superseded)

The earlier 12-section layout mapped 1:1 to Chapter 4:

1. Objectives, scope and research questions
2. Reproducibility and holdout protection
3. Data sources, schema and integrity (comprehensive data-quality table, monthly
   5m coverage heatmap, gap structure with no empty axes, funding/mark coverage,
   resampling-consistency test)
4. Price evolution and market episodes (+ monthly-returns calendar)
5. Return distributions and tail risk (redesigned readable distribution figure,
   full stats incl. IQR/MAD/quantiles/Jarque-Bera, historical VaR/ES, ranked
   extreme events with leak-free context)
6. Volatility and temporal dependence (ADF/KPSS/Ljung-Box/ARCH-LM, rolling
   30-day vol/skew/kurt, ACF)
7. Volume, liquidity proxies and seasonality (dollar volume, Amihud, ATR/price,
   taker-buy ratio; Kruskal-Wallis; hour x weekday heatmap)
8. Funding-rate characteristics (shares/tails, lag-1/lag-3 persistence, runs,
   yearly summary, leak-free future-return relation)
9. BTC-ETH dependence (Pearson/Spearman, conditional-on-regime/sign, tail
   co-exceedance, block-bootstrap CI, documented lead-lag sign convention)
10. Multi-timeframe comparison and explicit 1h selection (decision table)
11. Preliminary market regimes (vol-regime price shading, full transition matrix
    incl. self-transitions + conditional-on-leaving, duration/characteristics
    tables, threshold+window sensitivity)
12. Main findings and methodological implications (findings table with downstream
    component mapping; Chapter-4 mapping)

New reusable, tested modules under `src/perp_lab/eda`: `coverage`, `stationarity`,
`rolling`, `extremes`, `liquidity`, `calendar`, plus extensions to `correlation`,
`funding`, `seasonality`, `regimes`. Artifact system extended to export vector
PDF alongside PNG. Development window 2020-01 .. 2025-12 (holdout frozen at
2026-01-01, never loaded). Notebook executes end-to-end from a clean kernel with
0 error cells (~215 s); generates 19 figures (PNG+PDF), 40 tables (CSV+Markdown)
and 59 metadata sidecars under `reports/{figures,tables,metadata}/eda`.

Gate after the upgrade: `ruff check` and `ruff format --check` clean; `pyright`
0 errors; `pytest -m "not network"` 121 passed.


### Implemented (code written, not yet executed)

- Project scaffold: `pyproject.toml` (uv, Phase-1 deps), `.python-version`,
  `.gitignore`, `README.md`, `.env.example`.
- Config: pydantic models + YAML loaders (`src/perp_lab/config`, `configs/`).
- Data layer: `ExchangeDataProvider` ABC, `BinanceVisionBulkProvider`,
  `CcxtIncrementalProvider`, `bars.py`, `splits.py`, `manifest.py`, `download.py`.
- Validation: pandera schemas + quality report (`src/perp_lab/validation`).
- EDA library: returns, volatility, dependence, seasonality, correlation,
  regimes, plots (`src/perp_lab/eda`).
- CLI: `perp-lab download` / `perp-lab validate`.
- Tests: unit + offline integration; opt-in network test marked `network`.
- Docs: data contract, experimental protocol, roadmap, ADRs 0001-0003.
- Governance: `AGENTS.md`, 5 rules, 6 skills, 4 subagents.

### Quality gate (real results)

| Check | Status | Result |
|-------|--------|--------|
| `uv sync --extra dev` | PASS | `.venv/` created, `uv.lock` generated (149 pkgs, CPython 3.12.3) |
| `uv run ruff check .` | PASS | `All checks passed!` |
| `uv run ruff format --check .` | PASS | `104 files already formatted` |
| `uv run pyright` | PASS | `0 errors, 0 warnings, 0 informations` |
| `uv run pytest -m "not network"` | PASS | `129 passed, 1 deselected` |
| `uv run pytest -m network` (optional) | PENDING | on-demand real download |

Scaffold fixes applied to reach green: removed an unused import; replaced 5
unused/blind lint directives; `dict()` -> literals in 2 tests; typed schema dicts
as `DataType | type[DataType]`; `matplotlib.figure.Figure` import; `np.asarray`
around `acf`; typed `scipy.jarque_bera` result; `cast(datetime, ...)` for Polars
`.max()/.min()` in tests; corrected a `.item()` misuse in one bar-resampling test.

Note: one harmless `DeprecationWarning` from pandera internals (`pl.concat`
`how='horizontal'`); not from project code.

### Terminal-dependent tasks

1. [DONE] Re-confirmed and deleted the legacy virtualenv (`Lib/`, `Scripts/`,
   `pyvenv.cfg`). New env = `.venv/` managed by uv only.
2. [DONE] Generated `.venv/` and `uv.lock` via `uv sync --extra dev`.
3. [DONE] Ran the full quality gate; fixed only scaffold errors; re-ran until green.
4. [DONE] Recorded the real output above.
5. [DONE] Initialised Git and connected the private GitHub remote
   (`origin`, branch `main`). The EDA deliverable was committed and pushed
   (`feat: add reproducible narrative EDA notebook and analysis library`);
   `main` tracks `origin/main`.

### Decisions locked

- Data source: Binance USDT-M via `data.binance.vision` (+ CCXT incremental).
- Symbols: `BTCUSDT`, `ETHUSDT`. Base 5m; derived 15m/1h from 5m.
- Cutoff: `2026-07-01` (exclusive) -> last bar opens 2026-06-30 23:55 UTC.
- Frozen holdout: `[2026-01-01 00:00 UTC, 2026-07-01)`. See ADR 0003.

### Git / versioning

- `.gitignore` hardened to exclude secrets, virtualenvs, heavy data
  (zip/parquet/csv/db), logs, caches and temp artifacts; manifests, code,
  configs, docs and `uv.lock` are tracked.
- Two commits on `main`, pushed to the private remote
  `github.com/alexcolllizandra-hub/tfm-algorithmic-trading`: the Phase-1
  scaffold and the EDA deliverable. Heavy artifacts (figures/tables PNG/CSV,
  data lake) remain git-ignored; the EDA notebook is versioned with its
  rendered outputs.

---

## Chapter 5 - Methodology & experimental contract (SPECIFICATION ONLY)

_Last updated: 2026-08-03. No modelling code implemented; specification only._

### Inspected
`README.md`, `pyproject.toml`, `configs/{data_contract,eda}.yaml`,
`docs/{roadmap,experimental_protocol,progress}.md`, ADRs 0001-0003,
`src/perp_lab/{config,data,validation,eda,reporting,utils}`, the tracked test
suite, committed data manifests, and the executed EDA notebook + its metadata.

### Repository audit (status classification)
- **Implemented & verified** (offline gate green, 129 tests): `config`, `data`
  (providers, bars, splits, manifest, download), `validation`, `eda`,
  `reporting`, `utils`, CLI `download`, EDA notebook.
- **Implemented, not verified**: network ingestion path (`pytest -m network`
  is opt-in and not run offline); local data lake exists (manifests committed)
  but data files are git-ignored.
- **Partially implemented**: CLI exposes only data commands (no experiment
  entry points); `regimes.py` provides a *descriptive* full-sample regime tag
  (fine for EDA, must not feed modelling).
- **Planned (missing)**: `features/`, `strategies/`, `labeling/`,
  `backtesting/`, `search/`, `models/`, `evaluation/`, `tracking/` packages;
  `configs/experiment.yaml` consumer (`ExperimentConfig` model).

### Inconsistencies / risks noted (not refactored)
- `docs/roadmap.md` phase numbering (Phase 2/3/4) does not match the thesis
  Chapter 5 sub-sections; the methodology docs use Chapter-5 numbering.
- `pyproject.toml` intentionally has no strategy/search/ML deps yet; these are
  deferred until the corresponding module is implemented.
- **Leakage watch:** the descriptive `vol_regime` uses full-sample quantiles;
  the causal Chapter-5 regime feature must use expanding/rolling quantiles.
  Contemporaneous `basis_bps` / `taker_buy_imbalance` must be lagged before any
  predictive use. No code currently touches the frozen holdout.

### Created (this task)
- `configs/experiment.yaml` - experiment contract (provisional values flagged).
- `docs/methodology/experimental_design.md` - RQs, hypotheses, protocols,
  binding leakage rules.
- `docs/methodology/hypothesis_matrix.md` - traceability matrix (H1-H5).
- `docs/methodology/feature_catalogue.md` - causal feature catalogue (sets A/B).
- `docs/methodology/strategy_specification.md` - baseline families, GA
  chromosome, RS/GA parity, fitness.
- `docs/methodology/validation_protocol.md` - walk-forward, purge/embargo,
  costs, metrics, robustness.
- `docs/methodology/module_specification.md` - planned module public APIs.
- `docs/architecture.md` - pipeline + Mermaid diagram + module responsibilities.
- ADR 0004 (methodology contract), ADR 0005 (provisional transaction costs).

### Verification performed
- `configs/experiment.yaml` parses as valid YAML (checked).
- Full offline quality gate re-run after adding docs/config (see table above):
  ruff / ruff format / pyright / `pytest -m "not network"` all green.
- No code changed, so no behavioural tests were added in this task.

### Open decisions (not silently assumed)
Transaction fees/slippage (provisional, ADR 0005); exact walk-forward fold
geometry (recommended, pending confirmation); position-sizing method and vol
target; triple-barrier widths/horizon; GA per-asset vs. joint; final
meta-labeling model family and calibration.

### Blockers
None for specification. Implementation will require adding modelling
dependencies (`scikit-learn`, optional `lightgbm`, a GA implementation) and
confirming the provisional cost schedule.

### Staged implementation plan (next milestones)
1. **Causal feature engine** (`features/`) + leakage-validation tests. *(next)*
2. Baseline strategies (`strategies/`) with the shared parameter space.
3. Cost-aware backtester (`backtesting/`) - next-bar, fees/slippage/funding.
4. Temporal validation (walk-forward folds + purge/embargo).
5. Random Search over the shared space.
6. Genetic Algorithm (matched budget/space/folds/costs/seeds).
7. Triple-barrier labels (`labeling/`).
8. Meta-labeling models (`models/`) with calibration.
9. Robustness tests (`evaluation/`).
10. Final frozen-holdout evaluation (opened once).
11. Dashboard and paper trading (later phase).

### Next implementation milestone
**Implement the causal feature engine and leakage-validation tests**
(`src/perp_lab/features/` + `tests/unit/test_features_*.py`).

---

## Chapter 5 — First executable vertical slice (governance + slice)

Status legend: **[impl]** implemented, **[test]** tested, **[prov]** provisional.

### Governance upgrade (experimental phase)
- `.cursor/agents/`: added `feature-engineer`, `strategy-backtest-engineer`,
  `experiment-researcher`, `thesis-researcher`; extended `architect` (config +
  tracking ownership) and `verifier` (causality/parity/holdout/tracking checks).
- `.cursor/skills/`: added `implement-causal-feature`,
  `validate-feature-causality`, `implement-baseline-strategy`,
  `validate-backtest-engine`, `register-experiment-run`.
- `.cursor/rules/`: added `causal-modeling.mdc`, `holdout-isolation.mdc`,
  `experiment-parity.mdc`, `evidence.mdc`; moved `project-core.mdc` and
  `AGENTS.md` "current phase" to the Chapter 5 experimental slice.

### Configuration [impl][test]
- `src/perp_lab/config/experiment.py`: strict, frozen `ExperimentConfig`
  (`extra="forbid"`). Validated: UTC/ordered/contiguous dates, dev ends at
  holdout start, positive feature windows, strategy parameter bounds
  (ATR multiples > 0, momentum fast < slow, mean-reversion entry > exit,
  known directions), RS/GA budget parity, derived purge (96) / embargo (118)
  bars, deterministic seed, provisional flags preserved, holdout cross-check.

### Causal feature engine [impl][test]
- `src/perp_lab/features/causal.py`: `log_return`, `momentum_w`, `sma_w`,
  `rvol_w`, `atr_w` (SMA of true range), `rel_volume_w` and a lagged
  `taker_buy_imbalance` (context). Rolling with `min_samples == window`, no
  centring; contextual feature shifted ≥ 1; zero denominators → null (no inf).
  `feature_metadata()` documents each column for run records.
- Availability: all close-t causal; `taker_buy_imbalance` lagged by
  `min_lookback_shift_bars`. Execution delay to t+1 is applied by the backtester.

### Baseline strategy [impl][test]
- `src/perp_lab/strategies/momentum.py`: `MomentumCrossover` emits
  `side ∈ {-1,0,1}` from `sma_fast` vs `sma_slow` at close *t* (warm-up → flat).

### Backtester [impl][test][prov costs]
- `src/perp_lab/backtesting/`: next-bar execution (`position = side.shift(1)`,
  open-to-open return), per-side fee + slippage charged on `|Δposition|`
  (adverse for both sides), 365-day annualised metrics. Funding **not** included
  in the minimal path (documented). Costs provisional (ADR 0005).

### Development pipeline + tracking [impl][test]
- `src/perp_lab/experiments/pipeline.py`: data → manifest verify → holdout guard
  → features → signals → next-bar backtest → metrics → artifacts, with Rich
  per-stage logging (run id, interval, rows, hash, holdout status, feature names,
  warm-up/null counts, execution timing, costs, trades/exposure, metrics,
  artifact paths, elapsed, status).
- `src/perp_lab/tracking/`: `RunTracker` writes the contract
  `artifacts/runs/<run_id>/` (`resolved_config.yaml`, `dataset_manifests.json`,
  `environment.json`, `git_state.json`, `metrics.json`, `feature_metadata.json`,
  `trades.parquet`, `equity.parquet`, `logs/`, `figures/`). `artifacts/` is
  git-ignored. The run id ties config + data hashes + git + seed + metrics +
  strategy + artifacts.
- CLI: `uv run perp-lab pipeline development --config configs/experiment.yaml`
  (plus `--synthetic` offline smoke). Timestamped file logs; non-zero exit on
  failure.

### Holdout protection [impl][test]
- Development load defaults to the development partition and asserts
  `max(open_time) < holdout_start`; `build_features` re-checks; the pipeline runs
  an explicit third guard. Tests prove `HoldoutLeakageError` on any crossing.

### Verification (this task) — exact results
- `uv run ruff check .` → All checks passed!
- `uv run ruff format --check .` → 141 files already formatted
- `uv run pyright` → 0 errors, 0 warnings, 0 informations
- `uv run pytest -m "not network"` → 177 passed, 1 deselected, 19 warnings
- Real run (development data, in-sample, **not** a thesis result):
  BTCUSDT 1h, 52,608 bars `2020-01-01 … 2025-12-31 23:00 UTC`, momentum(24,96),
  Sharpe ≈ 0.264, final equity ≈ 0.830; 9 artifacts under
  `artifacts/runs/<run_id>/`.

### Still unresolved / deferred (not assumed)
- Transaction fees/slippage (provisional, ADR 0005); funding in the backtest;
  walk-forward folds, purge/embargo application; Random Search, GA,
  triple-barrier, meta-labeling, robustness, final holdout evaluation.

### Recommended next task
Generalise and validate the causal feature engine (broaden the catalogue set
with the same leakage tests) before implementing the full baseline strategy set
and the walk-forward framework.

---

## Chapter 5 — Config-driven causal feature engine (this stage)

_Last updated: 2026-08-03. Builds on commit `001390b`. See ADR 0007._

### Feature contract + engine [impl][test]
- `src/perp_lab/features/spec.py`: dependency-light `KIND_REGISTRY` of feature
  *kinds* + frozen, JSON-serialisable `FeatureSpec` (name, family, inputs,
  asset/timeframe dependency, params/lookback, availability, shift, warm-up,
  null/inf policy, consumers, leakage risk, dtype, `IMPL_VERSION`). Validation
  (`validate_feature_item`) rejects unknown kinds, missing/extra windows,
  invalid lags and unknown sources.
- `src/perp_lab/features/causal.py`: pure Polars builders (returns/momentum,
  SMA, price-distance-from-MA, price z-score, rolling volatility, ATR,
  normalised range, relative volume, volume z-score, cyclical hour/day-of-week,
  lagged taker-buy imbalance). No in-place mutation; guarded denominators (no
  infinities).
- `src/perp_lab/features/registry.py`: `resolve_feature_set` (validate,
  de-duplicate, inject baseline SMAs), `build_feature_frame` (dependency check →
  holdout guard → deterministic build → `(frame, specs)`), `specs_to_metadata`.

### Configuration-driven selection [impl][test]
- `ExperimentConfig.features.feature_set` (+ `configs/experiment.yaml`) lists the
  concrete features; validated at load time against the registry, and checked
  for duplicate output columns. Distinct from the wider search-space window
  lists.

### Default feature set (14 columns, BTC/ETH 1h, same code)
`log_return` (ln P_t/P_{t-1}, warm-up 1) · `momentum_12`, `momentum_24`
(ln P_t/P_{t-w}, warm-up w) · `sma_24`, `sma_96` (trailing mean, warm-up w−1) ·
`price_dist_sma_48` (P/sma−1, warm-up w−1) · `zscore_48` ((P−mean)/std sample,
std=0→null, warm-up w−1) · `rvol_96` (rolling std of log return, warm-up w) ·
`atr_14` (trailing mean of true range with prev close, warm-up w−1) ·
`range_norm` ((high−low)/close, warm-up 0) · `rel_volume_24` (volume/rolling
mean, mean≤0→null, warm-up w−1) · `hour_sin`, `hour_cos` (ex-ante, shift 0,
warm-up 0) · `taker_buy_imbalance` (2·taker/quote−1, lagged 1, denom≤0→null).
`volume_zscore_w` and `dow_sin/dow_cos` are registered but off by default.
- Availability: close-based features `shift = 0` / "close t" (the t+1 execution
  delay is applied once by the backtester); contextual imbalance `shift = lag`;
  cyclical time is the ex-ante exception.

### Causality / numerical tests [test]
- `tests/unit/test_features_causal.py` (17 tests) proves the 15 invariants:
  append-future invariance, future-mutation invariance, trailing-only rolling
  (hand calcs for sma/log-return/momentum/zscore/rvol/atr), exact-once shift,
  declared warm-up == actual leading nulls for every feature, deterministic
  null handling, no infinities (incl. flat prices / zero volume / constant
  windows), alignment + tz preserved, input immutability, deterministic column
  order, BTC/ETH independence, reproducibility, holdout isolation.
- `tests/unit/test_features_registry.py` (12 tests): contract completeness +
  JSON-serialisability for every kind, validation rejections, `resolve_feature_set`
  ordering/dedupe/SMA injection, and config rejection (unknown kind, bad params,
  duplicate columns).

### Pipeline + artifact integration [impl][test]
- `experiments/pipeline.py` Stage 3 now resolves `feature_set` (ensuring the
  baseline SMAs), builds via `build_feature_frame`, logs specs→columns, warm-up/
  null counts and an explicit **infinity check**, and writes the resolved
  `FeatureSpec` contract to `feature_metadata.json`. The momentum baseline and
  next-bar execution semantics are unchanged.

### Verification (this stage) — exact results
- `uv run ruff check .` → All checks passed!
- `uv run ruff format --check .` → 144 files already formatted; the only flag is
  the **pre-existing, out-of-scope** `docs/methodology/module_specification.md`
  (embedded code-block drift already on `origin/main`), intentionally not
  reformatted in this stage.
- `uv run pyright` → 0 errors, 0 warnings, 0 informations.
- `uv run pytest -m "not network"` → 196 passed, 1 deselected.
- Synthetic smoke run (`perp-lab pipeline development --synthetic`, **not** a
  research result) built the 14-column set, passed the holdout + infinity
  guards and wrote 9 artifacts. **Real development-data execution remains
  unverified locally** (no `data/processed/` present); the integration is
  covered by deterministic fixtures + synthetic mode.

### Still provisional / deferred (not assumed)
- Cross-asset (BTC–ETH corr/beta), funding/basis and causal expanding
  vol-regime features remain **Planned** (documented, not approximated): they
  need aux data alignment tests and must not touch the holdout.
- Feature *windows* are not tuned on performance (out of scope). Transaction
  costs remain provisional (ADR 0005). Walk-forward, RS, GA, triple-barrier,
  meta-labeling, robustness and holdout evaluation are unchanged / not started.

### Recommended next task (updated)
Implement the interpretable **baseline strategy family set** on the shared
parameter space (breakout + mean-reversion alongside momentum), reusing the
config-driven feature engine, then wire the **expanding walk-forward** harness
with purge/embargo — before any Random Search / GA.

---

## Chapter 5 — Experimental foundation (this stage)

_Last updated: 2026-08-04. See ADR 0008. Status legend: **[impl]** implemented,
**[test]** tested, **[cfg]** configured, **[plan]** planned._

### Extended causal features [impl][test]
- `features/causal.py`: added `ema`, `cum_return`, `roll_std`, `ma_distance`
  (fast/slow), `true_range`, lagged `taker_buy_ratio` — all trailing-only,
  guarded denominators (no infinities).
- `features/context.py` (new): `FeatureContext` + context-dependent builders
  `xasset_rel_return`, `xasset_rel_momentum`, `xasset_corr` (backward-aligned
  BTC–ETH), `funding_rate` (backward as-of), `basis` (mark−index) and
  `oi_change` (log Δ open interest). Missing input frame → feature reported
  **unavailable** (not fabricated).
- `features/spec.py`: `KIND_REGISTRY` extended with the new single-asset and
  context kinds; `KindDef` gains `requires_window_slow` / `requires_context` /
  `context_kind`; `IMPL_VERSION` = `0.3.0`. Config `FeatureItem` supports
  `window_slow` (validated `window < window_slow`).
- `features/manifest.py` (new): machine-readable JSON manifest (name, family,
  inputs, formula, params/lookback, warm-up, availability, missing-data rule),
  `MANIFEST_SCHEMA_VERSION` = `1.0`.
- `features/predictors.py` (new): `build_predictor_rows` with four separated
  timestamp roles — feature / signal / execution / (future) label time; label
  left null this phase.

### Fold-fit transforms + market regimes [impl][test]
- `regimes/transforms.py` (new): `StandardScaler`, `QuantileClipper` — `fit` on
  train only, `transform` unchanged on val/test; constant columns handled (no
  infinities).
- `regimes/models.py` (new): `ThresholdRegime` (interpretable vol-quantile
  baseline), `KMeansRegime`, `GMMRegime` — fitted on train only, canonically
  ordered low→high volatility, missing inputs → `UNKNOWN_LABEL`. Reproducible
  under fixed seeds.
- `scikit-learn>=1.5` added as a runtime dependency (K-means / GMM).

### Common strategy interface + family [impl][test]
- `strategies/base.py`: `Strategy` protocol now requires `params()` +
  `required_features()`; new O(n) `evolve_positions` state machine (entries,
  exits, direct reversals).
- `strategies/filters.py` (new): shared causal `regime_gate` / `trend_gate`.
- `strategies/momentum.py`: `MomentumCrossover` adapted (optional trend + regime
  gates), behaviour otherwise unchanged (fast < slow enforced).
- `strategies/breakout.py` (new): `Breakout` — channels from **previous** bars
  only (`shift(1)`), configurable channel window + confirmation bars.
- `strategies/mean_reversion.py` (new): `MeanReversion` — price z-score entry/
  exit, `exit_z < entry_z` enforced.
- All families read window/threshold options from `configs/experiment.yaml`
  (`strategies.families.*`); no duplicated constants.

### Funding-aware backtester [impl][test][prov costs]
- `backtesting/engine.py`: next-bar execution retained; rich per-bar ledger now
  records raw signal, target/executed position, execution price, gross return,
  separate fee + slippage, funding, net return, equity, drawdown, `trade_id`,
  `exit_reason`. Turnover = `|Δposition|` (reversal = 2 units). Funding aligned
  by backward search on its own timestamps and signed by the active position.
  `funding_applied` flag recorded; `require_funding=True` raises rather than
  substituting zero. `BacktestResult.trades()` extracts trade records.

### Expanding walk-forward [impl][test]
- `validation/walk_forward.py` (new): anchored/expanding folds; purge/embargo
  **derived from config** (`purge_bars = max(label_horizon, max_holding)`;
  `embargo_bars = purge_bars + ceil(fraction_of_test·test_bars)`), converted to
  durations by the primary-timeframe step. `split_fold` yields disjoint
  train/val/test; `assert_folds_exclude_holdout` guards the frozen holdout.
  `generate_walk_forward(..., strict=True)` enforces `min_folds`.

### Pipeline + artifacts [impl]
- `experiments/pipeline.py`: generates walk-forward folds (asserting holdout
  exclusion) and a feature manifest, and writes both — plus resolved strategy
  parameters — into the run contract alongside the existing artifacts.

### Tests added [test]
- Unit: `test_features_extended.py`, `test_features_context.py`,
  `test_regimes.py`, `test_strategies_extended.py`,
  `test_backtesting_extended.py`, `test_walk_forward.py`.
- Integration: `test_experimental_foundation.py` (validated bars → features +
  manifest → regimes → multi-strategy signals → funding-aware backtest →
  predictor rows), asserting no infinities and timestamp-role separation.

### Verification (this stage) — exact results
- `uv run ruff check .` → All checks passed!
- `uv run ruff format --check .` → 170 files already formatted.
- `uv run pyright` → 0 errors, 0 warnings, 0 informations.
- `uv run pytest -m "not network"` → 278 passed, 1 deselected (pre-existing
  pandera/`spearmanr` warnings only; none from this stage).

### Still provisional / deferred (not assumed)
- Transaction costs remain provisional (ADR 0005). Funding is supported and
  tested but only applied when a funding frame is supplied; real
  development-data funding wiring is deferred. Cross-asset/derivatives features
  are validated on fixtures — production aux-data alignment on the real lake is
  not yet exercised end to end.
- **[plan]** Random Search, Genetic Algorithm, triple-barrier labeling,
  meta-labeling models, robustness battery, dashboard and paper trading. The
  frozen holdout is never accessed during development.

### Recommended next task (updated)
Implement **Random Search** over the shared strategy parameter space, evaluated
through the expanding walk-forward folds and the funding-aware backtester, with
per-candidate run artifacts — the fair-budget baseline the Genetic Algorithm
will later be compared against.

---

## Chapter 5 — Strategy search: Random Search vs Genetic Algorithm (this stage)

_Last updated: 2026-08-04. See ADR 0009 and
`docs/methodology/strategy_search.md`. Status legend: **[impl]** implemented,
**[test]** tested, **[smoke]** end-to-end on synthetic data, **[cfg]** configured,
**[future]** not implemented._

### Typed parameter spaces + registry [impl][test]
- `search/space.py`: `IntParam` / `FloatParam` (optional log) / `CategoricalParam`
  / `BoolParam`, conditional parameters, `SearchSpace` (deterministic sampling,
  per-parameter + family repair, validation, canonical serialization, stable
  `candidate_hash`, duplicate detection), plus `param_distance` /
  `population_diversity`.
- `search/registry.py`: one `SearchSpace` per family (`momentum`, `breakout`,
  `mean_reversion`) built **from validated `ExperimentConfig`** — no duplicated
  constants. Repairs enforce `fast < slow` and `exit_z < entry_z`. Adding a
  family = one builder; neither search algorithm changes.

### Candidate + leakage-safe evaluator [impl][test]
- `search/candidate.py`: reproducible `Candidate` (id/family/params/active/seed/
  step/parents/status/failure/components/fitness/fold-metrics/duration).
- `search/evaluator.py`: features built **once**; `build_folds_data` pre-splits
  folds and fits the regime model on **train only** (attached causally to
  val/test); `CandidateEvaluator` scores candidates on **validation** for
  selection and **once** on **test** for the fold winner. Reuses the existing
  funding-aware backtester (no second backtester); per-run cache only.

### Objective + constraints [impl][test]
- `search/objective.py`: Sharpe reward minus drawdown / turnover / fold-
  instability / complexity penalties (config weights, every component stored).
  Hard constraints (finite metrics, min trades total/per-fold, max drawdown,
  required funding) ⇒ explicit failure with deterministic `FAILURE_PENALTY`.

### Random Search + Genetic Algorithm [impl][test]
- `search/random_search.py`: deterministic sample→repair→validate→dedupe→evaluate
  to a unique-evaluation budget; exact counters + monotone convergence.
- `search/genetic_algorithm.py`: tournament selection, uniform crossover, typed
  mutation, family repair, elitism, duplicate handling, budget-capped early
  termination, per-generation diversity and full parent→offspring lineage.
- **Fair budget**: the budget caps **unique objective evaluations**; invalid /
  duplicate / cached proposals do not consume it; a backtested-but-infeasible
  candidate does. Identical for both algorithms, so the GA never buys extra
  evaluations. Verdict uses aggregated walk-forward **test** metrics of fold
  winners (never in-sample/validation).

### Comparison runner + config + CLI [impl][test][smoke]
- `search/runner.py`: matched RS/GA comparison; per-fold validation winners
  scored once on test; artifact directory (candidate + failed ledgers, fold
  winners, convergence, GA lineage/diversity, fold-winner test equity/trades,
  `comparison_summary.json`, `comparison_report.md`, `warnings.json`, logs).
- `search/config.py`: strict `SearchRunConfig` (algorithm/family/data/geometry/
  objective overrides) reusing experiment budget parity, costs, walk-forward and
  fitness. `configs/search_smoke.yaml` (synthetic, clearly labelled) and
  `configs/search.yaml` (research).
- CLI: `perp-lab search` (+ `--algorithm` / `--family` overrides) and
  `perp-lab search-summary <run_dir>`.

### Tests added [test]
- Unit: `test_search_space.py`, `test_search_objective.py`,
  `test_search_random.py`, `test_search_ga.py`, `test_search_temporal_safety.py`
  (+ `tests/unit/search_helpers.py`).
- Integration: `test_search_pipeline.py` — synthetic bars → features → regimes →
  strategy → walk-forward search → backtester → ranking → fold winner → test →
  artifacts; RS/GA fair-budget; reproducible repeated run; CLI smoke.

### Smoke run (synthetic — NOT a research result) [smoke]
`uv run perp-lab search --config configs/search_smoke.yaml` — 3 folds, budget 18,
family `mean_reversion`, synthetic funding fixture (labelled). RS evaluated 18 /
GA evaluated ≤ 18 unique candidates; 30 artifacts written and reloaded; explicit
exploratory warning emitted.

### Still provisional / deferred (not assumed)
- Real development-data search is **[cfg]** (verified offline on synthetic data;
  needs a populated local lake). No partial-resume of interrupted runs yet.
- **[future]** Triple-barrier labeling, meta-labeling, robustness battery,
  distributed execution, Docker, dashboard and paper trading. The frozen holdout
  is never accessed during development.

### Recommended next task (updated)
With RS and the GA compared fairly on the shared substrate, the next phase is
**triple-barrier labeling** and **meta-labeling** on the primary signals
(predictor rows already separate feature/signal/execution/label timestamps),
followed by the robustness battery — before the single frozen-holdout evaluation.

## Real development-data pilot + Research Dashboard v0 (this stage)

### Real development-data pilot [smoke][real-data]
- Local lake validated: BTCUSDT & ETHUSDT `1h` **development** partition =
  52,608 bars each, `2020-01-01 00:00` → `2025-12-31 23:00` UTC, no OHLC nulls;
  funding = 6,576 rows each, no nulls. All strictly before the frozen holdout
  (`2026-01-01`); the holdout is never read.
- `configs/search_pilot.yaml`: real experiment geometry (730/90/90 days) capped
  to **3 folds** via the new `max_folds` field, momentum family, budget **12**
  (GA pop 4 × 3 gen), seed 42, `require_funding: true` (real funding applied —
  never a silent zero), threshold regimes.
- Command: `uv run perp-lab search --config configs/search_pilot.yaml`. Runtime
  ≈ 11 s. RS evaluated 12/12; GA evaluated 10 unique (≤ budget). Artifacts
  written (32 files) and reloaded/validated. **Exploratory** development metrics,
  not final holdout performance.

### Research Dashboard v0 [impl][test][smoke]
- New Streamlit-free `dashboard/loader.py` (artifact loading + transforms) and
  `dashboard/app.py` (UI, imports only `loader`, never the search engine).
- Screens: run browser + filters (kind/family/run/algorithm); Overview
  (RS vs GA comparison, fair-budget verification, report); Configuration;
  Data & Features (dataset/feature manifests, folds); Convergence & Diversity;
  Candidates (ranking, parameter inspection, failed ledger); Folds & Test
  (fold winners, val/test metrics, equity/drawdown, trades). Prominent
  exploratory warning on all non-holdout runs; runs tagged synthetic-smoke /
  development / final-holdout.
- CLI: `perp-lab dashboard` (port 8501; `--port` / `--runs-dir` / `--headless`).
- Streamlit is an **optional** dependency (`dashboard` extra; also in `dev`).
- Tests: `tests/unit/test_dashboard_loader.py` (artifact loading, kind
  classification, comparison table, fair-budget check incl. violation,
  convergence/diversity, fold winners, folds, candidate ranking, equity/trades,
  manifests, missing-artifact tolerance).
- Docs: `docs/research_dashboard.md` (screens, launch, future service
  architecture + proposed ports — documented only, not implemented).

### Still out of scope (unchanged)
- **[future]** FastAPI/PostgreSQL/MinIO/Grafana/Prometheus, distributed workers,
  paper trading, triple-barrier labeling, meta-labeling, robustness battery and
  the single frozen-holdout evaluation.
