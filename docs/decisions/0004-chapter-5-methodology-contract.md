# ADR 0004: Chapter 5 methodology and experimental contract

- Status: Accepted
- Date: 2026-08-03

## Context

Before implementing the modelling pipeline (features, strategies, labeling,
backtesting, search, meta-labeling, evaluation) the thesis needs a fixed,
auditable methodological contract so that later implementation cannot silently
change the research design, the validation protocol, or the leakage rules.

## Decision

We adopt the Chapter 5 contract defined by:

- [`configs/experiment.yaml`](../../configs/experiment.yaml) — the machine-
  readable experiment configuration (scope, periods, feature windows, strategy
  space, labeling, walk-forward, costs, search budgets, fitness, robustness,
  risk).
- `docs/methodology/experimental_design.md` — research questions, hypotheses,
  units, protocols and binding leakage-prevention rules.
- `docs/methodology/hypothesis_matrix.md` — traceability of hypotheses to
  methods, metrics and accept/reject rules.
- `docs/methodology/feature_catalogue.md` — the causal feature catalogue.
- `docs/methodology/strategy_specification.md` — baseline families, the
  fixed-length GA chromosome and the Random-Search/GA parity contract.
- `docs/methodology/validation_protocol.md` — walk-forward geometry, purge/
  embargo derivation, cost model, metrics and robustness battery.
- `docs/architecture.md` and `docs/methodology/module_specification.md` — the
  intended module structure and public APIs.

Key fixed decisions: expanding walk-forward with purge/embargo **derived** from
the maximum label horizon / holding period; net-of-cost, next-bar execution;
Random Search and GA constrained to identical space/budget/folds/costs/seeds;
meta-labeling may only suppress/size base trades; the frozen holdout is opened
exactly once at the end. Hypotheses are never accepted on in-sample results.

## Consequences

- Implementation proceeds against a stable contract; deviations require a new
  ADR and a `version` bump of `experiment.yaml`.
- Several values remain **provisional** (costs, exact fold geometry, sizing,
  barrier widths); these are flagged in the config and tracked as open
  decisions in `docs/progress.md`. Provisional transaction costs are recorded
  separately in ADR 0005.
- No modelling code is created by this decision; only the specification.
