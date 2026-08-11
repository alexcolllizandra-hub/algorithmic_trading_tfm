# Experimental Design (Chapter 5 methodology contract) — v0.1

This document operationalises the methodology for **discovering and validating
interpretable trading strategies** on BTCUSDT and ETHUSDT USDT-M perpetual
futures. It is the human-readable counterpart of
[`configs/experiment.yaml`](../../configs/experiment.yaml) and fixes the
contract that the Chapter 5 modelling pipeline must respect. It does not repeat
general theory; it states how each concept is realised in this project.

## Document status (two layers — do not conflate)

| Layer | Meaning |
|---|---|
| **Frozen methodological contract** | Research questions RQ1–RQ5, hypotheses H1–H5, temporal rules, cost assumptions, leakage-prevention rules and gate structure defined here and in [`hypothesis_matrix.md`](hypothesis_matrix.md). These rules were **not altered retrospectively** when experiments closed. |
| **Experimental execution state (2026-08-10)** | Phase gates **R1–R3 completed** under the corrected protocol; **R4 SKIPPED** (zero R3 promotions); frozen holdout **not opened**; meta-labeling gates **M1/M2 not started**. See [phase_gates.md](../roadmap/phase_gates.md) and ADRs 0012, 0013, 0015. |

Sections 7–11 below describe capabilities **specified** for the full Chapter 5
pipeline (including meta-labeling and extended robustness). Their *execution
status* is recorded in the table above and in the integrated thesis Chapter 8
traceability matrix — not by rewriting the original accept/reject rules here.

Values marked *provisional* in the configuration remain documented in ADR 0005.

---

## 1. Research questions

- **RQ1 — Profitability after costs.** Do interpretable rule-based strategies
  (momentum, breakout, mean-reversion) produce positive risk-adjusted
  performance on 1h BTC/ETH perpetuals *after realistic transaction costs*, out
  of sample?
- **RQ2 — Search method.** Under an identical strategy space, evaluation budget
  and validation protocol, does a **Genetic Algorithm (GA)** discover better
  out-of-sample strategies than **Random Search (RS)**?
- **RQ3 — Meta-labeling.** Does **meta-labeling** (a secondary model deciding
  whether to *act* on a base signal) improve the risk-adjusted performance of
  the base strategies?
- **RQ4 — Regime dependence.** Does strategy performance change materially
  across **volatility regimes**?
- **RQ5 — Robustness.** Does apparent performance survive **cost and parameter
  perturbations, delayed execution, subperiod and cross-asset stress**?

## 2. Testable hypotheses

See [`hypothesis_matrix.md`](hypothesis_matrix.md) for the full traceability
table (metrics, acceptance rules, evidence required). Summary:

- **H1.** At least one interpretable family yields net-of-cost OOS Sharpe > 0
  with a lower bound above a naive benchmark, on a majority of walk-forward
  folds. *Success is never declared on in-sample performance.*
- **H2.** GA achieves higher median net OOS fitness than RS at equal budget,
  with the difference stable across folds/seeds.
- **H3.** Meta-labeling improves net OOS Sharpe and/or reduces drawdown of the
  base signals without materially cutting the trade count below the minimum.
- **H4.** Net OOS performance differs across low/medium/high volatility regimes.
- **H5.** Promoted strategies retain positive net OOS performance under the
  robustness battery (higher costs, ±parameter jitter, delayed fills).

## 3. Experimental units

The unit of analysis is a **(strategy configuration, asset, timeframe)** triple
evaluated over the **walk-forward out-of-sample folds** of the development
period. A "candidate" is one point in the shared strategy space; an
"evaluation" is one full walk-forward backtest of one candidate. Meta-labeling
units are **individual base-signal events** (one per triggered entry).

## 4. Assets, timeframes and periods

- **Assets:** BTCUSDT, ETHUSDT (Binance USDT-M perpetuals).
- **Timeframes:** primary **1h** (modelling + backtesting); secondary **15m**
  (complementary experiments); base **5m** (source for deterministic resampling).
- **Development:** `2020-01-01 00:00 UTC` → `2025-12-31 23:xx UTC`
  (i.e. `[2020-01-01, 2026-01-01)`).
- **Frozen holdout:** `[2026-01-01 00:00 UTC, 2026-07-01)` — never loaded,
  plotted, inspected or used for any decision, feature, threshold or tuning.
  Opened **once**, at the very end, for the final report (ADR 0003).
- **Annualization:** 365 days (24/7 market).

## 5. Baseline strategies

Three interpretable families, fully specified in
[`strategy_specification.md`](strategy_specification.md):

1. **Momentum / trend-following** — moving-average relationships with an
   optional longer-horizon trend gate.
2. **Breakout** — Donchian-style rolling channel breakouts with confirmation.
3. **Mean-reversion** — z-score extremes with a reversion exit.

Every strategy declares: entry rule, direction, exit rule, stop-loss,
take-profit, maximum holding period, volatility/regime filter, parameter ranges,
position-sizing rule and execution timestamp. All exits include a hard
time-based barrier.

## 6. Random Search vs. Genetic Algorithm

Both methods are constrained to be *identical except for the search operator*:

- Same fixed strategy space (Section 5 / `strategies` block).
- Same historical information and causal features.
- Same walk-forward folds and purging/embargo.
- Same transaction-cost assumptions.
- Same **evaluation budget** (equal number of candidate evaluations).
- Reproducible seeds derived from the global seed.

The GA uses a **fixed-length chromosome** encoding family, direction, feature
windows, thresholds and risk parameters (see strategy specification). Fitness is
the penalised multi-objective score of Section 8. Neither method ever optimises
on the holdout.

## 7. Meta-labeling experiment

Base signals define **when** and **which direction** to trade. A secondary
classifier (logistic regression, random forest, LightGBM) predicts the
**probability that the base trade is profitable after costs**, using contextual
past-only features (funding, funding changes, trade–mark basis *lagged*,
taker-buy imbalance *lagged*, BTC–ETH dependence, volatility regime, temporal
encodings and properties of the base signal). Probabilities are calibrated on
validation folds; the decision threshold is tuned on validation, **never** on
the holdout. Meta-labeling can only *suppress or size* trades, not create new
directional signals.

## 8. Fitness and promotion

Penalised, maximised fitness computed on **OOS folds only**:

```
fitness = w_sharpe * WF_Sharpe
        - w_dd      * MaxDrawdownPenalty
        - w_turn    * TurnoverPenalty
        - w_inst    * FoldInstabilityPenalty
        - w_cplx    * ComplexityPenalty
```

with a hard penalty/rejection when `min_trades` constraints or leverage limits
are violated. Weights and constraints live in the `fitness` block of
`experiment.yaml` (provisional). Candidate **promotion** to the robustness
battery requires positive net OOS performance on a majority of folds and
satisfaction of the trade-count and exposure constraints.

## 9. Temporal validation protocol

Expanding-window walk-forward over 2020–2025 with **purging** and **embargo**
derived from the maximum label horizon / holding period (not chosen
arbitrarily). Data roles are strictly separated: **training** → **validation /
candidate selection** → **walk-forward OOS** → **frozen holdout**. Full details,
including the recommended fold geometry and its justification, are in
[`validation_protocol.md`](validation_protocol.md).

## 10. Transaction-cost assumptions

Provisional Binance USDT-M VIP-0 style model (must be confirmed via ADR before
final results): taker fee 0.040%/side, maker 0.020%/side, baseline slippage
1 bp/side on the next-bar open, funding paid/received on open positions using an
as-of-past alignment (no leakage). Robustness sweeps higher costs and slippage.
All backtests are **net of costs**; gross figures are reported only as context.

## 11. Evaluation and robustness

Primary and secondary metrics (net return, annualised volatility, Sharpe,
Sortino, max drawdown, Calmar, profit factor, hit rate, Expected Shortfall,
turnover, number of trades, exposure), broken down by asset, fold and
volatility regime, plus a robustness battery (higher costs, parameter
perturbation, delayed execution, subperiod stability, asset transfer,
regime-conditioned performance, trade-order bootstrap / Monte Carlo, deflated
Sharpe and benchmark comparison). See
[`validation_protocol.md`](validation_protocol.md).

## 12. Leakage-prevention rules (binding)

1. **Causality.** Every feature/decision input at time *t* uses information
   available at or before *t*. Rolling/expanding statistics only; no
   full-sample statistics feed models or parameters.
2. **Execution lag.** A signal computed on the close of bar *t* is executed at
   the **open of bar *t+1***, never at the close of *t*.
3. **Contemporaneous variables** (taker-buy imbalance, trade–mark basis) are
   **lagged ≥ 1 bar** before use and are never treated as contemporaneously
   predictive.
4. **Funding / mark price** are joined **as-of the past** with a declared
   direction and tolerance; never forward-filled into the future.
5. **Holdout isolation.** The `[2026-01-01, 2026-07-01)` block is not loaded in
   any development, selection or tuning code path. A guard raises if any
   observation with timestamp ≥ `2026-01-01` enters a development frame.
6. **Purge + embargo.** Training samples whose triple-barrier label horizon
   overlaps a validation/test window are purged; an embargo follows each test
   window before training resumes.
7. **Determinism.** A single global seed (42) seeds Python, NumPy and
   `PYTHONHASHSEED`; every stochastic component derives from it.

## 13. Open decisions

Recorded, not silently assumed (see also `progress.md`):

- Exact fee/slippage schedule (currently provisional) — pending ADR 0005.
- Final walk-forward fold geometry (recommended, pending confirmation).
- Position-sizing method (volatility-target vs. fixed-fraction) and vol target.
- Triple-barrier widths and horizon (provisional ATR multiples / 24-bar horizon).
- Whether GA operates per-asset or jointly across assets.
- Final meta-labeling model family and calibration method.
