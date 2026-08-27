# Final holdout evaluation — result

> **The frozen holdout was opened once, here.** This is the honest result of the best available candidate. It is not a promoted strategy, and no threshold is attached to it, because nothing was promoted.

**Opened:** 2026-08-13T11:13:37+00:00 · **Commit:** `31c241f8e09ed3555b8d453e486d00a4d486a53c`
**Worktree clean:** False
**Partition evaluated:** holdout

## The candidate, as frozen

`volatility_breakout` on BTCUSDT 1h, random_search, fold 14 winner of each of 10 seeds, equally weighted.

| Seed | Selection fingerprint | Candidate |
|---|---|---|
| 278037 | `f244f3cf7299d1b2` | `volatility_breakout-51490f1dd3f0ecdb` |
| 341110 | `a0ba0f759c44fabe` | `volatility_breakout-f4e656ddcc09d02c` |
| 605142 | `a7ac8714d8be5336` | `volatility_breakout-8f84b5704a432074` |
| 671194 | `ef3f68b360f7beb6` | `volatility_breakout-256ae29759fa4cf4` |
| 683778 | `49167992d0dd0871` | `volatility_breakout-4347b3b8ad6d4ec1` |
| 692467 | `71242cc9028e3313` | `volatility_breakout-98c40d4244fabcad` |
| 693857 | `3506e509f551f01d` | `volatility_breakout-4afdb6177a528274` |
| 707014 | `105d053ba03d9bee` | `volatility_breakout-a8d823dea4f2e3ed` |
| 765570 | `6ceaa524c4ca8a5a` | `volatility_breakout-4c6230f700b51ada` |
| 891022 | `1f3e9f9ed2be5493` | `volatility_breakout-dbf8e9e76441189e` |

## Datasets opened

| Dataset | Rows | SHA-256 | Role |
|---|---:|---|---|
| `binance_um_BTCUSDT_klines_1h_development` | 52,608 | `49250896a17b27d5…` | feature history and regime fit |
| `binance_um_BTCUSDT_klines_1h_holdout` | 4,344 | `dec28172d8089dc7…` | EVALUATION - the frozen holdout |
| `binance_um_BTCUSDT_fundingRate` | 543 | `a85942930e58a2d1…` | funding |

## Result

Window: 2026-01-01 00:00:00+00:00 .. 2026-06-30 22:00:00+00:00 (4,343 bars)

| Metric | Candidate | Buy and hold |
|---|---:|---:|
| Total net return | -12.17% | -33.23% |
| Annualised return | -23.02% | -55.72% |
| Sharpe | -1.34 | -1.51 |
| Sortino | -1.80 | -1.97 |
| Maximum drawdown | -14.40% | -40.32% |
| Annualised volatility | 18.22% | 46.62% |
| Exposure | 99.2% | 100.0% |
| Trades | 281 | — |

Costs actually paid over the window: +2.17% in fees and slippage and +0.12% in funding, +2.29% in total, as a fraction of equity.

### Per seed

| Seed | Total return | Sharpe | Trades |
|---|---:|---:|---:|
| 278037 | -0.19% | -0.12 | 20 |
| 341110 | -34.88% | -1.62 | 1 |
| 605142 | -3.19% | -1.00 | 76 |
| 671194 | -3.92% | -1.07 | 42 |
| 683778 | +1.58% | +1.00 | 26 |
| 692467 | -36.20% | -1.72 | 1 |
| 693857 | +66.73% | +2.46 | 7 |
| 707014 | -36.20% | -1.72 | 1 |
| 765570 | -15.34% | -2.21 | 254 |
| 891022 | -36.20% | -1.72 | 1 |

## Cost model and regime, as frozen

Fees 4.0 bps per side, slippage 1.0 bps per side, funding realized; annualised over 365 days. The regime model was fitted on 52,608 development bars and applied forward; no evaluation bar informed its boundaries.
