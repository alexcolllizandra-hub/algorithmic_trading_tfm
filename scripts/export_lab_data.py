"""Export development-partition 1h candles + funding for the browser lab.

Run with: ``uv run python scripts/export_lab_data.py``

Writes one columnar JSON per symbol to ``apps/web/public/data/lab/``:

    {
      "symbol": "BTCUSDT", "timeframe": "1h",
      "start": "...", "end": "...", "n": 52608,
      "t": [unix_seconds, ...],       # bar open times
      "o": [...], "h": [...], "l": [...], "c": [...],
      "ft": [unix_seconds, ...],      # funding settlement times
      "fr": [...],                    # funding rates
      "source": {"dataset_id": ..., "sha256": ...}
    }

The holdout partition [2026-01-01, cutoff) is EXCLUDED: the lab is an
exploratory teaching tool and must not let anyone backtest into the frozen
window. Prices are rounded to 2 decimals (tick-scale for BTC/ETH USDT-M);
funding rates keep 8 decimals (they are ~1e-4).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import polars as pl

VALIDATED = Path("data/validated")
PROCESSED = Path("data/processed")
MANIFESTS = Path("data/manifests")
OUT_DIR = Path("apps/web/public/data/lab")
HOLDOUT_START = datetime(2026, 1, 1, tzinfo=UTC)
SYMBOLS = ("BTCUSDT", "ETHUSDT")


def manifest_for(dataset_id: str) -> dict:
    path = MANIFESTS / f"{dataset_id}.json"
    if not path.exists():
        return {}
    m = json.loads(path.read_text(encoding="utf-8"))
    return {"dataset_id": m.get("dataset_id"), "sha256": m.get("data_sha256")}


def export_symbol(symbol: str) -> str:
    # The ingestion pipeline already writes the development/holdout partitions
    # as separate files; reading the development one keeps the holdout
    # physically absent from this export, not merely filtered.
    bars = pl.read_parquet(PROCESSED / symbol / "1h_development.parquet").sort("open_time")

    funding_path = VALIDATED / symbol / "fundingRate.parquet"
    funding = pl.read_parquet(funding_path).sort("funding_time")
    funding = funding.filter(pl.col("funding_time") < HOLDOUT_START)

    payload = {
        "symbol": symbol,
        "timeframe": "1h",
        "start": bars["open_time"][0].isoformat(),
        "end": bars["open_time"][-1].isoformat(),
        "n": bars.height,
        "holdout_excluded_from": HOLDOUT_START.date().isoformat(),
        "t": (bars["open_time"].dt.epoch("ms") // 1000).to_list(),
        "o": [round(v, 2) for v in bars["open"].to_list()],
        "h": [round(v, 2) for v in bars["high"].to_list()],
        "l": [round(v, 2) for v in bars["low"].to_list()],
        "c": [round(v, 2) for v in bars["close"].to_list()],
        "ft": (funding["funding_time"].dt.epoch("ms") // 1000).to_list(),
        "fr": [round(v, 8) for v in funding["funding_rate"].to_list()],
        "source": {
            "bars": manifest_for(f"binance_um_{symbol}_klines_1h_development"),
            "funding": manifest_for(f"binance_um_{symbol}_fundingRate"),
        },
        "generated_at": datetime.now(UTC).isoformat(),
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"{symbol}.json"
    out.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
    return f"{out} -> {out.stat().st_size // 1024} KB | bars={bars.height} funding={funding.height}"


def main() -> int:
    for symbol in SYMBOLS:
        print(export_symbol(symbol))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
