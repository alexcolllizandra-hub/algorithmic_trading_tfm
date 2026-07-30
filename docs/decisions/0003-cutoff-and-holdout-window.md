# ADR 0003: Cutoff date and frozen holdout window

- Status: Accepted
- Date: 2026-07-30

## Context

The thesis needs a fixed, unambiguous data boundary and a final out-of-sample
period that is protected from any decision-making, so that reported
out-of-sample performance is credible and reproducible.

## Decision

- **Cutoff** = `2026-07-01`, interpreted as an **exclusive** upper bound. The
  ingested history therefore ends at the 5-minute bar opening
  **2026-06-30 23:55 UTC**.
- **Frozen holdout** = the fixed interval **`[2026-01-01 00:00 UTC, 2026-07-01)`**
  (the last six months before the cutoff). It is pinned with an explicit
  `holdout.start` (not a months-back approximation) so the boundary is exact.
- The holdout is hashed (per-partition manifest) and is **not** used for:
  EDA that drives design decisions, feature selection, strategy selection, or
  hyperparameter tuning. It is opened exactly once, for the final results.
- Everything strictly before `2026-01-01 00:00 UTC` is the development set,
  which later phases further partition chronologically (walk-forward).

## Consequences

- A single, deterministic boundary shared by data, EDA and modelling code.
- Six months (~half a year, 24/7) of untouched data for a final, honest
  out-of-sample evaluation across at least one regime shift.
- If the cutoff changes later, this ADR is superseded and the data-contract
  `version` is bumped; the holdout must be re-frozen accordingly.
