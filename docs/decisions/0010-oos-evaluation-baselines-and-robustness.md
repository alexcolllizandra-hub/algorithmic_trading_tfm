# ADR 0010: Out-of-sample evaluation layer — baselines, robustness and feature packs

- Status: Accepted
- Date: 2026-08-05
- Builds on: ADR 0005 (provisional transaction costs), ADR 0008 (experimental
  foundation), ADR 0009 (Random Search / Genetic Algorithm search framework)

## Context

The search framework (ADR 0009) produces a per-fold winner and its concatenated
out-of-sample development evidence. Until now the pipeline reported that evidence
as a small set of point estimates (total return, Sharpe, max drawdown) with
nothing to compare them against and no measure of how fragile they are.

Three gaps made those numbers impossible to defend:

1. **No reference point.** A concatenated out-of-sample return of +36% over 3.7
   years means nothing without knowing what holding the asset would have returned
   over exactly the same bars.
2. **No uncertainty.** A single Sharpe estimate over one walk-forward pass does
   not say whether the effect is distinguishable from zero.
3. **No sensitivity to the cost assumption.** Fees and slippage are provisional
   (ADR 0005). If the conclusion flips when they are doubled, the conclusion is
   about the assumption, not about the strategy.

Separately, the feature registry had grown to 25 causal kinds with no mechanism
to stop a search from drawing on all of them at once, and no machine-readable
distinction between an observed quantity and an approximation of one.

## Decision

1. **Persist the market return in the ledger.** The backtester now writes
   `oo_return` (the market return of each holding interval) as a first-class
   ledger column. It cannot be recovered from execution prices after the fact,
   because the ledger drops each fold's final bar and cross-fold price ratios are
   meaningless. Persisting it makes every downstream re-pricing exact rather than
   approximate.

2. **Baselines are evaluated on the strategy's own bars.** `evaluation/baselines.py`
   re-evaluates the fixed baseline suite directly from the concatenated
   out-of-sample ledger, so baselines see identical bars, identical funding,
   identical next-bar execution and the run's *realised* cost rate. This removes
   any possibility of an accidental advantage from a different data window or a
   cheaper cost assumption, and it means the comparison needs no access to market
   data — closing one more path to the frozen holdout.

3. **Baseline parameters are frozen in code.** `strategies/baselines.py` fixes
   flat, always-long, a 24/96 moving-average crossover, 24-bar momentum, a 48-bar
   z-score fade and a seeded random-entry control. None of them is tuned on
   validation, and none is selected by looking at test. A tuned baseline is not a
   baseline.

4. **Uncertainty is reported as a block-bootstrap interval.** `evaluation/robustness.py`
   resamples contiguous blocks circularly, preserving the serial dependence that
   an i.i.d. bootstrap would destroy and that would otherwise make the interval far
   too narrow. Intervals are reported at several block sizes (one day, one week,
   one month of hourly bars) so the reader can see the sensitivity to that choice
   instead of trusting a single value.

5. **Provisional assumptions are stressed, not asserted.** The battery re-prices
   the same positions at 1x / 1.5x / 2x fees-and-slippage, at 2x / 5x slippage
   alone, and under one- and two-bar execution delays. Because fees and slippage
   are proportional to turnover and to their bps rate, scaling the persisted
   per-bar amounts is exactly equivalent to re-running the backtest with scaled
   rates; the identity at 1x is asserted by test.

6. **Feature packs bound the search space.** Every registered kind declares a pack
   (`core` < `extended` < `experimental`, cumulative). A run declares the packs it
   may use; kinds outside them are unavailable rather than merely unused. This is
   an overfitting control: a search over every registered kind would almost
   certainly find *some* parameterisation that looks good by chance.

7. **Proxies are labelled in the registry, not in prose.** Kinds that approximate
   an unobserved quantity carry `is_proxy` and a `proxy_note` explaining what they
   actually measure, and these flags propagate into run artifacts. In particular
   `basis` is the mark-versus-index deviation, not a spot basis (no independent
   spot price is ingested), and the taker-buy features are aggressor-flow proxies
   derived from aggregated trades, not order-book imbalance.

8. **Metrics have one implementation.** VaR, expected shortfall, skewness, excess
   kurtosis, time in drawdown, drawdown duration, Ulcer index, streaks, profit
   factor, expectancy and payoff ratio live in `backtesting/metrics.py` next to the
   existing metrics rather than in a parallel evaluation module.

## Consequences

- Ledgers written before this change lack `oo_return`; the robustness battery
  rejects them with an explicit message instead of silently approximating. Older
  runs must be re-executed to be analysed.
- The evaluation layer is strictly read-only with respect to the search: it never
  re-selects a candidate and never re-runs a fold, so it cannot leak test
  information back into selection.
- The first development results obtained under this layer are negative or
  inconclusive (see the run artifacts). That is a valid outcome and is recorded as
  such; it is not a reason to weaken the battery.
