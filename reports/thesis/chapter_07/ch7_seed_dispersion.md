# Seed dispersion per family-asset cell (RS engine, full studies)

Aggregations, stated exactly: `sharpe_concat_ann_*` summarise, across seeds, the annualised Sharpe of each seed's concatenated OOS test series (`study_robustness.json` -> `per_run.strategy.sharpe`); `mean_fold_test_sharpe_mean_across_seeds` averages, across seeds, each seed's mean of the 15 frozen-winner fold-test Sharpes (`*_fold_winners.json`). The two aggregations differ by construction (bars-weighted vs folds-weighted); never compare one against the other. Ranges are dispersion across seeds, not confidence intervals. Benchmark = buy & hold over the same OOS window.

| round | family | symbol | n_seeds | sharpe_concat_ann_mean_across_seeds | sharpe_concat_ann_sd_across_seeds | sharpe_concat_ann_min | sharpe_concat_ann_max | mean_fold_test_sharpe_mean_across_seeds | total_return_net_mean_across_seeds | seeds_positive_return | bh_total_return_same_window | n_trades_mean_across_seeds |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| CRT_INTRADAY_V1 | crt_htf_range_reversal | BTCUSDT | 10 | -0.290 | 0.533 | -1.466 | 0.230 | -0.329 | -0.128 | 3 | 0.523 | 603.000 |
| CRT_INTRADAY_V1 | crt_htf_range_reversal | ETHUSDT | 10 | -0.570 | 0.589 | -1.389 | 0.467 | -0.568 | -0.280 | 1 | -0.219 | 760.900 |
| CRT_INTRADAY_V1 | crt_three_candle_model | BTCUSDT | 10 | -0.732 | 0.365 | -1.468 | -0.154 | -0.543 | -0.340 | 0 | 0.523 | 490.600 |
| CRT_INTRADAY_V1 | crt_three_candle_model | ETHUSDT | 10 | -0.104 | 0.241 | -0.411 | 0.249 | -0.166 | -0.119 | 3 | -0.219 | 481.500 |
| CRT_INTRADAY_V1 | double_sweep_reversal | BTCUSDT | 10 | 0.043 | 0.285 | -0.392 | 0.576 | -0.119 | 0.002 | 5 | 0.523 | 150.100 |
| CRT_INTRADAY_V1 | double_sweep_reversal | ETHUSDT | 10 | 0.035 | 0.338 | -0.463 | 0.475 | -0.188 | -0.001 | 6 | -0.219 | 167.100 |
| CRT_INTRADAY_V1 | failed_breakout_reversal | BTCUSDT | 10 | 0.091 | 0.218 | -0.214 | 0.351 | -0.139 | 0.017 | 6 | 0.523 | 327.500 |
| CRT_INTRADAY_V1 | failed_breakout_reversal | ETHUSDT | 10 | -0.478 | 0.289 | -0.848 | 0.013 | -0.357 | -0.182 | 0 | -0.219 | 308.200 |
| CRT_INTRADAY_V1 | opening_range_breakout_retest | BTCUSDT | 10 | -0.469 | 0.237 | -0.798 | -0.079 | -0.723 | -0.070 | 0 | 0.523 | 127.000 |
| CRT_INTRADAY_V1 | opening_range_breakout_retest | ETHUSDT | 10 | -0.556 | 0.376 | -1.176 | 0.074 | -0.483 | -0.098 | 1 | -0.219 | 113.600 |
| CRT_INTRADAY_V1 | pdh_reclaim_short | BTCUSDT | 10 | 0.016 | 0.412 | -0.547 | 0.504 | 0.153 | -0.006 | 5 | 0.523 | 231.400 |
| CRT_INTRADAY_V1 | pdh_reclaim_short | ETHUSDT | 10 | -0.500 | 0.068 | -0.607 | -0.383 | -0.207 | -0.236 | 0 | -0.219 | 371.400 |
| CRT_INTRADAY_V1 | pdl_reclaim_long | BTCUSDT | 10 | 0.471 | 0.135 | 0.300 | 0.622 | 0.163 | 0.143 | 10 | 0.523 | 248.700 |
| CRT_INTRADAY_V1 | pdl_reclaim_long | ETHUSDT | 10 | -0.384 | 0.112 | -0.523 | -0.127 | -0.295 | -0.223 | 0 | -0.219 | 363.200 |
| CRT_INTRADAY_V1 | session_liquidity_sweep | BTCUSDT | 10 | -0.229 | 0.290 | -0.712 | 0.165 | -0.454 | -0.057 | 3 | 0.523 | 246.500 |
| CRT_INTRADAY_V1 | session_liquidity_sweep | ETHUSDT | 10 | -0.481 | 0.311 | -0.907 | 0.013 | -0.911 | -0.126 | 0 | -0.219 | 194.100 |
| CRT_INTRADAY_V1 | session_range_rotation | BTCUSDT | 10 | -0.334 | 0.290 | -0.623 | 0.309 | -0.723 | -0.040 | 1 | 0.523 | 72.300 |
| CRT_INTRADAY_V1 | session_range_rotation | ETHUSDT | 10 | -0.720 | 0.366 | -1.115 | -0.071 | -0.576 | -0.112 | 0 | -0.219 | 102.500 |
| R2 | momentum | BTCUSDT | 10 | -0.221 | 0.220 | -0.626 | 0.019 | -0.713 | -0.322 | 0 | 0.523 | 577.900 |
| R2 | momentum | ETHUSDT | 10 | -0.327 | 0.169 | -0.712 | -0.097 | -0.494 | -0.474 | 0 | -0.219 | 456.400 |
| R3 | BTC_ETH_confirmation | BTCUSDT | 10 | -0.504 | 0.299 | -0.813 | 0.215 | -0.654 | -0.599 | 1 | 0.523 | 848.200 |
| R3 | BTC_ETH_confirmation | ETHUSDT | 10 | -0.440 | 0.347 | -1.073 | -0.026 | -0.492 | -0.699 | 0 | -0.219 | 960.700 |
| R3 | breakout | BTCUSDT | 10 | -0.749 | 0.202 | -1.183 | -0.437 | -1.185 | -0.161 | 0 | 0.523 | 328.200 |
| R3 | breakout | ETHUSDT | 10 | -1.066 | 0.145 | -1.337 | -0.879 | -1.437 | -0.261 | 0 | -0.219 | 443.600 |
| R3 | funding | BTCUSDT | 10 | -0.267 | 0.177 | -0.549 | -0.062 | -0.301 | -0.405 | 0 | 0.523 | 358.000 |
| R3 | funding | ETHUSDT | 10 | -0.287 | 0.386 | -0.789 | 0.530 | -0.240 | -0.471 | 1 | -0.219 | 463.900 |
| R3 | mean_reversion | BTCUSDT | 10 | -0.582 | 0.339 | -1.254 | -0.191 | -0.504 | -0.609 | 0 | 0.523 | 436.700 |
| R3 | mean_reversion | ETHUSDT | 10 | -0.863 | 0.183 | -1.265 | -0.653 | -0.599 | -0.799 | 0 | -0.219 | 465.800 |
| R3 | volatility_breakout | BTCUSDT | 10 | 0.116 | 0.468 | -0.537 | 0.835 | -0.282 | 0.109 | 6 | 0.523 | 245.800 |
| R3 | volatility_breakout | ETHUSDT | 10 | -0.486 | 0.384 | -0.833 | 0.330 | -0.430 | -0.575 | 1 | -0.219 | 297.300 |
| S3 | macro_event_brake | BTCUSDT | 10 | -0.217 | 0.119 | -0.404 | -0.079 | -0.990 | -0.305 | 0 | 0.523 | 383.400 |
| S3 | macro_event_brake | ETHUSDT | 10 | -0.414 | 0.264 | -0.858 | -0.032 | -0.679 | -0.549 | 0 | -0.219 | 421.800 |
