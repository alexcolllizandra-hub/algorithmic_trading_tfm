"""Tests for run identity on a dirty worktree.

A commit hash identifies a run only when the worktree is clean, and during
development it almost never is. These tests pin down the property that actually
matters: two runs get the same fingerprint if and only if everything that can
change the result is the same -- configuration, methodological contract, data,
commit, uncommitted diff and untracked source files.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from perp_lab.tracking.identity import (
    RELEVANT_DIRS,
    build_identity,
    identity_record,
    stable_hash,
    worktree_state,
)


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A tiny git repository with the directories identity actually inspects."""
    root = tmp_path / "repo"
    (root / "src" / "perp_lab").mkdir(parents=True)
    (root / "configs").mkdir()
    (root / "src" / "perp_lab" / "core.py").write_text("VALUE = 1\n", encoding="utf-8")
    (root / "configs" / "experiment.yaml").write_text("budget: 10\n", encoding="utf-8")
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "t@example.com")
    _git(root, "config", "user.name", "T")
    _git(root, "add", ".")
    _git(root, "commit", "-q", "-m", "initial")
    return root


def _identity(repo: Path, **kwargs):
    payload = {"family": "momentum", "budget": 10}
    payload.update(kwargs.pop("config", {}))
    return build_identity(config_payload=payload, repo_root=repo, **kwargs)


# --------------------------------------------------------------------------- #
# Clean worktree
# --------------------------------------------------------------------------- #


def test_clean_repository_is_reproducible_from_the_commit(repo: Path) -> None:
    state = worktree_state(repo)
    assert state["dirty"] is False
    assert state["diff_sha256"] is None
    assert state["untracked_files"] == []
    assert state["reproducible_from_commit_alone"] is True


def test_identity_is_stable_across_repeated_calls(repo: Path) -> None:
    assert _identity(repo).fingerprint == _identity(repo).fingerprint


# --------------------------------------------------------------------------- #
# Dirty worktree: the case that actually occurs
# --------------------------------------------------------------------------- #


def test_an_uncommitted_source_change_changes_the_fingerprint(repo: Path) -> None:
    before = _identity(repo)
    (repo / "src" / "perp_lab" / "core.py").write_text("VALUE = 2\n", encoding="utf-8")
    after = _identity(repo)
    assert after.fingerprint != before.fingerprint
    assert after.components["diff_sha256"] != before.components["diff_sha256"]


def test_an_untracked_source_file_changes_the_fingerprint(repo: Path) -> None:
    """Invisible to git diff, yet it can be imported and change every result."""
    before = _identity(repo)
    (repo / "src" / "perp_lab" / "new_rule.py").write_text("THRESHOLD = 3\n", encoding="utf-8")
    after = _identity(repo)
    assert after.fingerprint != before.fingerprint
    assert "src/perp_lab/new_rule.py" in worktree_state(repo)["untracked_files"]


def test_editing_an_untracked_file_changes_the_fingerprint(repo: Path) -> None:
    new = repo / "src" / "perp_lab" / "new_rule.py"
    new.write_text("THRESHOLD = 3\n", encoding="utf-8")
    before = _identity(repo)
    new.write_text("THRESHOLD = 4\n", encoding="utf-8")
    assert _identity(repo).fingerprint != before.fingerprint


def test_irrelevant_untracked_files_are_ignored(repo: Path) -> None:
    """Scratch output must not invalidate an otherwise identical run."""
    before = _identity(repo)
    (repo / "notes.txt").write_text("scratch\n", encoding="utf-8")
    (repo / "artifacts").mkdir()
    (repo / "artifacts" / "out.json").write_text("{}", encoding="utf-8")
    assert _identity(repo).fingerprint == before.fingerprint


def test_a_dirty_run_is_flagged_provisional(repo: Path) -> None:
    (repo / "src" / "perp_lab" / "core.py").write_text("VALUE = 9\n", encoding="utf-8")
    record = identity_record(_identity(repo), repo_root=repo)
    assert record["provisional"] is True
    assert "dirty worktree" in record["provisional_reason"]
    assert "reproducible only from the same working tree" in record["worktree"]["warning"]


def test_committing_the_change_clears_the_provisional_flag(repo: Path) -> None:
    (repo / "src" / "perp_lab" / "core.py").write_text("VALUE = 9\n", encoding="utf-8")
    assert identity_record(_identity(repo), repo_root=repo)["provisional"] is True
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "change")
    record = identity_record(_identity(repo), repo_root=repo)
    assert record["provisional"] is False
    assert record["worktree"]["reproducible_from_commit_alone"] is True


# --------------------------------------------------------------------------- #
# The other identity components
# --------------------------------------------------------------------------- #


def test_configuration_contract_and_data_each_move_the_fingerprint(repo: Path) -> None:
    base = _identity(repo, contract_payload={"holdout": "2026-01-01"}, dataset_hashes={"btc": "a"})

    changed_config = _identity(
        repo,
        config={"budget": 11},
        contract_payload={"holdout": "2026-01-01"},
        dataset_hashes={"btc": "a"},
    )
    changed_contract = _identity(
        repo, contract_payload={"holdout": "2026-02-01"}, dataset_hashes={"btc": "a"}
    )
    changed_data = _identity(
        repo, contract_payload={"holdout": "2026-01-01"}, dataset_hashes={"btc": "b"}
    )

    fingerprints = {
        base.fingerprint,
        changed_config.fingerprint,
        changed_contract.fingerprint,
        changed_data.fingerprint,
    }
    assert len(fingerprints) == 4, "some component is not part of the identity"


def test_differences_names_the_component_that_changed(repo: Path) -> None:
    base = _identity(repo, contract_payload={"holdout": "2026-01-01"})
    other = _identity(repo, contract_payload={"holdout": "2026-02-01"})
    diff = base.differences(other)
    assert set(diff) == {"contract_sha256"}


def test_stable_hash_ignores_key_order() -> None:
    assert stable_hash({"a": 1, "b": 2}) == stable_hash({"b": 2, "a": 1})


def test_relevant_dirs_cover_everything_that_changes_behaviour() -> None:
    """A run's behaviour can change from code, tests, config or the contract."""
    assert {"src", "tests", "configs"} <= set(RELEVANT_DIRS)
