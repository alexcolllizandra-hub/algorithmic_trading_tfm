"""Stamp pre-ADR-0012 run and study artifacts as superseded, without deleting them.

Every result produced before the per-outer-fold protocol was searched under a
fitness pooled across *all* walk-forward folds, including folds chronologically
later than the one being scored. Those fold winners were therefore selected with
partial knowledge of the future, and their numbers are not evidence.

Deleting them would destroy the provenance the thesis needs in order to explain
what went wrong and what changed. Instead this script writes a ``SUPERSEDED.json``
marker next to each affected artifact, recording:

* why the artifact is superseded and which ADR supersedes it;
* the protocol it was actually produced under;
* enough original provenance (run id, label, git commit, seed, budget) to trace
  the result back to the code that made it.

The script never modifies or removes an existing file, and it is idempotent: a
directory already carrying a marker is left untouched unless ``--refresh`` is
given. Directories already produced under the current protocol are skipped.

    uv run python scripts/mark_superseded_runs.py --runs-dir artifacts/runs
    uv run python scripts/mark_superseded_runs.py --dry-run
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from perp_lab.search.runner import SEARCH_PROTOCOL

MARKER = "SUPERSEDED.json"

REASON = (
    "Candidate search ranked candidates on a fitness pooled across ALL walk-forward "
    "folds, so each fold's winner was chosen with partial knowledge of chronologically "
    "later folds. This is outer-fold selection leakage."
)


def _read_json(path: Path) -> Any | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _summary_of(run_dir: Path) -> dict[str, Any] | None:
    summary = _read_json(run_dir / "comparison_summary.json")
    if isinstance(summary, dict):
        return summary
    metrics = _read_json(run_dir / "metrics.json")
    if isinstance(metrics, dict) and isinstance(metrics.get("summary"), dict):
        return metrics["summary"]
    return None


def _study_meta(run_dir: Path) -> dict[str, Any] | None:
    manifest = _read_json(run_dir / "study_manifest.json")
    return manifest if isinstance(manifest, dict) else None


def _provenance(run_dir: Path) -> dict[str, Any]:
    """Everything needed to trace the artifact back, kept verbatim."""
    summary = _summary_of(run_dir) or {}
    study = _study_meta(run_dir) or {}
    git = _read_json(run_dir / "git_state.json") or {}
    checkpoint = _read_json(run_dir / "checkpoint.json") or {}
    meta = checkpoint.get("meta", {}) if isinstance(checkpoint, dict) else {}
    return {
        "directory": run_dir.name,
        "run_id": summary.get("run_id") or study.get("study_id") or run_dir.name,
        "label": summary.get("label") or meta.get("family"),
        "family": summary.get("family") or meta.get("family"),
        "symbol": summary.get("symbol"),
        "seed": summary.get("seed"),
        "budget": summary.get("budget") or meta.get("budget"),
        "n_folds": summary.get("n_folds"),
        "symbols": study.get("symbols") or meta.get("symbols"),
        "seeds": study.get("seeds") or meta.get("seeds"),
        "n_units": study.get("n_units"),
        "git_commit": git.get("commit") or meta.get("git_commit"),
        "git_dirty": git.get("dirty", meta.get("git_dirty")),
        "config_fingerprint": meta.get("config_fingerprint"),
        "run_identity": meta.get("run_identity"),
    }


def _is_artifact_dir(path: Path) -> bool:
    return any(
        (path / name).exists()
        for name in ("comparison_summary.json", "metrics.json", "study_manifest.json")
    )


def _recorded_protocol(run_dir: Path) -> str | None:
    summary = _summary_of(run_dir)
    if isinstance(summary, dict) and isinstance(summary.get("search_protocol"), str):
        return str(summary["search_protocol"])
    meta = (_read_json(run_dir / "checkpoint.json") or {}).get("meta", {})
    if isinstance(meta, dict) and isinstance(meta.get("search_protocol"), str):
        return str(meta["search_protocol"])
    return None


def _marker_payload(run_dir: Path, protocol: str | None) -> dict[str, Any]:
    return {
        "status": "superseded",
        "contaminated_by": "outer-fold selection leakage",
        "reason": REASON,
        "produced_under_protocol": protocol or "pooled_across_folds_contaminated (unrecorded)",
        "superseded_by_protocol": SEARCH_PROTOCOL,
        "adr": "docs/decisions/0012-outer-fold-contamination-in-candidate-search.md",
        "usable_for": [
            "documenting what the superseded protocol produced",
            "reproducing the bug",
        ],
        "not_usable_for": [
            "any performance claim",
            "the RS-vs-GA comparison",
            "strategy or parameter selection",
            "pooling with runs from the current protocol",
        ],
        "artifacts_retained": True,
        "marked_at": datetime.now(UTC).isoformat(),
        "original_provenance": _provenance(run_dir),
    }


def mark(runs_dir: Path, *, dry_run: bool, refresh: bool) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {"marked": [], "already_marked": [], "clean": [], "skipped": []}
    if not runs_dir.exists():
        return result

    candidates = [runs_dir, *runs_dir.rglob("*")]
    for path in candidates:
        if not path.is_dir() or not _is_artifact_dir(path):
            continue
        name = str(path.relative_to(runs_dir)) or "."
        protocol = _recorded_protocol(path)
        if protocol == SEARCH_PROTOCOL:
            result["clean"].append(name)
            continue
        if (path / MARKER).exists() and not refresh:
            result["already_marked"].append(name)
            continue
        if dry_run:
            result["skipped"].append(name)
            continue
        payload = _marker_payload(path, protocol)
        (path / MARKER).write_text(
            json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8"
        )
        result["marked"].append(name)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs-dir", default="artifacts/runs", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--refresh", action="store_true", help="rewrite existing markers")
    args = parser.parse_args(argv)

    out = mark(args.runs_dir, dry_run=args.dry_run, refresh=args.refresh)
    print(f"runs_dir            : {args.runs_dir}")
    print(f"marked superseded   : {len(out['marked'])}")
    print(f"already marked      : {len(out['already_marked'])}")
    print(f"current protocol    : {len(out['clean'])}")
    if args.dry_run:
        print(f"would mark          : {len(out['skipped'])}")
        for name in out["skipped"]:
            print(f"  - {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
