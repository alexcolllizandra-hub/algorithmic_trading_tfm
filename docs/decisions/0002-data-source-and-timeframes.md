# ADR 0002: Binance USDT-M bulk data, 5m base with derived 15m/1h

- Status: Accepted
- Date: 2026-07-30

## Context

The thesis studies intraday strategies on BTC and ETH perpetual futures and
requires deep, reproducible, cost-free history with integrity guarantees.

## Decision

- Use **Binance USDT-M perpetuals** (`BTCUSDT`, `ETHUSDT`).
- Primary source: **`data.binance.vision`** bulk archive, with per-file
  SHA-256 checksum verification; **CCXT** only for incremental tail updates.
- Ingest a **5-minute base** and **construct 15m and 1h by aggregation**,
  cross-checked against native klines.
- Ingest max history per contract to a fixed **cutoff** (`2026-07-01`).
- Reserve the final **6 months** as a frozen holdout.

## Consequences

- Deepest free history and reproducibility; no API keys for bulk data.
- Single consistent provenance chain for all timeframes.
- `openInterest` is unavailable in bulk history and is excluded for now.
- Alternatives considered (Bybit, OKX) were rejected for Phase 1 to keep one
  well-documented, high-liquidity venue; revisiting is possible via a new ADR.
