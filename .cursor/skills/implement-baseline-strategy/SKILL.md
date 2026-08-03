---
name: implement-baseline-strategy
description: Add an interpretable baseline strategy under src/perp_lab/strategies that emits a target position from causal features. Use when implementing momentum, breakout or mean-reversion baselines in the perp-lab Chapter 5 phase.
disable-model-invocation: true
---

# Implement a baseline strategy

Owner agent: **strategy-backtest-engineer**. Do not edit features or config here.

## Purpose & triggers
Add an interpretable strategy that maps a causal feature frame to a target
position `side` ∈ {-1, 0, 1} decided at the close of bar *t*. Trigger: a request
for a new baseline family or parameterisation.

## Required inputs
- Entry/exit rules; permitted direction (long/short/both).
- Which catalogue features it consumes (must already be Implemented).
- Parameter ranges (from `configs/experiment.yaml → strategies`).

## Files it MAY modify
- `src/perp_lab/strategies/*.py`
- `tests/unit/test_strategies_*.py`

## Files it MUST NOT modify
- `src/perp_lab/features/`, `src/perp_lab/backtesting/`, config models, EDA.

## Prerequisites
- Consumed features exist and are causal (see validate-feature-causality).

## Procedure
1. Implement a frozen dataclass with validated parameters and a `name` property.
2. `signals(features) -> frame[open_time, side]`; warm-up / null inputs → flat.
3. Apply the direction constraint; keep the decision strictly at close *t*
   (execution delay belongs to the backtester, not the strategy).
4. Add tests; run the quality gate.

## Mandatory invariants
- Uses only feature columns available at close *t*; never shifts the future in.
- Deterministic given inputs; parameters validated (e.g. fast < slow).
- No holdout access; no backtesting/PnL logic inside the strategy.

## Required tests
- Correct sides vs the rule; direction clamping (long-only/short-only);
  warm-up → flat; invalid parameters rejected; missing feature columns raise.

## Generated artifacts
- Strategy class, tests.

## Stop conditions
- A consumed feature is not implemented/causal; parameter bounds are undefined.

## Completion report (exact)
- Strategy name, consumed features, exact entry/exit semantics, direction,
  parameter validation; files changed; tests and their results; quality-gate
  command outputs.
