"""Tests for the crash-safe experiment journal and checkpoint.

The point of these files is to survive an interruption, so the tests simulate
corruption and partial writes rather than only checking the happy path.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from perp_lab.tracking.journal import Checkpoint, Journal, atomic_write_json, atomic_write_text


def test_atomic_write_leaves_no_temporary_files(tmp_path: Path) -> None:
    target = tmp_path / "status.json"
    atomic_write_json(target, {"a": 1})
    assert json.loads(target.read_text()) == {"a": 1}
    assert list(tmp_path.glob(".*tmp*")) == []


def test_atomic_write_replaces_previous_content_wholesale(tmp_path: Path) -> None:
    target = tmp_path / "f.txt"
    atomic_write_text(target, "a much longer original content")
    atomic_write_text(target, "short")
    assert target.read_text() == "short"


def test_events_are_appended_one_json_object_per_line(tmp_path: Path) -> None:
    journal = Journal(tmp_path)
    journal.event("started", unit="BTCUSDT/seed=1")
    journal.event("finished", unit="BTCUSDT/seed=1", sharpe=0.3)
    lines = journal.events_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["kind"] == "started"
    assert json.loads(lines[1])["sharpe"] == 0.3


def test_a_truncated_final_event_line_is_skipped_not_fatal(tmp_path: Path) -> None:
    """A kill mid-write must cost at most the last event, never the whole history."""
    journal = Journal(tmp_path)
    journal.event("a", i=1)
    journal.event("b", i=2)
    with journal.events_path.open("a", encoding="utf-8") as fh:
        fh.write('{"ts": "2026-01-01", "kind": "c"')  # truncated
    events = journal.read_events()
    assert [e["kind"] for e in events] == ["a", "b"]


def test_status_reports_progress_and_a_work_based_eta(tmp_path: Path) -> None:
    journal = Journal(tmp_path)
    payload = journal.status(state="running", completed=4, total=20, phase="search")
    assert payload["progress"] == 0.2
    assert payload["state"] == "running"
    assert payload["eta_seconds"] is not None
    assert journal.read_status()["completed"] == 4


def test_status_does_not_invent_an_eta_before_any_work_finishes(tmp_path: Path) -> None:
    payload = Journal(tmp_path).status(state="running", completed=0, total=20)
    assert payload["eta_seconds"] is None
    assert payload["seconds_per_unit"] is None


def test_checkpoint_round_trips_completed_units(tmp_path: Path) -> None:
    cp = Checkpoint(tmp_path)
    assert not cp.is_done("BTCUSDT|1")
    cp.mark_done("BTCUSDT|1", {"run_id": "abc", "sharpe": 0.2})
    assert cp.is_done("BTCUSDT|1")
    stored = cp.result("BTCUSDT|1")
    assert stored is not None and stored["run_id"] == "abc"

    reopened = Checkpoint(tmp_path)
    assert reopened.completed_keys() == ["BTCUSDT|1"]
    assert reopened.results()["BTCUSDT|1"]["sharpe"] == 0.2


def test_resuming_skips_only_finished_units(tmp_path: Path) -> None:
    cp = Checkpoint(tmp_path)
    for key in ("a", "b"):
        cp.mark_done(key, {"ok": True})
    pending = [k for k in ("a", "b", "c", "d") if not Checkpoint(tmp_path).is_done(k)]
    assert pending == ["c", "d"]


def test_a_corrupt_checkpoint_fails_loudly(tmp_path: Path) -> None:
    """Silently discarding finished work would be worse than refusing to start."""
    (tmp_path / "checkpoint.json").write_text("{not json", encoding="utf-8")
    with pytest.raises(ValueError, match="corrupt"):
        Checkpoint(tmp_path)


def test_resume_refuses_an_incompatible_contract(tmp_path: Path) -> None:
    cp = Checkpoint(tmp_path)
    cp.set_meta(config_hash="aaa", git_commit="c1")
    cp.mark_done("a", {"ok": True})

    reopened = Checkpoint(tmp_path)
    reopened.assert_compatible(config_hash="aaa", git_commit="c1")
    with pytest.raises(ValueError, match="different"):
        reopened.assert_compatible(config_hash="bbb", git_commit="c1")


def test_fresh_checkpoint_accepts_any_contract(tmp_path: Path) -> None:
    Checkpoint(tmp_path).assert_compatible(config_hash="anything")
