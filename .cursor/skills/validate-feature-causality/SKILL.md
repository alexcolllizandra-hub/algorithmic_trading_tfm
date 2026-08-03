---
name: validate-feature-causality
description: Independently verify that features under src/perp_lab/features are causal and leakage-free. Use before promoting a feature or when reviewing a feature change in the perp-lab Chapter 5 phase.
disable-model-invocation: true
---

# Validate feature causality

Owner: **verifier** (read-only preference). Add targeted tests only if genuinely
missing; never silently change methodology.

## Purpose & triggers
Confirm, with executable evidence, that every implemented feature is causal.
Trigger: a feature was added/changed, or a review is requested.

## Required inputs
- The feature list and their catalogue metadata.
- The feature build entry point (`build_features`) and its parameters.

## Files it MAY modify
- `tests/unit/test_features_*.py` (only to add missing verification tests).

## Files it MUST NOT modify
- Any `src/perp_lab/**` production code; methodology docs; config.

## Prerequisites
- Feature is documented in `feature_catalogue.md` with Implemented status.

## Procedure
1. For each feature, build on full history and on truncated histories; assert the
   overlap matches exactly (including nulls).
2. Assert rolling features change only when past inputs change (perturb a future
   row; past values must be identical).
3. Assert lagged/contextual features equal the raw series shifted by the lag.
4. Assert warm-up nulls and zero-denominator nulls are deterministic; assert no
   infinities are produced.
5. Assert holdout rows cannot be loaded through the development path.
6. Run the quality gate and the focused feature tests.

## Mandatory invariants (verified, not assumed)
- Truncation invariance; past-only information; correct lag; deterministic
  warm-up/null; no infinities; alignment preserved; holdout inaccessible.

## Required tests
- The five/seven causality tests above must exist and pass.

## Generated artifacts
- A pass/fail report per invariant with file/line references.

## Stop conditions
- Any invariant fails: stop, report the exact failing case, do not "fix" the
  methodology.

## Completion report (exact)
- Per-invariant pass/fail with references; the exact commands executed and their
  outputs; any feature that could not be verified and why.
