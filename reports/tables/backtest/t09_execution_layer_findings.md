**Table — Findings of the execution, cost and validation layer.**

| id | finding | evidence | implication |
| --- | --- | --- | --- |
| E1 | Execution is delayed by exactly one bar on every observation | position[t] == raw_signal[t-1] on all 52,607 bars; reversals charged 2 units | No decision can be filled at the price that produced it |
| E2 | Net return decomposes exactly into gross, fee, slippage and funding | max residual 3.5e-18 | The cost attribution in t01 is exhaustive, not indicative |
| E3 | Costs consume roughly 60% of the gross return and the result does not survive a doubling of the fee schedule | t01: net = 40% of gross; t02: Sharpe +0.37 at zero cost -> +0.18 at contract -> negative at 2x | Results must be reported across a cost range, and turnover penalised in the objective |
| E4 | Cost drag is explained almost entirely by turnover; only slow parameterisations stay net positive, and none beats buy-and-hold | t03: 14/15 positive gross vs 9/15 positive net; best net Sharpe well below always_long | The viable region of the parameter space is knowable before any search runs |
| E5 | Funding is directional and material: longs pay, shorts receive | t04: net +0.3040 paid (18% of gross); 87% of settlements positive | Funding is mandatory in the engine; omitting it biases long-biased strategies upward |
| E6 | 15 chronological folds with non-overlapping test windows | t05/t06: 0 overlapping test pairs; all folds strictly ordered and disjoint | Fold results are non-overlapping, but not exchangeable (training windows grow) |
| E7 | Every holdout and funding guard raises rather than warning | t08: 3/3 deliberate violations raised | The frozen holdout cannot be reached accidentally from the development path |
