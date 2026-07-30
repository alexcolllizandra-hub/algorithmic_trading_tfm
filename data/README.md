# Data lake

Four layers (see [../docs/data_contract.md](../docs/data_contract.md)):

- `raw/` -- immutable zips downloaded from `data.binance.vision` (+ `.CHECKSUM`).
  Mirrors the archive path structure. **Never edited by hand.**
- `validated/` -- base 5-minute parquet per symbol, after quality validation.
- `processed/` -- 15m and 1h bars built from the 5m base, each split into a
  `development` partition and a frozen `holdout` partition.
- `manifests/` -- committed JSON provenance records (one per dataset file).

Everything except `manifests/` is git-ignored: it is large and fully
reproducible from the data contract via `uv run perp-lab download`.
