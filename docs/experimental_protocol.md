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

## To be defined in later phases

- Walk-forward scheme, purging and embargo lengths.
- Strategy grammar and search space.
- Random-search vs. evolutionary-search budget parity.
- Backtesting cost model (fees, slippage, funding) and execution timing.
- Triple-barrier labeling and meta-labeling protocol.
- Candidate promotion gate and robustness / Monte Carlo tests.
