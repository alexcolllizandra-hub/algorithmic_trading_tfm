"""Crash-safe progress journal for long experiments.

A multi-seed walk-forward study runs for a long time and must survive being
interrupted. Three files carry that state, all written atomically so a kill in
the middle of a write leaves the previous good version intact rather than a
truncated file:

* ``events.jsonl`` -- append-only log of everything that happened, one JSON
  object per line, so a partially written final line never corrupts the history.
* ``status.json`` -- the current snapshot: phase, progress, timing estimate.
* ``checkpoint.json`` -- the set of work units already completed, with their
  results, so a resumed run skips them instead of paying for them twice.

Atomicity is achieved by writing to a sibling temporary file and then calling
``os.replace``, which is atomic on both POSIX and Windows.
"""

from __future__ import annotations

import json
import os
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

EVENTS = "events.jsonl"
STATUS = "status.json"
CHECKPOINT = "checkpoint.json"


def _now() -> str:
    return datetime.now(UTC).isoformat()


def atomic_write_text(path: Path, text: str) -> Path:
    """Replace ``path`` with ``text`` atomically.

    The temporary file lives in the destination directory so the final rename
    never crosses a filesystem boundary (which would make it non-atomic).
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp{os.getpid()}")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)  # atomic on POSIX and Windows
    return path


def atomic_write_json(path: Path, payload: Any) -> Path:
    return atomic_write_text(path, json.dumps(payload, indent=2, default=str))


class Journal:
    """Append-only event log plus an atomically-replaced status snapshot."""

    def __init__(self, run_dir: str | Path) -> None:
        self.run_dir = Path(run_dir)
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self._started = time.monotonic()

    @property
    def events_path(self) -> Path:
        return self.run_dir / EVENTS

    @property
    def status_path(self) -> Path:
        return self.run_dir / STATUS

    def event(self, kind: str, **fields: Any) -> dict[str, Any]:
        """Append one structured event. Never raises on a serialisation quirk."""
        record = {"ts": _now(), "kind": kind, **fields}
        line = json.dumps(record, default=str)
        with self.events_path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        return record

    def read_events(self) -> list[dict[str, Any]]:
        """Every complete event. A truncated trailing line is skipped, not fatal."""
        if not self.events_path.exists():
            return []
        out: list[dict[str, Any]] = []
        for line in self.events_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return out

    def status(
        self,
        *,
        state: str,
        completed: int,
        total: int,
        phase: str = "",
        **extra: Any,
    ) -> dict[str, Any]:
        """Write the current progress snapshot with a work-based ETA.

        The estimate is derived from units already finished in *this* process, not
        from a guess: with nothing finished yet it reports ``None`` rather than a
        fabricated number.
        """
        elapsed = time.monotonic() - self._started
        per_unit = (elapsed / completed) if completed > 0 else None
        remaining = max(total - completed, 0)
        payload = {
            "updated_at": _now(),
            "state": state,
            "phase": phase,
            "completed": completed,
            "total": total,
            "progress": round(completed / total, 4) if total else None,
            "elapsed_seconds": round(elapsed, 1),
            "seconds_per_unit": round(per_unit, 3) if per_unit is not None else None,
            "eta_seconds": round(per_unit * remaining, 1) if per_unit is not None else None,
            **extra,
        }
        atomic_write_json(self.status_path, payload)
        return payload

    def read_status(self) -> dict[str, Any]:
        if not self.status_path.exists():
            return {}
        try:
            return json.loads(self.status_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}


class Checkpoint:
    """Records which work units are already done so a resume never redoes them.

    Each unit is addressed by a stable key. ``mark_done`` rewrites the whole file
    atomically, which is cheap at this scale (tens to hundreds of units) and much
    safer than appending to a structure that must stay parseable.
    """

    def __init__(self, run_dir: str | Path) -> None:
        self.run_dir = Path(run_dir)
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self._units: dict[str, dict[str, Any]] = {}
        self._meta: dict[str, Any] = {}
        self._load()

    @property
    def path(self) -> Path:
        return self.run_dir / CHECKPOINT

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            # A corrupt checkpoint must not silently discard finished work: fail
            # loudly so the operator decides whether to repair or restart.
            raise ValueError(
                f"Checkpoint at {self.path} is corrupt and cannot be parsed. "
                "Inspect or remove it explicitly; refusing to guess."
            ) from None
        self._units = dict(payload.get("units", {}))
        self._meta = dict(payload.get("meta", {}))

    def _flush(self) -> None:
        atomic_write_json(self.path, {"meta": self._meta, "units": self._units})

    def set_meta(self, **fields: Any) -> None:
        """Record the identity of the experiment this checkpoint belongs to."""
        self._meta.update(fields)
        self._flush()

    @property
    def meta(self) -> dict[str, Any]:
        return dict(self._meta)

    def is_done(self, key: str) -> bool:
        return key in self._units

    def result(self, key: str) -> dict[str, Any] | None:
        unit = self._units.get(key)
        return dict(unit) if unit else None

    def mark_done(self, key: str, payload: dict[str, Any]) -> None:
        self._units[key] = {"completed_at": _now(), **payload}
        self._flush()

    def completed_keys(self) -> list[str]:
        return sorted(self._units)

    def results(self) -> dict[str, dict[str, Any]]:
        return {k: dict(v) for k, v in self._units.items()}

    def assert_compatible(self, **expected: Any) -> None:
        """Refuse to resume into a checkpoint built under a different contract.

        Resuming across a changed configuration, code version or dataset would
        silently mix incomparable results into one aggregate, which is worse than
        starting again.
        """
        if not self._meta:
            return
        mismatches = {
            k: (self._meta.get(k), v) for k, v in expected.items() if self._meta.get(k) != v
        }
        if mismatches:
            detail = "; ".join(
                f"{k}: checkpoint={a!r} requested={b!r}" for k, (a, b) in mismatches.items()
            )
            raise ValueError(
                "Refusing to resume: this checkpoint was created under a different "
                f"contract ({detail}). Start a new run directory instead."
            )
