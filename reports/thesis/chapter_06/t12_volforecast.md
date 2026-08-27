**Table — Volatility-forecasting annex: out-of-sample QLIKE and MSE of naive, HAR and LSTM forecasts of 24h-ahead log realized variance, walk-forward over the development period.**

| symbol | model | qlike | mse_log_rv | r2_oos_vs_naive |
| --- | --- | --- | --- | --- |
| BTCUSDT | naive (random walk) | 0.922473 | 0.315333 | 0 |
| BTCUSDT | HAR | 0.507307 | 0.218533 | 0.306976 |
| BTCUSDT | LSTM (mean of 3 seeds) | 0.488621 | 0.224011 | 0.289604 |
| ETHUSDT | naive (random walk) | 0.737295 | 0.258214 | 0 |
| ETHUSDT | HAR | 0.46932 | 0.182569 | 0.292957 |
| ETHUSDT | LSTM (mean of 3 seeds) | 0.427691 | 0.181257 | 0.298035 |
