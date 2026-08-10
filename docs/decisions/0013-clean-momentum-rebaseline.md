# ADR 0013 -- Clean momentum re-baseline after outer-fold isolation

- **Status:** accepted
- **Date:** 2026-08-09
- **Supersedes as evidence:** ADR 0011's numerical results
- **Depends on:** ADR 0012 (independent search per outer fold)

## Context

ADR 0011's momentum study ranked candidates on a fitness pooled across all
walk-forward folds. The genetic algorithm evolved on that contaminated ranking,
so both the momentum result and the RS-vs-GA comparison were invalid as
inference. ADR 0012 corrected the protocol and pre-registered two expectations:

1. momentum should remain negative or worsen once later folds cannot influence
   earlier selections;
2. the apparent GA advantage (`GA - RS = +0.183`) should move toward zero.

The old study remains under
`artifacts/runs/multiseed_momentum_baseline/`, marked `SUPERSEDED.json`. It was
not overwritten or deleted.

## Experiment

Study `multiseed_momentum_r2_clean_v2`:

- real development data only; the frozen holdout was not requested or loaded;
- BTCUSDT and ETHUSDT;
- the same ten seeds derived from base seed 42:
  `891022, 341110, 693857, 683778, 765570, 692467, 605142, 671194, 707014,
  278037`;
- 15 chronological outer folds per unit, OOS 2022-03-31 through 2025-12-09;
- Random Search and GA, each spending exactly 300 unique, valid, non-cached
  evaluations **inside every fold** (4,500 per engine and unit);
- each winner fingerprinted on its fold's validation data before one test
  evaluation;
- 20 asset-seed units, 300 paired symbol-seed-fold cells;
- inference over 15 calendar folds after averaging seeds and then the two assets
  inside each fold.

The first launch (`multiseed_momentum_r2_clean`) stopped in BTC fold 7 when the
GA reached 299/300 evaluations at the 40-generation safety cap. This is evidence
that the parity guard works: it aborted rather than accept unequal effort. No
unit completed and no result from that attempt is used. The successful config
raises only `ga.max_generations` to 200. This is a safety cap, not an
experimental budget: every fold still stops at exactly 300 evaluations.

The completed study records commit `aac3357`, configuration fingerprint
`b48a352a0cfa3e87`, run identity `48f61ce9fdeca881`, the current search protocol,
dataset/config identity components and every derived stream. It is marked
provisional because `configs/search_r2_momentum.yaml` was untracked when the run
started; its exact contents and hash are nevertheless captured by the run
identity and every unit's resolved config. This status must remain visible until
the configuration is committed.

## Results

### Momentum

| Symbol / engine | Positive seeds | Beats B&H | Survives 2x costs | Bootstrap CI > 0 | Median OOS return |
|---|---:|---:|---:|---:|---:|
| BTCUSDT / RS | 0 / 10 | 0 / 10 | 0 / 10 | 0 / 10 | -0.350 |
| BTCUSDT / GA | 0 / 10 | 0 / 10 | 0 / 10 | 0 / 10 | -0.455 |
| ETHUSDT / RS | 0 / 10 | 0 / 10 | 0 / 10 | 0 / 10 | -0.475 |
| ETHUSDT / GA | 0 / 10 | 0 / 10 | 0 / 10 | 0 / 10 | -0.507 |

All 40 asset-seed-engine combinations lose money. None beats the fixed
buy-and-hold reference, survives doubled costs or has a one-week-block bootstrap
Sharpe interval excluding zero. Momentum therefore fails its promotion criterion
under the corrected protocol and is **rejected**. It must not be retuned
retrospectively.

### Random Search versus the genetic algorithm

Seeds are averaged within each symbol-fold cell; BTC and ETH are then averaged
within each of the 15 shared calendar folds. This avoids treating two correlated
assets as independent market histories.

- mean paired `GA - RS`: **-0.061**;
- 95% interval: **[-0.399, +0.277]**;
- Cohen's dz: **-0.100**;
- folds favouring GA / RS / ties: **5 / 9 / 1**;
- per-symbol intervals also include zero.

There is no evidence that either search engine is superior. The pre-registered
expectation is met: the old +0.183 estimate moves past zero to a small -0.061,
while uncertainty still spans both signs.

Seed-to-fold SD ratios are 0.401 for Random Search and 0.049 for the GA. Search
randomness remains material for RS, though smaller than variation across market
periods; the corrected fold-local GA is comparatively stable in this study.

## Comparison with the superseded study

| Quantity | Superseded ADR 0011 | Clean R2 |
|---|---:|---:|
| Positive BTC seeds (RS / GA) | 0 / 0 | 0 / 0 |
| Positive ETH seeds (RS / GA) | 5 / 7 | 0 / 0 |
| Bootstrap Sharpe CI > 0 (of 40) | 0 | 0 |
| Mean paired GA - RS | +0.183 | -0.061 |
| 95% interval | [-0.053, +0.419] | [-0.399, +0.277] |
| Cohen's dz | +0.289 | -0.100 |
| Independent units used | 30 symbol-folds | 15 calendar folds |

The direction matches the pre-registration: the momentum conclusion strengthens
from negative/inconclusive to uniformly negative, and the apparent GA advantage
vanishes.

This table is **not** a controlled estimate of the causal effect of fixing
outer-fold leakage. R2 also enforces the declared 300 evaluations in every fold
(the old runner consumed roughly 177-186 pooled evaluations per unit), uses the
correct 15-calendar-fold inference instead of counting correlated assets as 30
periods, and includes subsequent baseline-pricing fixes. The direct evaluator
regression in ADR 0012, not this before/after table, isolates the leakage channel.

## Verification

`scripts/audit_study_isolation.py` audited all 20 units and reported zero
failures:

- both engines spent 300 evaluations in each of all 15 folds;
- all 600 fold winners were fingerprinted on validation before test;
- each winner belonged to its own fold's candidate ledger;
- all scored candidates recorded within-fold dispersion;
- every run declared `independent_search_per_outer_fold`.

The robustness artifact is
`artifacts/runs/multiseed_momentum_r2_clean_v2/study_robustness.json`; the
statistical analysis is `multi_seed_analysis.json`.

## Decision

1. **Reject momentum.** Do not retune or reopen its parameter space.
2. **Retain Random Search as the default search baseline.** The GA has not earned
   the extra complexity; it may remain as a comparator where the roadmap
   requires it, under equal per-fold budget.
3. **Close Gate R2.** The next executable phase is R3: evaluate the other
   pre-registered families under the clean protocol.
4. **Keep ADR 0011 and all old artifacts.** They document the superseded result
   and the methodological correction, but are not evidence.
