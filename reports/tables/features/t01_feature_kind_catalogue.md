**Table — Complete registry of feature kinds with family, pack, availability and leakage risk.**

| kind | family | pack | availability | parameterised | requires_context | is_proxy | leakage_risk |
| --- | --- | --- | --- | --- | --- | --- | --- |
| atr | volatility | core | close t | True | False | False | low (uses current bar range + previous close) |
| basis | derivatives | extended | close t (mark/index aligned to bar grid) | False | True | True | low (contemporaneous mark vs index; scale-free) |
| cum_return | returns | core | close t | False | False | False | low (expanding sum of past log returns) |
| dow_cyclical | time | extended | open t (known ex-ante) | False | False | False | none (calendar clock, known in advance) |
| ema | trend | core | close t | True | False | False | low (recursive past-only mean) |
| funding_rate | derivatives | extended | as-of past (funding known before it is charged) | False | True | False | low (backward as-of join; never forward) |
| hour_cyclical | time | extended | open t (known ex-ante) | False | False | False | none (calendar clock, known in advance) |
| log_return | returns | core | close t | False | False | False | low (past-only difference) |
| ma_distance | trend | core | close t | True | False | False | low (ratio of two trailing means; scale-free) |
| momentum | momentum | core | close t | True | False | False | low (past-only difference) |
| oi_change | derivatives | extended | as-of past (open interest snapshot <= open_time) | True | True | False | low (backward as-of join + past-only difference) |
| price_dist_sma | trend | core | close t | True | False | False | low (trailing mean; scale-free) |
| range_norm | range | core | close t | False | False | False | low (current-bar range, scale-free) |
| rel_volume | volume | extended | close t | True | False | False | low (ratio to trailing mean; mean=0 -> null) |
| roll_std | mean_reversion | core | close t | True | False | False | low (trailing std of the price level) |
| rvol | volatility | core | close t | True | False | False | low (trailing std of past returns) |
| sma | trend | core | close t | True | False | False | low (trailing mean) |
| taker_buy_imbalance | order_flow | experimental | close t (contextual microstructure) | True | False | True | high if contemporaneous -> must be lagged >= 1 bar |
| taker_buy_ratio | order_flow | experimental | close t (contextual microstructure) | True | False | True | high if contemporaneous -> must be lagged >= 1 bar |
| true_range | range | core | close t | False | False | False | low (current-bar range + previous close) |
| volume_zscore | volume | extended | close t | True | False | False | low (trailing mean/std; std=0 -> null) |
| xasset_corr | cross_asset | extended | close t (peer bar closes simultaneously) | True | True | False | low (trailing correlation of past returns) |
| xasset_rel_momentum | cross_asset | extended | close t (peer bar closes simultaneously) | True | True | False | low (exact join; past-only momentum difference) |
| xasset_rel_return | cross_asset | extended | close t (peer bar closes simultaneously) | False | True | False | low (exact join; peer bar closes with own bar) |
| zscore | trend | core | close t | True | False | False | low (trailing mean/std; std=0 -> null) |
