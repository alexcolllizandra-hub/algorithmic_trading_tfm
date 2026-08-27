"""Phase H: the single, recorded opening of the frozen holdout."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import polars as pl
import pytest

from perp_lab.experiments.final_holdout import (
    FinalEvaluationError,
    buy_and_hold,
    git_state,
    load_frozen_candidate,
)


def _winners(tmp_path: Path, seed: int, entries: list[dict]) -> Path:
    run_dir = tmp_path / f"run_{seed}"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "random_search_fold_winners.json").write_text(json.dumps(entries), encoding="utf-8")
    return run_dir


def _sealed(fold: int, name: str = "cand", **params: object) -> dict:
    return {
        "fold": fold,
        "winner": f"{name}-{fold}",
        "params": params or {"level_window": 24},
        "selection_fingerprint": f"fp{fold}",
        "frozen_before_test": True,
    }


def _load(run_dirs: dict[int, Path]):
    return load_frozen_candidate(
        run_dirs,
        family="volatility_breakout",
        symbol="BTCUSDT",
        timeframe="1h",
        engine="random_search",
    )


def test_the_last_fold_is_the_one_carried_into_the_holdout(tmp_path: Path) -> None:
    # Every earlier selection was superseded before the holdout window began.
    run_dirs = {1: _winners(tmp_path, 1, [_sealed(0), _sealed(14), _sealed(7)])}
    candidate = _load(run_dirs)
    assert candidate.fold == 14
    assert candidate.members[0].candidate_id == "cand-14"


def test_folds_that_found_no_winner_are_skipped_not_treated_as_the_last(tmp_path: Path) -> None:
    entries = [_sealed(12), {"fold": 14, "winner": None, "reason": "no feasible candidate"}]
    candidate = _load({1: _winners(tmp_path, 1, entries)})
    assert candidate.fold == 12


def test_a_winner_not_sealed_before_its_test_slice_is_refused(tmp_path: Path) -> None:
    leaky = _sealed(14) | {"frozen_before_test": False}
    with pytest.raises(FinalEvaluationError, match="frozen before"):
        _load({1: _winners(tmp_path, 1, [leaky])})


def test_seeds_that_disagree_on_the_last_fold_are_refused(tmp_path: Path) -> None:
    # A candidate assembled from different folds would not be one frozen object.
    run_dirs = {
        1: _winners(tmp_path, 1, [_sealed(14)]),
        2: _winners(tmp_path, 2, [_sealed(13)]),
    }
    with pytest.raises(FinalEvaluationError, match="disagree"):
        _load(run_dirs)


def test_a_seed_with_no_winner_at_all_is_refused(tmp_path: Path) -> None:
    entries = [{"fold": 0, "winner": None, "reason": "no feasible candidate"}]
    with pytest.raises(FinalEvaluationError, match="sealed no winner"):
        _load({1: _winners(tmp_path, 1, entries)})


def test_a_missing_frozen_record_is_refused_rather_than_reconstructed(tmp_path: Path) -> None:
    empty = tmp_path / "nothing"
    empty.mkdir()
    with pytest.raises(FinalEvaluationError, match="No frozen winners"):
        _load({1: empty})


def test_every_seed_is_carried_into_the_candidate(tmp_path: Path) -> None:
    run_dirs = {s: _winners(tmp_path, s, [_sealed(14)]) for s in (1, 2, 3)}
    candidate = _load(run_dirs)
    assert [m.seed for m in candidate.members] == [1, 2, 3]
    assert candidate.to_dict()["n_members"] == 3


def test_buy_and_hold_measures_the_same_window_held_long() -> None:
    n = 2000
    close = 100.0 * np.power(1.0001, np.arange(n, dtype=float))
    frame = pl.DataFrame(
        {"open_time": np.arange(n) * 3_600_000, "close": close},
    ).with_columns(pl.col("open_time").cast(pl.Datetime("ms", "UTC")))
    metrics = buy_and_hold(frame, timeframe="1h", days_per_year=365)
    assert metrics["total_return"] == pytest.approx(close[-1] / close[0] - 1.0, rel=1e-6)
    assert metrics["exposure"] == pytest.approx(1.0)


def test_the_run_records_which_commit_it_ran_from() -> None:
    state = git_state(Path.cwd())
    assert len(state["commit"]) == 40
    assert isinstance(state["worktree_clean"], bool)
