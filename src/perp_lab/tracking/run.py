"""Run identity, environment/git capture and the artifact-folder writer."""

from __future__ import annotations

import json
import platform
import subprocess
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from importlib import metadata
from pathlib import Path
from typing import Any

import polars as pl
import yaml

from perp_lab import __version__
from perp_lab.data.manifest import read_git_commit

# Contract filenames written under each run directory.
RESOLVED_CONFIG = "resolved_config.yaml"
DATASET_MANIFESTS = "dataset_manifests.json"
ENVIRONMENT = "environment.json"
GIT_STATE = "git_state.json"
METRICS = "metrics.json"
FEATURE_METADATA = "feature_metadata.json"
TRADES = "trades.parquet"
EQUITY = "equity.parquet"

_TRACKED_PACKAGES = ("polars", "numpy", "pydantic", "scipy", "pyarrow", "matplotlib")


def generate_run_id(prefix: str = "dev", *, now: datetime | None = None) -> str:
    """A sortable, unique run id: ``<prefix>_<UTCstamp>_<short>``."""
    stamp = (now or datetime.now(UTC)).strftime("%Y%m%dT%H%M%SZ")
    return f"{prefix}_{stamp}_{uuid.uuid4().hex[:6]}"


def environment_info() -> dict[str, Any]:
    """Capture the interpreter and key package versions for reproducibility."""
    packages: dict[str, str | None] = {}
    for name in _TRACKED_PACKAGES:
        try:
            packages[name] = metadata.version(name)
        except metadata.PackageNotFoundError:  # pragma: no cover - env-specific
            packages[name] = None
    return {
        "perp_lab_version": __version__,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "packages": packages,
    }


def _git(args: list[str], repo_root: str | Path) -> str | None:
    try:
        out = subprocess.run(
            ["git", *args],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):  # pragma: no cover - git absent
        return None
    if out.returncode != 0:
        return None
    return out.stdout.strip()


def git_state(repo_root: str | Path = ".") -> dict[str, Any]:
    """Best-effort git commit / branch / dirty flag (never fabricated)."""
    commit = _git(["rev-parse", "HEAD"], repo_root) or read_git_commit(repo_root)
    branch = _git(["rev-parse", "--abbrev-ref", "HEAD"], repo_root)
    porcelain = _git(["status", "--porcelain"], repo_root)
    dirty = None if porcelain is None else bool(porcelain.strip())
    return {"commit": commit, "branch": branch, "dirty": dirty}


@dataclass(frozen=True)
class RunTracker:
    """Owns one ``artifacts/runs/<run_id>/`` directory and writes its contract."""

    run_id: str
    run_dir: Path

    @classmethod
    def create(
        cls,
        runs_root: str | Path,
        *,
        run_id: str | None = None,
        prefix: str = "dev",
    ) -> RunTracker:
        rid = run_id or generate_run_id(prefix)
        run_dir = Path(runs_root) / rid
        (run_dir / "logs").mkdir(parents=True, exist_ok=True)
        (run_dir / "figures").mkdir(parents=True, exist_ok=True)
        return cls(run_id=rid, run_dir=run_dir)

    @property
    def logs_dir(self) -> Path:
        return self.run_dir / "logs"

    @property
    def figures_dir(self) -> Path:
        return self.run_dir / "figures"

    def path(self, name: str) -> Path:
        return self.run_dir / name

    def write_yaml(self, name: str, obj: dict[str, Any]) -> Path:
        p = self.path(name)
        p.write_text(yaml.safe_dump(obj, sort_keys=False, default_flow_style=False), "utf-8")
        return p

    def write_json(self, name: str, obj: Any) -> Path:
        p = self.path(name)
        p.write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")
        return p

    def write_parquet(self, name: str, df: pl.DataFrame) -> Path:
        p = self.path(name)
        df.write_parquet(p)
        return p
