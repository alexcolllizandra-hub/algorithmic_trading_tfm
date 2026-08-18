# M1/M2 meta-labeling - validation on synthetic data

> **EXPLORATORY / INFRASTRUCTURE-ONLY - synthetic data, no operational candidate**

**Verdict: MACHINERY VALIDATED.** This states that the implementation behaves correctly on markets whose ground truth is known. It is not a trading result, not a candidate, and not evidence about any real asset. No S2 family fired the partial-signal criterion, so there is no eligible primary strategy; this run validates the machinery in advance of one.

Holdout accessed: **no**. Data: **synthetic**. Seeds: 42, 43, 44.

## Pre-specified checks

| Check | Result |
|---|---|
| `signal_improves_primary` | PASS |
| `signal_probabilities_informative` | PASS |
| `noise_not_profitable` | PASS |
| `noise_probabilities_uninformative` | PASS |

Signal market: the filter improved the primary in 89% of folds, with a median PR-AUC lift of 1.227. Noise control: the layer acted in 13 of 18 folds and was profitable in 3, with a median PR-AUC lift of 1.009 and a median filtered return of -11.52%.

## primary_only vs primary_plus_meta_labeling (test blocks only)

Returns compound the disjoint test blocks of every fold. *Improved* counts folds where the filter beat the primary; *profitable* counts folds where the filtered arm actually made money. On the noise control the two diverge, and only the second one means anything: filtering a rule that pays nothing but costs always improves it.

| Market | Seed | Folds | Acted | primary_only | primary_plus_meta | Improved | Profitable | Median delta | Delta SD |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| signal | 42 | 6 | 6 | -68.17% | +95.51% | 5/6 | 6/6 | +0.322 | 0.173 |
| signal | 43 | 6 | 6 | -8.41% | +161.55% | 5/6 | 6/6 | +0.209 | 0.172 |
| signal | 44 | 6 | 6 | -67.09% | +113.30% | 6/6 | 6/6 | +0.307 | 0.153 |
| noise | 42 | 6 | 5 | -66.58% | -3.69% | 5/6 | 2/6 | +0.141 | 0.118 |
| noise | 43 | 6 | 4 | -53.28% | -12.53% | 6/6 | 1/6 | +0.072 | 0.094 |
| noise | 44 | 6 | 4 | -68.09% | -11.52% | 6/6 | 0/6 | +0.137 | 0.066 |

## Predictive metrics (test blocks only)

PR-AUC is the headline because the meta-label is imbalanced after costs; ROC-AUC is secondary. `pr_auc_lift` divides PR-AUC by the block's base rate, so 1.0 means the model is worth exactly nothing.

| Market | Seed | PR-AUC | PR-AUC lift | ROC-AUC | Brier | Meta Sharpe |
|---|---:|---:|---:|---:|---:|---:|
| signal | 42 | 0.618 | 1.278 | 0.686 | 0.226 | +4.45 |
| signal | 43 | 0.687 | 1.219 | 0.666 | 0.226 | +7.91 |
| signal | 44 | 0.624 | 1.221 | 0.647 | 0.234 | +4.67 |
| noise | 42 | 0.502 | 1.045 | 0.534 | 0.266 | -0.93 |
| noise | 43 | 0.526 | 1.014 | 0.501 | 0.272 | -0.22 |
| noise | 44 | 0.479 | 0.993 | 0.496 | 0.256 | -1.29 |

## Model competition

Logistic regression is the interpretable baseline and is reported whether it wins or loses. The winner is chosen on validation economics only; AUC never selects a model.

| Market | Model | Folds won |
|---|---|---:|
| signal | `lightgbm` | 5 |
| signal | `logistic_regression` | 9 |
| signal | `random_forest` | 4 |
| noise | `lightgbm` | 5 |
| noise | `logistic_regression` | 4 |
| noise | `random_forest` | 9 |

## Per fold

| Market | Seed | Fold | Model | Abstained | Train events | Test events | Signal rate | primary_only | primary_plus_meta | PR-AUC | ROC-AUC |
|---|---:|---:|---|---|---:|---:|---:|---:|---:|---:|---:|
| signal | 42 | 0 | logistic_regression | no | 719 | 249 | 0.53 | -32.26% | +12.90% | 0.621 | 0.710 |
| signal | 42 | 1 | random_forest | no | 969 | 249 | 0.35 | -15.89% | +10.98% | 0.615 | 0.663 |
| signal | 42 | 2 | lightgbm | no | 1219 | 249 | 0.47 | -16.91% | +0.78% | 0.534 | 0.551 |
| signal | 42 | 3 | logistic_regression | no | 1470 | 249 | 0.40 | -27.36% | +13.66% | 0.598 | 0.688 |
| signal | 42 | 4 | logistic_regression | no | 1719 | 249 | 0.56 | -22.05% | +15.45% | 0.627 | 0.684 |
| signal | 42 | 5 | lightgbm | no | 1969 | 247 | 0.16 | +18.75% | +17.99% | 0.762 | 0.720 |
| signal | 43 | 0 | logistic_regression | no | 719 | 248 | 0.57 | +19.51% | +37.22% | 0.708 | 0.694 |
| signal | 43 | 1 | random_forest | no | 970 | 249 | 0.12 | -23.10% | +9.74% | 0.676 | 0.699 |
| signal | 43 | 2 | logistic_regression | no | 1220 | 249 | 0.16 | -6.15% | +1.62% | 0.629 | 0.630 |
| signal | 43 | 3 | random_forest | no | 1470 | 249 | 0.39 | -11.59% | +23.65% | 0.699 | 0.699 |
| signal | 43 | 4 | lightgbm | no | 1719 | 249 | 0.29 | +27.41% | +16.84% | 0.699 | 0.634 |
| signal | 43 | 5 | lightgbm | no | 1970 | 247 | 0.26 | -5.74% | +18.30% | 0.661 | 0.638 |
| signal | 44 | 0 | logistic_regression | no | 719 | 249 | 0.13 | -2.79% | +6.40% | 0.629 | 0.642 |
| signal | 44 | 1 | lightgbm | no | 970 | 249 | 0.28 | -35.33% | +7.51% | 0.567 | 0.645 |
| signal | 44 | 2 | logistic_regression | no | 1219 | 249 | 0.47 | +1.17% | +15.55% | 0.637 | 0.618 |
| signal | 44 | 3 | random_forest | no | 1469 | 249 | 0.53 | -16.70% | +17.13% | 0.620 | 0.660 |
| signal | 44 | 4 | logistic_regression | no | 1719 | 248 | 0.46 | -7.96% | +19.52% | 0.633 | 0.649 |
| signal | 44 | 5 | logistic_regression | no | 1969 | 247 | 0.28 | -32.51% | +15.27% | 0.595 | 0.664 |
| noise | 42 | 0 | random_forest | no | 719 | 249 | 0.60 | +10.25% | +8.52% | 0.600 | 0.534 |
| noise | 42 | 1 | lightgbm | no | 970 | 249 | 0.42 | -10.14% | +1.35% | 0.585 | 0.564 |
| noise | 42 | 2 | logistic_regression | no | 1219 | 248 | 0.17 | -11.12% | -3.31% | 0.502 | 0.490 |
| noise | 42 | 3 | random_forest | no | 1469 | 249 | 0.67 | -23.34% | -6.55% | 0.495 | 0.538 |
| noise | 42 | 4 | random_forest | no | 1718 | 249 | 0.06 | -32.97% | -3.08% | 0.440 | 0.480 |
| noise | 42 | 5 | lightgbm | yes | 1970 | 247 | 0.00 | -26.14% | +0.00% | n/a | n/a |
| noise | 43 | 0 | lightgbm | no | 720 | 248 | 0.10 | -1.81% | +0.21% | 0.558 | 0.501 |
| noise | 43 | 1 | random_forest | no | 969 | 250 | 0.87 | -14.52% | -2.77% | 0.552 | 0.560 |
| noise | 43 | 2 | random_forest | no | 1218 | 249 | 0.18 | -9.91% | -9.58% | 0.500 | 0.455 |
| noise | 43 | 3 | logistic_regression | yes | 1470 | 248 | 0.00 | -15.75% | +0.00% | n/a | n/a |
| noise | 43 | 4 | lightgbm | no | 1719 | 249 | 0.08 | -24.70% | -0.70% | 0.495 | 0.500 |
| noise | 43 | 5 | logistic_regression | yes | 1969 | 247 | 0.00 | -2.62% | +0.00% | n/a | n/a |
| noise | 44 | 0 | random_forest | yes | 720 | 249 | 0.00 | -15.42% | +0.00% | n/a | n/a |
| noise | 44 | 1 | lightgbm | no | 969 | 249 | 0.08 | -17.53% | -1.20% | 0.471 | 0.461 |
| noise | 44 | 2 | logistic_regression | no | 1219 | 249 | 0.18 | -31.60% | -4.36% | 0.466 | 0.506 |
| noise | 44 | 3 | random_forest | no | 1469 | 250 | 0.04 | -12.96% | -1.07% | 0.512 | 0.491 |
| noise | 44 | 4 | random_forest | no | 1719 | 249 | 0.39 | -14.16% | -5.35% | 0.487 | 0.502 |
| noise | 44 | 5 | random_forest | yes | 1970 | 247 | 0.00 | -10.47% | +0.00% | n/a | n/a |

## What this does not establish

- No claim about BTC, ETH or any traded market. The data is generated.
- No operational candidate. The primary rule here is a synthetic momentum rule chosen to leave room for a filter, not a strategy that passed a gate.
- The planted edge is stationary and known. Real edges are neither, so the measured improvement is an upper bound on what the same machinery would achieve on real data.
- The frozen holdout was not read, and no exchange endpoint was contacted.
