# ADR 0011 -- Multi-seed baseline for the momentum family

- **Status:** superseded as evidence by ADR 0013; retained for traceability
- **Date:** 2026-08-05
- **Supersedes:** nothing. Extends ADR 0009 (fair RS/GA comparison) and ADR 0010
  (OOS evaluation, baselines and robustness).

> **Qualification (added 2026-08-08).** The study below was produced under a
> search protocol that ranked candidates on a fitness pooled across *all*
> walk-forward folds, including folds later than the one being scored. See
> [ADR 0012](0012-outer-fold-contamination-in-candidate-search.md). The bias runs
> in the genetic algorithm's favour, so the negative conclusions here are
> conservative -- but the RS-vs-GA point estimate is partly bias and must not be
> read as a real, merely-underpowered effect. The study is scheduled for re-run
> under the corrected protocol.
>
> The single-seed interval `[0.011, 1.044]` cited in the Context section is
> **documentary only**: no artifact in `artifacts/` reproduces those bounds, and
> this ADR itself states that pre-scheduler runs are not poolable with this study.
> It must not be cited as a result.
>
> **Resolution (2026-08-09).** The pre-registered clean re-baseline is complete.
> See [ADR 0013](0013-clean-momentum-rebaseline.md). Momentum is uniformly
> negative across both assets and engines; the paired GA - RS estimate moves
> from `+0.183` to `-0.061` with a 95% interval of `[-0.399, +0.277]`.
> This document and its artifacts remain unchanged as the record of the
> superseded experiment.

## Context

Every search result reported so far came from a single seed. A stochastic search
run once tells us what that run found; it cannot tell us whether the finding is a
property of the market or an accident of the random number generator. Before the
strategy space is widened, that ambiguity has to be removed, because a wider space
makes it strictly worse.

The concrete trigger: a one-seed run of this exact configuration reported the
genetic algorithm ahead of random search with a 95% confidence interval of
`[0.011, 1.044]` -- nominally significant. That number is reproduced below with
ten seeds.

## Decision

### 1. The momentum experiment is frozen as the baseline

Features, fitness, costs, walk-forward geometry and the strategy space are
unchanged. The multi-seed study varies **only** the seed and the asset.

### 2. Seeds are derived, not enumerated

`utils.seeds.SeedScheduler` derives every stream from one recorded base seed via
`numpy.random.SeedSequence`, with the stream's identity hashed into the spawn key:

```
stream(namespace, **keys) -> SeedSequence(entropy=base_seed,
                                          spawn_key=blake2b(namespace|sorted keys))
```

Streams are separated by asset, fold and engine. Two consequences matter:

- A stream never shifts when an unrelated component is added or changes its number
  of draws, so a run stays reproducible from the base seed alone.
- `base + 1` and `base + 2` are adjacent, not independent; hashing avoids handing
  two components correlated sequences.

Random Search and the genetic algorithm now get **different** streams. Giving both
the same seed never made them comparable -- it only coupled them to one arbitrary
sequence. Comparability comes from running many seeds, not from sharing RNG state.

**This changes numerical results.** The single-seed runs from ADR 0010 were
computed under the old scheme and are therefore *not* poolable with this study.
They are kept on disk, unchanged, and are excluded from every aggregate here.

### 3. Long runs are crash-safe before they are launched

`tracking/journal.py` provides `events.jsonl` (append-only), `status.json`
(atomically replaced snapshot with a work-based ETA) and `checkpoint.json` (the set
of completed units and their results). Writes go to a sibling temp file followed by
`replace`, which is atomic on POSIX and Windows.

Resuming into a checkpoint whose `config_fingerprint` or git commit differs is
**refused**, not merged: silently pooling units computed under two contracts is
worse than starting again. The fingerprint hashes the whole search config except
`seed`, `symbol` and `label` -- the three dimensions the study deliberately varies.

### 4. Seeds are not out-of-sample periods

This is the load-bearing methodological decision. A 2 x 10 x 15 study yields 300
numbers per engine, but not 300 independent observations: the ten seeds run over
the *same* price history.

The analysis therefore:

- averages seeds **within** each (symbol, fold) cell, then does inference across
  folds -- so the sample size is 30, not 300;
- reports seed spread separately, as *search instability*, never as an error bar on
  market performance;
- bootstraps each run's **own** concatenated out-of-sample series, never a
  concatenation across seeds.

`tests/unit/test_multi_seed_analysis.py` asserts the interval is more than twice as
wide as the naive all-cells-independent calculation, so a future refactor that
starts counting seeds as observations fails the suite.

### 5. The holdout is closed by code, not by access times

Filesystem `atime` is not evidence: it is disabled on many volumes and changes when
a backup tool reads a file. `tests/unit/test_holdout_guards.py` exercises all five
guards -- contract cross-check, pre-load manifest guard, fold geometry, feature
engine, row-level loader -- and asserts each one *raises*.

## Results

Study `multiseed_momentum_baseline`: 2 assets x 10 seeds x 15 folds, 20 units,
177-186 unique evaluations per engine per unit, exact parity in every unit.

| symbol / engine | seeds | positive | beats B&H | survives 2x costs | bootstrap CI > 0 |
|---|---|---|---|---|---|
| BTCUSDT / random_search | 10 | 0 | 0 | 0 | 0 |
| BTCUSDT / genetic_algorithm | 10 | 0 | 0 | 0 | 0 |
| ETHUSDT / random_search | 10 | 5 | 7 | 1 | 0 |
| ETHUSDT / genetic_algorithm | 10 | 7 | 8 | 2 | 0 |

Paired GA - RS, 300 cells collapsed to 30 fold-level units: mean difference
`+0.183`, 95% CI `[-0.053, +0.419]`, Cohen's dz `0.29`.

Seed-to-fold standard-deviation ratio: `0.51` (RS), `0.43` (GA).

## Consequences

- **The single-seed GA advantage does not survive.** The interval that excluded
  zero with one seed includes it with ten. No superiority claim is made for either
  engine.
- **The momentum baseline has no demonstrable edge.** Zero of forty run/engine
  combinations have a bootstrap Sharpe interval excluding zero. On BTCUSDT no seed
  is even profitable, against a buy-and-hold that returned +78% over the same
  window. On ETHUSDT the median return is near zero and only 3 of 20 combinations
  survive doubled costs.
- **Re-running the search moves the result about half as much as changing the
  market period.** Any conclusion drawn from one seed of this pipeline is
  unreliable by construction.
- This negative result is retained and reported. It is the reference every widened
  strategy space must be compared against.

## Alternatives considered

- *Common random numbers for RS and GA.* A legitimate variance-reduction technique
  when two procedures consume randomness in the same way. These do not, so it would
  buy nothing while re-introducing the coupling.
- *Reusing the ADR-0010 single-seed runs as seed #1.* Rejected: the stream
  derivation changed, so they are not the same experiment.
- *Treating each (seed, fold) cell as an observation.* Rejected; this is the error
  the module exists to prevent.
