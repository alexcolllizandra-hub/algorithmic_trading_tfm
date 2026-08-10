"""Tests for expanding walk-forward folds with purge and embargo."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from itertools import pairwise

import polars as pl
import pytest

from perp_lab.config import load_experiment_config
from perp_lab.validation.walk_forward import (
    assert_folds_exclude_holdout,
    generate_folds,
    generate_walk_forward,
    split_fold,
)

_DEV_START = datetime(2020, 1, 1, tzinfo=UTC)
_DEV_END = datetime(2023, 1, 1, tzinfo=UTC)


def _folds(**kw: object):
    defaults: dict[str, object] = {
        "initial_train_days": 365,
        "validation_days": 90,
        "test_days": 90,
        "step_days": 90,
        "purge": timedelta(days=4),
        "embargo": timedelta(days=5),
        "purge_bars": 96,
        "embargo_bars": 118,
    }
    defaults.update(kw)
    return generate_folds(_DEV_START, _DEV_END, **defaults)  # type: ignore[arg-type]


def test_folds_are_chronologically_ordered_and_disjoint() -> None:
    for f in _folds():
        assert f.train_start < f.train_end <= f.val_start
        assert f.val_start < f.val_end <= f.test_start
        assert f.test_start < f.test_end


def test_purge_and_embargo_create_real_gaps() -> None:
    f = _folds()[0]
    # Embargo gap between train and validation; purge gap between validation and test.
    assert f.val_start - f.train_end == timedelta(days=5)
    assert f.test_start - f.val_end == timedelta(days=4)


def test_expanding_training_grows_each_fold() -> None:
    folds = _folds()
    spans = [(f.train_end - f.train_start) for f in folds]
    assert all(earlier < later for earlier, later in pairwise(spans))
    assert all(f.train_start == _DEV_START for f in folds)


def test_test_windows_are_non_overlapping() -> None:
    folds = _folds()
    for a, b in pairwise(folds):
        assert a.test_end <= b.test_start  # strictly no OOS overlap


def test_folds_never_reach_holdout() -> None:
    folds = _folds()
    for f in folds:
        assert f.test_end <= _DEV_END
    assert_folds_exclude_holdout(folds, _DEV_END)


def test_holdout_guard_raises_when_crossed() -> None:
    folds = _folds()
    with pytest.raises(ValueError, match="frozen holdout"):
        assert_folds_exclude_holdout(folds, folds[-1].test_end - timedelta(days=1))


def test_split_fold_produces_disjoint_frames() -> None:
    times = [_DEV_START + timedelta(hours=i) for i in range(24 * 800)]
    df = pl.DataFrame({"open_time": times, "close": list(range(len(times)))})
    f = _folds()[0]
    parts = split_fold(df, f)
    tr, va, te = parts["train"], parts["validation"], parts["test"]
    assert tr["open_time"].max() < va["open_time"].min()  # type: ignore[operator]
    assert va["open_time"].max() < te["open_time"].min()  # type: ignore[operator]
    assert te.height > 0


def test_folds_are_reproducible() -> None:
    a = [f.to_dict() for f in _folds()]
    b = [f.to_dict() for f in _folds()]
    assert a == b


def test_generate_from_repo_config_meets_min_folds() -> None:
    cfg = load_experiment_config("configs/experiment.yaml")
    folds = generate_walk_forward(cfg, strict=True)  # raises if < min_folds
    assert len(folds) >= cfg.walk_forward.min_folds
    assert_folds_exclude_holdout(folds, cfg.periods.holdout_start)


def test_strict_raises_when_span_too_short() -> None:
    cfg = load_experiment_config("configs/experiment.yaml")
    short = cfg.model_copy(
        update={"walk_forward": cfg.walk_forward.model_copy(update={"initial_train_days": 100000})}
    )
    with pytest.raises(ValueError, match="min_folds"):
        generate_walk_forward(short, strict=True)
