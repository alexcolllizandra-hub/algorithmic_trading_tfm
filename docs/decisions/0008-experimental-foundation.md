# ADR 0008: Experimental foundation — regimes, strategy family, funding-aware backtester and walk-forward

- Status: Accepted
- Date: 2026-08-04
- Builds on: ADR 0006 (vertical slice + run tracking) and ADR 0007 (config-driven
  causal feature engine)

## Context

ADR 0007 delivered a configuration-driven causal feature engine and a single
momentum baseline executed through a minimal next-bar backtester. To reach the
point where Random Search and the Genetic Algorithm can be built on a fair,
leakage-free substrate, the experimental *foundation* still needed:

1. a broader causal feature catalogue (cross-asset and derivatives families);
2. fold-fit transformations and market-regime models that learn parameters on
   training data only;
3. a common interpretable strategy interface with more than one family;
4. a realistic, funding-aware backtester with a rich per-bar ledger;
5. an expanding walk-forward partitioner with config-derived purge/embargo.

The Genetic Algorithm, triple-barrier labeling, meta-labeling, robustness
battery, dashboard and paper trading are explicitly **out of scope** for this
ADR and remain planned.

## Decision

1. **Extended causal features.** `features/causal.py` gains `ema`, `cum_return`,
   `roll_std`, `ma_distance` (fast/slow), `true_range` and a lagged
   `taker_buy_ratio`; a new `features/context.py` adds context-dependent kinds —
   `xasset_rel_return`, `xasset_rel_momentum`, `xasset_corr` (backward-aligned
   BTC–ETH), `funding_rate`, `basis` and `oi_change` — each requiring an explicit
   `FeatureContext` (peer / funding / mark / index / open-interest frames) joined
   only with backward as-of logic. Multi-parameter kinds are supported through a
   new `window_slow` config field. Open interest is reported **unavailable**
   rather than fabricated when its input frame is absent.
2. **Machine-readable manifest + predictor rows.** `features/manifest.py` emits a
   JSON manifest (name, family, inputs, formula, params/lookback, warm-up,
   availability, missing-data rule) derived from the resolved specs.
   `features/predictors.py` builds meta-labeling predictor rows with four
   **separated timestamp roles** — feature / signal / execution / (future) label
   time — the label column intentionally left null in this phase.
3. **Fold-fit transforms + regimes.** `regimes/transforms.py` (`StandardScaler`,
   `QuantileClipper`) and `regimes/models.py` (`ThresholdRegime`, `KMeansRegime`,
   `GMMRegime`) all `fit` on training data only and `transform` validation/test
   unchanged. Cluster regimes are canonically ordered low→high volatility for a
   stable economic interpretation; missing inputs map to an explicit
   `UNKNOWN_LABEL`. `scikit-learn` is added as a runtime dependency.
4. **Common strategy interface + family.** The `Strategy` protocol now requires
   `params()` and `required_features()`. `strategies/filters.py` provides shared
   causal regime/trend gates. `MomentumCrossover` is adapted (optional trend +
   regime gates) and two families are added: `Breakout` (channels built only from
   *previous* highs/lows, confirmation bars) and `MeanReversion` (price z-score
   entry/exit, `exit_z < entry_z`). A shared O(n) `evolve_positions` state machine
   handles entries, exits and direct reversals for stateful strategies.
5. **Funding-aware backtester.** `run_backtest` keeps next-bar execution
   (`position = target.shift(1)`, open-to-open return) and now records a rich
   ledger: raw signal, target/executed position, execution price, gross return,
   separate fee and slippage, funding, net return, equity, drawdown, `trade_id`
   and `exit_reason`. Turnover is `|Δposition|` (a +1→−1 reversal = 2 units);
   funding is aligned to bars by backward search on its own timestamps and signed
   by the active position. A `funding_applied` flag records whether funding data
   was actually supplied; `require_funding=True` raises rather than silently
   substituting zero.
6. **Expanding walk-forward.** `validation/walk_forward.py` cuts the development
   period into anchored (expanding) folds. Purge/embargo are **derived from the
   config**: `purge_bars = max(label_horizon, max_holding)` removed from the end
   of validation; `embargo_bars = purge_bars + ceil(fraction_of_test·test_bars)`
   removed from the end of training. Bar counts are converted to durations with
   the primary-timeframe step. `assert_folds_exclude_holdout` guarantees no fold
   ever reaches the frozen holdout.
7. **Pipeline + artifacts.** The development pipeline generates the folds and the
   feature manifest and writes them alongside the resolved config, strategy
   parameters and the existing run contract.

## Consequences

- The experimental substrate is now complete enough to build Random Search on:
  features, regimes, three interpretable strategy families, a funding-aware
  ledger and leakage-controlled temporal folds are all implemented and tested.
- Causality is preserved end to end: every new feature is trailing-only or
  explicitly lagged, context joins are backward-only, transforms/regimes fit on
  training data only, and folds are purged/embargoed from the central config.
- Costs remain **provisional** (ADR 0005). Funding is *supported and tested* but
  only applied when a funding frame is supplied; real development-data funding
  wiring is deferred.
- Out of scope / unchanged: Genetic Algorithm, triple-barrier labeling,
  meta-labeling models, robustness battery, dashboard and paper trading. The
  frozen holdout is never accessed.
