# Experimental Protocol v0.1 (Phase 1 stub)

This document will grow with the project. In Phase 1 it fixes only the
research-integrity invariants that later phases must respect. Modelling,
search, backtesting and evaluation protocols are defined in later phases (see
[roadmap.md](roadmap.md)).

## Invariants fixed now

1. **Chronological partitioning only.** No random train/test/validation splits
   at any stage. Time order is always preserved.
2. **Frozen final holdout.** The interval `[2026-01-01 00:00 UTC, 2026-07-01)`
   (the last 6 months before the cutoff) is set aside, hashed, and never used to
   make EDA-driven decisions, tune parameters, or select strategies. It is
   opened once, at the very end, for the final report. See ADR 0003.
3. **No leakage in transformations.** Any statistic used as a feature or a
   decision input must be computed from past data only (rolling / expanding,
   not full-sample). Full-sample statistics are allowed **only** for descriptive
   EDA that does not feed model or parameter choices, and must be labeled as such.
4. **Determinism.** A single global seed (`AppSettings.seed`) seeds Python,
   NumPy and `PYTHONHASHSEED`. Every stochastic component seeds from it.
5. **Provenance.** Every dataset consumed by an experiment is identified by its
   manifest (id + SHA-256), so results are traceable to exact inputs.

## Chapter 5 methodology (now specified)

The items below are specified in the Chapter 5 methodology contract (ADR 0004),
which operationalises them without yet implementing the code:

- Walk-forward scheme, purging and embargo lengths →
  [`methodology/validation_protocol.md`](methodology/validation_protocol.md).
- Strategy grammar and search space →
  [`methodology/strategy_specification.md`](methodology/strategy_specification.md).
- Random-search vs. evolutionary-search budget parity → same document.
- Backtesting cost model (fees, slippage, funding) and execution timing →
  validation protocol + ADR 0005 (provisional costs).
- Triple-barrier labeling and meta-labeling protocol →
  [`methodology/experimental_design.md`](methodology/experimental_design.md).
- Candidate promotion gate and robustness / Monte Carlo tests → validation
  protocol.
- Causal feature catalogue →
  [`methodology/feature_catalogue.md`](methodology/feature_catalogue.md).
- Machine-readable configuration →
  [`../configs/experiment.yaml`](../configs/experiment.yaml).

These remain a **specification**; values flagged *provisional* must be confirmed
via ADR before they influence any reported result.
