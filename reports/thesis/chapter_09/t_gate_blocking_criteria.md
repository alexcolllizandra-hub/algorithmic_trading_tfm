# Gate R3 positive control: what blocks the replications that are not promoted

| scaffold | target_sharpe | n_replications | n_blocked | most_blocking_criterion | most_blocking_share | most_frequent_rejection |
|---|---|---|---|---|---|---|
| volatility_breakout | 0.000 | 50 | 50 | ETHUSDT: survives_drop_top_trades | 1.000 | ETHUSDT: no_bootstrap_ci_excludes_zero |
| volatility_breakout | 0.300 | 50 | 50 | ETHUSDT: survives_drop_top_trades | 1.000 | ETHUSDT: no_bootstrap_ci_excludes_zero |
| volatility_breakout | 0.500 | 50 | 50 | ETHUSDT: survives_drop_top_trades | 1.000 | BTCUSDT: no_bootstrap_ci_excludes_zero |
| volatility_breakout | 1.000 | 50 | 43 | ETHUSDT: bootstrap_sharpe_ci_excludes_zero | 0.744 |  |
| momentum | 0.000 | 50 | 50 | ETHUSDT: survives_drop_top_trades | 1.000 | ETHUSDT: no_bootstrap_ci_excludes_zero |
| momentum | 0.300 | 50 | 50 | ETHUSDT: survives_drop_top_trades | 1.000 | ETHUSDT: no_bootstrap_ci_excludes_zero |
| momentum | 0.500 | 50 | 50 | ETHUSDT: bootstrap_sharpe_ci_excludes_zero | 1.000 | BTCUSDT: no_bootstrap_ci_excludes_zero |
| momentum | 1.000 | 50 | 39 | BTCUSDT: bootstrap_sharpe_ci_excludes_zero | 0.769 |  |
