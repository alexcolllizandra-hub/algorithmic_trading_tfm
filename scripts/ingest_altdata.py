"""Ingest the alternative-data annex inputs: Fear & Greed and US macro events.

Run with: ``uv run python scripts/ingest_altdata.py``

Two datasets, both written to ``data/external/`` with committed JSON manifests
under ``data/manifests/`` following the same provenance contract as the market
data (row count, period, SHA-256, code version):

* ``fear_greed.parquet`` — the daily Crypto Fear & Greed index from
  alternative.me (full public history, one row per UTC day). Downloaded live;
  re-running refreshes the file and its manifest.
* ``us_macro_events.parquet`` — the curated calendar of US CPI releases and
  FOMC decisions 2020-2025 from ``configs/altdata/us_macro_events.csv``
  (sources: BLS yearly schedules, Federal Reserve FOMC calendars). The CSV is
  the committed source of truth; this script only converts and manifests it.

Neither dataset enters the canonical study: they feed the descriptive
alternative-data annex only.
"""

from __future__ import annotations

import json
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

import polars as pl

from perp_lab.config.models import Paths
from perp_lab.data.manifest import write_manifest

FNG_URL = "https://api.alternative.me/fng/?limit=0&format=json"


def ingest_fear_greed(paths: Paths) -> None:
    with urllib.request.urlopen(FNG_URL, timeout=60) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    rows = payload["data"]
    frame = (
        pl.DataFrame(
            {
                "date": [datetime.fromtimestamp(int(r["timestamp"]), tz=UTC) for r in rows],
                "value": [int(r["value"]) for r in rows],
                "classification": [r["value_classification"] for r in rows],
            }
        )
        .sort("date")
        .unique(subset="date", keep="first", maintain_order=True)
    )
    out = Path(paths.data_root) / "external" / "fear_greed.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    manifest = write_manifest(
        frame,
        data_path=out,
        manifests_dir=paths.manifests_dir,
        dataset_id="alternative_me_fear_greed_daily",
        source="alternative.me",
        exchange="external",
        market_type="na",
        symbol="CRYPTO",
        stream="fearGreed",
        timeframe="1d",
        time_col="date",
        notes="Daily Crypto Fear & Greed index, full public history. "
        "Point-in-time caveat: served by a live API; historical methodology "
        "changes are not versioned by the provider. Descriptive annex only.",
    )
    print(f"{out} -> {frame.height} rows, sha256 {manifest.data_sha256[:16]}…")


def ingest_macro_events(paths: Paths) -> None:
    csv_path = Path("configs/altdata/us_macro_events.csv")
    frame = (
        pl.read_csv(csv_path)
        .with_columns(pl.col("datetime_utc").str.to_datetime("%Y-%m-%dT%H:%M:%SZ", time_zone="UTC"))
        .sort("datetime_utc")
    )
    out = Path(paths.data_root) / "external" / "us_macro_events.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    manifest = write_manifest(
        frame,
        data_path=out,
        manifests_dir=paths.manifests_dir,
        dataset_id="us_macro_events_2020_2025",
        source="bls.gov + federalreserve.gov (curated CSV in configs/altdata)",
        exchange="external",
        market_type="na",
        symbol="US",
        stream="macroEvents",
        timeframe=None,
        time_col="datetime_utc",
        notes="71 CPI releases (08:30 ET; Oct-2025 reference month not "
        "published due to the federal shutdown) and 49 FOMC decisions "
        "(14:00 ET statements; the two March-2020 emergency actions carry "
        "their actual announcement times). Descriptive annex only.",
    )
    print(f"{out} -> {frame.height} rows, sha256 {manifest.data_sha256[:16]}…")


def main() -> int:
    paths = Paths()
    ingest_fear_greed(paths)
    ingest_macro_events(paths)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
