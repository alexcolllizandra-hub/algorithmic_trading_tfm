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

## 5. The result

**Holdout status: OPENED, once, on 2026-08-13T11:13:37Z, from commit
`31c241f`.** Everything above this line was committed at `02b79f1`, before the
partition was read; the ordering is verifiable with `git log`.

> **This is the honest result of the best available candidate.** It is not a
> promoted strategy. No threshold is attached to it, because nothing was
> promoted.

Window: 2026-01-01 .. 2026-06-30, 4,343 bars. Datasets and their SHA-256 are
recorded in [`reports/study_closure/final_holdout.md`](../../reports/study_closure/final_holdout.md);
the holdout hash matches the one pre-recorded in section 3.

| Metric | Candidate on holdout | Buy and hold, same window | Family on development |
|---|---:|---:|---:|
| Total net return | **−12.17%** | −33.23% | +6.9% |
| Annualised return | −23.02% | −55.72% | — |
| Sharpe | **−1.34** | −1.51 | +0.19 |
| Sortino | −1.80 | −1.97 | — |
| Maximum drawdown | −14.40% | −40.32% | — |
| Annualised volatility | 18.22% | 46.62% | — |
| Hit rate | 49.1% | 49.2% | — |
| Time in drawdown | 98.8% | 99.2% | — |
| Trades | 281 | — | — |

Costs actually paid: 2.17% in fees and slippage, 0.12% in funding, **2.29% of
equity in total**. The candidate would have lost money before costs as well;
costs are not the explanation.

**The development result did not transfer.** The family was selected as the
least-rejected of thirteen on the strength of +6.9% and a Sharpe of +0.19 out of
sample in development. On the holdout it returns −12.17% at a Sharpe of −1.34.
The sign of the effect reverses. That is the outcome the study-level accounting
predicted: with a raw p-value of 0.345 and a probability of backtest overfitting
of 0.486, +6.9% was never distinguishable from noise, and noise does not repeat.

### The dispersion across seeds is the finding

| Seed | Total return | Sharpe | Trades |
|---|---:|---:|---:|
| 693857 | **+66.73%** | +2.46 | 7 |
| 683778 | +1.58% | +1.00 | 26 |
| 278037 | −0.19% | −0.12 | 20 |
| 605142 | −3.19% | −1.00 | 76 |
| 671194 | −3.92% | −1.07 | 42 |
| 765570 | −15.34% | −2.21 | 254 |
| 341110 | −34.88% | −1.62 | 1 |
| 692467 / 707014 / 891022 | −36.20% | −1.72 | 1 |

Ten runs of the same family, differing only in the random seed of the parameter
search, span **103 percentage points** on the same six months of the same
instrument. One seed returns +66.7% on seven trades; three others buy once and
ride the market down. Under a real effect the seeds would agree, because they
would all be estimating the same thing. They do not agree, so what the search
selected was seed-specific noise. A study that had opened the holdout on a
single seed could have reported either +66.7% or −36.2% with equal honesty and
equal meaninglessness — which is precisely why the combination rule was fixed in
advance.

### What must not be read into this

The candidate lost 12% while the market lost 33%, with a third of the
volatility. **This is not a defensive property and is not claimed as one.** It
is mostly the arithmetic of averaging ten members that disagree with each other:
the offsetting positions cancel, which lowers the combined volatility by
construction. No individual member shows the pattern, the candidate was never
selected for downside behaviour, and one window is not evidence of anything. The
protocol forbids re-reading the result as a success on a criterion it was never
asked to meet.

**Provenance note.** The run recorded `worktree clean: false`. The only tracked
modifications at that moment were two files with line-ending differences and an
empty content diff (`git diff` returns nothing for them); the rest were untracked
report outputs. Neither is on the evaluation path. The state is recorded as
measured rather than presented as clean.

---

## 6. The conclusion of the arc

**What was tested.** Thirteen strategy families across four rounds (R2, R3, S1,
S2), on BTCUSDT and ETHUSDT perpetuals at 1h, under walk-forward validation with
purging and embargo, ten seeds per family, and a cost model applied inside the
selection rather than after it. 496,500 configurations were actually scored.

**What survived correction.** Nothing. No family survives Holm at α = 0.05, nor
Benjamini–Hochberg, nor an uncorrected threshold: the smallest raw p-value in the
entire study is 0.345, which misses significance by a factor of seven even with
no correction at all. The probability of backtest overfitting is 0.486, against
0.5 expected under pure noise.

**What the regime conditioning added.** Nothing either, and that is informative:
none of the 65 family-by-regime cells survives correction within its own block,
so the negative result is not an artifact of averaging a real effect away across
market states. There was no high-volatility corner where the edge was hiding.

**What the holdout said.** The best available candidate, frozen in writing
before the partition was read, lost 12.17% at a Sharpe of −1.34 over six months,
reversing the sign of its development result. The rejection is confirmed on data
that informed none of it.

**The reading.** The value of this arc is not a strategy; it is a rigorous map of
where the edge is not, drawn with a method whose rejection behaviour is
documented rather than assumed. Phase-1 EDA had already drawn the outline of that
map, and it did so with more precision than a blanket pessimism would suggest.

What it predicted, it predicted correctly. Lag-1 autocorrelation of 1h raw
returns is −0.017 on BTC and −0.008 on ETH — statistically detectable under
Ljung-Box, but **economically negligible**, which is how finding F5 recorded it.
On that basis `scientific_questions.md` stated in advance that "simple linear
trend-following on raw returns should not work" and entered momentum as "a
falsifiable baseline, not a favourite". Momentum returned −32.4% out of sample.
The prediction held.

What it could not predict is the more interesting half. The same EDA found
volatility strongly persistent — |r| lag-1 ACF ≈ 0.29, rolling-volatility
persistence 0.99, ARCH-LM rejecting at machine precision — and concluded that
families conditioning on *magnitude* rather than direction were **better
motivated**. `volatility_breakout` is exactly such a family. It was the
best-motivated candidate the EDA produced, it was the least-rejected of the
thirteen, it was the one carried to the holdout, and it lost 12.17% there. So the
finding is not merely "the EDA said no and the strategies failed". It is sharper:
**predictable volatility did not convert into predictable, cost-surviving
returns**, even when the strategy family was designed around the one property the
data genuinely has. Persistence of magnitude is not an edge in direction, and
after 2.29% of costs on a six-month window it did not become one.

That is the result — a negative result that is stable across families, assets,
seeds, regimes, counting rules and, finally, across the frozen holdout itself,
and that is consistent in both directions with what the data said before any
strategy was written.

**The holdout is now spent.** It cannot be used again in this study. Nothing in
this document licenses a re-ranking of the other twelve families, a variant of
the candidate, or a second window.
