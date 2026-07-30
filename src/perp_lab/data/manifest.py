"""Dataset manifests: the provenance record for every processed dataset.

A manifest is a small JSON document committed to ``data/manifests/``. It makes
each parquet file reproducible and auditable: what it is, where it came from,
the exact period it covers, and a content hash.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import polars as pl
from pydantic import BaseModel, ConfigDict, Field

from perp_lab import __version__
from perp_lab.utils.hashing import sha256_file


class DatasetManifest(BaseModel):
    """Provenance and integrity metadata for one processed dataset file."""

    model_config = ConfigDict(frozen=True)

    dataset_id: str
    source: str
    exchange: str
    market_type: str
    symbol: str
    stream: str  # "klines" | "markPriceKlines" | "fundingRate"
    timeframe: str | None
    period_start: datetime
    period_end: datetime
    row_count: int
    relative_path: str
    data_sha256: str
    code_version: str = __version__
    git_commit: str | None = None
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    notes: str = ""

    def to_json(self) -> str:
        return self.model_dump_json(indent=2)


def read_git_commit(repo_root: str | Path = ".") -> str | None:
    """Best-effort read of the current git commit without invoking git."""
    head = Path(repo_root) / ".git" / "HEAD"
    if not head.exists():
        return None
    ref = head.read_text(encoding="utf-8").strip()
    if ref.startswith("ref:"):
        ref_path = Path(repo_root) / ".git" / ref.split(" ", 1)[1].strip()
        if ref_path.exists():
            return ref_path.read_text(encoding="utf-8").strip()
        return None
    return ref  # detached HEAD already contains the sha


def _time_bounds(df: pl.DataFrame, time_col: str) -> tuple[datetime, datetime]:
    lo = df.select(pl.col(time_col).min()).item()
    hi = df.select(pl.col(time_col).max()).item()
    return lo, hi


def write_manifest(
    df: pl.DataFrame,
    *,
    data_path: str | Path,
    manifests_dir: str | Path,
    dataset_id: str,
    source: str,
    exchange: str,
    market_type: str,
    symbol: str,
    stream: str,
    timeframe: str | None,
    time_col: str = "open_time",
    repo_root: str | Path = ".",
    notes: str = "",
) -> DatasetManifest:
    """Persist ``df`` to parquet and write its committed JSON manifest.

    Returns the :class:`DatasetManifest`. The parquet content hash is computed
    after writing so the manifest describes exactly what is on disk.
    """
    data_path = Path(data_path)
    data_path.parent.mkdir(parents=True, exist_ok=True)
    df.write_parquet(data_path)

    if df.is_empty():
        period_start = period_end = datetime.now(UTC)
    else:
        period_start, period_end = _time_bounds(df, time_col)

    manifest = DatasetManifest(
        dataset_id=dataset_id,
        source=source,
        exchange=exchange,
        market_type=market_type,
        symbol=symbol,
        stream=stream,
        timeframe=timeframe,
        period_start=period_start,
        period_end=period_end,
        row_count=df.height,
        relative_path=str(data_path).replace("\\", "/"),
        data_sha256=sha256_file(data_path),
        git_commit=read_git_commit(repo_root),
        notes=notes,
    )

    manifests_dir = Path(manifests_dir)
    manifests_dir.mkdir(parents=True, exist_ok=True)
    (manifests_dir / f"{dataset_id}.json").write_text(manifest.to_json(), encoding="utf-8")
    return manifest


def read_manifest(path: str | Path) -> DatasetManifest:
    """Load a manifest JSON from disk."""
    return DatasetManifest.model_validate(json.loads(Path(path).read_text(encoding="utf-8")))
