**Table — Findings of the search and overfitting analysis.**

| id | finding | evidence | implication |
| --- | --- | --- | --- |
| S1 | Space cardinality differs by two orders of magnitude; the shared budget is bounded by the smallest space, so coverage ranges from near-exhaustive to ~1% | t01: coverage 1.1% .. 92.6%; ADR 0014 | The GA had ample room to win on the three large families and did not; only the breakout result carries a small-space caveat |
| S2 | Validation scores are severely optimistic estimates of test performance | t02: mean validation +3.47 vs mean test -0.57; 95% of winners underperform their selection score | A validation-selected number is never reportable as performance |
| S3 | Only about 28% of a validation advantage transfers to the test slice | i02: regression slope +0.277 against an honest 1.0, R^2 0.040 | Ranking candidates by validation Sharpe is mostly ranking them by noise |
| S4 | Realised test Sharpe is flat across validation bins; a higher selection score buys nothing | t04: mean test Sharpe is a small negative number in every well-populated bin, from '1 .. 1.5' through '> 3' | An impressive validation result should not raise confidence at all |
| S5 | Budget parity is exact: both engines spent identical unique evaluations in every fold | t05: [150000, 150000] evaluations; target met in every fold = True | Any engine difference cannot be attributed to unequal search effort |
| S6 | 1 of 5 families has a CI excluding zero - consistent with chance across five tests, and inconsistent in direction across families | t06: ['mean_reversion'] nominally significant; ~0.25 expected under the null | No reliable engine advantage; Random Search remains the default and the GA an equal-budget comparator only |
| S7 | Seed noise rivals market variation on the large-space families | t07: seed-to-fold SD ratio ranges 0.05 .. 1.29; funding exceeds 1.0 | Multiple seeds are mandatory; the unit of inference is symbol x fold, not seed-run |
| S8 | Both engines converge within the first tenth of the budget | t08 / i06: mean best fitness reaches most of its final value early | The remaining budget rediscovers known candidates; the space is the binding constraint |
