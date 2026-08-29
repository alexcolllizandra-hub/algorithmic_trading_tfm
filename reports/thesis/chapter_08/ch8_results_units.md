# Units and aggregation of every chapter-8 result

| File | Unit of analysis | Seeds mixed? | Aggregation |
|---|---|---|---|
| ch8_observed_seed_metrics | one seed's concatenated OOS record | no | none (observed) |
| ch8_simulation_summary (path_within_seed) | one simulated path within ONE seed | no | quantiles over 1,000 paths per seed |
| ch8_simulation_summary (hierarchical_primary) | one simulated path after a uniform seed pick | yes (declared) | quantiles over 4,000 paths |
| ch8_path_quantiles | equity at decimated bar index | yes | cross-path quantiles per time point |
| ch8_exposure_sensitivity / ch8_breach_probabilities | hierarchical path under r->m*r | yes | probabilities + Wilson 95% + MC SE |
| ch8_method_sensitivity | hierarchical path | yes | quantiles over 2,000 paths per cell |
| ch8_trade_concentration | engine trade within one seed | no | per-seed diagnostics |
| ch8_trade_secondary_bootstraps | engine trade (median seed) | no | quantiles over 1,000 resamples |

All simulated ranges are CONDITIONAL SIMULATION INTERVALS on the observed development record - never confidence intervals on a true edge, and the ten seeds are ten searches over ONE market history, not ten markets.
