# Hypothesis Traceability Matrix (Chapter 5) — v0.1

Each hypothesis links a research question to the methods compared, the data and
validation protocol used, the metrics that decide it, the robustness evidence
required, and an explicit accept/reject rule. **No hypothesis is decided on
in-sample performance.** Implementation status is one of: *Implemented &
verified · Implemented, not verified · Partially implemented · Planned (missing)*.

All primary evidence comes from **walk-forward out-of-sample (OOS)** folds on
the development period; the frozen holdout `[2026-01-01, 2026-07-01)` is used
only once for the final confirmation and never to accept/reject during
development.

## Compact matrix

| ID | Research question | Hypothesis (H0 → H1) | Methods compared | Input data | Validation | Primary metric | Secondary metrics | Robustness checks | Evidence required | Accept/Reject rule | Status |
|----|-------------------|----------------------|------------------|-----------|-----------|----------------|-------------------|-------------------|-------------------|--------------------|--------|
| H1 | RQ1 profitability after costs | H0: net OOS Sharpe ≤ benchmark. H1: ≥1 interpretable family beats benchmark net of costs | Momentum / Breakout / Mean-reversion vs. buy&hold, flat cash, random-entry | 1h BTC/ETH causal features (strategy set A) | Expanding walk-forward, purge+embargo | Net-of-cost OOS Sharpe | Sortino, MaxDD, Calmar, profit factor, hit rate, ES, turnover, #trades | Higher costs, param jitter, delayed fill, per-year, deflated Sharpe | Positive net OOS on majority of folds; deflated Sharpe > 0; > benchmark | Reject H0 only if all met; else inconclusive/reject | Planned (missing) |
| H2 | RQ2 search method | H0: GA ≤ RS at equal budget. H1: GA > RS | Genetic Algorithm vs. Random Search (identical space/budget/folds/costs/seeds) | Same as H1; shared strategy space | Same walk-forward; multiple seeds | Median net OOS fitness of best candidates | Sharpe, MaxDD, turnover, convergence vs. budget | Repeat over seeds; budget sensitivity; per-asset | GA median > RS median, stable across seeds and folds | Reject H0 if GA advantage consistent and not seed-artifact | Planned (missing) |
| H3 | RQ3 meta-labeling | H0: meta-labeling does not improve base signals. H1: it improves risk-adjusted performance | Base signal vs. base + meta-label (LogReg / RF / LightGBM) | Base signals + contextual meta features (set B, lagged) | Walk-forward; calibration + threshold on validation only | Net OOS Sharpe uplift vs. base | MaxDD reduction, precision/recall, calibration, #trades retained | Threshold sensitivity, model family swap, per-regime | Uplift on majority of folds without trade count < minimum | Reject H0 if uplift consistent and calibrated | Planned (missing) |
| H4 | RQ4 regime dependence | H0: performance equal across vol regimes. H1: it differs | Same strategies, partitioned by causal volatility regime | 1h features + causal vol-regime tag | Walk-forward OOS grouped by regime | Net OOS Sharpe by regime | Return, MaxDD, hit rate, exposure per regime | Threshold sensitivity of regime cut; per-asset | Economically meaningful and consistent regime gap | Reject H0 if regime differences stable across folds/assets | Planned (missing) |
| H5 | RQ5 robustness | H0: performance is fragile. H1: it survives perturbations | Promoted strategies under stress vs. baseline evaluation | Promoted candidates + cost/param/exec perturbations | Walk-forward + robustness battery | Sign & magnitude retention of net OOS Sharpe | Distribution of bootstrapped Sharpe, drawdown tails | Trade-order bootstrap/MC, subperiod, asset transfer | Positive net OOS retained under all core stress scenarios | Reject H0 if performance persists; else fragile | Planned (missing) |

## Per-hypothesis detail

### H1 — Interpretable strategies remain profitable after costs
- **Benchmarks:** buy-and-hold, flat cash, random-entry matched-exposure.
- **Evidence required:** net-of-cost OOS Sharpe with a positive lower bound
  above the best naive benchmark on a majority of folds, and a **deflated
  Sharpe ratio > 0** to account for selection over the search space.
- **Accept/Reject:** reject H0 only if the fold-majority and deflated-Sharpe
  conditions both hold; otherwise report as inconclusive or reject. In-sample
  fitness is never sufficient.

### H2 — GA outperforms Random Search at equal budget
- **Fairness constraints:** identical strategy space, feature set, folds,
  cost model, evaluation budget and seed policy (only the search operator
  differs).
- **Evidence required:** GA's median best-candidate net OOS fitness exceeds
  RS's across repeated seeds, with the advantage stable across folds and
  robust to the evaluation budget.
- **Accept/Reject:** reject H0 only if the GA advantage is consistent and not
  attributable to a single lucky seed.

### H3 — Meta-labeling improves risk-adjusted base performance
- **Constraint:** meta-labeling may only suppress or size base trades; it never
  invents new directional signals. It must not reduce the trade count below the
  configured minimum.
- **Evidence required:** net OOS Sharpe uplift and/or drawdown reduction on a
  majority of folds, with calibrated probabilities (reliability check).
- **Accept/Reject:** reject H0 if the uplift is consistent, calibrated and not
  driven by trade starvation.

### H4 — Performance changes across volatility regimes
- **Regime definition:** causal (past-only) volatility-regime tag; the
  descriptive EDA regime terciles are *not* used for decisions.
- **Evidence required:** economically meaningful and fold-stable differences in
  net OOS metrics across low/medium/high regimes.
- **Accept/Reject:** reject H0 if regime differences are stable across folds and
  assets; sensitivity to the regime threshold is reported.

### H5 — Performance is stable under perturbations
- **Battery:** higher fees/slippage, ±5/10/20% parameter jitter, delayed
  execution (1–2 bars), per-year subperiods, asset transfer, regime-conditioned
  performance, trade-order bootstrap / Monte Carlo, deflated/probabilistic
  Sharpe, benchmark comparison.
- **Evidence required:** the sign and a meaningful fraction of the magnitude of
  net OOS Sharpe are retained under all core stress scenarios.
- **Accept/Reject:** reject H0 (fragility) if performance persists across the
  battery; otherwise classify the strategy as fragile.
