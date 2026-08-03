---
name: implement-causal-feature
description: Add a new causal feature to src/perp_lab/features with full metadata, a leakage-invariance test and a feature-catalogue entry. Use when introducing or changing any feature consumed by strategies, regimes or meta-labeling in the perp-lab Chapter 5 phase.
disable-model-invocation: true
---

# Implement a causal feature

Owner agent: **feature-engineer**. One owner per module; do not edit strategies,
backtesting or config models here.

## Purpose & triggers
Add/modify a feature returning a Polars frame that is provably causal and fully
documented. Trigger: a request to add a feature, adjust a window, or fix a
leakage risk.

## Required inputs (must be stated before coding)
- Mathematical / algorithmic definition.
- Input columns and the timeframe.
- Lookback (in bars).
- Availability timestamp (when the input is first known).
- Required shift (≥ 1 bar for anything used at decision time).
- Warm-up behaviour and null policy; infinity policy (zero denominators → null).
- Permitted consumers (BS/GA/ML/RG/RK) and leakage risk.

## Files it MAY modify
- `src/perp_lab/features/*.py`
- `tests/unit/test_features_*.py`
- `docs/methodology/feature_catalogue.md`

## Files it MUST NOT modify
- `src/perp_lab/strategies/`, `src/perp_lab/backtesting/`,
  `src/perp_lab/config/`, `src/perp_lab/tracking/`, any EDA/notebook output.

## Prerequisites
- The feature appears (or is added) in `feature_catalogue.md` with all metadata.
- `configs/experiment.yaml` provides the window(s); do not hard-code magic values.

## Procedure
1. Add a small, pure function computing the feature with rolling/expanding logic
   (`min_samples == window`, no centring, `shift` where required).
2. Wire it into `build_features` (or the relevant builder) with a documented lag.
3. Add the catalogue row and mark status **Implemented**.
4. Add the required tests (below); run the quality gate.

## Mandatory invariants
- Future rows cannot change past feature values.
- Only past/available information enters each value.
- Contextual variables are lagged; zero denominators → null (no infinities).
- Regime thresholds are rolling/expanding, never full-sample.
- Timestamp, index and symbol alignment are preserved.

## Required tests
- Truncation invariance (full vs truncated history match up to the cut).
- Warm-up nulls deterministic; lag correctness; no infinities; alignment kept.

## Generated artifacts
- Updated feature function, tests and catalogue row.

## Stop conditions
- Availability or shift is ambiguous; the feature would need holdout data; the
  window is unspecified. Stop and report instead of guessing.

## Completion report (exact)
- Feature name, formula, inputs, lookback, availability, shift, null/inf policy,
  consumers, leakage risk; files changed; tests added and their results; the
  exact quality-gate command outputs.
