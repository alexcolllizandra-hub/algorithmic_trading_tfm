**Table — Canonical kline schema, dtypes and units**

| column | dtype | meaning |
| --- | --- | --- |
| open_time | Datetime(time_unit='ms', time_zone='UTC') | UTC bar-open timestamp (ms precision) |
| open | Float64 | first trade price in bar (USDT) |
| high | Float64 | max price in bar (USDT) |
| low | Float64 | min price in bar (USDT) |
| close | Float64 | last trade price in bar (USDT) |
| volume | Float64 | traded base volume (BTC/ETH) |
| quote_volume | Float64 | traded quote volume (USDT ~ dollar volume) |
| trade_count | Int64 | number of trades (int) |
| taker_buy_base | Float64 | taker-initiated buy base volume |
| taker_buy_quote | Float64 | taker-initiated buy quote volume (USDT) |
