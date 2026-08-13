# Study-level multiple-testing accounting

**Generated:** 2026-08-13T10:40:18+00:00 · **Commit:** `232bc372d4e283c24f8e6a9bab3ade64671841cc`
**Partition:** development only · **Holdout accessed:** False

Every gate corrected for multiplicity inside itself and none corrected across the gates. This document does that once, over all 13 families, on BTCUSDT with the `random_search` engine. It recomputes no backtest: it reads the out-of-sample ledgers the gates already wrote and judges them against the full family of tests the study actually ran.

## 1. Inventory of everything tested

| Gate | Family | Assets | Seeds | Engines | Units |
|---|---|---|---:|---|---:|
| R2 | `momentum` | BTC, ETH | 10 | 2 | 40 |
| R3 | `BTC_ETH_confirmation` | BTC, ETH | 10 | 2 | 40 |
| R3 | `breakout` | BTC, ETH | 10 | 2 | 40 |
| R3 | `funding` | BTC, ETH | 10 | 2 | 40 |
| R3 | `mean_reversion` | BTC, ETH | 10 | 2 | 40 |
| R3 | `volatility_breakout` | BTC, ETH | 10 | 2 | 40 |
| S1 | `funding_reversal` | BTC | 1 | 2 | 2 |
| S1 | `intraday_seasonality` | BTC | 1 | 2 | 2 |
| S1 | `mtf_trend_consensus` | BTC | 1 | 2 | 2 |
| S1 | `xasset_spread_reversion` | BTC | 1 | 2 | 2 |
| S2 | `flow_price_divergence` | BTC, ETH | 3 | 2 | 12 |
| S2 | `illiquidity_reversion` | BTC, ETH | 3 | 2 | 12 |
| S2 | `taker_flow_extreme` | BTC, ETH | 3 | 2 | 12 |

**Total distinct families tested: 13.**

Pre-registered acceptance criterion by gate:

- **R2** — Six robustness criteria on Random Search, both assets, majority of 10 seeds (ADR 0013). Momentum re-baselined after the outer-fold leakage fix.
- **R3** — All six promotion criteria (positive net OOS return, bootstrap Sharpe CI excluding zero, survives doubled costs, beats buy-and-hold, survives dropping the top five trades, not confined to one fold) on Random Search, on both assets, on at least 6 of 10 seeds; plus a veto below 5 OOS trades (ADR 0015).
- **S1** — S1-B screened for mechanical viability only and could not reject on performance; the S1-C promotion criterion (same six, 6/10 seeds, both assets, plus deflated Sharpe > 0.95, PBO < 0.5 and BH at 0.05) was never executed (ADR 0016).
- **S2** — S2-B partial-signal trigger: positive compounded net OOS return on at least 2 of 3 seeds, at least 5 OOS trades on each such seed, and not confined to a single fold. It did not fire, so S2-C promotion was never authorised.

## 2. Corrected results

The p-value is one-sided, from a stationary bootstrap on the concatenated out-of-sample bar returns, against the null that the family earns nothing. Seeds are averaged within a family because the protocol treats them as replicates of one hypothesis, not as separate hypotheses.

| Family | Gate | Bars | Total return | Sharpe (ann.) | p | p Holm | p BH | Survives |
|---|---|---:|---:|---:|---:|---:|---:|:--:|
| `volatility_breakout` | R3 | 32,385 | +6.9% | +0.19 | 0.345 | 1.000 | 0.997 | no |
| `taker_flow_extreme` | S2 | 32,385 | +1.5% | +0.09 | 0.455 | 1.000 | 0.997 | no |
| `momentum` | R2 | 32,385 | -32.4% | -0.23 | 0.652 | 1.000 | 0.997 | no |
| `funding_reversal` | S1 | 32,385 | -38.3% | -0.32 | 0.738 | 1.000 | 0.997 | no |
| `funding` | R3 | 32,385 | -35.0% | -0.39 | 0.797 | 1.000 | 0.997 | no |
| `flow_price_divergence` | S2 | 32,385 | -6.7% | -0.45 | 0.809 | 1.000 | 0.997 | no |
| `mtf_trend_consensus` | S1 | 32,385 | -67.8% | -0.51 | 0.851 | 1.000 | 0.997 | no |
| `mean_reversion` | R3 | 32,385 | -60.8% | -0.68 | 0.901 | 1.000 | 0.997 | no |
| `BTC_ETH_confirmation` | R3 | 32,385 | -58.7% | -0.69 | 0.913 | 1.000 | 0.997 | no |
| `intraday_seasonality` | S1 | 32,385 | -42.0% | -0.75 | 0.918 | 1.000 | 0.997 | no |
| `breakout` | R3 | 32,385 | -16.1% | -0.80 | 0.943 | 1.000 | 0.997 | no |
| `xasset_spread_reversion` | S1 | 32,385 | -84.0% | -1.26 | 0.987 | 1.000 | 0.997 | no |
| `illiquidity_reversion` | S2 | 32,385 | -37.6% | -1.31 | 0.997 | 1.000 | 0.997 | no |

**Surviving Holm (FWER, alpha = 0.05): 0 of 13.** Surviving Benjamini-Hochberg (FDR): 0.

## 3. Is the best of them real?

The best family by out-of-sample Sharpe is `volatility_breakout`. The deflated Sharpe ratio asks how surprising that maximum is, given how many chances the study had to produce it.

| Selection counted over | Trials | Deflated Sharpe | P(best is spurious) |
|---|---:|---:|---:|
| family selection | 13 | 0.139 | 0.861 |
| all configurations evaluated | 496,500 | 0.000 | 1.000 |

Both rows use the dispersion of Sharpe ratios across the thirteen family series. For the second row that is an understatement: individual configurations vary more than family averages do, and a smaller dispersion lowers the null's expected maximum, which makes the observed Sharpe easier to beat. The assumption therefore favours the strategies, and the verdict survives it anyway.

**Probability of backtest overfitting: 0.486** (70 CSCV splits over 32,385 aligned bars and 13 families). This is the probability that the family looking best in one half of the sample is median-or-worse in the other half.

## 4. Does the verdict depend on how the tests are counted?

The study never pre-registered a single study-level N, so the count is chosen here. It is reported under several defensible definitions so the choice cannot carry the conclusion.

| Counting rule | N | Bonferroni threshold | Anything survives |
|---|---:|---:|:--:|
| families | 13 | 3.85e-03 | no |
| family x asset | 22 | 2.27e-03 | no |
| family x asset x seed | 142 | 3.52e-04 | no |
| all configurations evaluated | 496,500 | 1.01e-07 | no |

## 5. ETHUSDT consistency check

Reported over the subset of families tested on this asset. It is a consistency check on the same hypotheses, not an additional block of tests, and it is not merged into the count above.

| Family | Bars | Total return | Sharpe (ann.) | p |
|---|---:|---:|---:|---:|
| `taker_flow_extreme` | 32,385 | +1.4% | +0.09 | 0.426 |
| `momentum` | 32,385 | -47.4% | -0.34 | 0.750 |
| `funding` | 32,385 | -49.9% | -0.39 | 0.770 |
| `flow_price_divergence` | 28,067 | -8.3% | -0.49 | 0.786 |
| `BTC_ETH_confirmation` | 32,385 | -68.7% | -0.64 | 0.886 |
| `volatility_breakout` | 32,385 | -59.6% | -0.67 | 0.902 |
| `mean_reversion` | 32,385 | -79.2% | -0.97 | 0.969 |
| `breakout` | 32,385 | -26.2% | -1.11 | 0.981 |
| `illiquidity_reversion` | 32,385 | -55.5% | -1.49 | 0.994 |

## Conclusion

Across the 13 strategy families the study tested, and against the 496,500 configurations actually evaluated to produce them, no family survives family-wise error control at alpha = 0.05; the probability of backtest overfitting is 0.486, and the probability that the best family is a product of selection rather than of edge is 1.000.
