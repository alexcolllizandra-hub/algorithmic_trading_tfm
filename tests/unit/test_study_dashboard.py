"""What the consolidated study payload must guarantee before anyone reads it.

The dashboard is where a reader who never opens a notebook forms their opinion
of the study, so the properties tested here are about honesty of presentation as
much as correctness: the decimated curve must end where the real curve ends, the
resampling fan must be reproducible and must not quietly change the result it
describes, and the criteria grid must report what the gate scored rather than a
rounded impression of it.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import polars as pl
import pytest

from perp_lab.backtesting.metrics import performance_metrics
from perp_lab.reporting.study_dashboard import (
    DAYS_PER_YEAR,
    TIMEFRAME,
    StudyDashboardError,
    _decimate,
    _summary,
    criteria_matrix,
    monte_carlo_fan,
)


def _series(returns: list[float]) -> pl.DataFrame:
    n = len(returns)
    return pl.DataFrame(
        {"open_time": np.arange(n) * 3_600_000, "net_return": returns},
    ).with_columns(pl.col("open_time").cast(pl.Datetime("ms", "UTC")))


def test_the_decimated_curve_still_ends_at_the_true_final_equity() -> None:
    rng = np.random.default_rng(7)
    returns = rng.normal(0.0002, 0.01, size=5_000)
    frame = _series(list(returns))

    points = _decimate(frame, 100)

    exact = float(np.prod(1.0 + returns))
    assert len(points) == 100
    assert points[-1]["equity"] == pytest.approx(exact, rel=1e-12)
    assert points[0]["equity"] == pytest.approx(1.0 + returns[0], rel=1e-12)


def test_a_series_shorter_than_the_budget_is_returned_whole() -> None:
    frame = _series([0.01, -0.02, 0.03])
    points = _decimate(frame, 600)
    assert len(points) == 3


def test_an_empty_series_decimates_to_nothing_rather_than_failing() -> None:
    assert _decimate(_series([]), 600) == []


def test_the_summary_reports_the_worst_drawdown_not_the_last_one() -> None:
    # Up, deep trough, partial recovery, milder dip: the deepest trough wins.
    returns = np.array([0.5, -0.5, 0.4, -0.1], dtype=float)
    summary = _summary(returns)
    assert summary["max_drawdown"] == pytest.approx(-0.5, rel=1e-9)


def test_the_summary_agrees_with_the_metrics_the_reports_were_written_from() -> None:
    """The dashboard must not contradict the tables it illustrates.

    ``_summary`` exists only because the payload needs three numbers per seed
    without paying for the full metric suite, so it has to reproduce
    ``performance_metrics`` exactly — including its convention that drawdown is
    measured from the peak of the realised path rather than from initial
    capital. If the two ever diverge, the dashboard would show one drawdown and
    the thesis another for the same series.
    """
    rng = np.random.default_rng(21)
    returns = rng.normal(0.0001, 0.008, size=4_000)

    mine = _summary(returns)
    theirs = performance_metrics(
        returns,
        timeframe=TIMEFRAME,
        positions=np.ones(returns.size),
        days_per_year=DAYS_PER_YEAR,
    )

    assert mine["total_return"] == pytest.approx(theirs["total_return"], rel=1e-12)
    assert mine["sharpe"] == pytest.approx(theirs["sharpe"], rel=1e-12)
    assert mine["max_drawdown"] == pytest.approx(theirs["max_drawdown"], rel=1e-12)


def test_a_flat_series_gets_a_zero_sharpe_instead_of_dividing_by_zero() -> None:
    summary = _summary(np.zeros(50))
    assert summary["sharpe"] == 0.0
    assert summary["total_return"] == 0.0


class TestMonteCarloFan:
    """The fan is a resampling of the observed series, and must behave like one."""

    @staticmethod
    def _returns() -> np.ndarray:
        rng = np.random.default_rng(11)
        return rng.normal(0.0001, 0.006, size=3_000)

    def test_the_same_seed_reproduces_the_same_fan(self) -> None:
        returns = self._returns()
        first = monte_carlo_fan(returns, seed=99, n_paths=200)
        second = monte_carlo_fan(returns, seed=99, n_paths=200)
        assert first["bands"] == second["bands"]
        assert first["terminal"] == second["terminal"]

    def test_a_different_seed_moves_the_fan(self) -> None:
        returns = self._returns()
        first = monte_carlo_fan(returns, seed=1, n_paths=200)
        second = monte_carlo_fan(returns, seed=2, n_paths=200)
        assert first["terminal"]["p50"] != second["terminal"]["p50"]

    def test_the_bands_are_ordered_at_every_checkpoint(self) -> None:
        fan = monte_carlo_fan(self._returns(), seed=3, n_paths=300)
        bands = fan["bands"]
        for i in range(len(bands["p50"])):
            assert bands["p05"][i] <= bands["p25"][i] <= bands["p50"][i]
            assert bands["p50"][i] <= bands["p75"][i] <= bands["p95"][i]

    def test_the_observed_path_is_the_real_one_and_is_not_resampled(self) -> None:
        returns = self._returns()
        fan = monte_carlo_fan(returns, seed=4, n_paths=100)
        exact = float(np.prod(1.0 + returns))
        assert fan["observed"][-1] == pytest.approx(exact, rel=1e-12)
        assert fan["terminal"]["observed_total_return"] == pytest.approx(exact - 1.0, rel=1e-12)

    def test_resampling_preserves_the_sign_of_a_strongly_positive_series(self) -> None:
        # A series that genuinely compounds upward should not resample into a
        # coin flip; if it does, the block construction is broken.
        returns = np.full(2_000, 0.001)
        fan = monte_carlo_fan(returns, seed=5, n_paths=200)
        assert fan["terminal"]["probability_positive"] == 1.0
        assert fan["terminal"]["p05"] > 0.0

    def test_every_resampled_bar_comes_from_the_observed_series(self) -> None:
        # Three distinct values: any resampled path may only ever compound
        # products of those three, so the terminal wealth must be reachable.
        returns = np.array([0.1, 0.0, -0.1] * 10, dtype=float)
        fan = monte_carlo_fan(returns, seed=6, n_paths=200)
        n = returns.size
        assert fan["terminal"]["p95"] <= (1.1**n) - 1.0
        assert fan["terminal"]["p05"] >= (0.9**n) - 1.0

    def test_an_empty_series_is_refused_rather_than_resampled(self) -> None:
        with pytest.raises(StudyDashboardError, match="empty"):
            monte_carlo_fan(np.array([], dtype=float))

    def test_the_payload_says_what_it_measures(self) -> None:
        fan = monte_carlo_fan(self._returns(), seed=8, n_paths=100)
        assert fan["measures"] == "path_risk_not_significance"
        assert fan["method"] == "stationary_bootstrap"


def test_the_criteria_grid_reports_the_counts_the_gate_recorded(tmp_path: Path) -> None:
    report = tmp_path / "reports/r3_gate/r3_full_budget100_ga21/thesis_report.json"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(
        json.dumps(
            {
                "primary_table_rs": [
                    {
                        "family": "volatility_breakout",
                        "symbol": "BTCUSDT",
                        "verdict": "REJECTED",
                        "diagnostic_note": "partial non-robust signal",
                        "majority_required": 6,
                        "median_oos_return": 0.065,
                        "median_oos_sharpe": 0.215,
                        "median_buy_and_hold_return": 0.523,
                        "min_oos_trades_met": {
                            "n_pass": 10,
                            "n_seeds": 10,
                            "veto_triggered": False,
                        },
                        "criteria": {
                            "positive_total_return": {
                                "label": "C1 positive return",
                                "n_pass": 6,
                                "n_seeds": 10,
                                "majority_required": 6,
                                "pass": True,
                            },
                            "bootstrap_sharpe_ci_excludes_zero": {
                                "label": "C2 bootstrap Sharpe CI",
                                "n_pass": 0,
                                "n_seeds": 10,
                                "majority_required": 6,
                                "pass": False,
                            },
                        },
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    matrix = criteria_matrix(tmp_path)
    row = matrix["volatility_breakout|BTCUSDT"]

    assert row["verdict"] == "REJECTED"
    assert [c["label"] for c in row["criteria"]] == [
        "C1 positive return",
        "C2 bootstrap Sharpe CI",
    ]
    assert row["criteria"][1]["passed"] == 0
    assert row["criteria"][1]["met"] is False
    # The trade-count check is a veto, not a seventh criterion; it must not be
    # merged into the grid, because doing so would imply the family cleared
    # seven bars when the gate only ever set six.
    assert len(row["criteria"]) == 2
    assert row["min_trades_veto"] == {"passed": 10, "of": 10, "triggered": False}


def test_a_missing_gate_report_is_refused_rather_than_defaulted(tmp_path: Path) -> None:
    with pytest.raises(StudyDashboardError, match="missing"):
        criteria_matrix(tmp_path)
