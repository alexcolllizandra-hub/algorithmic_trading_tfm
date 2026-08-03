# ADR 0007: Configuration-driven causal feature engine and contract

- Status: Accepted
- Date: 2026-08-03
- Supersedes: the ad-hoc `build_features` / `feature_metadata` interface from ADR 0006

## Context

The first vertical slice (ADR 0006) shipped a small causal feature set through a
single `build_features(...)` function with a **parallel, hand-maintained**
`feature_metadata(...)`. That interface does not scale to the wider feature
catalogue needed for the baseline-strategy and walk-forward experiments: adding
a feature meant editing a builder and, separately, remembering to update the
metadata (drift risk), and the set was not selectable through configuration.

We need a feature engine that is configuration-driven, self-documenting,
reusable across assets (BTCUSDT and ETHUSDT 1h) without code duplication, and
whose resolved metadata flows into run artifacts — while preserving every
causality invariant and the momentum baseline's behaviour.

## Decision

1. **Explicit feature contract** (`features/spec.py`, standard-library only so
   the config can import it without a cycle): a `KIND_REGISTRY` of feature
   *kinds*, each described once by a `KindDef`, and a frozen, JSON-serialisable
   `FeatureSpec` that records the full contract — canonical name(s), family,
   input columns, asset/timeframe dependency, params and lookback, decision-time
   availability, mandatory shift, warm-up length, null policy, infinity policy,
   permitted consumers, leakage risk, output dtype and an `IMPL_VERSION`.
2. **Pure column builders** (`features/causal.py`): small, dependency-light
   Polars transforms (returns/momentum, SMA, price-distance-from-MA, price
   z-score, rolling volatility, ATR, normalised range, relative volume, volume
   z-score, cyclical hour/day-of-week, lagged taker-buy imbalance). Each returns
   a new frame; the input is never mutated.
3. **Engine** (`features/registry.py`): `resolve_feature_set` validates and
   de-duplicates a requested set (and injects the SMA windows the momentum
   baseline needs), and `build_feature_frame` checks input-column dependencies,
   applies the holdout guard, builds columns in a deterministic order and
   returns `(frame, resolved_specs)`. Metadata is **derived** from the resolved
   specs, eliminating drift.
4. **Configuration-driven selection**: `ExperimentConfig.features.feature_set`
   (mirrored in `configs/experiment.yaml`) lists the concrete features; each item
   is validated against the registry at load time (unknown kind, missing/extra
   window, invalid lag or unknown source → hard `ValidationError`), separate from
   the wider search-space window lists.
5. **Artifacts**: the resolved `FeatureSpec` contract is written to each run's
   `feature_metadata.json`; the pipeline logs generated column names, warm-up/
   null counts and an explicit infinity check before signals are produced.

## Consequences

- Adding or changing a feature is a single, contract-complete change; the run
  record and catalogue cannot silently drift from the implementation.
- The default set is a bounded **14 columns** covering returns/momentum, trend,
  volatility/range, volume and time, plus one contextual order-flow feature.
  `volume_zscore` and `dow` encodings are registered but off by default to avoid
  redundancy.
- BTCUSDT and ETHUSDT use the identical stateless engine; multi-asset
  independence and reproducibility are tested.
- The momentum baseline is unchanged: it still consumes `sma_{fast}`/`sma_{slow}`,
  which the engine guarantees are present.
- Out of scope (unchanged): breakout/mean-reversion strategies, walk-forward,
  purge/embargo execution, Random Search, the GA, triple-barrier labeling,
  meta-labeling, ML models, robustness and holdout evaluation. Cross-asset
  (BTC–ETH), funding, basis and causal regime features remain **Planned** and are
  documented, not approximated.
