# Gate S1-B — development pilot (DEV-ONLY)

> **DEVELOPMENT-ONLY EVIDENCE. Gate S1-B is a mechanical viability screen, not a promotion decision. No holdout data was read.**

Primary engine: `random_search` (confirmatory). The genetic algorithm is a secondary diagnostic and decides nothing.

## Per family x engine

| Family | Engine | Median OOS return | Median OOS Sharpe | OOS trades | Folds w/ trades | Folds return > 0 | Feasible | Median DSR | Mechanically viable |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| `funding_reversal` | random_search | +0.21% | 0.17 | 515 | 14/15 | 8/15 | 358/375 | 0.576 | yes |
| `funding_reversal` | genetic_algorithm | +2.83% | 0.76 | 463 | 15/15 | 8/15 | 365/375 | 0.456 | yes |
| `intraday_seasonality` | random_search | -2.96% | -1.22 | 1387 | 15/15 | 4/15 | 375/375 | 0.091 | yes |
| `intraday_seasonality` | genetic_algorithm | -3.05% | -1.30 | 1468 | 14/15 | 2/15 | 375/375 | 0.165 | yes |
| `mtf_trend_consensus` | random_search | -6.84% | -0.94 | 1334 | 15/15 | 6/15 | 61/375 | 0.411 | yes |
| `mtf_trend_consensus` | genetic_algorithm | -7.69% | -0.57 | 441 | 14/15 | 5/15 | 101/375 | 0.438 | yes |
| `xasset_spread_reversion` | random_search | -8.07% | -1.12 | 1227 | 15/15 | 3/15 | 310/375 | 0.258 | yes |
| `xasset_spread_reversion` | genetic_algorithm | -8.05% | -0.93 | 844 | 15/15 | 4/15 | 321/375 | 0.285 | yes |

## Multiple-testing accounting

Benjamini-Hochberg at alpha = 0.05 over the four families' one-sided bootstrap p-values (`random_search`, null: the family earns nothing):

| Family | Bootstrap p-value | Rejected under BH |
|---|---:|---|
| `funding_reversal` | 0.7455 | no |
| `intraday_seasonality` | 0.9195 | no |
| `mtf_trend_consensus` | 0.8375 | no |
| `xasset_spread_reversion` | 0.9910 | no |

Across the four families (32385 aligned out-of-sample bars, benchmark = flat):

* Hansen SPA: statistic 0.000, p = 1.0000
* White Reality Check: statistic -0.002, p = 0.9955

These correct for selection across the four families only. They do **not** correct for the evaluations spent inside each family; see the deflated Sharpe ratio.

**PBO (CSCV) not computed.** CSCV needs one performance matrix of the same configurations across all time blocks. Under ADR 0012 the search is independent per outer fold, so no configuration is shared between folds. Computing it requires evaluating a common candidate set across every fold, which is an S1-C task.

## What this table is not

S1-B drops a family only for a mechanical reason (no valid candidates, no trades, or a failed invariant), never for weak performance (gate_s1_batch_01.md section 3). The performance columns above are descriptive: at one seed, one asset and 25 evaluations per fold they cannot evaluate the pre-registered promotion criteria C1-C6, which are defined over 10 seeds and both assets in S1-C. No family is promoted or rejected here.
