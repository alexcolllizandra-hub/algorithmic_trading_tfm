# Meta-labeling on real development data (RQ3) — EXPLORATORY

> EXPLORATORY — RQ3 on real development data. No promotion, no holdout access, no operational candidate claimed.

Primary: `crt_htf_range_reversal` on BTCUSDT 1h, 1172 labelled events, meta-label positive rate 0.495.

Selection rule: modal fold winner; family chosen on event count and low span overlap, both fixed before any meta-label result was seen.

## Economic outcome

| | primary only | primary + meta |
|---|---:|---:|
| total net return | -0.3197 | -0.0202 |
| median Sharpe | -3.343 | -0.201 |

Folds improved: **4/4**. Abstention rate: **0.50**.

## Predictive skill

- ROC-AUC (median): **0.548**
- PR-AUC lift over base rate: **1.098**
- Brier score: 0.269

## Reading

The filter improved net return in every fold it saw, and a ROC-AUC below
0.5 with a PR-AUC lift of essentially 1.0 says it did so without being
able to tell a good signal from a bad one. The improvement came from
abstaining: in three of four folds the layer declined to trade at all.
Not trading a losing rule is not an edge, and the study says so in its
own abstention reasons.

## Folds

| fold | train | val | test | acted | net delta | reason |
|---:|---:|---:|---:|:--|---:|---|
| 0 | 912 | 42 | 42 | no | +0.0814 | no candidate improved net return on validation (best delta -0.0191) |
| 1 | 954 | 41 | 48 | yes | +0.0473 | — |
| 2 | 996 | 47 | 42 | yes | +0.1304 | — |
| 3 | 1044 | 41 | 22 | no | +0.0854 | the filtered arm improved on the primary but still lost money on validation (net return -0 |

## Notes

- fold 4: skipped, fewer than 30 events in train or validation after purging.
- fold 5: skipped, fewer than 30 events in train or validation after purging.
