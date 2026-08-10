# Current state inventory

**Audit date:** 2026-08-08 · **Updated:** 2026-08-10 (Gates R1, R2 and R3 closed)
**Audited branch:** `feat/multi-seed-and-strategy-families` (commit `2393eb6`);
R1 implemented on `docs/roadmap-consolidation`
**Method:** direct inspection of source, tests, configs, ADRs and local `artifacts/`.
Where documentation contradicted the code, **the code was taken as the source of
truth** and the contradiction is recorded in [Known inconsistencies](#known-inconsistencies).

Related: [master roadmap](master_roadmap.md) · [phase gates](phase_gates.md) ·
[scientific questions](scientific_questions.md) · [future architecture](future_architecture.md)

---

## How to read this document

Two independent axes are tracked. **A component being implemented says nothing
about whether it works.**

### Implementation status

| Status | Meaning |
|---|---|
| `SPECIFIED` | Designed in prose/ADR; no code |
| `IMPLEMENTED` | Code exists in `src/perp_lab/` |
| `TESTED` | Code exists and has targeted unit/integration tests that pass |

### Validation maturity

| Maturity | Meaning |
|---|---|
| `NOT EVALUATED` | Never run as an experiment on real data |
| `PILOTED` | Run once on real data, single seed, reduced budget — pipeline evidence only |
| `MULTI-SEED` | Run across ≥10 derived seeds with fold-level inference |
| `ROBUST` | Survives the robustness battery (bootstrap CI, cost stress, delay, concentration) |
| `PROMOTED` | Meets promotion criteria; eligible for holdout |
| `REJECTED` | Failed its promotion criterion on recorded evidence |

The frozen holdout `[2026-01-01, 2026-07-01)` **has never been opened.** No
component anywhere in this repository is `PROMOTED`.

---

## Headline findings

1. **The scientific pipeline is far more complete than `docs/roadmap.md` claims.**
   That file still states "only Phase 1 is implemented"; in reality data, EDA,
   features, six strategy families, the backtester, walk-forward validation,
   Random Search, the Genetic Algorithm, budget parity, multi-seed orchestration,
   a robustness battery and a FastAPI + Next.js dashboard are all implemented and
   tested.

2. **No strategy family has demonstrated a robust edge.** Momentum (R2) and all
   five R3 families are **`REJECTED`** with multi-seed evidence. The strongest
   partial signal was volatility_breakout on BTC (6/10 RS seeds positive), but
   **0/10** seeds had a bootstrap Sharpe CI excluding zero on either asset. See
   [ADR 0013](../decisions/0013-clean-momentum-rebaseline.md) and
   [ADR 0015](../decisions/0015-r3-family-evaluation-negative.md).

3. **Gate R3 closed 2026-08-10.** Full studies under
   `artifacts/runs/r3_full_budget100_ga21/`: 5 families × 20 units × 15 folds,
   budget 100/fold/engine, 100/100 isolation audits passed, **0 promoted**.

4. **A confirmed outer-fold contamination affected every result produced up to
   2026-08-08.** Candidate search optimised a fitness pooled across *all*
   walk-forward folds, including folds chronologically later than the fold being
   scored. See
   [Inconsistency 1](#inconsistency-1-outer-fold-contamination-in-candidate-search).

5. **That contamination is fixed as of 2026-08-09 (Gate R1).** Search now runs
   independently inside each outer fold, each fold's winner is fingerprinted on
   validation before its test slice is scored, and budget parity is enforced per
   fold. Verified by a real 15-fold pilot and by
   `tests/unit/test_search_fold_isolation.py`. **Every pre-existing experimental
   number remains invalid as inference** and is marked `SUPERSEDED.json` on disk;
   nothing has been deleted.

6. **Gate R2 is complete.** The clean paired GA - RS estimate is -0.061, 95% CI
   [-0.399, +0.277], versus the superseded +0.183. There is still no evidence of
   engine superiority. See [ADR 0013](../decisions/0013-clean-momentum-rebaseline.md).

---

| Branch | Head | Relationship | Contains |
|---|---|---|---|
| `main` | `daa8de0` | baseline | Data, EDA, features, 3 families, backtester, walk-forward, RS/GA, dashboard v0 |
| `feat/multi-seed-and-strategy-families` | `2393eb6` | 18 commits ahead of `main` | **Everything in `main` plus** evaluation layer, 3 extra families, multi-seed orchestration, budget parity, journaling, run identity |
| `feat/research-dashboard-redesign` | `c621760` | 2 commits ahead of `main`, **diverged from** the multi-seed branch | Dashboard/API hardening and docs only |
| `fix/outer-fold-leakage` | `588ab8e` | 1 commit ahead of the dashboard branch | Per-outer-fold independent search — **abandoned**: built on a base that lacks the multi-seed work |
| `docs/roadmap-consolidation` | current | descends from the multi-seed branch | Roadmap consolidation **plus the R1 leakage fix**, re-implemented on the correct base |

`feat/research-dashboard-redesign` and `fix/outer-fold-leakage` branched from
`main`, not from the multi-seed branch. They therefore do **not** contain the
`evaluation/` package, the three newer strategy families, `effective_budget`
parity or the multi-seed orchestrator. `fix/outer-fold-leakage` was consequently
**not merged**; R1 was re-implemented from scratch on
`docs/roadmap-consolidation`, where it also covers the newer families, the
per-fold budget parity and the multi-seed contract.

---

## Component inventory

### Data

| Field | Value |
|---|---|
| **Purpose** | Acquire, validate and partition BTC/ETH USDT-M perpetual bars and funding |
| **Implementation** | `TESTED` |
| **Validation maturity** | n/a (infrastructure) |
| **Files** | `src/perp_lab/data/{download,bars,manifest,provenance,splits}.py`, `src/perp_lab/data/providers/{binance_vision,ccxt_incremental,base}.py`, `configs/data_contract.yaml` |
| **Evidence** | `tests/unit/test_binance_vision.py`, `tests/unit/test_schemas.py`, `reports/data_provenance/data_provenance_audit.md`, committed manifests under `data/manifests/` |
| **Limitations** | Funding is real for BTC/ETH; `basis` and order-flow features remain declared proxies |
| **Next action** | None. Stable. |

Cutoff `2026-07-01` (exclusive); frozen holdout `[2026-01-01, 2026-07-01)`;
development strictly before `2026-01-01`. Pinned in `configs/data_contract.yaml`
and [ADR 0003](../decisions/0003-cutoff-and-holdout-window.md).

### EDA

| Field | Value |
|---|---|
| **Purpose** | Characterise return, volatility, dependence, funding and tail behaviour to motivate hypotheses |
| **Implementation** | `TESTED` |
| **Validation maturity** | n/a (descriptive) |
| **Files** | 23 modules in `src/perp_lab/eda/` (`returns`, `volatility`, `regimes`, `dependence`, `leadlag`, `funding`, `tailrisk`, `extremes`, `seasonality`, `orderflow`, `stationarity`, `stress_dependence`, …) |
| **Evidence** | 59 metadata sidecars in `reports/metadata/eda/`, figures in `reports/figures/` |
| **Limitations** | Full-sample descriptive statistics; explicitly **not** usable as model inputs |
| **Next action** | Map findings to hypotheses — done in [scientific_questions.md](scientific_questions.md) |

### Features

| Field | Value |
|---|---|
| **Purpose** | Causal, configuration-driven predictors with declared warm-up |
| **Implementation** | `TESTED` |
| **Validation maturity** | n/a (inputs) |
| **Files** | `src/perp_lab/features/{spec,registry,causal,context,predictors,manifest}.py` |
| **Evidence** | 25 kinds in `KIND_REGISTRY`; packs `core` (13) / `extended` (10) / `experimental` (2); leakage tests in `tests/unit/test_features_causal.py` (prefix invariance, future-mutation invariance), `test_features_context.py` (backward as-of join), `test_feature_packs.py` |
| **Limitations** | `basis` and taker order-flow kinds are flagged `is_proxy` |
| **Next action** | None for current phase |

`predictors.py` already separates `feature_time` / `signal_time` /
`execution_time` / `label_time`, which is the hook a future meta-labeling layer
will consume. `label_time` is currently always null — **no labeling exists.**

### Strategy: Momentum

| Field | Value |
|---|---|
| **Purpose** | SMA crossover trend-following baseline |
| **Implementation** | `TESTED` — `MomentumCrossover` in `src/perp_lab/strategies/momentum.py` |
| **Validation maturity** | **`REJECTED`** — failed under the clean R2 multi-seed protocol |
| **Evidence** | `artifacts/runs/multiseed_momentum_r2_clean_v2/` — 2 assets × 10 seeds × 15 isolated folds, OOS 2022-03-31 … 2025-12-09; [ADR 0013](../decisions/0013-clean-momentum-rebaseline.md) |
| **Limitations** | Development-period result, not final-holdout evidence. The study identity is marked provisional because its dedicated config was untracked at launch; exact config/hash are recorded |
| **Next action** | **Do not retune.** Retain as the rejected baseline and proceed to R3 families |

Current clean result:

| Symbol / engine | Seeds with positive mean test Sharpe | Median OOS total return | Buy-and-hold |
|---|---|---|---|
| BTCUSDT / RS | 0 / 10 | −0.350 | +0.523 |
| BTCUSDT / GA | 0 / 10 | −0.455 | +0.523 |
| ETHUSDT / RS | 0 / 10 | −0.475 | −0.219 |
| ETHUSDT / GA | 0 / 10 | −0.507 | −0.219 |

Bootstrap Sharpe CI excluded zero in **0 of 40** run/engine combinations; all
40 lose money and none beats buy-and-hold or survives doubled costs.

### Strategy: Breakout

| Field | Value |
|---|---|
| **Purpose** | Donchian channel breakout with confirmation |
| **Implementation** | `TESTED` — `Breakout` in `src/perp_lab/strategies/breakout.py` |
| **Validation maturity** | **`REJECTED`** — Gate R3 multi-seed (2026-08-10) |
| **Evidence** | `artifacts/runs/r3_full_budget100_ga21/breakout/`: 0/10 RS seeds positive on BTC and ETH; median OOS return −15.8% / −25.5%; isolation audit passed 20/20 |
| **Limitations** | No bootstrap Sharpe CI excluding zero on any seed |
| **Next action** | **Do not retune.** Recorded as rejected |

### Strategy: Mean Reversion

| Field | Value |
|---|---|
| **Purpose** | Fade trailing price z-score |
| **Implementation** | `TESTED` — `MeanReversion` in `src/perp_lab/strategies/mean_reversion.py` |
| **Validation maturity** | **`REJECTED`** — Gate R3 multi-seed (2026-08-10) |
| **Evidence** | `artifacts/runs/r3_full_budget100_ga21/mean_reversion/`: 0/10 RS seeds positive both assets; median OOS return −60.0% / −79.9% |
| **Limitations** | Worst median performance of the five families |
| **Next action** | **Do not retune.** Recorded as rejected |

### Strategy: Volatility Breakout

| Field | Value |
|---|---|
| **Purpose** | ATR-scaled breakout of prior range with explicit exit modes |
| **Implementation** | `TESTED` — `VolatilityBreakout` in `src/perp_lab/strategies/volatility_breakout.py` |
| **Validation maturity** | **`REJECTED`** — Gate R3 multi-seed (2026-08-10) |
| **Evidence** | `artifacts/runs/r3_full_budget100_ga21/volatility_breakout/`: BTC 6/10 RS seeds positive but 0/10 CI bootstrap >0; median +6.5% BTC / −73.5% ETH |
| **Limitations** | Strongest partial BTC signal; fails robustness and ETH criteria |
| **Next action** | **Do not retune.** Recorded as rejected |

### Strategy: Funding

| Field | Value |
|---|---|
| **Purpose** | Trade the funding-rate z-score (fade or follow) |
| **Implementation** | `TESTED` — `FundingTilt` in `src/perp_lab/strategies/funding.py` |
| **Validation maturity** | **`REJECTED`** — Gate R3 multi-seed (2026-08-10) |
| **Evidence** | `artifacts/runs/r3_full_budget100_ga21/funding/`: 0/10 BTC RS positive; 1/10 ETH RS positive; median −40.9% / −59.9% |
| **Limitations** | Signal only; funding cashflow applied by backtester |
| **Next action** | **Do not retune.** Recorded as rejected |

### Strategy: BTC-ETH Confirmation (cross-asset)

| Field | Value |
|---|---|
| **Purpose** | Use the other asset's lagged move as confirmation, lead-lag or divergence signal |
| **Implementation** | `TESTED` — `CrossAssetConfirmation` in `src/perp_lab/strategies/cross_asset.py` |
| **Validation maturity** | **`REJECTED`** — Gate R3 multi-seed (2026-08-10) |
| **Evidence** | `artifacts/runs/r3_full_budget100_ga21/BTC_ETH_confirmation/`: 1/10 BTC RS positive; 0/10 ETH RS positive; median −65.8% / −68.3% |
| **Limitations** | Cross-asset reference causal; no robust multi-seed edge |
| **Next action** | **Do not retune.** Recorded as rejected |

### Baselines (fixed references)

| Field | Value |
|---|---|
| **Purpose** | Non-searched reference strategies so a searched result has something to beat |
| **Implementation** | `TESTED` |
| **Files** | `src/perp_lab/strategies/baselines.py`, `src/perp_lab/evaluation/baselines.py` |
| **Evidence** | `Flat`, `AlwaysLong` (buy-and-hold), `FixedCrossover(24, 96)`, `FixedMomentum(24)`, `FixedMeanReversion(48, 2.0)`, `RandomEntry(seed, exposure)`; tests in `tests/unit/test_baselines.py`, `tests/unit/test_evaluation_baselines.py` |
| **Limitations** | Repriced on the same OOS ledger bars; `coverage_id` guards against comparing different spans |
| **Next action** | None |

### Backtester

| Field | Value |
|---|---|
| **Purpose** | Cost- and funding-aware next-bar execution |
| **Implementation** | `TESTED` — `src/perp_lab/backtesting/{engine,metrics}.py` |
| **Validation maturity** | n/a (infrastructure) |
| **Evidence** | `tests/unit/test_backtesting.py`, `test_backtesting_extended.py` |
| **Limitations** | Costs are provisional ([ADR 0005](../decisions/0005-provisional-transaction-costs.md)); no partial fills, no market impact, no order book |
| **Next action** | None for current phase |

Execution timing: side decided at close of bar *t*, position applied at bar *t+1*,
return measured open-to-open. Costs: fee + slippage on `|Δposition|`; funding
settled inside the holding interval; `require_funding=True` raises rather than
substituting zero. Metrics include Sharpe, Sortino, Calmar, max drawdown, Ulcer
index, VaR/ES at 95 % and 99 %, skewness, excess kurtosis, exposure, hit rate,
turnover and trade counts, annualised on 365 days.

### Walk-forward validation

| Field | Value |
|---|---|
| **Purpose** | Chronological expanding train → validation → test folds with purge and embargo |
| **Implementation** | `TESTED` — `src/perp_lab/validation/walk_forward.py` |
| **Evidence** | `tests/unit/test_walk_forward.py`, `test_walk_forward_coverage.py`, `tests/unit/test_holdout_guards.py` |
| **Limitations** | Only the `expanding` scheme is implemented |
| **Next action** | None |

Research geometry: 730-day initial train, 90-day validation, 90-day test, 90-day
step → **15 folds** on the development period. `assert_folds_exclude_holdout`
fails closed.

### Random Search

| Field | Value |
|---|---|
| **Purpose** | Unbiased search baseline against which the GA must justify itself |
| **Implementation** | `TESTED` — `src/perp_lab/search/random_search.py` |
| **Validation maturity** | `MULTI-SEED` (as part of the momentum study) |
| **Evidence** | `tests/unit/test_search_random.py`; clean R2 study and [ADR 0013](../decisions/0013-clean-momentum-rebaseline.md) |
| **Limitations** | Search instability is material in R2 (seed/fold SD ratio 0.401); multiple seeds remain mandatory |
| **Next action** | Remains the default search baseline for R3 |

### Genetic Algorithm

| Field | Value |
|---|---|
| **Purpose** | Evolutionary search over the same space, evaluator and budget |
| **Implementation** | `TESTED` — `src/perp_lab/search/genetic_algorithm.py` |
| **Validation maturity** | `MULTI-SEED` — **no evidence of superiority over Random Search** |
| **Evidence** | Clean paired comparison over 15 calendar folds: mean GA − RS = **−0.061**, 95% CI **[−0.399, +0.277]**, Cohen's dz = −0.100 |
| **Limitations** | Has not justified its additional complexity; the interval spans plausible advantages for either engine |
| **Next action** | Keep only as an equal-budget comparator where R3 requires it; do not prefer it over RS |

### Budget parity

| Field | Value |
|---|---|
| **Purpose** | Guarantee both engines spend an identical number of objective evaluations |
| **Implementation** | `TESTED` |
| **Files** | `src/perp_lab/search/config.py` (`effective_budget`, `reachable_evaluations`), `src/perp_lab/config/experiment.py` (`ga_unique_evaluations`), `_assert_budget_parity` / `_budget_report` in `src/perp_lab/search/runner.py` |
| **Evidence** | `BudgetParityError` raised when an engine falls short, naming the offending fold; first R2 attempt aborted at GA 299/300; successful R2 audit confirms 300 evaluations per engine in every fold of all 20 units |
| **Limitations** | None known. Parity is now asserted **inside every outer fold**, since a matching run-level total can still hide an unevenly searched fold |
| **Next action** | None |

Budget counts **unique, valid, non-cached** evaluations. Invalid proposals,
duplicates and cache hits do not consume it — this is what makes the GA's elitism
non-exploitable.

### Determinism and seeding

| Field | Value |
|---|---|
| **Purpose** | Byte-reproducible experiments from one base seed |
| **Implementation** | `TESTED` — `src/perp_lab/utils/seeds.py` |
| **Evidence** | `SeedScheduler` derives streams via `blake2b(namespace ‖ keys)` → `numpy.SeedSequence`; per-run-seed, per-engine and per-fold-regime streams; `tests/unit/test_seed_scheduler.py` |
| **Limitations** | `evaluation/` bootstrap and `RandomEntry` take a plain integer seed rather than a scheduler namespace |
| **Next action** | None blocking |

### Multi-seed orchestration

| Field | Value |
|---|---|
| **Purpose** | Run a `(symbol, seed)` grid with crash-safe resume |
| **Implementation** | `TESTED` — `src/perp_lab/experiments/multi_seed.py` |
| **Evidence** | `tests/integration/test_multi_seed_orchestration.py`; `study_manifest.json` + `checkpoint.json` in the study directory |
| **Limitations** | Resume compatibility is keyed on a config fingerprint that deliberately excludes seed and symbol |
| **Next action** | None |

### Multi-seed statistical analysis

| Field | Value |
|---|---|
| **Purpose** | Turn a seed grid into defensible inference |
| **Implementation** | `TESTED` — `src/perp_lab/evaluation/multi_seed.py` |
| **Evidence** | `long_table`, `per_seed_aggregate`, `variance_decomposition`, `paired_rs_ga`, `seed_stability_report`, `analyse_study`; `tests/unit/test_multi_seed_analysis.py` |
| **Limitations** | Inference is a paired *t* interval and Cohen's dz. **No** Wilcoxon, permutation or study-level bootstrap test is implemented |
| **Next action** | Consider a distribution-free companion test given heavy tails |

The unit of inference is **symbol × fold with seeds averaged inside each cell**
(30 units, not 300). Seeds share one price history, so counting them as
independent would shrink intervals by roughly √10 and manufacture significance.
Measured seed-to-fold SD ratio: **0.512 (RS)**, **0.428 (GA)** — re-running the
search moves a result about half as much as changing the market period.

### Robustness battery

| Field | Value |
|---|---|
| **Purpose** | Stress a candidate's OOS ledger without re-running search |
| **Implementation** | `TESTED` — `src/perp_lab/evaluation/{robustness,study_robustness}.py` |
| **Validation maturity** | Applied to the momentum study only |
| **Evidence** | `tests/unit/test_robustness.py`, `test_study_robustness.py`; `artifacts/runs/multiseed_momentum_baseline/study_robustness.json` |
| **Limitations** | See the coverage table below — several advertised checks do **not** exist |
| **Next action** | Implement parameter perturbation and regime-conditional evaluation |

| Check | Status | Where |
|---|---|---|
| Circular block bootstrap CI (blocks 24 / 168 / 720) | **Implemented** | `block_bootstrap_ci` |
| Cost stress (fee × 1, 1.5, 2) | **Implemented** | `stress_costs` |
| Slippage stress (× 1, 2, 5) | **Implemented** | `RobustnessBattery` |
| Execution-delay stress (1, 2 bars) | **Implemented** | `stress_execution_delay` |
| Trade concentration / drop-top-k | **Implemented** | `concentration_analysis`, `drop_best_trades` |
| Parameter perturbation | **Not implemented** | — |
| Regime-conditional evaluation | **Not implemented** | regime code exists in `eda/`, not wired into evaluation |
| Monte Carlo path simulation | **Not implemented** | only bootstrap resampling exists |

Per-run binary tests: `positive_total_return`, `beats_buy_and_hold`,
`survives_double_costs`, `bootstrap_sharpe_ci_excludes_zero`.

### Tracking and provenance

| Field | Value |
|---|---|
| **Purpose** | Make every run reconstructible and comparable |
| **Implementation** | `TESTED` — `src/perp_lab/tracking/{run,identity,journal}.py` |
| **Evidence** | `tests/unit/test_run_identity.py`, `test_journal.py`; per-run `git_state.json`, `environment.json`, `dataset_manifests.json`, `feature_manifest.json`, `folds.json`, `objective.json` |
| **Limitations** | Runs from a dirty worktree are marked `provisional` but still executable |
| **Next action** | None |

`RunIdentity` fingerprints config + contract + dataset hashes + commit + diff +
untracked-file hashes, so two runs are only pooled when their experimental
contract genuinely matches.

### Dashboard (FastAPI + Next.js)

| Field | Value |
|---|---|
| **Purpose** | Educational, auditable presentation of the research |
| **Implementation** | `TESTED` |
| **Files** | `src/perp_lab/api/` (routers `health`, `market`, `eda`, `runs`, `research`), `apps/web/src/app/` (Spanish canonical routes + English legacy routes) |
| **Evidence** | `tests/api/test_api_endpoints.py`, `test_api_security.py`, `test_research_dashboard.py`; Playwright suite in `apps/web` |
| **Limitations** | Cannot yet express the maturity model in this document; a Streamlit app (`src/perp_lab/dashboard/`) remains as legacy |
| **Next action** | Add a maturity/evidence surface — see [master roadmap](master_roadmap.md) |

### ML / meta-labeling

| Field | Value |
|---|---|
| **Implementation** | **`SPECIFIED` only — no code** |
| **Evidence** | Referenced in `docs/methodology/experimental_design.md`; the only concrete hook is `features/predictors.py`, whose `label_time` is always null |
| **Next action** | Blocked until at least one base strategy is `ROBUST` |

There is **no** triple-barrier labeling, **no** meta-labeling, **no** Logistic
Regression, Random Forest or LightGBM anywhere in `src/`.

### Portfolio · Risk · Simulation · Funded accounts · Execution

| Field | Value |
|---|---|
| **Implementation** | **Not present in any form** — no directories, no specification documents |
| **Evidence** | `src/perp_lab/` contains exactly: `api`, `backtesting`, `config`, `dashboard`, `data`, `eda`, `evaluation`, `experiments`, `features`, `regimes`, `reporting`, `search`, `strategies`, `tracking`, `utils`, `validation` |
| **Next action** | Specified for the first time in [master roadmap](master_roadmap.md) and [future architecture](future_architecture.md). No directories created — see the note below |

Per the operating contract, **no empty directories were created** for these
layers. They stay documented until the phase that implements them.

---

## Current clean scientific results

### CR-1 — Momentum is rejected

**Source:** `artifacts/runs/multiseed_momentum_r2_clean_v2/`,
[ADR 0013](../decisions/0013-clean-momentum-rebaseline.md).
**Design:** 2 assets × 10 derived seeds × 15 isolated outer folds; 300 unique
evaluations per engine and fold; OOS 2022-03-31 … 2025-12-09.

All 40 asset-seed-engine combinations lose money. Zero beat buy-and-hold, zero
survive doubled costs and zero have a one-week-block bootstrap Sharpe interval
excluding zero. **Status: rejected. Do not retune.**

### CR-2 — No evidence that the GA beats Random Search

Paired over 15 calendar folds after averaging seeds and correlated assets:
mean GA − RS = **−0.061**, 95% CI **[−0.399, +0.277]**, Cohen's dz =
**−0.100**. Five folds favour GA, nine favour RS and one ties. **Status: no
difference demonstrated; Random Search remains the default baseline.**

### CR-3 — Seed instability remains material, but is engine-dependent

Seed-to-fold SD ratio **0.401 (RS)** / **0.049 (GA)**. The clean fold-local GA
is considerably less seed-sensitive in this study, but that stability does not
translate into better OOS performance.

---

## Frozen superseded scientific results

These results are **frozen**. They may be superseded by a re-run under a
corrected protocol, but they must never be quietly deleted, retuned or restated
more favourably.

> **All of FR-1 … FR-4 were produced under the superseded search protocol and
> are invalid as inference as of 2026-08-09.** They are retained verbatim for
> traceability. Their run directories carry a `SUPERSEDED.json` marker recording
> the reason and the original provenance (run id, git commit, seeds, budget,
> config fingerprint), written by `scripts/mark_superseded_runs.py`; 64
> directories were marked and none deleted. Gate R2 has now replaced FR-1/FR-2
> with CR-1/CR-2 above; the text below remains verbatim historical context.

### FR-1 — Momentum has no demonstrated edge

**Source:** `artifacts/runs/multiseed_momentum_baseline/`,
[ADR 0011](../decisions/0011-multi-seed-baseline.md)
**Design:** 2 assets × 10 derived seeds × 15 folds; OOS 2022-03-31 … 2025-12-09.
**Seeds:** 891022, 341110, 693857, 683778, 765570, 692467, 605142, 671194, 707014, 278037

BTCUSDT loses money under both engines across all ten seeds and is beaten by
buy-and-hold in every case. ETHUSDT is centred near zero. **No** run/engine
combination has a bootstrap Sharpe CI excluding zero.

**Status: negative to inconclusive. Momentum must not be retuned retrospectively.**

### FR-2 — No evidence that the GA beats Random Search

Paired over 30 symbol × fold units: mean GA − RS = **+0.183**, 95 % CI
**[−0.053, +0.419]**, Cohen's dz = **0.289**, GA favoured in 19 folds, RS in 10.
The interval includes zero.

**Status: no difference demonstrated.** The single-seed runs that appeared to
favour the GA did not survive ten seeds.

### FR-3 — Single-seed conclusions are unreliable in this problem

Seed-to-fold SD ratio **0.512 (RS)** / **0.428 (GA)**: changing only the search
seed moves the result roughly half as much as moving to a different market
period. Any single-seed claim in this repository is provisional by construction.

### FR-4 — The four-family pilot is pipeline evidence, not performance evidence

`artifacts/runs/pilot/pilot_summary.json`, 2026-08-07: four families × 2 assets ×
15 folds at budget 60 with **one** seed (891022). Its `multi_seed_analysis.json`
files contain no valid confidence interval because a single seed cannot produce
one. Reported Sharpe values must never be cited as evidence of edge.

---

## Known inconsistencies

### Inconsistency 1 — Outer-fold contamination in candidate search

**Severity: high. RESOLVED IN CODE 2026-08-09 (Gate R1). Every experimental
result produced before that date remains invalid as inference.**

The description below is retained because it explains what the superseded
artifacts contain and why they may not be cited. For the corrected contract, the
measured cost and the isolation evidence, see
[ADR 0012](../decisions/0012-outer-fold-contamination-in-candidate-search.md).

`CandidateEvaluator.evaluate()` in `src/perp_lab/search/evaluator.py` backtests a
candidate on the validation slice of **every** fold and collapses the result into
one scalar through `aggregate_objective`:

```python
for fold in self.bundle.folds:
    result = self._backtest(strategy, fold.val)
    fold_metrics.append(_fold_metrics(result))

obj = aggregate_objective(fold_metrics, ...)
candidate.fitness = obj.fitness
```

Both engines rank candidates on that pooled fitness. For fold 0, the pool
includes validation windows from fold 14 — years *after* fold 0's test window.

`_fold_winners()` then picks each fold's winner using only that fold's own
validation Sharpe, which limits but does not remove the problem:

- **Random Search** samples independently of fitness, so its *candidate pool* is
  not shaped by future data. Its per-fold winner is comparatively clean; its
  reported `best` candidate is not.
- **The Genetic Algorithm** evolves its population *on* the pooled fitness. Its
  candidate pool is directly shaped by validation windows that lie in the future
  relative to earlier folds.

**Consequence: the RS-vs-GA comparison is confounded in the GA's favour.** That
FR-2 still finds no GA advantage makes the negative conclusion conservative, but
it invalidates any positive reading of the GA's single-seed results.

**Resolution (2026-08-09).** Search now runs independently inside every outer
fold via `single_fold_bundle()` and one evaluator per fold; another fold's data
is absent rather than filtered, and a cross-fold request raises
`FoldIsolationError`. The cross-fold dispersion penalty was replaced by a
within-fold sub-block dispersion so the robustness pressure survived the change.
Each fold's winner is fingerprinted on validation before its test slice is
scored once. Verified by `tests/unit/test_search_fold_isolation.py` and by
`scripts/audit_fold_isolation.py` on a real 15-fold momentum pilot.

**Still outstanding:** every *number* produced before the fix. See
[Phase R2](master_roadmap.md).

### Inconsistency 2 — The leakage fix was on a divergent branch — RESOLVED

`fix/outer-fold-leakage` (`588ab8e`) descended from `main` via
`feat/research-dashboard-redesign`, so it lacked the `evaluation/` package, the
three newer families, `effective_budget` parity and the multi-seed orchestrator,
and could not be merged.

**Resolution:** the branch was abandoned rather than merged, and R1 was
re-implemented on `docs/roadmap-consolidation`, which descends from the
multi-seed branch. The re-implementation additionally covers what the old branch
could not see: per-fold budget parity across both engines, the within-fold
dispersion penalty, the multi-seed protocol guard
(`ContaminatedStudyError`), the per-fold artifact schema (v2) and the
API/dashboard contract.

### Inconsistency 3 — `docs/roadmap.md` is stale

It states "only Phase 1 is implemented" and lists Phases 2, 3 and 5 as "not
started", contradicting the shipped search framework, evaluation layer and
dashboard. Superseded by this directory; the old file now points here.

### Inconsistency 4 — `docs/architecture.md` module status is stale

Chapter 5 modules are marked 🟡 (in progress) although `search/`, `evaluation/`,
`experiments/` and `tracking/` are implemented and tested.

### Inconsistency 5 — An ADR cites a CI not reproducible from artifacts

[ADR 0011](../decisions/0011-multi-seed-baseline.md) quotes a single-seed interval
`[0.011, 1.044]`. No artifact JSON in `artifacts/` contains those bounds. The ADR
itself states pre-scheduler runs are not poolable with the study, so the figure is
**documentary only** and must not be cited as a result.

### Inconsistency 6 — Advertised robustness exceeds implemented robustness

`docs/methodology/validation_protocol.md` describes a broader battery than was
required for the R3 negative outcome. Regime-conditional metrics, trade-path
bootstrap and parameter-perturbation replay are implemented in `evaluation/` as
of 2026-08-10; Gate R4 experimental application was skipped because no family
survived R3. The circular block bootstrap must **not** be described as a Monte
Carlo account simulator.

### Inconsistency 7 — Orchestration smoke runs look like results

Roughly 20 `search_mean_reversion_*` directories from 2026-08-05 are multi-seed
orchestration test output, not a mean-reversion study. Mean reversion is
`NOT EVALUATED`.

---

## Summary table

| Component | Implementation | Validation maturity | Evidence | Next action |
|---|---|---|---|---|
| Data | `TESTED` | n/a | Manifests, provenance audit | None |
| EDA | `TESTED` | n/a | 59 metadata sidecars | Feeds hypotheses |
| Features | `TESTED` | n/a | Leakage tests pass | None |
| Momentum | `TESTED` | **`REJECTED`** | CR-1, ADR 0013 | Do not retune |
| Breakout | `TESTED` | **`REJECTED`** | ADR 0015, R3 rollup | Do not retune |
| Mean Reversion | `TESTED` | **`REJECTED`** | ADR 0015, R3 rollup | Do not retune |
| Volatility Breakout | `TESTED` | **`REJECTED`** | ADR 0015, R3 rollup | Do not retune |
| Funding | `TESTED` | **`REJECTED`** | ADR 0015, R3 rollup | Do not retune |
| BTC-ETH Confirmation | `TESTED` | **`REJECTED`** | ADR 0015, R3 rollup | Do not retune |
| Baselines | `TESTED` | n/a | 6 fixed references | None |
| Backtester | `TESTED` | n/a | Next-bar tests | None |
| Walk-forward | `TESTED` | n/a | 15 folds, guards fail closed | None |
| Random Search | `TESTED` | `MULTI-SEED` — clean baseline | CR-2 | Default R3 search baseline |
| Genetic Algorithm | `TESTED` | `MULTI-SEED` — no advantage | CR-2 | Equal-budget comparator only |
| Budget parity | `TESTED` | n/a | R3: 100/fold/engine across 100 runs | None |
| Fold isolation (R1) | `TESTED` | verified | ADR 0012, 100/100 R3 audits | None |
| Multi-seed | `TESTED` | R2 + R3 complete | CR-1, ADR 0015 | None |
| Robustness | `TESTED` | R3 studies complete | Bootstrap, cost stress, promotion gate; R4 code added | R4 gate skipped |
| Tracking | `TESTED` | n/a | Run identity | None |
| Dashboard | `TESTED` | n/a | API + Playwright | Add maturity surface |
| ML / meta-labeling | `SPECIFIED` | — | None | Blocked on a robust base |
| Portfolio | `SPECIFIED` | — | None | Blocked |
| Risk | `SPECIFIED` | — | None | Blocked |
| Simulation | `SPECIFIED` | — | None | Blocked |
| Funded accounts | `SPECIFIED` | — | None | Blocked |
| Execution / live | `SPECIFIED` | — | None | Blocked |
| Holdout evaluation | `SPECIFIED` | **never opened** | — | Final report only |
