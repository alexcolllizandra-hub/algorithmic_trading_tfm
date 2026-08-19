# M1/M2 — meta-labeling machinery validated on synthetic data

> **EXPLORATORY / INFRASTRUCTURE-ONLY.** Everything below was measured on
> generated data. No claim is made about BTC, ETH or any traded market, and no
> operational candidate is proposed. The frozen holdout
> `[2026-01-01, 2026-07-01)` was not read.

- **Date:** 2026-08-11
- **Decision record:** [ADR 0017](../decisions/0017-meta-labeling-validated-on-synthetic-data.md)
- **Evidence:** `reports/meta_labeling_synthetic/meta_labeling_synthetic.md`
  and its JSON payload
- **Reproduce:** `uv run python scripts/validate_meta_labeling_synthetic.py`

## Why this ran at all

M1/M2 exists to filter an eligible primary strategy, and there is none. Gate R3
closed with zero promotions, no S1 family passed, and the S2 development pilots
produced no family that fired the partial-signal criterion. Rather than leave the
layer untested until its first use on a real candidate — where an implementation
fault and a market result look identical — it was exercised on markets whose
ground truth is known in advance.

## What was built

| Component | Path |
|---|---|
| Cost-aware triple-barrier labels, purging, embargo, uniqueness weights | `src/perp_lab/labeling/triple_barrier.py` |
| Classifiers, calibration, validation-only threshold, SHAP | `src/perp_lab/meta_labeling/model.py` |
| Permutation importance, PSI drift, position scaling | `src/perp_lab/meta_labeling/diagnostics.py` |
| Predictive and economic scorecards | `src/perp_lab/meta_labeling/metrics.py` |
| Synthetic signal market and pure-noise control | `src/perp_lab/meta_labeling/synthetic.py` |
| Walk-forward study, model selection, the two arms | `src/perp_lab/meta_labeling/study.py` |
| Report | `src/perp_lab/reporting/meta_labeling_synthetic.py` |
| Runner | `scripts/validate_meta_labeling_synthetic.py` |

## What was run

Three seeds (42, 43, 44) on each of two markets, 20 000 hourly bars each, six
expanding walk-forward folds per market. Every fold trains three candidates
(logistic regression, random forest, LightGBM), calibrates and thresholds them on
validation, selects the winner on validation economics, and only then reads the
test block. Costs are 4 bps fee + 1 bps slippage per side plus realised funding,
charged both in the labels and in the backtested arms.

## Result

| Market | primary_only | primary_plus_meta | Profitable folds | Median PR-AUC lift |
|---|---:|---:|---:|---:|
| signal (edge planted) | -68.17% / -8.41% / -67.09% | **+95.51% / +161.55% / +113.30%** | 18/18 | 1.227 |
| noise (GBM control) | -66.58% / -53.28% / -68.09% | **-3.69% / -12.53% / -11.52%** | 3/18 | 1.009 |

Compounded over the disjoint test blocks, one figure per seed in seed order. All
four pre-specified checks passed.

**On the planted edge** the layer recovers the hidden state well enough to turn a
losing primary into a profitable one in all eighteen test blocks, with
probabilities worth about 23% more than the base rate.

**On the pure-noise control** it does not. The filtered arm ends negative on all
three seeds, only 3 of 18 folds happen to close positive, and the PR-AUC lift sits
at 1.009 — the model is worth nothing, and the report says so.

## The trap this control exposes

On the noise market the filter *improves* the primary in 17 of 18 folds. That
looks like success and is not: filtering a rule that pays nothing but transaction
costs always improves it, because trading less loses less. Two consequences were
built into the machinery rather than left to interpretation:

1. a fold is only allowed to act if the filtered arm beats the primary **and**
   is profitable on validation — otherwise it abstains and holds nothing
   (it abstained in 5 of 18 noise folds and 0 of 18 signal folds);
2. the report's headline column is *profitable folds*, not *improved folds*.

## What this does not establish

- Nothing about real markets. The data is generated.
- No operational candidate. The primary here is a synthetic momentum rule chosen
  to leave room for a filter, not a strategy that passed a gate.
- The planted edge is stationary and driven by a state that is observable through
  a noisy proxy by construction. Real edges are neither, so the measured
  improvement is an **upper bound** on what this machinery would achieve on real
  data.

## Next

The layer stays unwired from every search, family and promotion decision. When a
primary strategy becomes eligible, `configs/meta_labeling_primary_only.yaml` and
`configs/meta_labeling_primary_plus_meta.yaml` are filled in and the same study
runs on the development partition. The holdout remains closed.
