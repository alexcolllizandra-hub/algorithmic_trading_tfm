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
