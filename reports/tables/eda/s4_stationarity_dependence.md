**Table — Summary Table 4 - ADF/KPSS on log price and log returns, Ljung-Box on raw and squared returns, ARCH-LM (BTC/ETH, 1h, development). Tests are low-powered under structural breaks; statistical significance is NOT economic exploitability.**

| symbol | test | series | statistic | pvalue | null |
| --- | --- | --- | --- | --- | --- |
| BTCUSDT | ADF | log_price | -1.78605 | 0.38741 | unit root (non-stationary) |
| BTCUSDT | ADF | log_return | -31.9488 | 0 | unit root (non-stationary) |
| BTCUSDT | KPSS | log_price | 22.9489 | 0.01 | stationary |
| BTCUSDT | KPSS | log_return | 0.162274 | 0.1 | stationary |
| BTCUSDT | Ljung-Box(l=20) | log_return | 122.893 | 8.28547e-17 | no autocorrelation |
| BTCUSDT | Ljung-Box(l=20) | squared_return | 17273.5 | 0 | no autocorrelation |
| BTCUSDT | ARCH-LM(l=12) | log_return | 4258.21 | 0 | no ARCH effects |
| ETHUSDT | ADF | log_price | -2.90563 | 0.0446972 | unit root (non-stationary) |
| ETHUSDT | ADF | log_return | -32.1473 | 0 | unit root (non-stationary) |
| ETHUSDT | KPSS | log_price | 18.0163 | 0.01 | stationary |
| ETHUSDT | KPSS | log_return | 0.384428 | 0.0838671 | stationary |
| ETHUSDT | Ljung-Box(l=20) | log_return | 87.7442 | 1.83331e-10 | no autocorrelation |
| ETHUSDT | Ljung-Box(l=20) | squared_return | 17277 | 0 | no autocorrelation |
| ETHUSDT | ARCH-LM(l=12) | log_return | 4172.04 | 0 | no ARCH effects |
