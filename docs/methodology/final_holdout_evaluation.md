# Final holdout evaluation — selection rule, pre-declared

**Version:** 0.1.0 (pre-declaration) · **Date:** 2026-08-13
**Holdout status at the time of writing: CLOSED. Never opened.**

> This half of the document is committed **before** any holdout row is read. The
> commit that contains it must precede, in git history, the commit that contains
> the result. That ordering is the evidence that the candidate was frozen before
> the data was seen; nothing below may be edited afterwards.

Inputs: [study-level multiple testing](study_level_multiple_testing.md) (Piece 1)
and [regime-conditioned evaluation](regime_conditioned_eval.md) (Piece 2).

---

## 1. The selection rule

Fixed in advance, in this order, with no discretion left at any step:

1. **The candidate is the family with the best corrected metric from Piece 1.**
2. **If Piece 2 produced a better-motivated conditional candidate — a
   family-by-regime cell surviving correction within its own block — that one is
   chosen instead.**
3. The holdout is opened **exactly once**, on that single candidate. No variants
   are tested. If it fails, it is not reopened, and nothing is re-selected.
4. The result is reported as it comes out, labelled *the honest result of the
   best available candidate*. It is **not** a promoted strategy, and no threshold
   is attached to it, because nothing was promoted.

### Applying rule 2 first

**Piece 2 offers no candidate.** None of the 65 family-by-regime cells survived
correction within its block, and the best of them had a raw p-value of 0.077,
failing even an uncorrected threshold. The fall-through to rule 1 is the designed
behaviour and is not worked around.

### Applying rule 1

Every Holm-adjusted p-value in Piece 1 is 1.000 and every Benjamini–Hochberg
value is 0.997: the corrected metric is **tied at its ceiling across all thirteen
families**, so it cannot by itself order them. The tie-break is therefore
declared explicitly — and it is not a real choice, because every defensible
ordering selects the same family:

| Tie-break criterion | Best family |
|---|---|
| Smallest raw bootstrap p-value (the statistic the correction is applied to) | `volatility_breakout` (0.345) |
| Highest out-of-sample Sharpe | `volatility_breakout` (+0.19) |
| Highest total out-of-sample return | `volatility_breakout` (+6.9%) |
| Best cell in the Piece 2 re-analysis | `volatility_breakout` in low volatility (p = 0.077) |

**Selected candidate: `volatility_breakout`.**

This selection carries no claim that the family works. It is the least-rejected
of thirteen rejected families, chosen because the protocol requires the holdout
to be opened once on the best available candidate even when — especially when —
that candidate is expected to fail.

---

## 2. The frozen configuration

| Item | Value | Why this and not something else |
|---|---|---|
| Family | `volatility_breakout` | Rule 1 above |
| Asset | BTCUSDT | The study's primary asset, and the only one all thirteen families were tested on |
| Timeframe | 1h | The study's primary timeframe |
| Engine | `random_search` | The confirmatory engine in every gate; the GA was always diagnostic |
| Parameters | The **fold-14 winner of each of the 10 seeds**, equally weighted | See below |
| Costs, execution, funding | `resolved_experiment_config.yaml` from the R3 runs, unchanged | Changing a cost after seeing development results would invalidate the comparison |
| Holdout window | `[2026-01-01, 2026-07-01)` | ADR 0003, frozen since the data contract |

**Why the last fold, and why all ten seeds.** Under ADR 0012 each outer fold ran
its own independent search, so there is no single parameter set for the family —
there are 15 per seed. Fold 14 is the **last selection made before the holdout
window begins**, which is the only one that could have been deployed into it.
Combining the ten seeds equally reproduces exactly the object Piece 1 measured:
the family's performance is defined there as the seed-averaged series, so the
thing tested on the holdout must be the same thing that was ranked.

### The ten frozen parameter sets

Each was sealed by the search before its own test slice was scored
(`frozen_before_test: true`); the fingerprint is the search's own hash of the
selection and is reproducible from the artifacts.

| Seed | Fingerprint | Parameters |
|---|---|---|
| 278037 | `f244f3cf7299d1b2` | level 48, atr 24, entry 1.0, exit 0.1, volatility_stop, long, atr floor 0.5 |
| 341110 | `a0ba0f759c44fabe` | level 24, atr 14, entry 0.5, exit 0.5, opposite_break, long, gate medium+high |
| 605142 | `a7ac8714d8be5336` | level 48, atr 14, entry 0.25, exit 0.1, volatility_stop, long, atr floor 0.25, gate medium+high |
| 671194 | `ef3f68b360f7beb6` | level 48, atr 14, entry 1.0, exit 0.5, reenter_level, short, atr floor 0.25 |
| 683778 | `49167992d0dd0871` | level 24, atr 24, entry 1.0, exit 0.1, reenter_level, long, atr floor 0.5 |
| 692467 | `71242cc9028e3313` | level 48, atr 24, entry 0.5, exit 0.5, opposite_break, long, gate medium+high |
| 693857 | `3506e509f551f01d` | level 24, atr 14, entry 1.0, exit 0.25, opposite_break, both, atr floor 0.5 |
| 707014 | `105d053ba03d9bee` | level 48, atr 14, entry 0.25, exit 0.5, opposite_break, long, gate medium+high |
| 765570 | `6ceaa524c4ca8a5a` | level 48, atr 14, entry 0.25, exit 0.1, volatility_stop, both, gate medium+high |
| 891022 | `1f3e9f9ed2be5493` | level 48, atr 14, entry 0.5, exit 0.25, opposite_break, long, gate medium+high |

### The regime model

Four of the ten configurations gate on market regime, so a regime model is
required. It is fitted on **development data only** and then applied to the
holdout window, exactly as each fold fitted on its training slice and applied to
its test slice. No holdout row informs the regime boundaries.

---

## 3. The dataset that will be opened

Recorded here, from the manifests, **before** the data is read. The manifest
records provenance; reading it is not reading the partition.

| Item | Value |
|---|---|
| File | `data/processed/BTCUSDT/1h_holdout.parquet` |
| Rows | 4,344 |
| Period | 2026-01-01T00:00:00Z .. 2026-06-30T23:00:00Z |
| SHA-256 | `dec28172d8089dc77a9c9ed4dfdb5270d23fee2dbf5f45c91b4bb9e7e7b50721` |

---

## 4. What will be reported, and what will not

**Reported:** net return, Sharpe, Sortino, maximum drawdown, number of trades,
turnover and total costs over the holdout window, plus buy-and-hold over the same
window for context. Reported whatever they are.

**Not reported, because it would be dishonest:** any comparison against a
threshold the candidate was never required to meet; any re-ranking of the other
twelve families after the fact; any variant, re-parameterisation or second
window. The expected outcome is that the rejection is confirmed. It will be
reported the same way if it is not.

---

*Sections 5 onward are added after the holdout is opened, in a separate commit.*
