# Cost scenarios: how many units and seed runs cross each bar

| scenario | fee_bps_per_side | slippage_bps_per_side | funding_charged | n_units | n_units_mean_return_positive | n_units_majority_positive | n_units_majority_beat_bh | n_seed_runs | n_seed_runs_positive | n_seed_runs_ci_excludes_zero | median_unit_sharpe | best_unit_sharpe |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| taker_4_1 | 4.000 | 1.000 | yes | 22 | 3 | 1 | 1 | 142 | 12 | 0 | -0.463 | 0.116 |
| maker_2_1 | 2.000 | 1.000 | yes | 22 | 3 | 2 | 2 | 142 | 13 | 0 | -0.292 | 0.219 |
| no_fees | 0.000 | 0.000 | yes | 22 | 5 | 5 | 2 | 142 | 25 | 2 | -0.121 | 0.518 |
| gross | 0.000 | 0.000 | no | 22 | 5 | 5 | 1 | 142 | 27 | 2 | -0.093 | 0.536 |
