# CRT_INTRADAY_V1 gate summary (derived; for CHAPTER 7)

Derived from the nine per-family `study_robustness.json` files under
`artifacts/runs/crt_v1_budget100/` (full 2 assets x 10 seeds x 15 folds,
budget 100/fold/engine, RS confirmatory; same contract as R3).
Study-level Holm/BH/DSR/PBO for this round: NOT COMPUTED (the 13-family
closure predates CRT and was not extended).

| Family | Symbol | C1 seeds+ | C2 CI>0 | C3 2x costs | C4 >B&H | Promoted | Mean OOS Sharpe (RS) |
|---|---|---|---|---|---|---|---|
| crt_htf_range_reversal | BTC | 3/10 | 0/10 | 0/10 | 0/10 | NO | -0.329 |
| crt_htf_range_reversal | ETH | 1/10 | 0/10 | 0/10 | 4/10 | NO | -0.568 |
| crt_three_candle_model | BTC | 0/10 | 0/10 | 0/10 | 0/10 | NO | -0.543 |
| crt_three_candle_model | ETH | 3/10 | 0/10 | 0/10 | 7/10 | NO | -0.166 |
| double_sweep_reversal | BTC | 5/10 | 0/10 | 1/10 | 0/10 | NO | -0.119 |
| double_sweep_reversal | ETH | 6/10 | 0/10 | 2/10 | 10/10 | NO | -0.188 |
| failed_breakout_reversal | BTC | 6/10 | 0/10 | 0/10 | 0/10 | NO | -0.139 |
| failed_breakout_reversal | ETH | 0/10 | 0/10 | 0/10 | 6/10 | NO | -0.357 |
| opening_range_breakout_retest | BTC | 0/10 | 0/10 | 0/10 | 0/10 | NO | -0.723 |
| opening_range_breakout_retest | ETH | 1/10 | 0/10 | 0/10 | 10/10 | NO | -0.483 |
| pdh_reclaim_short | BTC | 5/10 | 0/10 | 2/10 | 0/10 | NO | 0.153 |
| pdh_reclaim_short | ETH | 0/10 | 0/10 | 0/10 | 3/10 | NO | -0.207 |
| pdl_reclaim_long | BTC | 10/10 | 0/10 | 6/10 | 0/10 | NO | 0.163 |
| pdl_reclaim_long | ETH | 0/10 | 0/10 | 0/10 | 4/10 | NO | -0.295 |
| session_liquidity_sweep | BTC | 3/10 | 0/10 | 0/10 | 0/10 | NO | -0.454 |
| session_liquidity_sweep | ETH | 0/10 | 0/10 | 0/10 | 9/10 | NO | -0.911 |
| session_range_rotation | BTC | 1/10 | 0/10 | 1/10 | 0/10 | NO | -0.723 |
| session_range_rotation | ETH | 0/10 | 0/10 | 0/10 | 10/10 | NO | -0.576 |

Partial signals worth reporting in Chapter 7: `pdl_reclaim_long` BTC
(10/10 positive seeds, 6/10 survive doubled costs, 0/10 bootstrap CI>0;
mean OOS Sharpe +0.163) and `pdh_reclaim_short` BTC (5/10, +0.153).
Verdict: 0 of 18 family x asset cells promoted.