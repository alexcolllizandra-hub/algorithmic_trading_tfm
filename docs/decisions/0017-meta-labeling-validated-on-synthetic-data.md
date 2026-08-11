# ADR 0017 — The meta-labeling layer is validated on synthetic data, not on a candidate

- **Status:** accepted
- **Date:** 2026-08-11
- **Affects:** `labeling/`, `meta_labeling/`, `reporting/meta_labeling_synthetic.py`
- **Depends on:** ADR 0015 (Gate R3 closed negative), ADR 0016 (Gate S1
  pre-specification)

## Context

The meta-labeling layer (M1/M2) was specified long before anything could use it.
Its contract is that an interpretable primary rule supplies the *direction* and a
classifier decides only *whether to act*. That contract presupposes an eligible
primary strategy, and there is none: Gate R3 closed with zero promotions, no S1
family passed its gate, and the S2 development pilots produced no family that
fired the pre-specified partial-signal criterion.

Two options were available. Leave the layer unexercised until a primary appears —
in which case its first use would be on a real candidate, with no way to tell an
implementation fault from a market result. Or exercise it where the answer is
already known. The frozen methodology contract permits the second explicitly: if
no primary is eligible, the machinery may be built and validated on synthetic
data or a clearly-labelled exploratory contract, provided **no operational
candidate is claimed**.

A validation of this kind has one obvious failure mode: generating a market with
an edge, showing the layer finds it, and calling that a success. Any pipeline —
including a leaking one — passes that test. The validation is only informative if
it also runs a market with no edge at all and shows the layer comes back
empty-handed.

## Decision

**1. The layer is validated on two paired synthetic markets, never on one.**
`meta_labeling/synthetic.py` generates a *signal* market, where a persistent
hidden state decides whether the bars after a signal drift with or against it,
and a *noise* control built from the geometric Brownian motion in
`stochastic/processes.py`, where increments are independent and no filter can add
value. Both markets share the same primary rule, the same feature construction
and the same hidden state; only the price process differs. A result on one
without the other is not reported.

**2. Labels are cut on net returns, and the fill convention is explicit.**
`LabelCosts` charges the backtester's fee, slippage and funding to the labelled
round trip, so a meta-label means "acting on this signal would have paid *after
costs*". `TripleBarrierSpec.exit_fill` records which execution mechanism the
label assumes: `barrier` is the classical convention and presumes resting
stop/target orders; `next_open` is what this project's next-bar-open engine can
actually fill. The study uses `next_open`, which makes the label and the
backtested arm describe the same trade — verified to within compounding by test.

**3. Selection may not touch the test block.** Each fold trains on one block,
calibrates and thresholds on the next, and chooses the winning model there too;
the test block is read once, afterwards. The structure enforces it — the
selection function receives no test data — and a test asserts that rewriting the
test block changes neither the chosen model nor any threshold.

**4. The layer may decline to act, and acceptance requires profit, not
improvement.** A filter is deployed on a fold only if, on validation, it beats
the unfiltered primary **and** is profitable in absolute terms. The second
condition is the load-bearing one: filtering a rule that only pays costs always
improves it, so an improvement-only rule would have reported success on the pure
noise control. When neither condition holds the fold abstains and the filtered
arm holds no position at all.

**5. The reported statistic for the control is profitable folds, not improved
folds.** The report shows both, side by side, precisely because they diverge on
noise.

**6. Nothing produced by this work is an operational candidate.** Every artifact
carries the banner `EXPLORATORY / INFRASTRUCTURE-ONLY`. The frozen holdout is not
addressable from any module involved: the study generates its own data.

## Consequences

The thesis can state that the meta-labeling implementation was verified against a
known ground truth before ever being pointed at market data — that it recovers a
planted edge, and that it does not invent one where none exists. That is a
statement about the instrument, not about crypto markets, and it must be reported
as such.

The measured improvement on the signal market is an **upper bound** on what the
same machinery would achieve on real data: the planted edge is stationary, its
hidden driver is observable through a noisy proxy by construction, and the
signal-to-noise ratio is chosen by us. None of those hold in a real market.

When a primary strategy eventually becomes eligible, the two arm configurations
(`configs/meta_labeling_primary_only.yaml` and
`configs/meta_labeling_primary_plus_meta.yaml`) are filled in and the same study
runs on real data. Until then the layer stays unwired from every search, family
and promotion decision.
