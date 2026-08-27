# Strategy & Discovery Specification (Chapter 5.4–5.5) — v0.1

Defines the three interpretable baseline families, the shared parameter space,
the fixed-length GA chromosome, and the Random-Search / Genetic-Algorithm
parity contract. Parameter ranges are the authoritative source in
[`configs/experiment.yaml → strategies`](../../configs/experiment.yaml). Status:
**specification only** (no `strategies/`/`search/` code yet).

Common conventions for all families:
- **Timeframe:** primary 1h (15m for complementary runs).
- **Execution timestamp:** signal computed at **close of bar *t***, filled at
  the **open of bar *t+1*** (`next_bar_open`).
- **Position sizing:** volatility-target (provisional) or fixed-fraction; capped
  by `risk.max_position_leverage`.
- **Exits (shared):** stop-loss = `k_sl · ATR`, take-profit = `k_tp · ATR`,
  hard **max holding period** in bars; whichever triggers first.
- **Filter (shared, optional):** volatility/regime gate restricting entries to
  an allowed set of causal volatility regimes.

## 1. Momentum / trend-following

- **Entry:** fast MA crosses slow MA (`sma_fast` vs `sma_slow`); long on upward
  cross, short on downward cross. Optional trend gate: only take longs when
  `close > sma(trend_filter_ma)` (and mirror for shorts).
- **Direction:** long / short / both (configurable).
- **Exit:** opposite cross, or shared stop/TP/time barrier.
- **Parameters:** `fast_ma ∈ {6,12,24,48}`, `slow_ma ∈ {48,96,168,336}`
  (`fast_ma < slow_ma` enforced), `trend_filter_ma ∈ {168,336}` (optional).

## 2. Breakout

- **Entry:** close breaks above the rolling Donchian high (long) or below the
  rolling low (short), where the channel **excludes the current bar**;
  `confirmation_bars` consecutive closes required.
- **Direction:** long / short / both.
- **Exit:** re-entry into the channel, or shared stop/TP/time barrier.
- **Parameters:** `channel_window ∈ {24,48,96}`, `confirmation_bars ∈ {1,2,3}`.

## 3. Mean-reversion

- **Entry:** `zscore_w = (close − sma_w)/std_w` beyond `±entry_z`; fade the move
  (short when z ≥ +entry_z, long when z ≤ −entry_z).
- **Direction:** long / short / both.
- **Exit:** z-score reverts within `±exit_z`, or shared stop/TP/time barrier.
- **Parameters:** `zscore_window ∈ {24,48,96}`, `entry_z ∈ {1.5,2.0,2.5,3.0}`,
  `exit_z ∈ {0.0,0.5,1.0}` (`exit_z < entry_z` enforced).

## 4. Fixed-length GA chromosome

A single fixed-length vector represents **any** candidate in the shared space.
Unused genes for the active family are ignored by the decoder but remain present
(fixed length simplifies crossover/mutation). Genes are integer indices into the
discrete option lists in `experiment.yaml` (or normalised reals mapped to
ranges).

| Gene | Meaning | Encoding | Source list |
|------|---------|----------|-------------|
| g0 | family | int {0,1,2} | momentum / breakout / mean_reversion |
| g1 | direction | int {0,1,2} | long / short / both |
| g2 | momentum.fast_ma | index | `fast_ma` |
| g3 | momentum.slow_ma | index | `slow_ma` |
| g4 | momentum.trend_filter_ma (+off) | index | `trend_filter_ma` ∪ {none} |
| g5 | breakout.channel_window | index | `channel_window` |
| g6 | breakout.confirmation_bars | index | `confirmation_bars` |
| g7 | mean_rev.zscore_window | index | `zscore_window` |
| g8 | mean_rev.entry_z | index | `entry_z` |
| g9 | mean_rev.exit_z | index | `exit_z` |
| g10 | stop_loss_atr | index | `stop_loss_atr` |
| g11 | take_profit_atr | index | `take_profit_atr` |
| g12 | max_holding_bars | index | `max_holding_bars` |
| g13 | volatility_filter.enabled | int {0,1} | on/off |
| g14 | regime_gate | index | `regime_gate_options` |

Decoder enforces validity constraints (`fast<slow`, `exit_z<entry_z`); invalid
draws are repaired to the nearest valid combination. `encode`/`decode` are exact
inverses on valid genes.

## 5. Random Search vs. GA — parity contract

Both methods MUST share, so any performance difference is attributable to the
search operator alone:

- The **same** chromosome/parameter space (Sections 1–4).
- The **same** causal features and historical information.
- The **same** walk-forward folds, purging and embargo.
- The **same** transaction-cost model.
- The **same** `evaluation_budget` (candidate evaluations) — GA:
  `population_size × generations = budget`.
- Reproducible seeds derived from the global seed (per-method, per-repeat).

**Random Search:** i.i.d. uniform sampling over the discrete space (with the
same validity repair), evaluate, keep the best.

**Genetic Algorithm:** tournament selection, single-/uniform crossover
(`crossover_rate`), per-gene mutation (`mutation_rate`), elitism
(`elitism`), for `generations` generations. Fitness = Section 6.

## 6. Fitness function

Maximised, computed on **walk-forward OOS folds only** (never the holdout):

```
fitness = w_sharpe · WF_Sharpe
        − w_dd     · f(MaxDrawdown)
        − w_turn   · f(Turnover)
        − w_inst   · std_over_folds(Sharpe)
        − w_cplx   · complexity(params)
subject to:  n_trades_total ≥ min_trades_total
             n_trades_per_fold ≥ min_trades_per_fold
             leverage ≤ max_leverage
```

Constraint violations incur a hard penalty (or rejection). Weights and
thresholds are in `experiment.yaml → fitness` (provisional). `complexity`
counts active rules/parameters, penalising needlessly elaborate strategies to
favour interpretable ones.

## 7. Promotion and holdout discipline

Only candidates that (i) satisfy the constraints and (ii) show positive net OOS
performance on a majority of folds proceed to the robustness battery
(`validation_protocol.md`). The frozen holdout is evaluated **once**, after all
selection and robustness analysis is complete, for the final reported numbers.

---

## As-executed status note (added 2026-08-28; the v0.1 text above is preserved unchanged)

This file is the pre-implementation specification (v0.1, `specification
only`). Two of its shared conventions were superseded by the implemented
search spaces that the confirmatory rounds actually froze (registry space
v1.1.0, ADR 0014 cardinalities, run identities recorded per study):

- **Position sizing**: the volatility-target option was never implemented in
  the engine; every executed round ran fixed-fraction 1.0 as emitted by the
  strategy. `risk.max_position_leverage` is not consumed by the backtester;
  `max_leverage` exists only as a provisional fitness constraint.
- **Shared exits (ATR stop-loss / take-profit / max holding)**: not part of
  any executed family's parameter space. The only price stop among non-CRT
  families is volatility_breakout's `volatility_stop` exit mode; CRT
  families carry their own trade-management engine; several S1/S2 families
  use pure time exits.

The executed contracts are the per-round pre-registrations (ADR 0012 SS5 /
0013 for R2, ADR 0014, strategy_catalogue_s1.md, gate_s2_batch_01.md,
crt_intraday.md, strategy_catalogue_s3.md + ADR 0019); this note exists so
the v0.1 conventions are not cited as executed protocol.
