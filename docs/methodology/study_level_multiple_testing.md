# Study-level multiple-testing accounting

**Version:** 1.0.0 · **Date:** 2026-08-13 · **Partition:** development only
**Holdout accessed:** no

Generated artifacts: [`reports/study_closure/study_level_multiple_testing.md`](../../reports/study_closure/study_level_multiple_testing.md)
and its JSON companion. Reproduce with:

```bash
uv run python scripts/run_study_closure.py
```

Related: [validation protocol](validation_protocol.md) ·
[phase gates](../roadmap/phase_gates.md) ·
[scientific questions](../roadmap/scientific_questions.md)

---

## 1. The problem this closes

Every gate corrected for multiplicity **inside itself**. R3 judged five families
together, S1 four, S2 three. No one ever corrected **across** the gates.

That gap matters because the question the thesis actually answers is not "did
breakout work, considered alone". It is *"of everything we tried, did anything
work?"* — and that question selects a maximum over the whole study. Correcting
each batch separately while reporting a study-wide conclusion would understate
the number of chances the search had to produce a winner.

This document supplies the missing denominator and applies the correction once,
over all thirteen families at once. **It recomputes no backtest.** It reads the
out-of-sample ledgers the gates already wrote and judges those same numbers
against the full family of tests the study ran.

---

## 2. What was tested

Thirteen distinct strategy families, across four gates, in 284 executed search
units (family × asset × seed × engine).

| Gate | Families | Assets | Seeds | Units |
|---|---|---|---:|---:|
| R2 | `momentum` | BTC, ETH | 10 | 40 |
| R3 | `breakout`, `mean_reversion`, `volatility_breakout`, `funding`, `BTC_ETH_confirmation` | BTC, ETH | 10 | 200 |
| S1 | `mtf_trend_consensus`, `funding_reversal`, `intraday_seasonality`, `xasset_spread_reversion` | BTC | 1 | 8 |
| S2 | `taker_flow_extreme`, `illiquidity_reversion`, `flow_price_divergence` | BTC, ETH | 3 | 36 |

The inventory is rebuilt from the **gate reports**, not from listing the artifact
store. That distinction is deliberate: the store also holds earlier pilots and
abandoned attempts, and counting those would inflate the denominator with work
that never entered the scientific record.

Each gate's pre-registered acceptance criterion is quoted verbatim in the
generated report. In summary: R2 and R3 required all six promotion criteria on
Random Search, on both assets, on at least 6 of 10 seeds; S1-B and S2-B were
pilots whose promotion stages (S1-C, S2-C) were never reached.

---

## 3. Method

**The statistic.** For each family, the per-bar out-of-sample net returns of
every fold are concatenated into one series, and a one-sided stationary bootstrap
tests the null that the family earns nothing. The bootstrap draws, block
probability and seed are inherited unchanged from `reporting/s1_pilot.py`, so
these p-values are comparable with the ones S1 already reported.

**Seeds are averaged inside a family, not counted as separate tests.** The
protocol treats a seed as a replicate of one hypothesis: a family is a single
idea, and its performance is what that idea delivered once the arbitrary starting
point of the search is integrated out. Averaging per bar across seeds is exactly
the return of an equal-weight portfolio of the seeds.

**BTCUSDT is the primary asset** because it is the only one all thirteen families
were tested on. ETHUSDT is reported separately, over the nine families that have
it, as a consistency check — not as an extra block of tests.

**Folds without a winner are absent, not zero.** A fold whose search found no
admissible candidate wrote no ledger. Recording that as a zero return would
credit the family with a flat, costless bar it never actually held.

**Corrections applied.** Holm step-down for family-wise error, Benjamini–Hochberg
for false-discovery rate, both at α = 0.05 over the thirteen p-values; CSCV
probability of backtest overfitting over the thirteen aligned family series; and
a deflated Sharpe ratio on the best family.

`holm_bonferroni` and `benjamini_hochberg_correction` were added to
`evaluation/multiple_testing.py` for this document — the repository previously
had only the flag-returning BH variant and no FWER control at all.

---

## 4. Results

Ranked by raw p-value. Full table in the generated report.

| Family | Gate | Total return | Sharpe (ann.) | p | p Holm | p BH | Survives |
|---|---|---:|---:|---:|---:|---:|:--:|
| `volatility_breakout` | R3 | +6.9% | +0.19 | 0.345 | 1.000 | 0.997 | no |
| `taker_flow_extreme` | S2 | +1.5% | +0.09 | 0.455 | 1.000 | 0.997 | no |
| `momentum` | R2 | −32.4% | −0.23 | 0.652 | 1.000 | 0.997 | no |
| `funding_reversal` | S1 | −38.3% | −0.32 | 0.738 | 1.000 | 0.997 | no |
| `funding` | R3 | −35.0% | −0.39 | 0.797 | 1.000 | 0.997 | no |
| `flow_price_divergence` | S2 | −6.7% | −0.45 | 0.809 | 1.000 | 0.997 | no |
| `mtf_trend_consensus` | S1 | −67.8% | −0.51 | 0.851 | 1.000 | 0.997 | no |
| `mean_reversion` | R3 | −60.8% | −0.68 | 0.901 | 1.000 | 0.997 | no |
| `BTC_ETH_confirmation` | R3 | −58.7% | −0.69 | 0.913 | 1.000 | 0.997 | no |
| `intraday_seasonality` | S1 | −42.0% | −0.75 | 0.918 | 1.000 | 0.997 | no |
| `breakout` | R3 | −16.1% | −0.80 | 0.943 | 1.000 | 0.997 | no |
| `xasset_spread_reversion` | S1 | −84.0% | −1.26 | 0.987 | 1.000 | 0.997 | no |
| `illiquidity_reversion` | S2 | −37.6% | −1.31 | 0.997 | 1.000 | 0.997 | no |

Three observations carry the section.

**Only two of thirteen families finished positive at all**, and neither is close
to significance *before* any correction: raw p-values of 0.345 and 0.455 against
a 0.05 threshold. There is nothing for the correction to destroy — the
correction is not what killed these results.

**The best family does not survive contact with the second asset.**
`volatility_breakout` returns +6.9% on BTC and **−59.6% on ETH**. A genuine
structural effect in a market as coupled as BTC/ETH should not reverse sign and
magnitude like that. This is the single most informative number in the table.

**The probability of backtest overfitting is 0.486.** Under pure noise the
expected value is 0.5: the configuration that looks best in one half of the
sample is a coin flip in the other half. The study measures 0.486. The selection
process is, to within sampling error, carrying no information.

### Is the best one real?

| Selection counted over | Trials | Deflated Sharpe | P(best is spurious) |
|---|---:|---:|---:|
| family selection | 13 | 0.139 | 0.861 |
| all configurations evaluated | 496,500 | 0.000 | 1.000 |

**496,500 configurations were actually scored** across the study — every
candidate both engines evaluated, over all folds, seeds and assets. That is the
honest answer to "how many things did you try", and it is the number the deflated
Sharpe ratio deserves.

Both rows use the dispersion of Sharpe across the thirteen family series. For the
second row that understates the true dispersion, because individual
configurations vary more than family averages do, and a smaller dispersion lowers
the null's expected maximum. The assumption therefore **favours the strategies**,
and the verdict survives it regardless.

### Does the verdict depend on how the tests were counted?

The study never pre-registered a single study-level N, so the count is chosen
here rather than inherited. It is reported under four defensible definitions so
that the choice cannot carry the conclusion.

| Counting rule | N | Bonferroni threshold | Anything survives |
|---|---:|---:|:--:|
| families | 13 | 3.85 × 10⁻³ | no |
| family × asset | 22 | 2.27 × 10⁻³ | no |
| family × asset × seed | 142 | 3.52 × 10⁻⁴ | no |
| all configurations evaluated | 496,500 | 1.01 × 10⁻⁷ | no |

The smallest raw p-value in the entire study is 0.345. It fails the most generous
possible threshold — N = 1, no correction at all — by a factor of seven. **The
choice of N is irrelevant to the conclusion**, which is the strongest form this
result could take.

---

## 5. Conclusion

> Across the thirteen strategy families the study tested, and against the 496,500
> configurations actually evaluated to produce them, **no family survives
> family-wise error control at α = 0.05** — nor Benjamini–Hochberg, nor any
> uncorrected threshold. The probability of backtest overfitting is 0.486, within
> sampling error of the 0.5 expected from pure noise, and the probability that
> the best family is a product of selection rather than of edge is 1.000.

The result does not depend on the correction, on the counting rule, or on the
choice of statistic. Under this cost model, on this instrument class, at this
horizon, the study finds no edge — and can now say so with a number attached.

---

## Change log

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-08-13 | Study-level accounting over R2+R3+S1+S2; Holm and BH-with-adjusted-values added to `evaluation/multiple_testing.py` |
