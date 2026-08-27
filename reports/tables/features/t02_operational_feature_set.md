**Table — The resolved feature set built by the development pipeline, with declared availability, shift and warm-up.**

| name | kind | family | columns | params | availability | shift | warmup | lookback | pack | proxy |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| log_return | log_return | returns | log_return | - | close t | 0 | 1 | 1 | core | False |
| momentum_12 | momentum | momentum | momentum_12 | window=12 | close t | 0 | 12 | 12 | core | False |
| momentum_24 | momentum | momentum | momentum_24 | window=24 | close t | 0 | 24 | 24 | core | False |
| sma_24 | sma | trend | sma_24 | window=24 | close t | 0 | 23 | 24 | core | False |
| sma_96 | sma | trend | sma_96 | window=96 | close t | 0 | 95 | 96 | core | False |
| price_dist_sma_48 | price_dist_sma | trend | price_dist_sma_48 | window=48 | close t | 0 | 47 | 48 | core | False |
| zscore_48 | zscore | trend | zscore_48 | window=48 | close t | 0 | 47 | 48 | core | False |
| rvol_96 | rvol | volatility | rvol_96 | window=96 | close t | 0 | 96 | 96 | core | False |
| atr_14 | atr | volatility | atr_14 | window=14 | close t | 0 | 13 | 14 | core | False |
| range_norm | range_norm | range | range_norm | - | close t | 0 | 0 | 1 | core | False |
| rel_volume_24 | rel_volume | volume | rel_volume_24 | window=24 | close t | 0 | 23 | 24 | extended | False |
| hour_cyclical | hour_cyclical | time | hour_sin, hour_cos | - | open t (known ex-ante) | 0 | 0 | 1 | extended | False |
| taker_buy_imbalance | taker_buy_imbalance | order_flow | taker_buy_imbalance | lag=1 | close t (contextual microstructure) | 1 | 1 | 1 | experimental | True |
