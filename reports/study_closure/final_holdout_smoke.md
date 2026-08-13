# Final holdout evaluation — result

> **SMOKE TEST, NOT A RESULT.** This run evaluated the development partition, whose bars trained and selected the very parameters being replayed. It exists only to prove the machinery works. The numbers below mean nothing and must not be quoted.

**Opened:** 2026-08-13T11:12:22+00:00 · **Commit:** `02b79f1de1415197a0105b3b00d1d48b30d9a890`
**Worktree clean:** False
**Partition evaluated:** development

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
| `binance_um_BTCUSDT_fundingRate` | 6,576 | `a85942930e58a2d1…` | funding |

## Result

Window: 2025-01-01 00:00:00+00:00 .. 2025-12-31 22:00:00+00:00 (8,759 bars)

| Metric | Candidate | Buy and hold |
|---|---:|---:|
| Total net return | -8.66% | -7.16% |
| Annualised return | -8.66% | -7.16% |
| Sharpe | -0.43 | +0.05 |
| Sortino | -0.54 | +0.07 |
| Maximum drawdown | -15.56% | -34.76% |
| Annualised volatility | 17.50% | 44.38% |
| Exposure | 99.6% | 100.0% |
| Trades | 529 | — |

Costs actually paid over the window: +4.48% in fees and slippage and +2.06% in funding, +6.53% in total, as a fraction of equity.

### Per seed

| Seed | Total return | Sharpe | Trades |
|---|---:|---:|---:|
| 278037 | -4.81% | -1.22 | 42 |
| 341110 | -13.86% | -0.11 | 1 |
| 605142 | -17.91% | -2.52 | 206 |
| 671194 | -5.14% | -1.50 | 68 |
| 683778 | -0.48% | -0.10 | 52 |
| 692467 | -17.18% | -0.20 | 1 |
| 693857 | +5.26% | +0.34 | 24 |
| 707014 | -16.13% | -0.18 | 1 |
| 765570 | -26.06% | -2.08 | 476 |
| 891022 | -17.18% | -0.20 | 1 |

## Cost model and regime, as frozen

Fees 4.0 bps per side, slippage 1.0 bps per side, funding realized; annualised over 365 days. The regime model was fitted on 43,848 development bars and applied forward; no evaluation bar informed its boundaries.
