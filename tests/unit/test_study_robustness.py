"""Tests for study-level baselines, bootstrap and cost stress.

The property that matters most here is negative: seeds must never be pooled into
one long out-of-sample series. A test suite that only checked the tallies would
not notice if someone concatenated ten replays of the same price history.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import polars as pl
import pytest

from perp_lab.evaluation.study_robustness import (
    BLOCK_SIZES,
    analyse_run,
    analyse_study_robustness,
    load_oos_ledger,
)

FEE_BPS = 2.0
SLIP_BPS = 1.0


def _ledger(n: int, *, start: datetime, drift: float, seed: int) -> pl.DataFrame:
    rng = np.random.default_rng(seed)
    oo = rng.normal(drift, 0.01, n)
    position = np.sign(rng.normal(0.2, 1.0, n))
    turnover = np.abs(np.diff(position, prepend=0.0))
    fee = turnover * FEE_BPS / 1e4
    slippage = turnover * SLIP_BPS / 1e4
    funding_rate = np.zeros(n)
    funding = position * funding_rate
    gross = position * oo
    net = gross - fee - slippage - funding
    return pl.DataFrame(
        {
            "open_time": [start + timedelta(hours=i) for i in range(n)],
            "position": position,
            "oo_return": oo,
            "gross_return": gross,
            "net_return": net,
            "fee": fee,
            "slippage": slippage,
            "cost": fee + slippage,
            "funding_rate_in_bar": funding_rate,
            "funding": funding,
            "turnover": turnover,
            "equity": np.cumprod(1.0 + net),
            "execution_price": 100.0 * np.cumprod(1.0 + oo),
        }
    )


def _write_run(run_dir: Path, method: str, *, n_folds: int = 12, drift: float, seed: int) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    start = datetime(2024, 1, 1, tzinfo=UTC)
    for fold in range(n_folds):
        frame = _ledger(200, start=start, drift=drift, seed=seed * 100 + fold)
        frame.write_parquet(run_dir / f"{method}_fold{fold}_test_equity.parquet")
        start += timedelta(hours=400)


def test_folds_are_concatenated_in_numeric_not_lexicographic_order(tmp_path: Path) -> None:
    """fold10 must not land between fold1 and fold2 and scramble the chronology."""
    _write_run(tmp_path / "run", "random_search", n_folds=12, drift=0.0, seed=1)
    ledger = load_oos_ledger(tmp_path / "run", "random_search")
    times = ledger["open_time"].to_list()
    assert times == sorted(times)
    assert ledger.height == 12 * 200


def test_out_of_order_ledgers_are_rejected_rather_than_analysed(tmp_path: Path) -> None:
    run = tmp_path / "run"
    _write_run(run, "random_search", n_folds=3, drift=0.0, seed=1)
    # Overwrite fold 2 with bars that predate fold 0.
    _ledger(200, start=datetime(2020, 1, 1, tzinfo=UTC), drift=0.0, seed=9).write_parquet(
        run / "random_search_fold2_test_equity.parquet"
    )
    with pytest.raises(ValueError, match="not chronological"):
        load_oos_ledger(run, "random_search")


def test_missing_ledgers_raise_instead_of_returning_an_empty_result(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_oos_ledger(tmp_path, "genetic_algorithm")


def test_analyse_run_reports_every_required_test(tmp_path: Path) -> None:
    _write_run(tmp_path / "run", "random_search", drift=0.0005, seed=3)
    report = analyse_run(
        tmp_path / "run",
        "random_search",
        resamples=80,
        fee_bps_per_side=FEE_BPS,
        slippage_bps_per_side=SLIP_BPS,
    )
    assert set(report["tests"]) == {
        "positive_total_return",
        "beats_buy_and_hold",
        "survives_double_costs",
        "bootstrap_sharpe_ci_excludes_zero",
    }
    assert set(report["bootstrap_sharpe"]) == {f"block_{b}" for b in BLOCK_SIZES}
    assert report["n_bars"] == 12 * 200


def test_doubling_costs_never_improves_the_result(tmp_path: Path) -> None:
    _write_run(tmp_path / "run", "random_search", drift=0.0005, seed=4)
    report = analyse_run(
        tmp_path / "run",
        "random_search",
        resamples=50,
        fee_bps_per_side=FEE_BPS,
        slippage_bps_per_side=SLIP_BPS,
    )
    stressed = report["cost_stress_2x"]["metrics"]["total_return"]
    assert stressed <= report["strategy"]["total_return"]


def test_bootstrap_uses_only_one_runs_own_series(tmp_path: Path) -> None:
    """Ten seeds must not make the interval sqrt(10) times narrower."""
    units = {}
    for seed in range(4):
        run = tmp_path / f"run{seed}"
        for method in ("random_search", "genetic_algorithm"):
            _write_run(run, method, drift=0.0002, seed=seed + 1)
        units[f"BTCUSDT|seed={seed}"] = {
            "symbol": "BTCUSDT",
            "seed": seed,
            "run_dir": str(run),
        }
    payload = analyse_study_robustness(
        units, resamples=80, fee_bps_per_side=FEE_BPS, slippage_bps_per_side=SLIP_BPS
    )

    n_bars = {entry["n_bars"] for entry in payload["per_run"].values()}
    assert n_bars == {12 * 200}, "a run's series grew, so seeds were pooled into one history"
    assert len(payload["per_run"]) == 4 * 2
    assert "never concatenated" in payload["method_note"]


def test_tally_counts_seeds_for_each_symbol_and_engine(tmp_path: Path) -> None:
    units = {}
    for seed in range(5):
        run = tmp_path / f"run{seed}"
        for method in ("random_search", "genetic_algorithm"):
            _write_run(run, method, drift=0.001, seed=seed + 1)
        units[f"ETHUSDT|seed={seed}"] = {"symbol": "ETHUSDT", "seed": seed, "run_dir": str(run)}

    tally = analyse_study_robustness(
        units, resamples=60, fee_bps_per_side=FEE_BPS, slippage_bps_per_side=SLIP_BPS
    )["by_symbol_and_engine"]
    for group in ("ETHUSDT|random_search", "ETHUSDT|genetic_algorithm"):
        row = tally[group]
        assert row["n_seeds"] == 5
        for key in ("n_positive", "n_beat_buy_and_hold", "n_survive_double_costs"):
            assert 0 <= row[key] <= 5
        assert row["min_total_return"] <= row["median_total_return"] <= row["max_total_return"]


def test_units_without_artifacts_are_skipped_not_counted(tmp_path: Path) -> None:
    units = {
        "BTCUSDT|seed=0": {"symbol": "BTCUSDT", "seed": 0, "run_dir": str(tmp_path / "missing")},
    }
    payload = analyse_study_robustness(
        units, resamples=40, fee_bps_per_side=FEE_BPS, slippage_bps_per_side=SLIP_BPS
    )
    assert payload["per_run"] == {}
    assert payload["by_symbol_and_engine"] == {}
