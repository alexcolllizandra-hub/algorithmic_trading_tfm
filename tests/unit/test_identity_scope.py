"""The run fingerprint must ignore changes outside RELEVANT_DIRS.

This is the test that would have saved the CRT round three interruptions on
2026-08-17: edits to the web app and to non-methodology docs flipped the
identity of a running study whose executed code had not changed. See ADR 0018.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from perp_lab.tracking.identity import worktree_state


def _git(args: list[str], cwd: Path) -> None:
    subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        env={
            "GIT_AUTHOR_NAME": "t",
            "GIT_AUTHOR_EMAIL": "t@t",
            "GIT_COMMITTER_NAME": "t",
            "GIT_COMMITTER_EMAIL": "t@t",
            "PATH": __import__("os").environ["PATH"],
        },
    )


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    _git(["init", "-q"], tmp_path)
    for rel in (
        "src/pkg/mod.py",
        "apps/web/page.tsx",
        "docs/notes.md",
        "docs/methodology/protocol.md",
        "configs/exp.yaml",
    ):
        f = tmp_path / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text("original\n", encoding="utf-8")
    _git(["add", "-A"], tmp_path)
    _git(["commit", "-qm", "base"], tmp_path)
    return tmp_path


def test_changes_outside_relevant_dirs_do_not_touch_the_fingerprint(repo: Path) -> None:
    clean = worktree_state(repo)
    assert clean["dirty"] is False
    assert clean["diff_sha256"] is None

    (repo / "apps/web/page.tsx").write_text("edited\n", encoding="utf-8")
    (repo / "docs/notes.md").write_text("edited\n", encoding="utf-8")
    (repo / "README.md").write_text("new untracked at root\n", encoding="utf-8")

    after = worktree_state(repo)
    assert after["diff_sha256"] is None, "an apps/web or plain-docs edit changed the diff hash"
    assert after["dirty"] is False
    assert after["untracked_files"] == []


def test_changes_inside_relevant_dirs_flip_the_fingerprint(repo: Path) -> None:
    (repo / "src/pkg/mod.py").write_text("changed logic\n", encoding="utf-8")
    tracked = worktree_state(repo)
    assert tracked["diff_sha256"] is not None
    assert tracked["dirty"] is True

    _git(["checkout", "--", "."], repo)
    (repo / "src/pkg/new_module.py").write_text("untracked source\n", encoding="utf-8")
    untracked = worktree_state(repo)
    assert untracked["diff_sha256"] is None
    assert untracked["untracked_files"] == ["src/pkg/new_module.py"]
    assert untracked["dirty"] is True


def test_methodology_docs_are_relevant_but_other_docs_are_not(repo: Path) -> None:
    (repo / "docs/methodology/protocol.md").write_text("tightened\n", encoding="utf-8")
    state = worktree_state(repo)
    assert state["diff_sha256"] is not None, "docs/methodology is part of the contract"

    _git(["checkout", "--", "."], repo)
    (repo / "docs/notes.md").write_text("reworded\n", encoding="utf-8")
    state = worktree_state(repo)
    assert state["diff_sha256"] is None, "plain docs must not invalidate a run"
