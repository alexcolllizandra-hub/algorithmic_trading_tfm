## Table 8.1. Simulation design, uncertainty layers and evaluation units

| layer | what_varies | unit | n | status |
|---|---|---|---|---|
| Search uncertainty | the RS search seed (10 observed seeds) | one seed's OOS record | 10 | observed, frozen in chapter 7 |
| Path uncertainty | temporal resampling within one seed | simulated path (32,385 bars) | 1000 | post-hoc diagnostic (frozen method core) |
| Combined diagnostic | uniform seed pick, then path resample | simulated path | 4000 | post-hoc diagnostic; NOT ten independent markets |

## Table 8.2. Observed OOS characteristics of the selected BTC candidates (RS engine, 10 seeds, 2022-03-31 to 2025-12-09)

| family | seed | total_return_net | sharpe_concat_ann | max_drawdown_pos | mdd_duration_days | time_under_water_share | n_trades |
|---|---|---|---|---|---|---|---|
| pdl_reclaim_long | 278037 | 0.2100 | 0.6217 | 0.1482 | 631.4167 | 0.9896 | 149 |
| pdl_reclaim_long | 341110 | 0.1453 | 0.5025 | 0.0931 | 351.3750 | 0.9902 | 141 |
| pdl_reclaim_long | 605142 | 0.1807 | 0.5969 | 0.0947 | 456.6250 | 0.9898 | 114 |
| pdl_reclaim_long | 671194 | 0.1693 | 0.5587 | 0.0961 | 353.9583 | 0.9897 | 127 |
| pdl_reclaim_long | 683778 | 0.0837 | 0.3017 | 0.0975 | 507.0000 | 0.9906 | 123 |
| pdl_reclaim_long | 692467 | 0.0947 | 0.3593 | 0.1119 | 656.2500 | 0.9905 | 114 |
| pdl_reclaim_long | 693857 | 0.0758 | 0.3001 | 0.0877 | 299.7500 | 0.9908 | 113 |
| pdl_reclaim_long | 707014 | 0.0896 | 0.3234 | 0.1233 | 927.8333 | 0.9906 | 125 |
| pdl_reclaim_long | 765570 | 0.1790 | 0.5407 | 0.0877 | 329.7917 | 0.9900 | 141 |
| pdl_reclaim_long | 891022 | 0.1979 | 0.6091 | 0.0931 | 331.4583 | 0.9901 | 153 |
| volatility_breakout | 278037 | -0.4890 | -0.4571 | 0.5309 | 1189.2917 | 0.9861 | 115 |
| volatility_breakout | 341110 | 0.0560 | 0.2152 | 0.4816 | 600.3333 | 0.9710 | 140 |
| volatility_breakout | 605142 | 0.2577 | 0.3540 | 0.3239 | 537.6667 | 0.9427 | 119 |
| volatility_breakout | 671194 | 0.0739 | 0.2155 | 0.3977 | 635.3750 | 0.9717 | 150 |
| volatility_breakout | 683778 | -0.1297 | 0.0585 | 0.4917 | 1189.2917 | 0.9897 | 168 |
| volatility_breakout | 692467 | 0.1267 | 0.2611 | 0.4455 | 539.2083 | 0.9873 | 140 |
| volatility_breakout | 693857 | 0.8236 | 0.6556 | 0.3576 | 377.9167 | 0.9191 | 129 |
| volatility_breakout | 707014 | -0.5617 | -0.5368 | 0.6804 | 1189.2917 | 0.9139 | 138 |
| volatility_breakout | 765570 | -0.3782 | -0.4392 | 0.5175 | 1189.2917 | 0.9234 | 127 |
| volatility_breakout | 891022 | 1.3144 | 0.8355 | 0.4189 | 293.7917 | 0.9860 | 190 |

## Table 8.3. Conditional bootstrap outcomes under the primary specification (hierarchical, stationary blocks)

| family | block | n_paths | terminal_p05 | terminal_p50 | terminal_p95 | prob_terminal_below_1 | prob_terminal_below_1_mc_se | prob_loss_gt_20 | expected_shortfall_5pct_terminal_return | prob_recovered_peak |
|---|---|---|---|---|---|---|---|---|---|---|
| pdl_reclaim_long | 167 | 4000 | 0.8795 | 1.1420 | 1.5043 | 0.2042 | 0.0064 | 0.0125 | -0.1719 | 0.5430 |
| volatility_breakout | 168 | 4000 | 0.2646 | 0.9617 | 3.7865 | 0.5190 | 0.0079 | 0.4050 | -0.8012 | 0.3075 |

## Table 8.4. Profit concentration and trade-sequence diagnostics (per-seed CSV: ch8_trade_concentration.csv)

| family | n_trades_median | share_top5_median | seeds_positive_after_drop_top5 | win_rate_median | max_consecutive_losses_worst_seed | obs_mdd_pct_in_permutations_median |
|---|---|---|---|---|---|---|
| pdl_reclaim_long | 126.0000 | 0.3113 | 2 | 0.4812 | 10 | 0.3840 |
| volatility_breakout | 139.0000 | 0.5129 | 0 | 0.4132 | 11 | 0.2665 |

## Table 8.5. Capital-breach probabilities across exposure multipliers (hierarchical primary; MC SE and Wilson bounds in ch8_breach_probabilities.csv)

| family | multiplier | 0.9 | 0.8 | 0.7 | 0.5 |
|---|---|---|---|---|---|
| pdl_reclaim_long | 0.2500 | 0.0008 | 0.0000 | 0.0000 | 0.0000 |
| pdl_reclaim_long | 0.5000 | 0.0350 | 0.0000 | 0.0000 | 0.0000 |
| pdl_reclaim_long | 0.7500 | 0.1212 | 0.0070 | 0.0000 | 0.0000 |
| pdl_reclaim_long | 1.0000 | 0.2177 | 0.0297 | 0.0015 | 0.0000 |
| pdl_reclaim_long | 1.2500 | 0.3058 | 0.0658 | 0.0092 | 0.0000 |
| pdl_reclaim_long | 1.5000 | 0.3755 | 0.1140 | 0.0230 | 0.0000 |
| pdl_reclaim_long | 2.0000 | 0.4800 | 0.2135 | 0.0735 | 0.0035 |
| volatility_breakout | 0.2500 | 0.4198 | 0.1585 | 0.0387 | 0.0003 |
| volatility_breakout | 0.5000 | 0.6665 | 0.4215 | 0.2465 | 0.0490 |
| volatility_breakout | 0.7500 | 0.7740 | 0.5847 | 0.4183 | 0.1715 |
| volatility_breakout | 1.0000 | 0.8413 | 0.6863 | 0.5445 | 0.2923 |
| volatility_breakout | 1.2500 | 0.8818 | 0.7565 | 0.6370 | 0.4005 |
| volatility_breakout | 1.5000 | 0.9077 | 0.8097 | 0.7073 | 0.4950 |
| volatility_breakout | 2.0000 | 0.9393 | 0.8798 | 0.8100 | 0.6372 |

## Table 8.6. Sensitivity to bootstrap method and block length

| family | method | block | is_primary | terminal_p05 | terminal_p50 | terminal_p95 | mdd_p95 | prob_terminal_below_1 |
|---|---|---|---|---|---|---|---|---|
| pdl_reclaim_long | stationary | 24 | False | 0.8801 | 1.1325 | 1.5171 | 0.2194 | 0.2120 |
| pdl_reclaim_long | stationary | 167 | True | 0.8812 | 1.1344 | 1.4986 | 0.2202 | 0.2070 |
| pdl_reclaim_long | stationary | 168 | False | 0.8796 | 1.1409 | 1.5002 | 0.2195 | 0.2030 |
| pdl_reclaim_long | stationary | 720 | False | 0.8920 | 1.1427 | 1.4879 | 0.2104 | 0.1885 |
| pdl_reclaim_long | circular_mbb | 24 | False | 0.8768 | 1.1333 | 1.5146 | 0.2254 | 0.2130 |
| pdl_reclaim_long | circular_mbb | 167 | False | 0.8723 | 1.1349 | 1.5166 | 0.2202 | 0.2190 |
| pdl_reclaim_long | circular_mbb | 168 | False | 0.8671 | 1.1355 | 1.5244 | 0.2250 | 0.2090 |
| pdl_reclaim_long | circular_mbb | 720 | False | 0.8930 | 1.1429 | 1.4779 | 0.2122 | 0.2115 |
| volatility_breakout | stationary | 24 | False | 0.2721 | 0.9511 | 3.6321 | 0.7899 | 0.5225 |
| volatility_breakout | stationary | 168 | True | 0.2883 | 0.9691 | 3.5625 | 0.7935 | 0.5130 |
| volatility_breakout | stationary | 720 | False | 0.3000 | 0.9644 | 3.6908 | 0.7878 | 0.5215 |
| volatility_breakout | circular_mbb | 24 | False | 0.2707 | 0.9561 | 3.4686 | 0.7956 | 0.5225 |
| volatility_breakout | circular_mbb | 168 | False | 0.2683 | 0.9732 | 3.4465 | 0.8038 | 0.5150 |
| volatility_breakout | circular_mbb | 720 | False | 0.2551 | 0.9509 | 3.8023 | 0.8054 | 0.5295 |

## Table 8.7. Account-threshold outcomes (ILLUSTRATIVE; frozen notebook-07 prop-firm configs, executed for volatility_breakout only; pdl_reclaim_long NOT EVALUATED under this scenario)

**Table — Published prop-firm rules (mapped 2026-08-19, sources in code) applied to bootstrap paths of the median seed and to coin flips with the same timing and costs.**

| firm | arm | pass_phase1 | pass_both | profit_target | max_total_drawdown | max_daily_loss | source |
| --- | --- | --- | --- | --- | --- | --- | --- |
| breakout_1step_classic | strategy | 0.137 | 0.017 | 0.1 | 0.06 | 0.03 | https://www.kraken.com/learn/breakout-vs-hyrotrader |
| breakout_1step_classic | coin_flip | 0.092 | 0.015 | 0.1 | 0.06 | 0.03 | https://www.kraken.com/learn/breakout-vs-hyrotrader |
| hyrotrader_2step | strategy | 0.178 | 0.033 | 0.1 | 0.06 | 0.04 | https://www.hyrotrader.com/evaluations/ |
| hyrotrader_2step | coin_flip | 0.128 | 0.024 | 0.1 | 0.06 | 0.04 | https://www.hyrotrader.com/evaluations/ |
