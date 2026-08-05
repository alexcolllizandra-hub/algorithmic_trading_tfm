# Data provenance & authenticity audit

- Generated: 2026-08-04T19:02:22.712824+00:00
- Holdout start (frozen, inaccessible): **2026-01-01T00:00:00+00:00**
- Datasets audited: 14  |  REAL_HISTORICAL: 14  |  SYNTHETIC_FIXTURE: 0  |  with issues: 0

| dataset | class | provider | tf | rows | min ts | max ts | checksum | dups | gaps | crosses holdout | ok |
|---|---|---|---|---|---|---|---|---|---|---|---|
| binance_um_BTCUSDT_fundingRate | REAL_HISTORICAL | binance_vision | - | 7119 | 2020-01-01T00:00:00+00:00 | 2026-06-30T16:00:00.005000+00:00 | OK | 0 | None | True | YES |
| binance_um_BTCUSDT_klines_15m_development | REAL_HISTORICAL | binance_vision | 15m | 210432 | 2020-01-01T00:00:00+00:00 | 2025-12-31T23:45:00+00:00 | OK | 0 | 0 | False | YES |
| binance_um_BTCUSDT_klines_15m_holdout | REAL_HISTORICAL | binance_vision | 15m | 17376 | 2026-01-01T00:00:00+00:00 | 2026-06-30T23:45:00+00:00 | OK | 0 | 0 | True | YES |
| binance_um_BTCUSDT_klines_1h_development | REAL_HISTORICAL | binance_vision | 1h | 52608 | 2020-01-01T00:00:00+00:00 | 2025-12-31T23:00:00+00:00 | OK | 0 | 0 | False | YES |
| binance_um_BTCUSDT_klines_1h_holdout | REAL_HISTORICAL | binance_vision | 1h | 4344 | 2026-01-01T00:00:00+00:00 | 2026-06-30T23:00:00+00:00 | OK | 0 | 0 | True | YES |
| binance_um_BTCUSDT_klines_5m | REAL_HISTORICAL | binance_vision | 5m | 683424 | 2020-01-01T00:00:00+00:00 | 2026-06-30T23:55:00+00:00 | OK | 0 | 0 | True | YES |
| binance_um_BTCUSDT_markPriceKlines_5m | REAL_HISTORICAL | binance_vision | 5m | 680818 | 2020-01-01T00:00:00+00:00 | 2026-06-30T23:55:00+00:00 | OK | 0 | 2606 | True | YES |
| binance_um_ETHUSDT_fundingRate | REAL_HISTORICAL | binance_vision | - | 7119 | 2020-01-01T00:00:00+00:00 | 2026-06-30T16:00:00.005000+00:00 | OK | 0 | None | True | YES |
| binance_um_ETHUSDT_klines_15m_development | REAL_HISTORICAL | binance_vision | 15m | 210432 | 2020-01-01T00:00:00+00:00 | 2025-12-31T23:45:00+00:00 | OK | 0 | 0 | False | YES |
| binance_um_ETHUSDT_klines_15m_holdout | REAL_HISTORICAL | binance_vision | 15m | 17376 | 2026-01-01T00:00:00+00:00 | 2026-06-30T23:45:00+00:00 | OK | 0 | 0 | True | YES |
| binance_um_ETHUSDT_klines_1h_development | REAL_HISTORICAL | binance_vision | 1h | 52608 | 2020-01-01T00:00:00+00:00 | 2025-12-31T23:00:00+00:00 | OK | 0 | 0 | False | YES |
| binance_um_ETHUSDT_klines_1h_holdout | REAL_HISTORICAL | binance_vision | 1h | 4344 | 2026-01-01T00:00:00+00:00 | 2026-06-30T23:00:00+00:00 | OK | 0 | 0 | True | YES |
| binance_um_ETHUSDT_klines_5m | REAL_HISTORICAL | binance_vision | 5m | 683424 | 2020-01-01T00:00:00+00:00 | 2026-06-30T23:55:00+00:00 | OK | 0 | 0 | True | YES |
| binance_um_ETHUSDT_markPriceKlines_5m | REAL_HISTORICAL | binance_vision | 5m | 682545 | 2020-01-01T00:00:00+00:00 | 2026-06-30T23:55:00+00:00 | OK | 0 | 879 | True | YES |
