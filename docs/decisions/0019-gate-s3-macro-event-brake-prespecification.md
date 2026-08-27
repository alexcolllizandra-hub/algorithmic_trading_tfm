# ADR 0019 — Gate S3 batch 01 is pre-specified and frozen before any run

- **Status:** accepted
- **Date:** 2026-08-26

## Context

The alternative-data annex (`docs/thesis/anexo_altdata.md`) measured a large,
seasonality-controlled volatility elevation in scheduled US macro event hours
(CPI ×2.5-2.6, FOMC ×2.7-3.2, permutation p < 0.001) with no directional
drift. That is descriptive evidence; turning it into a tradable claim
requires a new registered hypothesis that pays its multiplicity cost, exactly
as ADR 0016 established for Gate S1.

Separately, a deep-learning volatility-forecasting annex is specified to test
the only kind of structure Chapter 5 found (variance predictability) with a
sequence model against the classical HAR benchmark.

## Decision

1. Register Gate S3 batch 01 with a single family, `macro_event_brake`
   (momentum carrier + calendar flat-gate), with the frozen hypothesis,
   parameter space and evaluation contract of
   `docs/methodology/strategy_catalogue_s3.md`. The contract is identical to
   R3/S1-C (2 assets × 10 seeds × 15 folds, effective budget 100, RS
   confirmatory). The event calendar input is the committed
   `configs/altdata/us_macro_events.csv`.
2. Freeze the volatility-forecasting annex design in
   `docs/methodology/volforecast_spec.md` (targets, folds, models, metrics
   and the decision rule) before any model is fitted. The annex produces no
   strategy and no promotion evidence.
3. Both documents are committed before the first pilot bar of either
   experiment is simulated; results, whatever they are, are reported against
   these frozen texts.

## Consequences

- The study's family trial count increases by one (S3); study-level
  corrections that include S3 use N := N + 1. The CLOSED_NEGATIVE verdict of
  the original 13-family study is unaffected — S3 is reported as its own
  gate, like S1 and S2.
- The honest prior, written in the spec, is no promotion: the carrier failed
  R2/R3, and the gate can only remove exposure. The informative comparison is
  the seed-distribution shift versus the ungated momentum baseline.
- The DL annex has a pre-declared decision rule, so "the LSTM looked better
  on one plot" cannot be claimed as a finding.
