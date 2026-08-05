"""Path-traversal protection for artifact access.

Run identifiers arrive from untrusted clients. They must resolve to a directory
strictly beneath the configured runs root; anything else (separators, ``..``,
absolute paths, symlink escapes) is rejected before any filesystem access that
could leak data outside the artifact root.
"""

from __future__ import annotations

import re
from pathlib import Path

# Conservative allow-list: alphanumerics plus a few safe separators, and never
# a leading dot (blocks ``.`` / ``..`` / hidden paths).
_RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class InvalidRunId(ValueError):
    """Raised when a run id is malformed or attempts path traversal."""


class RunNotFound(FileNotFoundError):
    """Raised when a well-formed run id does not resolve to a run directory."""


def validate_run_id(run_id: str) -> str:
    """Return ``run_id`` if it is a safe single path segment, else raise."""
    if not _RUN_ID_RE.match(run_id):
        raise InvalidRunId(f"invalid run id: {run_id!r}")
    if run_id in {".", ".."} or "/" in run_id or "\\" in run_id or ".." in run_id:
        raise InvalidRunId(f"invalid run id: {run_id!r}")
    return run_id


def resolve_run_dir(run_id: str, runs_root: Path) -> Path:
    """Resolve a validated run id to a directory beneath ``runs_root``.

    Raises :class:`InvalidRunId` on traversal attempts and :class:`RunNotFound`
    when the directory is absent.
    """
    validate_run_id(run_id)
    root = runs_root.resolve()
    candidate = (root / run_id).resolve()
    if not candidate.is_relative_to(root):
        raise InvalidRunId(f"run id escapes artifact root: {run_id!r}")
    if not candidate.is_dir():
        raise RunNotFound(f"run not found: {run_id}")
    return candidate
