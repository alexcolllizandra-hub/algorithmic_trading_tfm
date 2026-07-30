---
name: ingest-perpetual-data
description: Download and process Binance USDT-M perpetual data from data.binance.vision into the raw/validated/processed layers with manifests. Use when the user wants to fetch, refresh, or extend BTC/ETH market data for the perp-lab thesis.
disable-model-invocation: true
---

# Ingest perpetual data

## Workflow

1. Ensure the environment is ready: `uv sync --extra dev`.
2. Review `configs/data_contract.yaml` (symbols, period, timeframes).
3. Run the bulk ingestion:
   `uv run perp-lab download --config configs/data_contract.yaml`.
4. This writes, per symbol:
   - `data/raw/...` immutable zips (+ `.CHECKSUM`, verified),
   - `data/validated/{sym}/5m.parquet` and `fundingRate.parquet`,
   - `data/processed/{sym}/{15m,1h}_{development,holdout}.parquet`,
   - one JSON manifest per file in `data/manifests/`.
5. Verify manifests exist and row counts look sane.

## Rules

- Never edit files under `data/raw/`.
- Bulk history comes from `data.binance.vision`. Use CCXT
  (`CcxtIncrementalProvider`) only to append the most recent candles.
- Higher timeframes are built from the 5m base (`resample_klines`), not
  downloaded as source of truth.
- If a monthly archive is missing, it is logged; investigate before proceeding.
