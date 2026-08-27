**Table — Main findings of the causal feature layer and the design decisions they constrain.**

| id | finding | evidence | implication |
| --- | --- | --- | --- |
| F1 | Every registered feature satisfies prefix and future-mutation invariance on the real development history | t04: G1/G2 maximum deviation exactly 0 for both assets | Backtest results cannot be explained by look-ahead bias in the predictor layer |
| F2 | Declared warm-up matches observed leading nulls for every column | t03: delta = 0 on all rows | The contract is auditable without reading implementations; fold geometry can be validated against it |
| F3 | A single centred (non-causal) moving average inflates |Sharpe| from 0.63 to 12.4 at identical costs; the sign is a free searchable parameter | t05 / g04: causal -0.63, leaked -16.36, leaked-flipped +12.37, buy-and-hold +0.77 | Causality checks are executed as tests, not asserted in prose; the same check fails immediately on the leaky feature |
| F4 | 14 feature columns span roughly 6.8 independent directions | t07 / g06: effective rank 6.79, 8 components for 90% variance | Multiple-testing corrections must be calibrated on effective, not nominal, dimensionality |
| F5 | Feature dispersion drifts substantially across calendar years | t08 / g07: per-year MAD varies by large factors, notably for volatility columns | Expanding walk-forward with out-of-sample test slices is required; decay is not automatically evidence of overfitting |
| F6 | Funding and cross-asset context are attached by backward as-of join; a forward join would alter most bars | Section 10: backward deviation 0; forward join changes 34,974 bars | Context joins are covered by explicit tests; missing auxiliary inputs raise rather than fabricate |
| F7 | Feature, signal, execution and label timestamps are separated, with a strictly positive execution lag | Section 11: minimum execution lag > 0 in all rows | Next-bar execution is structural, not a parameter that can be relaxed |
