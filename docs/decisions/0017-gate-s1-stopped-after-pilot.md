# ADR 0017 — Gate S1 stops after the pilot, inconclusive

- **Status:** accepted
- **Date:** 2026-08-11
- **Affects:** Gate S1 batch 01, Gate S1-C scope, Gate M1 scope, Gate R4 status
- **Depends on:** ADR 0016 (S1 batch 01 pre-specification), ADR 0015 (R3 closed negative), ADR 0012 (per-fold isolation)

## Context

Gate S1 batch 01 pre-specified four families and a three-stage protocol: S1-A
(implementation and registration), S1-B (development pilot at reduced budget) and
S1-C (full study at budget 100, ten seeds, both assets). S1-A and S1-B are
complete. S1-C has not been run.

This ADR records a **human decision to stop spending search budget**, not a
scientific verdict. It is written after S1-B and changes nothing in the frozen
pre-specification ([gate_s1_batch_01.md](../roadmap/gate_s1_batch_01.md)), which
remains exactly as frozen on 2026-08-11.

## Evidence

**S1-A — complete.** Four families implemented, registered and unit-tested:
`mtf_trend_consensus`, `funding_reversal`, `xasset_spread_reversion`,
`intraday_seasonality`. See ADR 0016.

**S1-B — complete.** Four pilot runs on the **development partition only**,
BTCUSDT, 15 chronological outer folds, one seed, 25 unique objective evaluations
per fold and engine. Report:
[`reports/gate_s1b/s1b_pilot_report.md`](../../reports/gate_s1b/s1b_pilot_report.md)
and the machine-readable `s1b_pilot_report.json`, which records
`holdout_accessed: false`.

All four families are **mechanically viable**: every one produced valid
candidates, traded, and recorded no invariant failure. Under section 3 of the
frozen contract that is the *only* verdict S1-B is entitled to reach, and it
sends all four to S1-C.

Development-period description on the confirmatory engine (Random Search).
These are descriptive numbers at one seed, one asset and a quarter of the S1-C
budget; they evaluate none of the promotion criteria C1–C6.

| Family | Compounded OOS return | Median fold return | Median OOS Sharpe | Median DSR | Folds with DSR > 0.95 | Bootstrap p |
|---|---:|---:|---:|---:|---:|---:|
| `funding_reversal` | −38.33% | +0.21% | 0.17 | 0.576 | 0/15 | 0.7455 |
| `intraday_seasonality` | −42.02% | −2.96% | −1.22 | 0.091 | 0/15 | 0.9195 |
| `mtf_trend_consensus` | −67.83% | −6.84% | −0.94 | 0.411 | 0/15 | 0.8375 |
| `xasset_spread_reversion` | −83.98% | −8.07% | −1.12 | 0.258 | 0/15 | 0.9910 |

The compounded and median-fold columns disagree in sign for
`funding_reversal`: the median fold is marginally positive while the stitched
out-of-sample ledger compounds to −38%. A minority of severe folds dominates the
aggregate. The compounded figure is the one that matches criterion C1.

Selection accounting across the four families: Benjamini–Hochberg at α = 0.05
rejects nothing; Hansen's SPA gives p = 1.0000 and White's Reality Check
p = 0.9955 against a flat benchmark over 32 385 aligned out-of-sample bars. PBO
(CSCV) is **not computable** from these artifacts, because ADR 0012 makes the
search independent per outer fold and CSCV needs one common configuration set
evaluated across all blocks.

**The partial-signal trigger did not fire.** The pre-registered condition for
attaching a meta-label comparison was at least one family showing criterion C1 —
positive total net out-of-sample return — on the confirmatory engine. All four
compounded returns are negative, so no family met it.

## Decision

1. **Gate S1 status is `S1_STOPPED_AFTER_PILOT_INCONCLUSIVE`.** S1-A and S1-B
   completed; S1-C is not run.
2. **S1-C is not executed, for resource allocation.** The frozen contract sends
   all four viable families to a full study of 10 seeds × 2 assets × 2 engines ×
   15 folds × 100 evaluations. Spending that on four families whose pilots all
   lost money is a cost judgement, and the contract contains no early-stopping
   rule that could make it a scientific one. The prepared configurations
   `configs/search_s1c_<family>.yaml` are retained, unexecuted.
3. **This is not a confirmatory rejection.** The four families are **not**
   `REJECTED` and Gate S1 is **not** `CLOSED_NEGATIVE`. Section 4 of the frozen
   contract defines `CLOSED_NEGATIVE` as the outcome of the S1-C promotion
   evaluation; a verdict from one seed, one asset and a quarter of the budget is
   not that evaluation. Their status is `PILOTED`, and the honest statement is
   that S1 was stopped before the evidence needed to reject them was collected.
4. **Meta-labeling is not applied to any S1 family.** The trigger did not fire.
   A meta-label filters a primary signal; it cannot create one. The machinery
   (`src/perp_lab/labeling/`, `src/perp_lab/meta_labeling/`) stays implemented
   and unit-tested, unused on S1.
5. **The holdout stays closed.** `[2026-01-01, 2026-07-01)` has never been read.
   No S1 candidate was promoted, so nothing is eligible to open it.
6. **Gate R4 remains `SKIPPED`**, unchanged from ADR 0015.
7. **All S1-B artifacts, reports and S1-C configurations are retained.** Negative
   and abandoned outcomes are provenance, not waste.
8. **The frozen pre-specification is not edited.** Reopening these four families
   would require a new, separately numbered batch, and it could not reuse this
   pilot's evidence to justify a narrower search space.

## Consequences

Four mechanism-driven families were specified in advance, implemented, screened
for mechanical viability and abandoned before the confirmatory study. The thesis
may report that S1 produced no promotable family; it may **not** report that the
four mechanisms were tested and found absent. The distinction is the difference
between a stopped experiment and a negative result.

The search budget released here funds Gate S2, whose families must be justified
by external evidence and by data the project does not yet exploit, rather than by
further recombination of price, mark price and funding.
