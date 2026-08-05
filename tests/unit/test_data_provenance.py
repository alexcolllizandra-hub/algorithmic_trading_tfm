"""Unit tests for the data-authenticity / provenance audit."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import polars as pl

from perp_lab.data.provenance import (
    REAL_HISTORICAL,
    SYNTHETIC_FIXTURE,
    audit_dataset,
)
from perp_lab.utils.hashing import sha256_file

HOLDOUT = datetime(2026, 1, 1, tzinfo=UTC)


def _write_klines(path: Path, n: int, start: datetime, *, gap_at: int | None = None) -> None:
    times = []
    t = start
    for i in range(n):
        times.append(t)
        step = timedelta(hours=2) if gap_at is not None and i == gap_at else timedelta(hours=1)
        t = t + step
    df = pl.DataFrame(
        {
            "open_time": times,
            "open": [100.0 + i for i in range(n)],
            "high": [101.0 + i for i in range(n)],
            "low": [99.0 + i for i in range(n)],
            "close": [100.5 + i for i in range(n)],
            "volume": [10.0] * n,
        }
    ).with_columns(pl.col("open_time").dt.replace_time_zone("UTC"))
    df.write_parquet(path)


def _manifest(repo: Path, data_path: Path, *, source: str, sha: str, rows: int) -> Path:
    mdir = repo / "data" / "manifests"
    mdir.mkdir(parents=True, exist_ok=True)
    dataset_id = "binance_um_BTCUSDT_klines_1h_development"
    payload = {
        "dataset_id": dataset_id,
        "source": source,
        "exchange": "binance",
        "market_type": "um",
        "symbol": "BTCUSDT",
        "stream": "klines",
        "timeframe": "1h",
        "period_start": "2020-01-01T00:00:00Z",
        "period_end": "2020-01-03T00:00:00Z",
        "row_count": rows,
        "relative_path": str(data_path.relative_to(repo)).replace("\\", "/"),
        "data_sha256": sha,
    }
    mp = mdir / f"{dataset_id}.json"
    mp.write_text(json.dumps(payload), encoding="utf-8")
    return mp


def test_audit_real_dataset_clean(tmp_path: Path) -> None:
    data = tmp_path / "data" / "processed" / "BTCUSDT" / "1h_development.parquet"
    data.parent.mkdir(parents=True, exist_ok=True)
    _write_klines(data, 48, datetime(2020, 1, 1, tzinfo=UTC))
    sha = sha256_file(data)
    mp = _manifest(tmp_path, data, source="binance_vision", sha=sha, rows=48)

    audit = audit_dataset(mp, holdout_start=HOLDOUT, repo_root=tmp_path)
    assert audit.classification == REAL_HISTORICAL
    assert audit.checksum_matches is True
    assert audit.row_count_matches is True
    assert audit.duplicate_timestamps == 0
    assert audit.missing_intervals == 0
    assert audit.crosses_holdout is False
    assert audit.provider == "binance_vision"
    assert audit.acquisition_method != "unknown"
    assert audit.ok
    assert len(audit.sample_records) == 4
    assert set(audit.schema).issuperset({"open", "high", "low", "close", "volume"})


def test_audit_detects_checksum_mismatch(tmp_path: Path) -> None:
    data = tmp_path / "data" / "processed" / "BTCUSDT" / "1h_development.parquet"
    data.parent.mkdir(parents=True, exist_ok=True)
    _write_klines(data, 10, datetime(2020, 1, 1, tzinfo=UTC))
    mp = _manifest(tmp_path, data, source="binance_vision", sha="deadbeef", rows=10)

    audit = audit_dataset(mp, holdout_start=HOLDOUT, repo_root=tmp_path)
    assert audit.checksum_matches is False
    assert not audit.ok
    assert any("sha256" in issue for issue in audit.issues)
    # Provenance class is still real; integrity failure is separate.
    assert audit.classification == REAL_HISTORICAL


def test_audit_detects_gaps(tmp_path: Path) -> None:
    data = tmp_path / "data" / "processed" / "BTCUSDT" / "1h_development.parquet"
    data.parent.mkdir(parents=True, exist_ok=True)
    _write_klines(data, 12, datetime(2020, 1, 1, tzinfo=UTC), gap_at=5)
    sha = sha256_file(data)
    mp = _manifest(tmp_path, data, source="binance_vision", sha=sha, rows=12)

    audit = audit_dataset(mp, holdout_start=HOLDOUT, repo_root=tmp_path)
    assert audit.missing_intervals == 1


def test_audit_synthetic_source_classified(tmp_path: Path) -> None:
    data = tmp_path / "data" / "processed" / "BTCUSDT" / "1h_development.parquet"
    data.parent.mkdir(parents=True, exist_ok=True)
    _write_klines(data, 5, datetime(2020, 1, 1, tzinfo=UTC))
    sha = sha256_file(data)
    mp = _manifest(tmp_path, data, source="synthetic_fixture", sha=sha, rows=5)

    audit = audit_dataset(mp, holdout_start=HOLDOUT, repo_root=tmp_path)
    assert audit.classification == SYNTHETIC_FIXTURE


def test_audit_missing_file(tmp_path: Path) -> None:
    data = tmp_path / "data" / "processed" / "BTCUSDT" / "1h_development.parquet"
    mp = _manifest(tmp_path, data, source="binance_vision", sha="x", rows=5)
    audit = audit_dataset(mp, holdout_start=HOLDOUT, repo_root=tmp_path)
    assert audit.file_exists is False
    assert not audit.ok
