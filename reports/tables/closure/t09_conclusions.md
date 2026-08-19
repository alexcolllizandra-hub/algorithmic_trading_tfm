**Table — Claims the study supports, with their evidential basis and scope limits.**

| id | claim | strength | basis | scope_limit |
| --- | --- | --- | --- | --- |
| C1 | No strategy family in this study has a demonstrable edge on BTC/ETH perpetuals at 1h | Strong | 13 families, 284 units, smallest raw p-value 0.345 before any correction | 1h timeframe, 2020-2025, these two assets, these rule families |
| C2 | The conclusion is invariant to how the number of hypotheses is counted | Strong | t05: 4 counting conventions spanning 13..496,500 tests, none produces a survivor | Applies to the family-level tests actually performed |
| C3 | In-sample selection carries essentially no out-of-sample information | Strong | PBO = 0.486 over 70 splits; deflated Sharpe implies the best family is spurious with probability 0.86 | Measured on this study's configuration set |
| C4 | Regime conditioning does not rescue any family | Moderate | 65 cells, 0 survivors after correction; p-value histogram consistent with the global null | Conditioning reduces power; weak narrow-regime effects could be missed |
| C5 | An evolutionary search offers no advantage over Random Search here | Moderate | Notebook 04: budget parity verified; 1 of 5 families nominally significant, consistent with chance across five tests | Spaces of this size; says nothing about much larger spaces |
| C6 | The apparatus itself is sound, so the negative is about the market and not the tooling | Strong | Notebook 02: causality guarantees G1-G7 pass on real data; notebook 03: execution, cost and fold-geometry guards verified and failing closed | Costs remain provisional (ADR 0005) |
