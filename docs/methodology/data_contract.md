# Data Contract v0.1.0

The single source of truth for **which** market data the thesis uses and
**how** it is processed. The machine-readable form is
[`configs/data_contract.yaml`](../configs/data_contract.yaml); this document
explains the rationale. Any change bumps the `version` and is recorded as an
ADR under [decisions/](decisions/).

## 1. Source and market

- **Exchange:** Binance.
- **Market:** USDT-M (linear) perpetual futures (`um` in the archive).
- **Primary source:** the public bulk archive at `https://data.binance.vision`.
- **Secondary source:** CCXT public endpoints, used **only** to append the most
  recent candles not yet in the archive (it lags real time by ~1 day).

Rationale: the bulk archive offers the deepest, most reproducible free history
(inception ~2019-09), ships SHA-256 `.CHECKSUM` files for integrity, and does
not require API keys.

## 2. Contracts and period

| Symbol | Contract | Nominal listing | 
|--------|----------|-----------------|
| `BTCUSDT` | Bitcoin USDT-M perpetual | 2019-09-08 |
| `ETHUSDT` | Ether USDT-M perpetual | 2019-11-27 |

- **Period:** each contract's inception through the **cutoff** (exclusive).
- **Cutoff:** `2026-07-01`, treated as an **exclusive** upper bound: the last
  ingested 5-minute bar opens at **2026-06-30 23:55 UTC**. Only fully-closed
  prior months are ingested. The exact first bar actually present in the
  archive is discovered at ingestion and recorded per-symbol in its manifest.

## 3. Timeframes

- **Base timeframe:** 5 minutes, downloaded directly.
- **Derived timeframes:** 15 minutes and 1 hour, **constructed by aggregating
  the 5-minute bars** (`open`=first, `high`=max, `low`=min, `close`=last,
  volumes and trade count summed). Derived bars are cross-checked against
  Binance native 15m/1h klines during quality control.

Rationale: building all higher timeframes from one consistent 5-minute source
guarantees internal consistency and a single provenance chain.

## 4. Streams

- **klines** (OHLCV + quote volume, trade count, taker-buy breakdown).
- **fundingRate** (nominal 8-hour interval).
- **markPriceKlines** (5m) for later liquidation/execution realism.
- **openInterest is excluded:** it is only available for recent history via the
  REST API, not in the bulk archive. This is a documented limitation.

## 5. Timestamps

- Raw millisecond epoch (UTC) integers are converted to timezone-aware UTC
  datetimes.
- Every bar is labeled by its **open time** and is **left-closed / right-open**:
  a 5m bar labeled `10:00` covers `[10:00, 10:05)`.

## 6. Data layers and immutability

```
raw/        immutable zips (+ .CHECKSUM), mirroring the archive paths
validated/  base 5m parquet per symbol, after structural validation
processed/  15m & 1h bars, each split into development + holdout
manifests/  committed JSON provenance (one per dataset file)
```

- `raw/` is **write-once**; it is never edited. `validated/` and `processed/`
  are deterministic functions of `raw/` plus the code version.
- Every processed file has a manifest with: source, exchange, market, symbol,
  stream, timeframe, period, row count, generation timestamp, code version,
  git commit and a **SHA-256 content hash**.

## 7. Chronological split and frozen holdout

- Splits are **strictly chronological**; there are **no random train/test
  splits**.
- The **frozen holdout** is the fixed interval **`[2026-01-01 00:00 UTC,
  2026-07-01)`** (the last 6 months before the cutoff), pinned via
  `holdout.start` for an exact, deterministic boundary. It is hashed and
  **never** used for EDA-driven decisions, strategy/parameter selection or
  tuning. It is opened once, for the final report. See ADR 0003.

## 8. Quality rules

- Structural validation (dtypes, ranges, OHLC positivity) via pandera.
- Reported (not mutated): missing candles / gaps, duplicate timestamps, OHLC
  consistency violations, coverage per asset and timeframe.
- **Extreme observations are flagged, never auto-dropped.** Whether an extreme
  move is a data error or a real event is decided during the EDA.

## 9. Conventions

- **Annualization uses 365 days** (crypto trades 24/7), not the 252-day equity
  convention. Volatility scales by `sqrt(bars_per_year)`.
- **Returns are log returns** unless explicitly stated otherwise.
