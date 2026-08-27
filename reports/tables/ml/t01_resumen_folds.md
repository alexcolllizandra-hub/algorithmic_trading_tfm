**Table — Every fold of the study: model chosen, decision to act, economics of both arms, and predictive skill where the filter traded.**

| fold | n_test | modelo | actuo | señales | ret_primaria | ret_meta | delta | trades_prim | trades_meta | roc_auc | pr_auc_lift | motivo_abstencion |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | 42 | random_forest | False | 0 | -0.0814346 | 0 | 0.0814346 | 42 | 0 |  |  | no candidate improved net return on validation (best delta -0.0191) |
| 1 | 48 | logistic_regression | True | 0.520833 | -0.0539199 | -0.00658835 | 0.0473316 | 44 | 26 | 0.60087 | 1.13572 |  |
| 2 | 42 | lightgbm | True | 0.214286 | -0.144149 | -0.0137522 | 0.130397 | 42 | 9 | 0.494213 | 1.05992 |  |
| 3 | 22 | lightgbm | False | 0 | -0.0853678 | 0 | 0.0853678 | 22 | 0 |  |  | the filtered arm improved on the primary but still lost money on valid |
