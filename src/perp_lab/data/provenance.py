"""Data-authenticity audit: verify provenance, coverage and integrity.

This module answers a single question for every dataset the pipeline may use:
*is this REAL historical exchange data or a SYNTHETIC fixture, and does the file
on disk match its committed manifest?* It never trusts a filename: it reads the
manifest, recomputes the content hash, inspects the schema and representative
records, and measures coverage (min/max timestamp, row count, duplicates, gaps).

The audit is read-only and holdout-aware: it reports the holdout boundary and
flags any dataset whose coverage crosses it, but it does not load or expose
holdout observations for modelling.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import polars as pl

from perp_lab.config.models import DataContract, Paths
from perp_lab.data.splits import resolve_holdout_start
from perp_lab.utils.hashing import sha256_file
from perp_lab.utils.timeutils import timeframe_to_timedelta

REAL_HISTORICAL = "REAL_HISTORICAL"
SYNTHETIC_FIXTURE = "SYNTHETIC_FIXTURE"
UNKNOWN = "UNKNOWN"

# Providers we recognise as genuine exchange-sourced acquisition methods.
_REAL_SOURCES = {"binance_vision", "binance_api", "ccxt"}
_ACQUISITION = {
    "binance_vision": "Binance public data dumps (data.binance.vision), bulk download + checksum",
    "binance_api": "Binance REST API pull",
    "ccxt": "CCXT exchange client pull",
}

_TIME_COL = {"fundingRate": "funding_time"}


@dataclass
class DatasetAudit:
    """Authenticity + coverage verdict for one dataset file."""

    dataset_id: str
    classification: str
    provider: str
    acquisition_method: str
    exchange: str | None
    market_type: str | None
    symbol: str | None
    stream: str | None
    timeframe: str | None
    relative_path: str
    file_exists: bool
    schema: dict[str, str] = field(default_factory=dict)
    row_count_manifest: int | None = None
    row_count_actual: int | None = None
    row_count_matches: bool | None = None
    min_timestamp: str | None = None
    max_timestamp: str | None = None
    sha256_manifest: str | None = None
    sha256_actual: str | None = None
    checksum_matches: bool | None = None
    duplicate_timestamps: int | None = None
    missing_intervals: int | None = None
    crosses_holdout: bool | None = None
    sample_records: list[dict[str, Any]] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.issues


def _classify(source: str) -> str:
    """Classify by acquisition provider. A checksum mismatch does not change the
    provenance class (the data still came from the exchange dump); it is recorded
    separately as an integrity issue."""
    if source in _REAL_SOURCES:
        return REAL_HISTORICAL
    if "synthetic" in source.lower():
        return SYNTHETIC_FIXTURE
    return UNKNOWN


def _count_gaps(df: pl.DataFrame, time_col: str, step_seconds: float) -> int:
    if df.height < 2:
        return 0
    ts = df.select(pl.col(time_col)).sort(time_col).to_series()
    deltas = ts.diff().drop_nulls()
    # number of missing bars = sum(round(delta/step) - 1) over all steps > step
    secs = deltas.dt.total_milliseconds() / 1000.0
    steps = (secs / step_seconds).round().cast(pl.Int64)
    missing = (steps - 1).filter(steps > 1).sum()
    return int(missing) if missing is not None else 0


def audit_dataset(manifest_path: Path, *, holdout_start: datetime, repo_root: Path) -> DatasetAudit:
    """Audit a single dataset described by its manifest JSON."""
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    source = str(manifest.get("source", ""))
    dataset_id = str(manifest.get("dataset_id", manifest_path.stem))
    stream = manifest.get("stream")
    timeframe = manifest.get("timeframe")
    rel = str(manifest.get("relative_path", ""))
    data_path = repo_root / rel

    audit = DatasetAudit(
        dataset_id=dataset_id,
        classification=UNKNOWN,
        provider=source or "unknown",
        acquisition_method=_ACQUISITION.get(source, "unknown"),
        exchange=manifest.get("exchange"),
        market_type=manifest.get("market_type"),
        symbol=manifest.get("symbol"),
        stream=stream,
        timeframe=timeframe,
        relative_path=rel,
        file_exists=data_path.exists(),
        row_count_manifest=manifest.get("row_count"),
        sha256_manifest=manifest.get("data_sha256"),
    )

    if not data_path.exists():
        audit.issues.append(f"data file missing: {rel}")
        audit.classification = _classify(source)
        return audit

    audit.sha256_actual = sha256_file(data_path)
    audit.checksum_matches = (
        audit.sha256_actual.lower() == str(audit.sha256_manifest).lower()
        if audit.sha256_manifest
        else None
    )
    if audit.checksum_matches is False:
        audit.issues.append("sha256 mismatch: file content differs from manifest")

    df = pl.read_parquet(data_path)
    audit.schema = {name: str(dtype) for name, dtype in zip(df.columns, df.dtypes, strict=True)}
    audit.row_count_actual = df.height
    audit.row_count_matches = (
        audit.row_count_actual == audit.row_count_manifest
        if audit.row_count_manifest is not None
        else None
    )
    if audit.row_count_matches is False:
        audit.issues.append("row_count mismatch vs manifest")

    time_col = _TIME_COL.get(str(stream), "open_time")
    if time_col in df.columns:
        lo = df.select(pl.col(time_col).min()).item()
        hi = df.select(pl.col(time_col).max()).item()
        audit.min_timestamp = lo.isoformat() if isinstance(lo, datetime) else str(lo)
        audit.max_timestamp = hi.isoformat() if isinstance(hi, datetime) else str(hi)
        audit.duplicate_timestamps = int(df.height - df.select(time_col).n_unique())
        if audit.duplicate_timestamps:
            audit.issues.append(f"{audit.duplicate_timestamps} duplicate timestamps")
        if isinstance(hi, datetime):
            audit.crosses_holdout = hi >= holdout_start
        if timeframe:
            step = timeframe_to_timedelta(str(timeframe)).total_seconds()
            audit.missing_intervals = _count_gaps(df, time_col, step)
    else:
        audit.issues.append(f"expected time column '{time_col}' not found")

    # Representative records: first and last two rows (small, human-checkable).
    head = df.head(2).to_dicts()
    tail = df.tail(2).to_dicts()
    audit.sample_records = [
        {k: (v.isoformat() if isinstance(v, datetime) else v) for k, v in row.items()}
        for row in (*head, *tail)
    ]

    audit.classification = _classify(source)
    return audit


def audit_all(
    contract: DataContract,
    paths: Paths,
    *,
    repo_root: str | Path = ".",
) -> dict[str, Any]:
    """Audit every dataset manifest and return a machine-readable report."""
    repo = Path(repo_root)
    holdout_start = resolve_holdout_start(contract)
    manifest_dir = paths.manifests_dir
    audits: list[DatasetAudit] = []
    for mpath in sorted(manifest_dir.glob("*.json")):
        audits.append(audit_dataset(mpath, holdout_start=holdout_start, repo_root=repo))

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "holdout_start": holdout_start.isoformat(),
        "n_datasets": len(audits),
        "n_real_historical": sum(a.classification == REAL_HISTORICAL for a in audits),
        "n_synthetic_fixture": sum(a.classification == SYNTHETIC_FIXTURE for a in audits),
        "n_with_issues": sum(not a.ok for a in audits),
        "datasets": [asdict(a) for a in audits],
    }


def write_report(report: dict[str, Any], out_dir: str | Path) -> tuple[Path, Path]:
    """Persist the audit as JSON and a human-readable Markdown table."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    json_path = out / "data_provenance_audit.json"
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    lines = [
        "# Data provenance & authenticity audit",
        "",
        f"- Generated: {report['generated_at']}",
        f"- Holdout start (frozen, inaccessible): **{report['holdout_start']}**",
        f"- Datasets audited: {report['n_datasets']}  |  "
        f"REAL_HISTORICAL: {report['n_real_historical']}  |  "
        f"SYNTHETIC_FIXTURE: {report['n_synthetic_fixture']}  |  "
        f"with issues: {report['n_with_issues']}",
        "",
        "| dataset | class | provider | tf | rows | min ts | max ts | checksum | dups | gaps | crosses holdout | ok |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for a in report["datasets"]:
        lines.append(
            f"| {a['dataset_id']} | {a['classification']} | {a['provider']} | "
            f"{a['timeframe'] or '-'} | {a['row_count_actual']} | {a['min_timestamp']} | "
            f"{a['max_timestamp']} | {'OK' if a['checksum_matches'] else 'FAIL' if a['checksum_matches'] is False else 'n/a'} | "
            f"{a['duplicate_timestamps']} | {a['missing_intervals']} | "
            f"{a['crosses_holdout']} | {'YES' if not a['issues'] else 'NO: ' + '; '.join(a['issues'])} |"
        )
    md_path = out / "data_provenance_audit.md"
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path
