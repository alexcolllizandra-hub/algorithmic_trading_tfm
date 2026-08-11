# ADR 0016 — Gate S1 batch 01 is pre-specified and frozen before any run

- **Status:** accepted
- **Date:** 2026-08-11
- **Affects:** Gate S1, strategy registry, experiment configuration, evaluation
- **Depends on:** ADR 0012 (per-fold isolation), ADR 0013 (momentum rejected),
  ADR 0015 (Gate R3 closed negative)

## Context

Gate R3 closed `CLOSED_NEGATIVE` with 0/5 promotions and Gate R4 was correctly
`SKIPPED`, because R4 is confirmatory on promoted families and there were none.
The development partition has therefore already been consulted once by a full
five-family, ten-seed, hundred-evaluation study. Any further search on the same
data increases the selection burden on every conclusion drawn from it.

Two failure modes are available at this point and both would invalidate the
thesis:

1. **Retrospective rescue** — re-tuning, renaming or re-parameterising a family
   that R3 rejected until it passes.
2. **Unbounded exploration** — adding families opportunistically, one at a time,
   until something clears the criteria, without ever recording how many
   hypotheses were tried.

The repository also needed the machinery to *quantify* the second problem: until
now it had bootstrap confidence intervals but no selection-bias correction.

## Decision

**1. A new phase, S1, opens as a numbered batch with a frozen contract.**
Batch 01 contains exactly four families, pre-specified in
[`strategy_catalogue_s1.md`](../methodology/strategy_catalogue_s1.md) and
[`gate_s1_batch_01.md`](../roadmap/gate_s1_batch_01.md) before any S1 result
existed: `mtf_trend_consensus`, `funding_reversal`, `xasset_spread_reversion`
and `intraday_seasonality`.

**2. R3-closed families are not re-searched.** `momentum`, `breakout`,
`mean_reversion`, `volatility_breakout`, `funding` and `BTC_ETH_confirmation`
remain in the registry as `R3_CLOSED_FAMILIES` solely so historical runs stay
reproducible. Two S1 families share an *input* with a rejected family; the
catalogue states, for each, the material economic and operational difference
that makes it a new hypothesis rather than a rename.

**3. Gate R4 is not reopened.** Its `SKIPPED` status stands. R4 is confirmatory
on promoted families only; running it now, against families that were never
promoted, would be exactly the retrospective rescue the protocol forbids.

**4. The hypothesis count is recorded before results are seen.** The batch
document states each family's space cardinality as an upper bound on degrees of
freedom, and fixes that the deflated Sharpe ratio uses the *recorded count of
unique valid objective evaluations*, not the budget and not the cardinality. A
batch attempt counter is reported with every S1 result, so the number of times
the development partition has been consulted is never lost.

**5. Promotion criteria are R3's, plus two additions, frozen in advance.** The
six criteria and the separate `min_oos_trades_met` veto are reused unchanged so
S1 and R3 results are comparable. Added: a deflated-Sharpe threshold with PBO and
Benjamini–Hochberg control across families, and a fold-stability requirement on
`intraday_seasonality`'s selected hour.

**6. Selection-bias corrections become library code, not a spreadsheet.**
`src/perp_lab/evaluation/multiple_testing.py` implements the expected maximum
Sharpe ratio of a null search, the deflated Sharpe ratio, the CSCV probability of
backtest overfitting, and Benjamini–Hochberg. White's Reality Check and Hansen's
SPA are named in the catalogue as **not yet implemented**.

## Consequences

- S1 cannot silently become "R3 with more attempts": the batch, its size, its
  criteria and its attempt number are all on record before the first run.
- A negative S1 result is publishable as-is, exactly as R3's was.
- The selection-bias correction applies to S1 and is available retrospectively as
  a *descriptive* statistic for R3; it does not alter R3's recorded verdict.
- The four new families enlarge the search registry from 6 to 10 entries and the
  space version moves to `1.1.0`. Historical R3 runs pin space version `1.0.0`
  and are unaffected.
- S1-A (technical validity) is complete. S1-B and S1-C have **not** been run: no
  S1 pilot configuration exists yet, so there are no S1 performance results of
  any kind.

## Evidence

- Implementation: `src/perp_lab/strategies/mtf_trend_consensus.py`,
  `funding_reversal.py`, `intraday_seasonality.py`,
  `xasset_spread_reversion.py`, `timed_exit.py`;
  `src/perp_lab/evaluation/multiple_testing.py`;
  `src/perp_lab/config/experiment.py`; `src/perp_lab/search/registry.py`.
- Tests: `tests/unit/test_strategies_s1.py`,
  `tests/unit/test_search_registry_s1.py`,
  `tests/unit/test_multiple_testing.py`.
- Quality gate on this change: `uv run ruff check .` passed,
  `uv run ruff format --check .` reported 300 files already formatted,
  `uv run pyright` reported 0 errors, and `uv run pytest -m "not network"`
  passed the full offline suite.
- Holdout: not read. No experiment, search or backtest was executed for this ADR.
