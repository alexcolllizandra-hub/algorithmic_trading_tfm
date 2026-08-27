**Table — Identical rule, identical bars, identical costs: a trailing versus a centred moving average, in both searchable orientations.**

| variant | sharpe | abs_sharpe | ann_return | max_drawdown | hit_rate | n_trades | final_equity |
| --- | --- | --- | --- | --- | --- | --- | --- |
| causal (trailing) | -0.634245 | 0.634245 | -0.44896 | -0.981464 | 0.471737 | 4043 | 0.0279067 |
| leaky (centred) | -16.3612 | 16.3612 | -1 | -1 | 0.400506 | 7294 | 1.05501e-27 |
| leaky, orientation flipped | 12.3696 | 12.3696 | 1840.04 | -0.336173 | 0.566941 | 7294 | 4.05419e+19 |
| buy and hold | 0.77463 | 0.77463 | 0.334631 | -0.792444 | 0.506881 | 1 | 5.6603 |
