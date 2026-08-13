"""Study-level accounting over every family the thesis tested."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import polars as pl
import pytest

from perp_lab.reporting.study_closure import (
    StudyClosureError,
    StudyUnit,
    _bootstrap_p_value,
    _moments,
    _run_dir,
    _unit_oos_returns,
    aligned_matrix,
    family_oos_series,
    family_results,
    sensitivity_to_the_count,
)

START = datetime(2024, 1, 1, tzinfo=UTC)


def _write_fold(run_dir: Path, engine: str, fold: int, returns: list[float], offset: int) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    times = [START + timedelta(hours=offset + i) for i in range(len(returns))]
    pl.DataFrame({"open_time": times, "net_return": returns}).with_columns(
        pl.col("open_time").cast(pl.Datetime("ms", "UTC"))
    ).write_parquet(run_dir / f"{engine}_fold{fold}_test_equity.parquet")


def _unit(
    tmp_path: Path, family: str, seed: int, returns_by_fold: dict[int, list[float]]
) -> StudyUnit:
    run_dir = tmp_path / f"search_{family}_{seed}"
    offset = 0
    for fold, returns in sorted(returns_by_fold.items()):
        _write_fold(run_dir, "random_search", fold, returns, offset)
        offset += len(returns)
    return StudyUnit("R3", family, "BTCUSDT", seed, "random_search", run_dir)


def test_a_recorded_run_directory_resolves_whatever_separator_it_was_written_with(
    tmp_path: Path,
) -> None:
    # R3 wrote Windows separators, S1 and S2 wrote POSIX ones; the accounting has
    # to read all of them on any platform.
    windows = _run_dir(tmp_path, "artifacts\\runs\\search_breakout_abc")
    posix = _run_dir(tmp_path, "artifacts/runs/search_breakout_abc")
    assert windows == posix == tmp_path / "artifacts" / "runs" / "search_breakout_abc"


def test_folds_are_concatenated_into_one_out_of_sample_series(tmp_path: Path) -> None:
    unit = _unit(tmp_path, "breakout", 1, {0: [0.01, 0.02], 1: [0.03]})
    series = _unit_oos_returns(unit.run_dir, "random_search")
    assert series.height == 3
    assert series["net_return"].to_list() == [0.01, 0.02, 0.03]


def test_overlapping_folds_are_refused_rather_than_double_counted(tmp_path: Path) -> None:
    run_dir = tmp_path / "overlap"
    _write_fold(run_dir, "random_search", 0, [0.01, 0.02], offset=0)
    _write_fold(run_dir, "random_search", 1, [0.03, 0.04], offset=1)  # shares a bar
    with pytest.raises(StudyClosureError, match="overlap"):
        _unit_oos_returns(run_dir, "random_search")


def test_a_fold_without_a_winner_is_absent_rather_than_a_zero_return(tmp_path: Path) -> None:
    # Writing no ledger means the family could not act; recording that as a zero
    # would silently credit it with a flat, costless bar.
    unit = _unit(tmp_path, "sparse", 1, {0: [0.01], 2: [0.05]})
    assert _unit_oos_returns(unit.run_dir, "random_search").height == 2


def test_seeds_are_averaged_within_a_family_not_treated_as_separate_hypotheses(
    tmp_path: Path,
) -> None:
    units = [
        _unit(tmp_path / "a", "breakout", 1, {0: [0.02, 0.04]}),
        _unit(tmp_path / "b", "breakout", 2, {0: [0.00, 0.00]}),
    ]
    series = family_oos_series(units, symbol="BTCUSDT", engine="random_search")
    assert series["breakout"]["net_return"].to_list() == [0.01, 0.02]


def test_a_family_is_reported_once_however_many_seeds_it_ran(tmp_path: Path) -> None:
    units = [
        _unit(tmp_path / "a", "breakout", 1, {0: [0.01] * 40}),
        _unit(tmp_path / "b", "breakout", 2, {0: [0.01] * 40}),
        _unit(tmp_path / "c", "momentum", 1, {0: [-0.01] * 40}),
    ]
    series = family_oos_series(units, symbol="BTCUSDT", engine="random_search")
    results = family_results(units, series, symbol="BTCUSDT")
    assert sorted(r.family for r in results) == ["breakout", "momentum"]
    breakout = next(r for r in results if r.family == "breakout")
    assert breakout.n_seeds == 2
    assert breakout.total_return > 0


def test_the_other_asset_is_not_mixed_into_the_primary_series(tmp_path: Path) -> None:
    btc = _unit(tmp_path / "a", "breakout", 1, {0: [0.02]})
    eth = StudyUnit("R3", "breakout", "ETHUSDT", 1, "random_search", (tmp_path / "b" / "eth"))
    _write_fold(eth.run_dir, "random_search", 0, [-0.5], offset=0)
    series = family_oos_series([btc, eth], symbol="BTCUSDT", engine="random_search")
    assert series["breakout"]["net_return"].to_list() == [0.02]


def test_the_cscv_matrix_keeps_only_bars_where_every_family_was_live(tmp_path: Path) -> None:
    series = {
        "a": pl.DataFrame(
            {"open_time": [START, START + timedelta(hours=1)], "net_return": [0.1, 0.2]}
        ),
        "b": pl.DataFrame({"open_time": [START + timedelta(hours=1)], "net_return": [0.3]}),
    }
    families, matrix = aligned_matrix(series)
    assert families == ["a", "b"]
    assert matrix.shape == (1, 2)
    assert matrix.tolist() == [[0.2, 0.3]]


def test_the_bootstrap_detects_a_planted_edge_and_clears_pure_noise() -> None:
    rng = np.random.default_rng(0)
    noise = rng.normal(0.0, 0.01, size=4000)
    planted = noise + 0.004
    assert _bootstrap_p_value(planted, seed=42) < 0.05
    assert _bootstrap_p_value(noise, seed=42) > 0.05


def test_the_bootstrap_is_reproducible_from_its_seed() -> None:
    returns = np.random.default_rng(3).normal(0.0, 0.01, size=1500)
    assert _bootstrap_p_value(returns, seed=7) == _bootstrap_p_value(returns, seed=7)


def test_moments_report_raw_kurtosis_so_a_gaussian_scores_three() -> None:
    gaussian = np.random.default_rng(1).normal(0.0, 1.0, size=200_000)
    skew, kurtosis = _moments(gaussian)
    assert skew == pytest.approx(0.0, abs=0.05)
    assert kurtosis == pytest.approx(3.0, abs=0.1)


def test_a_flat_series_falls_back_to_gaussian_moments() -> None:
    assert _moments(np.zeros(50)) == (0.0, 3.0)


def test_the_bonferroni_threshold_tightens_as_the_count_grows(tmp_path: Path) -> None:
    units = [_unit(tmp_path, "breakout", 1, {0: [0.01] * 40})]
    series = family_oos_series(units, symbol="BTCUSDT", engine="random_search")
    results = family_results(units, series, symbol="BTCUSDT")
    sensitivity = sensitivity_to_the_count(results, {"few": 10, "many": 100_000})
    assert sensitivity["many"]["bonferroni_threshold"] < sensitivity["few"]["bonferroni_threshold"]
    assert sensitivity["few"]["smallest_raw_p_value"] == sensitivity["many"]["smallest_raw_p_value"]
