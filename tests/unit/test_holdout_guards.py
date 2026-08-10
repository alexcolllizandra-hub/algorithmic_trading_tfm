"""Every guard that stands between the pipeline and the frozen holdout.

Filesystem access times are circumstantial evidence at best: they are disabled on
many volumes, they change when a backup tool reads a file, and they say nothing
about intent. Holdout isolation therefore has to be enforced by code that *fails*,
and each of those failures needs a test that would notice if it were removed.

The guards, in the order a run meets them:

1. the experiment contract refuses a development window that reaches the holdout;
2. a pre-load manifest check refuses a partition whose coverage reaches it, before
   a single row is read;
3. the fold generator refuses to emit a fold that crosses it;
4. the feature engine refuses to build features over rows at or past it;
5. the data lake's loader refuses a frame containing holdout timestamps.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import polars as pl
import pytest

from perp_lab.config import load_data_contract, load_experiment_config
from perp_lab.data.splits import resolve_holdout_start
from perp_lab.eda.datasets import HoldoutLeakageError, assert_no_holdout
from perp_lab.features.registry import build_feature_frame, resolve_feature_set
from perp_lab.search.runner import _assert_partition_before_holdout
from perp_lab.utils.logging import get_logger
from perp_lab.validation.walk_forward import assert_folds_exclude_holdout, generate_walk_forward

HOLDOUT_START = datetime(2026, 1, 1, tzinfo=UTC)


class _Item:
    def __init__(self, kind: str, window: int | None = None) -> None:
        self.kind = kind
        self.window = window
        self.window_slow: int | None = None
        self.lag: int | None = None
        self.source: str | None = None


def _frame(start: datetime, n: int) -> pl.DataFrame:
    times = [start + timedelta(hours=i) for i in range(n)]
    close = [100.0 + i for i in range(n)]
    return pl.DataFrame(
        {
            "open_time": times,
            "open": close,
            "high": [c + 1 for c in close],
            "low": [c - 1 for c in close],
            "close": close,
            "volume": [10.0] * n,
        }
    )


# --------------------------------------------------------------------------- #
# 1. Contract level
# --------------------------------------------------------------------------- #
def test_contract_and_experiment_agree_on_the_holdout_boundary() -> None:
    """The two configs are edited independently; a silent divergence must be caught."""
    exp = load_experiment_config("configs/experiment.yaml")
    contract = load_data_contract("configs/data_contract.yaml")
    contract_holdout = resolve_holdout_start(contract)
    exp.check_against_contract(holdout_start=contract_holdout, cutoff=exp.periods.cutoff_exclusive)
    assert contract_holdout == HOLDOUT_START
    assert exp.periods.development_end_exclusive == exp.periods.holdout_start


def test_experiment_rejects_a_shifted_contract_boundary() -> None:
    exp = load_experiment_config("configs/experiment.yaml")
    with pytest.raises(ValueError, match="holdout_start"):
        exp.check_against_contract(
            holdout_start=exp.periods.holdout_start - timedelta(days=30),
            cutoff=exp.periods.cutoff_exclusive,
        )


def test_experiment_rejects_a_development_window_reaching_into_the_holdout() -> None:
    """The one mistake that would open the holdout without touching any guard."""
    exp = load_experiment_config("configs/experiment.yaml")
    leaky = exp.model_copy(
        update={
            "periods": exp.periods.model_copy(
                update={"development_end_exclusive": exp.periods.holdout_start + timedelta(days=1)}
            )
        }
    )
    with pytest.raises(ValueError, match="frozen holdout"):
        leaky.check_against_contract(
            holdout_start=exp.periods.holdout_start, cutoff=exp.periods.cutoff_exclusive
        )


# --------------------------------------------------------------------------- #
# 2. Pre-load manifest guard (fails before any row is read)
# --------------------------------------------------------------------------- #
def test_preload_guard_rejects_a_partition_whose_manifest_reaches_the_holdout(
    tmp_path: Path,
) -> None:
    class _Paths:
        manifests_dir = tmp_path

    (tmp_path / "bad.json").write_text(
        json.dumps({"period_end": (HOLDOUT_START + timedelta(days=1)).isoformat()}),
        encoding="utf-8",
    )
    with pytest.raises(HoldoutLeakageError, match="Pre-load guard"):
        _assert_partition_before_holdout(
            _Paths(),  # type: ignore[arg-type]
            "bad",
            holdout_start=HOLDOUT_START,
            log=get_logger("test"),
        )


def test_preload_guard_accepts_a_partition_ending_before_the_holdout(tmp_path: Path) -> None:
    class _Paths:
        manifests_dir = tmp_path

    (tmp_path / "good.json").write_text(
        json.dumps({"period_end": (HOLDOUT_START - timedelta(hours=1)).isoformat()}),
        encoding="utf-8",
    )
    _assert_partition_before_holdout(
        _Paths(),  # type: ignore[arg-type]
        "good",
        holdout_start=HOLDOUT_START,
        log=get_logger("test"),
    )


def test_the_real_development_manifests_all_end_before_the_holdout() -> None:
    """The guard is only worth having if the shipped manifests actually satisfy it."""
    manifests = sorted(Path("data/manifests").glob("*_development.json"))
    if not manifests:
        pytest.skip("no processed development manifests in this checkout")
    for path in manifests:
        meta = json.loads(path.read_text(encoding="utf-8"))
        period_end = meta.get("period_end")
        if period_end is None:
            continue
        end = datetime.fromisoformat(str(period_end).replace("Z", "+00:00"))
        assert end < HOLDOUT_START, f"{path.name} covers {end}, which reaches the holdout"


def test_no_holdout_manifest_is_referenced_by_a_development_run() -> None:
    """A development manifest must never be named as if it were a holdout partition."""
    for path in sorted(Path("data/manifests").glob("*_development.json")):
        assert "holdout" not in path.stem


# --------------------------------------------------------------------------- #
# 3. Fold geometry
# --------------------------------------------------------------------------- #
def test_no_generated_fold_crosses_the_frozen_boundary() -> None:
    exp = load_experiment_config("configs/experiment.yaml")
    folds = generate_walk_forward(exp, strict=True)
    assert folds
    for fold in folds:
        assert fold.test_end <= exp.periods.holdout_start
    assert_folds_exclude_holdout(folds, exp.periods.holdout_start)


def test_fold_guard_raises_when_a_fold_would_cross_the_boundary() -> None:
    exp = load_experiment_config("configs/experiment.yaml")
    folds = generate_walk_forward(exp, strict=True)
    # Pretend the holdout began mid-study: every later fold is now illegal.
    with pytest.raises((ValueError, HoldoutLeakageError)):
        assert_folds_exclude_holdout(folds, folds[0].test_start + timedelta(days=1))


# --------------------------------------------------------------------------- #
# 4/5. Row-level guards
# --------------------------------------------------------------------------- #
def test_assert_no_holdout_rejects_a_frame_containing_holdout_rows() -> None:
    frame = _frame(HOLDOUT_START - timedelta(hours=5), 10)  # crosses the boundary
    with pytest.raises(HoldoutLeakageError):
        assert_no_holdout(frame, HOLDOUT_START)


def test_assert_no_holdout_accepts_a_frame_ending_one_bar_early() -> None:
    frame = _frame(HOLDOUT_START - timedelta(hours=10), 10)
    assert_no_holdout(frame, HOLDOUT_START)


def test_feature_engine_refuses_to_build_over_holdout_rows() -> None:
    """Features must never be computed on frozen data, even by accident."""
    frame = _frame(HOLDOUT_START - timedelta(hours=5), 20)
    specs = resolve_feature_set([_Item("sma", 3)])
    with pytest.raises(HoldoutLeakageError):
        build_feature_frame(frame, specs, holdout_start=HOLDOUT_START)


def test_feature_engine_builds_normally_below_the_boundary() -> None:
    frame = _frame(HOLDOUT_START - timedelta(hours=50), 20)
    specs = resolve_feature_set([_Item("sma", 3)])
    out, _ = build_feature_frame(frame, specs, holdout_start=HOLDOUT_START)
    assert "sma_3" in out.columns


def test_boundary_is_exclusive_so_the_first_holdout_bar_is_already_forbidden() -> None:
    """[holdout_start, ...) is left-closed: the bar labelled exactly at the start is in."""
    exactly = pl.DataFrame({"open_time": [HOLDOUT_START]})
    with pytest.raises(HoldoutLeakageError):
        assert_no_holdout(exactly, HOLDOUT_START)

    just_before = pl.DataFrame({"open_time": [HOLDOUT_START - timedelta(microseconds=1)]})
    assert_no_holdout(just_before, HOLDOUT_START)
