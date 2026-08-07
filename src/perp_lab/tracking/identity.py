"""Deterministic identity of an experiment run.

A commit hash alone does not identify what was executed. Almost every run during
development happens on a dirty worktree, and "commit abc123 plus some uncommitted
changes" is not reproducible. This module records the commit *and* a deterministic
hash of the uncommitted state, so two runs can be proven to have executed the same
code or proven not to have.

What is hashed, in order of decreasing obviousness:

* the resolved configuration, as it was actually validated (not as it was typed);
* the methodological contract (the data contract and experiment YAML);
* the SHA-256 of the development data partitions the run may read;
* the commit, branch and, when the worktree is dirty, the diff of tracked files
  plus the contents of untracked files under the directories that can change
  behaviour: ``src/``, ``tests/``, ``configs/`` and the contract documentation.

Untracked files matter as much as modified ones: a new module under ``src/`` that
is imported by the run is invisible to ``git diff`` yet changes the result
completely.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from perp_lab.tracking.run import environment_info, git_state

# Directories whose uncommitted contents can change what a run computes.
RELEVANT_DIRS: tuple[str, ...] = ("src", "tests", "configs", "docs/methodology")

# Extensions worth hashing inside those directories.
RELEVANT_SUFFIXES: frozenset[str] = frozenset({".py", ".yaml", ".yml", ".md", ".toml"})

_SKIP_PARTS = frozenset({"__pycache__", ".pytest_cache", ".ruff_cache", ".ipynb_checkpoints"})


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_hash(payload: Any) -> str:
    """Hash of a JSON-serialisable payload, independent of key order."""
    return _sha256_text(json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str))


def _git(args: list[str], repo_root: Path) -> str | None:
    try:
        out = subprocess.run(
            ["git", *args],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):  # pragma: no cover - git absent
        return None
    return out.stdout if out.returncode == 0 else None


def _untracked_relevant_files(repo_root: Path) -> list[str]:
    listing = _git(["ls-files", "--others", "--exclude-standard"], repo_root)
    if listing is None:
        return []
    out: list[str] = []
    for line in listing.splitlines():
        rel = line.strip()
        if not rel:
            continue
        path = Path(rel)
        if path.suffix not in RELEVANT_SUFFIXES:
            continue
        if _SKIP_PARTS & set(path.parts):
            continue
        if any(rel.startswith(f"{d}/") for d in RELEVANT_DIRS):
            out.append(rel)
    return sorted(out)


def worktree_state(repo_root: str | Path = ".") -> dict[str, Any]:
    """Commit, branch and a deterministic hash of everything uncommitted.

    The diff and the untracked hashes are computed unconditionally rather than
    only when git reports the tree dirty. Otherwise scratch output -- a log, a
    notebook checkpoint, a downloaded parquet -- would flip the run's identity
    without changing a single line of executed code.

    "Dirty" is therefore judged on what can actually change a result: a non-empty
    diff of tracked files, or an untracked file under the directories in
    :data:`RELEVANT_DIRS`.
    """
    root = Path(repo_root)
    state: dict[str, Any] = dict(git_state(root))
    state["worktree_dirty_any_file"] = state.pop("dirty", None)

    # Tracked modifications, staged and unstaged, in one canonical diff.
    diff = _git(["diff", "HEAD", "--"], root) or ""
    has_diff = bool(diff.strip())
    state["diff_sha256"] = _sha256_text(diff) if has_diff else None
    state["diff_bytes"] = len(diff.encode("utf-8"))

    untracked = _untracked_relevant_files(root)
    per_file = {rel: _sha256_file(root / rel) for rel in untracked if (root / rel).is_file()}
    state["untracked_files"] = untracked
    state["untracked_sha256"] = stable_hash(per_file) if per_file else None
    state["untracked_file_hashes"] = per_file

    relevant_dirty = has_diff or bool(per_file)
    state["dirty"] = relevant_dirty
    state["reproducible_from_commit_alone"] = state.get("commit") is not None and not relevant_dirty
    if relevant_dirty:
        state["warning"] = (
            "This run executed uncommitted code. It is identified exactly by "
            "commit + diff_sha256 + untracked_sha256, but it is reproducible only "
            "from the same working tree. Commit before a run whose results are "
            "meant to be citable."
        )
    return state


@dataclass(frozen=True)
class RunIdentity:
    """Everything needed to prove two runs executed the same experiment."""

    fingerprint: str
    components: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {"fingerprint": self.fingerprint, "components": self.components}

    def matches(self, other: RunIdentity) -> bool:
        return self.fingerprint == other.fingerprint

    def differences(self, other: RunIdentity) -> dict[str, dict[str, Any]]:
        """Which components differ, so a refusal to resume can say why."""
        keys = set(self.components) | set(other.components)
        return {
            key: {"expected": self.components.get(key), "found": other.components.get(key)}
            for key in sorted(keys)
            if self.components.get(key) != other.components.get(key)
        }


def build_identity(
    *,
    config_payload: Any,
    contract_payload: Any | None = None,
    dataset_hashes: dict[str, str] | None = None,
    repo_root: str | Path = ".",
    extra: dict[str, Any] | None = None,
) -> RunIdentity:
    """Assemble the run fingerprint from its independently checkable parts.

    Each component is hashed separately as well as jointly, so a mismatch can name
    the culprit ("the data contract changed") instead of only reporting that two
    opaque fingerprints differ.
    """
    worktree = worktree_state(repo_root)
    components: dict[str, Any] = {
        "config_sha256": stable_hash(config_payload),
        "contract_sha256": stable_hash(contract_payload) if contract_payload is not None else None,
        "dataset_sha256": stable_hash(dataset_hashes or {}),
        "commit": worktree.get("commit"),
        "diff_sha256": worktree.get("diff_sha256"),
        "untracked_sha256": worktree.get("untracked_sha256"),
    }
    if extra:
        components.update(extra)
    return RunIdentity(fingerprint=stable_hash(components)[:16], components=components)


def identity_record(identity: RunIdentity, *, repo_root: str | Path = ".") -> dict[str, Any]:
    """The full, human-readable identity block persisted alongside a run."""
    worktree = worktree_state(repo_root)
    return {
        "fingerprint": identity.fingerprint,
        "components": identity.components,
        "worktree": worktree,
        "environment": environment_info(),
        "provisional": not worktree.get("reproducible_from_commit_alone", False),
        "provisional_reason": (
            None
            if worktree.get("reproducible_from_commit_alone")
            else "executed on a dirty worktree; identified exactly but reproducible "
            "only from the same working tree"
        ),
    }
