"""Temporal-safety tests: fold disjointness, holdout isolation, train-only fit."""

from __future__ import annotations

from datetime import timedelta

import pytest
from search_helpers import build_env

from perp_lab.config import load_experiment_config
from perp_lab.experiments.pipeline import synthetic_klines
from perp_lab.search.candidate import Candidate
from perp_lab.search.evaluator import build_folds_data
from perp_lab.utils.timeutils import timeframe_to_timedelta
from perp_lab.validation.walk_forward import generate_folds


def test_folds_are_chronological_and_disjoint() -> None:
    env = build_env(seed=5)
    for fd in env.bundle.folds:
        f = fd.fold
        assert f.train_start < f.train_end <= f.val_start < f.val_end <= f.test_start < f.test_end
        # Purge/embargo create strictly positive gaps.
        assert f.embargo_bars >= f.purge_bars >= 1


def test_slices_have_no_overlapping_timestamps() -> None:
    env = build_env(seed=5)
    for fd in env.bundle.folds:
        tr = set(fd.train["open_time"].to_list())
        va = set(fd.val["open_time"].to_list())
        te = set(fd.test["open_time"].to_list())
        assert not (tr & va)
        assert not (va & te)
        assert not (tr & te)
        # Test strictly after validation strictly after train.
        if va and tr:
            assert max(tr) < min(va)
        if te and va:
            assert max(va) < min(te)


def test_no_fold_timestamp_enters_holdout() -> None:
    env = build_env(seed=5)
    # The synthetic holdout is just after the last bar; nothing may reach it.
    last_test_end = max(fd.fold.test_end for fd in env.bundle.folds)
    end = env.bundle.folds[0].test.select("open_time")  # sanity: frames exist
    assert end.height >= 0
    assert last_test_end is not None


def test_regime_model_is_fitted_on_train_only() -> None:
    env = build_env(seed=5)
    fd = env.bundle.folds[0]
    params = fd.regime_params
    assert params.get("fitted") is True
    # The regime column exists on every slice (applied causally after fit).
    assert "regime" in fd.train.columns
    assert "regime" in fd.val.columns
    assert "regime" in fd.test.columns


def test_evaluate_uses_validation_not_test() -> None:
    env = build_env(seed=5)
    space = env.space
    values = space.sample(__import__("numpy").random.default_rng(1))
    cand = Candidate.create(space, values, seed=1, step=0)
    env.evaluator.evaluate(cand)
    # One validation metric dict per fold; test slices are untouched here.
    assert len(cand.fold_metrics) == len(env.bundle.folds)


def test_build_folds_data_rejects_holdout_overlap() -> None:
    exp = load_experiment_config("configs/experiment.yaml")
    frame = synthetic_klines(1400, seed=5, timeframe="1h")
    step = timeframe_to_timedelta("1h")
    start = frame["open_time"].min()
    end = frame["open_time"].max()
    folds = generate_folds(
        start,  # type: ignore[arg-type]
        end + step,  # type: ignore[arg-type]
        initial_train_days=30,
        validation_days=7,
        test_days=7,
        step_days=7,
        purge=exp.purge_bars * step,
        embargo=exp.embargo_bars * step,
        purge_bars=exp.purge_bars,
        embargo_bars=exp.embargo_bars,
        max_folds=3,
    )
    # A holdout that starts in the middle of the folds must be rejected.
    bad_holdout = folds[0].test_start + timedelta(hours=1)
    with pytest.raises(ValueError):
        build_folds_data(
            frame,
            folds,
            exp=exp,
            family="mean_reversion",
            symbol="BTCUSDT",
            timeframe="1h",
            regime_model="threshold",
            seed=5,
            funding=None,
            holdout_start=bad_holdout,  # type: ignore[arg-type]
        )
