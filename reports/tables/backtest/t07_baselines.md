**Table — Fixed baselines repriced on identical bars with identical costs, alongside one hand-specified momentum rule.**

| baseline | sharpe | total_return | max_drawdown | exposure | turnover | final_equity |
| --- | --- | --- | --- | --- | --- | --- |
| always_long | 0.77463 | 4.6603 | -0.792444 | 0.999981 | 1 | 5.6603 |
| ma_crossover | 0.183508 | -0.387547 | -0.768378 | 0.998175 | 1437 | 0.612453 |
| (momentum_crossover_24_96_both) | 0.183508 | -0.387547 | -0.768378 | 0.998175 | 1437 | 0.612453 |
| flat | 0 | 0 | 0 | 0 | 0 | 1 |
| momentum | -1.51055 | -0.99898 | -0.99947 | 0.99943 | 10689 | 0.00102009 |
| mean_reversion | -2.03375 | -0.984091 | -0.98519 | 0.145532 | 4170 | 0.0159092 |
| random_entry | -7.16624 | -1 | -1 | 0.496778 | 39069 | 2.45616e-09 |
