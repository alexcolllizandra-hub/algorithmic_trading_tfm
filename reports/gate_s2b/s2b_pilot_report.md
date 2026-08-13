# Gate S2-B - development pilot (DEV-ONLY)

> **DEVELOPMENT-ONLY EVIDENCE. Gate S2-B is a screen, not a promotion decision. No holdout data was read.**

Batch attempt 1; development-partition consultation 4 (R2, R3, S1, S2).

Primary engine: `random_search` (confirmatory). The genetic algorithm is a secondary diagnostic and decides nothing.

## Per family x asset x seed x engine

| Family | Asset | Seed | Engine | Compounded OOS return | Median fold Sharpe | OOS trades | Folds with trades | Folds return > 0 | Median DSR | Viable |
|---|---|---:|---|---:|---:|---:|---:|---:|---:|---|
| `flow_price_divergence` | BTCUSDT | 42 | random_search | -16.71% | -0.66 | 118 | 10/15 | 3/15 | 0.448 | yes |
| `flow_price_divergence` | BTCUSDT | 42 | genetic_algorithm | -6.95% | 0.00 | 72 | 10/15 | 5/15 | 0.485 | yes |
| `flow_price_divergence` | BTCUSDT | 43 | random_search | +15.51% | 0.06 | 76 | 12/15 | 7/15 | 0.517 | yes |
| `flow_price_divergence` | BTCUSDT | 43 | genetic_algorithm | +14.04% | 0.00 | 86 | 10/15 | 5/15 | 0.478 | yes |
| `flow_price_divergence` | BTCUSDT | 44 | random_search | -14.32% | -0.47 | 134 | 13/15 | 5/15 | 0.499 | yes |
| `flow_price_divergence` | BTCUSDT | 44 | genetic_algorithm | -12.65% | -0.40 | 88 | 12/15 | 4/15 | 0.443 | yes |
| `flow_price_divergence` | ETHUSDT | 42 | random_search | -9.99% | -0.13 | 78 | 9/15 | 3/15 | 0.535 | yes |
| `flow_price_divergence` | ETHUSDT | 42 | genetic_algorithm | +2.99% | 0.00 | 87 | 11/15 | 5/15 | 0.436 | yes |
| `flow_price_divergence` | ETHUSDT | 43 | random_search | -6.63% | 0.00 | 94 | 11/15 | 5/15 | 0.557 | yes |
| `flow_price_divergence` | ETHUSDT | 43 | genetic_algorithm | -9.98% | -0.25 | 72 | 11/15 | 4/15 | 0.452 | yes |
| `flow_price_divergence` | ETHUSDT | 44 | random_search | -9.48% | -0.90 | 110 | 11/15 | 3/15 | 0.518 | yes |
| `flow_price_divergence` | ETHUSDT | 44 | genetic_algorithm | +1.97% | 0.00 | 112 | 11/15 | 5/15 | 0.574 | yes |
| `illiquidity_reversion` | BTCUSDT | 42 | random_search | -48.75% | -0.96 | 471 | 14/15 | 2/15 | 0.349 | yes |
| `illiquidity_reversion` | BTCUSDT | 42 | genetic_algorithm | -26.79% | -0.68 | 426 | 14/15 | 4/15 | 0.334 | yes |
| `illiquidity_reversion` | BTCUSDT | 43 | random_search | -33.09% | -0.17 | 493 | 15/15 | 6/15 | 0.257 | yes |
| `illiquidity_reversion` | BTCUSDT | 43 | genetic_algorithm | -36.25% | -0.40 | 319 | 15/15 | 5/15 | 0.325 | yes |
| `illiquidity_reversion` | BTCUSDT | 44 | random_search | -31.99% | -0.77 | 477 | 15/15 | 4/15 | 0.277 | yes |
| `illiquidity_reversion` | BTCUSDT | 44 | genetic_algorithm | -49.17% | -1.14 | 523 | 15/15 | 2/15 | 0.388 | yes |
| `illiquidity_reversion` | ETHUSDT | 42 | random_search | -56.11% | -0.66 | 442 | 15/15 | 3/15 | 0.383 | yes |
| `illiquidity_reversion` | ETHUSDT | 42 | genetic_algorithm | -59.54% | -1.36 | 610 | 15/15 | 6/15 | 0.332 | yes |
| `illiquidity_reversion` | ETHUSDT | 43 | random_search | -57.31% | -1.64 | 420 | 15/15 | 4/15 | 0.432 | yes |
| `illiquidity_reversion` | ETHUSDT | 43 | genetic_algorithm | +0.88% | 0.82 | 569 | 15/15 | 9/15 | 0.375 | yes |
| `illiquidity_reversion` | ETHUSDT | 44 | random_search | -56.07% | -0.12 | 517 | 14/15 | 6/15 | 0.363 | yes |
| `illiquidity_reversion` | ETHUSDT | 44 | genetic_algorithm | -52.02% | -0.40 | 467 | 15/15 | 4/15 | 0.463 | yes |
| `taker_flow_extreme` | BTCUSDT | 42 | random_search | -7.40% | -0.12 | 406 | 14/15 | 6/15 | 0.367 | yes |
| `taker_flow_extreme` | BTCUSDT | 42 | genetic_algorithm | -1.87% | -0.65 | 440 | 15/15 | 7/15 | 0.308 | yes |
| `taker_flow_extreme` | BTCUSDT | 43 | random_search | +27.51% | 0.35 | 524 | 15/15 | 10/15 | 0.297 | yes |
| `taker_flow_extreme` | BTCUSDT | 43 | genetic_algorithm | -12.77% | -0.65 | 410 | 15/15 | 6/15 | 0.348 | yes |
| `taker_flow_extreme` | BTCUSDT | 44 | random_search | -15.27% | 0.00 | 432 | 14/15 | 7/15 | 0.383 | yes |
| `taker_flow_extreme` | BTCUSDT | 44 | genetic_algorithm | -20.87% | -0.15 | 412 | 14/15 | 6/15 | 0.342 | yes |
| `taker_flow_extreme` | ETHUSDT | 42 | random_search | -18.80% | 0.00 | 430 | 14/15 | 7/15 | 0.331 | yes |
| `taker_flow_extreme` | ETHUSDT | 42 | genetic_algorithm | -23.71% | -0.91 | 623 | 14/15 | 4/15 | 0.410 | yes |
| `taker_flow_extreme` | ETHUSDT | 43 | random_search | +40.81% | 0.56 | 256 | 15/15 | 8/15 | 0.363 | yes |
| `taker_flow_extreme` | ETHUSDT | 43 | genetic_algorithm | -22.40% | -1.38 | 444 | 14/15 | 4/15 | 0.383 | yes |
| `taker_flow_extreme` | ETHUSDT | 44 | random_search | -17.46% | 0.14 | 548 | 15/15 | 8/15 | 0.349 | yes |
| `taker_flow_extreme` | ETHUSDT | 44 | genetic_algorithm | +26.91% | 0.10 | 437 | 15/15 | 8/15 | 0.346 | yes |

## Partial-signal criterion (the only decision S2-B may make)

P1 positive compounded net OOS return on a majority of seeds; P2 at least 5 OOS trades on each such seed; P3 the positive result spans more than one fold. Engine: `random_search`.

| Family | Asset | Seeds meeting all conditions | Required | Fires |
|---|---|---|---:|---|
| `flow_price_divergence` | BTCUSDT | 43 | 2 | no |
| `flow_price_divergence` | ETHUSDT | none | 2 | no |
| `illiquidity_reversion` | BTCUSDT | none | 2 | no |
| `illiquidity_reversion` | ETHUSDT | none | 2 | no |
| `taker_flow_extreme` | BTCUSDT | 43 | 2 | no |
| `taker_flow_extreme` | ETHUSDT | 43 | 2 | no |

**Any family fires: NO.**

## Probability of backtest overfitting (common candidate set)

CSCV over a common candidate set of configurations drawn from the frozen space and evaluated across contiguous development blocks (gate_s2_batch_01.md section 8). This is what S1-B could not do.

| Family | Asset | Configurations | Blocks | PBO | Median block Sharpe |
|---|---|---:|---:|---:|---:|
| `taker_flow_extreme` | BTCUSDT | 120 | 8 | 0.029 | -0.57 |
| `illiquidity_reversion` | BTCUSDT | 120 | 8 | 0.057 | -0.93 |
| `flow_price_divergence` | BTCUSDT | 120 | 8 | 0.600 | +0.00 |
| `taker_flow_extreme` | ETHUSDT | 120 | 8 | 0.286 | -0.38 |
| `illiquidity_reversion` | ETHUSDT | 120 | 8 | 0.300 | -0.77 |
| `flow_price_divergence` | ETHUSDT | 120 | 8 | 0.357 | +0.00 |

Scored window: bars from 2021-12-26T02:00:00+00:00 onward (35205 of 52608 development bars). The frozen space includes a regime gate, so the candidates need a regime label; the `threshold` model is fitted only on the first walk-forward training window ([2020-01-01T00:00:00+00:00, 2021-12-26T02:00:00+00:00)) and applied forward. Earlier bars would carry labels estimated from their own future, so they warm the rolling statistics up and are excluded from scoring. This narrows the frozen design's *whole development partition* to its causal part; the change is conservative and identical for all configurations.

## Multiple-testing accounting

Benjamini-Hochberg at alpha = 0.05 over the three families on **BTCUSDT** (median across seeds of the one-sided bootstrap p-values, null: the family earns nothing):

| Family | p-value | Rejected under BH |
|---|---:|---|
| `flow_price_divergence` | 0.8675 | no |
| `illiquidity_reversion` | 0.9665 | no |
| `taker_flow_extreme` | 0.5995 | no |

Benjamini-Hochberg at alpha = 0.05 over the three families on **ETHUSDT** (median across seeds of the one-sided bootstrap p-values, null: the family earns nothing):

| Family | p-value | Rejected under BH |
|---|---:|---|
| `flow_price_divergence` | 0.6900 | no |
| `illiquidity_reversion` | 0.9815 | no |
| `taker_flow_extreme` | 0.6165 | no |

Hansen SPA and White Reality Check across the three families (benchmark = flat), per asset and seed:

| Asset | Seed | Aligned OOS bars | SPA statistic | SPA p | RC statistic | RC p |
|---|---:|---:|---:|---:|---:|---:|
| BTCUSDT | 42 | 30226 | 0.000 | 1.0000 | -0.001 | 0.9845 |
| BTCUSDT | 43 | 30226 | 1.325 | 0.2580 | 0.002 | 0.3030 |
| BTCUSDT | 44 | 30226 | 0.000 | 1.0000 | -0.001 | 0.9940 |
| ETHUSDT | 42 | 23749 | 0.000 | 1.0000 | -0.000 | 0.9240 |
| ETHUSDT | 43 | 28067 | 1.646 | 0.1235 | 0.003 | 0.1440 |
| ETHUSDT | 44 | 25908 | 0.000 | 1.0000 | -0.000 | 0.9465 |

These correct for selection across the three S2 families only. They do **not** correct for the evaluations spent inside each family (see the deflated Sharpe), the three seeds, the two assets, or the four cumulative development consultations.

**Not covered by any correction above:** the cumulative burden of four development-partition consultations (R2, R3, S1, S2); see batch_attempt and development_partition_consultation.

## What this table is not

S2-B may authorise *preparing* an S2-C study and nothing else. The performance columns are descriptive: at 25 evaluations per fold they cannot evaluate the pre-registered promotion criteria C1-C6, which are defined over 10 seeds and both assets in S2-C. No family is promoted or rejected here, and no holdout data was read.
