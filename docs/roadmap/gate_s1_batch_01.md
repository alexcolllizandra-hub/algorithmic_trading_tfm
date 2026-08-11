# Gate S1 — Batch 01 (frozen pre-specification)

**Version:** 1.0 · **Frozen:** 2026-08-11 · **Status:** S1-A passed; S1-B and
S1-C **not started**

This instantiates the generic Gate S1 contract in
[phase_gates.md](phase_gates.md) with a concrete, limited and **frozen** batch.
Everything below was written before any S1 experimental result existed. Nothing
here may be edited after the first S1-B run starts; a change requires a new batch
with a new number.

Related: [strategy_catalogue_s1.md](../methodology/strategy_catalogue_s1.md) ·
[experimental_design.md](../methodology/experimental_design.md) · ADR 0016.

---

## Dependency status

The generic gate lists dependencies "Gates R3, R4". Their state at freeze time:

| Gate | State | Consequence for S1 |
|---|---|---|
| R3 | `CLOSED_NEGATIVE`, 0/5 promotions (ADR 0015) | Satisfied: R3 ran to completion and returned a verdict |
| R4 | `SKIPPED` — zero R3 promotions, `r4_required = false` at closure | Satisfied **vacuously**. R4 is confirmatory on *promoted* families only; with none, there is nothing for it to confirm. R4 is **not** run for S1 families retrospectively, and S1 does not reopen it |

The R3 verdict is **not** revisited, reinterpreted or re-searched. Its artifacts
are historical and immutable.

---

## 1. Batch contents and diversity justification

Four families, chosen to span mechanisms that fail for *different* reasons, so a
uniform negative result is informative rather than a single mechanism tested four
times:

| ID | Family | Tier | Mechanism class | Traded object | Exit governed by |
|---|---|---|---|---|---|
| S1-01 | `mtf_trend_consensus` | core | Trend / drift persistence | Single leg, directional | Signal (consensus decay) |
| S1-02 | `funding_reversal` | core | Positioning / carry unwind | Single leg, event-driven | Clock |
| S1-03 | `xasset_spread_reversion` | extended | Relative value | Single leg expressing a pair view | Signal (spread band) |
| S1-04 | `intraday_seasonality` | experimental | Calendar / flow periodicity | Single leg, no price predictor | Clock |

Two are signal-exited and two clock-exited; two use price only, one uses
derivatives data, one uses no price at all in its entry. No two share both a
mechanism class and an exit mechanism.

**Excluded from this batch on purpose** (candidates for a future S1 batch, not
implemented): adaptive channels, volume-anomaly and liquidity proxies, basis
carry, cointegration residuals, cross-sectional rotation, regime-transition
strategies and signal ensembles. Ensembles in particular may only be considered
**after** their components have been evaluated individually.

---

## 2. Frozen hypothesis count (data-snooping ledger)

The multiple-comparison burden must be stated before results are seen.

| Family | Configurations reachable | Assets | Nominal hypotheses |
|---|---:|---:|---:|
| `mtf_trend_consensus` | 4 horizon sets × 2 agreement × 2 exit × 3 strength × 2 window × 3 direction × 4 gate states | 2 | 2 304 |
| `funding_reversal` | 3 rank × 3 pct × 4 holding × 2 floor × 3 direction × 4 gate states | 2 | 1 728 |
| `xasset_spread_reversion` | 4 lookback × 3 entry × 3 exit × 7 corr states × 3 direction × 4 gate states | 2 | 6 048 |
| `intraday_seasonality` | 24 hours × 4 holding × 2 side × 3 trend states × 4 gate states | 2 | 4 608 |

These are **space cardinalities before repair and validation**, recorded as an
upper bound on the search's degrees of freedom. The number actually used for the
deflated Sharpe ratio is the count of **unique valid objective evaluations**
recorded by the run, per family and per asset — not the cardinality above and not
the budget.

**Batch attempt counter:** this is S1 attempt **1**. Every further batch
increments the counter and the counter is reported alongside any result, so the
number of times the development partition has been consulted is never lost.

---

## 3. Evaluation funnel

### S1-A — Technical validity · **PASSED 2026-08-11**

Unit, causality and invariance tests on synthetic data with known behaviour.

* Implementation: `src/perp_lab/strategies/{mtf_trend_consensus,funding_reversal,intraday_seasonality,xasset_spread_reversion,timed_exit}.py`
* Config: `src/perp_lab/config/experiment.py` (four new validated family models)
* Registry: `src/perp_lab/search/registry.py` (`S1_FAMILIES`, space version 1.1.0)
* Tests: `tests/unit/test_strategies_s1.py`, `tests/unit/test_search_registry_s1.py`, `tests/unit/test_multiple_testing.py`
* Evidence: `uv run ruff check .`, `uv run ruff format --check .`, `uv run pyright` (0 errors) and `uv run pytest -m "not network"` all pass on commit `feat/s1-prespecification`.

### S1-B — Development pilot · **NOT STARTED**

* Development partition only; holdout untouched.
* Pre-defined folds; **reduced budget, identical across engines**: 25 unique
  objective evaluations per fold per engine.
* Purpose: surface implementation faults and families that cannot trade at all
  (zero or near-zero trade counts). It is **not** a performance screen.
* A family is dropped from S1-C only for a *mechanical* reason — no valid
  candidates, no trades, or a failed invariant — never for weak performance.
* Negative and dropped outcomes are recorded as artifacts, not deleted.

### S1-C — Full study · **NOT STARTED**

* All planned outer folds; 10 seeds per asset per family.
* Random Search is the **confirmatory** engine; the Genetic Algorithm is a
  **secondary diagnostic** and never decides promotion.
* Budget parity: 100 unique objective evaluations per fold per engine, cached
  duplicates and repaired-invalid proposals excluded from the count.
* Independent seed streams derived from `AppSettings.seed = 42`.
* Reported per asset × family × engine × fold × seed.

---

## 4. Promotion criteria (frozen)

Reused unchanged from Gate R3 so results are comparable, with two additions.

A family is promoted only if, **on Random Search and on both assets**, at least
**6 of 10 seeds** satisfy all six criteria:

| # | Criterion |
|---|---|
| C1 | Positive total net OOS return |
| C2 | Bootstrap Sharpe confidence interval excludes zero |
| C3 | Survives doubled fees and slippage |
| C4 | Beats buy-and-hold on the same OOS ledger |
| C5 | Survives dropping the top five trades |
| C6 | Result is not confined to a single fold |

**Separate veto** (not a seventh criterion): `min_oos_trades_met` — at least five
OOS trades per seed. A family failing the veto is rejected regardless of C1–C6.

**Addition S1-a — selection-bias correction.** A promoted family must also show a
deflated Sharpe ratio above 0.95, computed with the family's recorded count of
unique valid evaluations as the trial count
(`evaluation/multiple_testing.deflated_sharpe_ratio`). The PBO estimate over the
family's per-fold performance matrix must be below 0.5
(`probability_of_backtest_overfitting`). Across the four families, Benjamini–Hochberg
false-discovery-rate control at α = 0.05 is applied to the family-level p-values.

**Addition S1-b — parameter stability across folds.** For `intraday_seasonality`
specifically, the selected `entry_hour` must be stable across outer folds; an
hour that changes from fold to fold falsifies the seasonality claim regardless of
aggregate performance.

**If S1 promotes nothing**, the result is recorded as `CLOSED_NEGATIVE` exactly
as R3 was. It may not be rescued by relaxing a criterion, by re-tuning a rejected
family, or by adding a family after seeing the results. Only a new,
pre-specified batch may open.

---

## 5. Invariants for this batch

1. The holdout `[2026-01-01, 2026-07-01)` is **not** read, loaded, summarised or
   used to inform any choice in this batch.
2. Search remains independent per outer fold (ADR 0012).
3. Purge and embargo unchanged from the R3 geometry.
4. R3-closed families are not re-searched or re-parameterised.
5. Criteria in section 4 are frozen; changing one requires a new batch number.
6. Every run records commit, resolved config, dataset manifests, seed schedule,
   budget accounting and the batch attempt counter.

---

## 6. Next command

S1-A is complete. The next step is S1-B, which requires a pilot search config per
family. It has not been created yet, so no S1-B run exists:

```bash
# Not yet runnable: configs/search_s1_*.yaml do not exist.
# S1-B starts by adding one pilot config per family, then:
uv run perp-lab search --config configs/search_s1_pilot_<family>.yaml
```
