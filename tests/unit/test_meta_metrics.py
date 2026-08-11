"""Predictive and economic scorecards for the meta-label layer."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import numpy as np
import polars as pl
import pytest

from perp_lab.backtesting.engine import run_backtest
from perp_lab.meta_labeling.metrics import (
    calibration_table,
    economic_metrics,
    expected_calibration_error,
    predictive_metrics,
)

START = datetime(2024, 1, 1, tzinfo=UTC)


def _prices(n: int, *, drift: float = 0.0) -> pl.DataFrame:
    closes = 100.0 * np.cumprod(np.full(n, 1.0 + drift))
    return pl.DataFrame(
        {
            "open_time": [START + timedelta(hours=i) for i in range(n)],
            "open": closes,
            "high": closes * 1.001,
            "low": closes * 0.999,
            "close": closes,
        }
    )


# --------------------------------------------------------------------------- #
# Predictive
# --------------------------------------------------------------------------- #


def test_a_perfect_ranking_scores_a_pr_auc_of_one() -> None:
    labels = np.array([0] * 30 + [1] * 20)
    probabilities = np.concatenate([np.linspace(0.01, 0.4, 30), np.linspace(0.6, 0.99, 20)])
    metrics = predictive_metrics(labels, probabilities)
    assert metrics.pr_auc == pytest.approx(1.0)
    assert metrics.roc_auc == pytest.approx(1.0)
    assert metrics.pr_auc_lift == pytest.approx(1.0 / 0.4)


def test_an_uninformative_model_lifts_the_base_rate_by_about_nothing() -> None:
    rng = np.random.default_rng(0)
    labels = rng.integers(0, 2, size=4000)
    probabilities = rng.uniform(0.0, 1.0, size=4000)
    metrics = predictive_metrics(labels, probabilities)
    assert metrics.pr_auc_lift == pytest.approx(1.0, abs=0.1)
    assert metrics.roc_auc == pytest.approx(0.5, abs=0.05)


def test_roc_auc_is_undefined_rather_than_neutral_on_a_single_class_block() -> None:
    # A ROC-AUC of 0.5 would read as "measured, no skill"; nothing was measured.
    metrics = predictive_metrics(np.ones(20, dtype=int), np.full(20, 0.7))
    assert np.isnan(metrics.roc_auc)
    assert metrics.pr_auc == pytest.approx(1.0)
    assert metrics.base_rate == pytest.approx(1.0)


def test_a_confident_wrong_model_is_punished_by_brier_and_log_loss() -> None:
    labels = np.array([1] * 20 + [0] * 20)
    honest = np.concatenate([np.full(20, 0.6), np.full(20, 0.4)])
    wrong = np.concatenate([np.full(20, 0.05), np.full(20, 0.95)])
    assert (
        predictive_metrics(labels, wrong).brier_score
        > predictive_metrics(labels, honest).brier_score
    )
    assert predictive_metrics(labels, wrong).log_loss > predictive_metrics(labels, honest).log_loss


def test_calibration_bins_account_for_every_observation() -> None:
    rng = np.random.default_rng(3)
    probabilities = rng.uniform(0.0, 1.0, size=500)
    labels = (rng.uniform(size=500) < probabilities).astype(int)
    table = calibration_table(labels, probabilities, n_bins=10)
    assert int(table["n"].sum()) == 500
    # Probabilities that mean what they say: predicted and realised agree.
    assert expected_calibration_error(labels, probabilities) < 0.1


def test_a_miscalibrated_model_reports_a_large_calibration_error() -> None:
    labels = np.array([0] * 90 + [1] * 10)
    probabilities = np.full(100, 0.9)
    assert expected_calibration_error(labels, probabilities) == pytest.approx(0.8)


def test_malformed_inputs_are_refused() -> None:
    with pytest.raises(ValueError, match="same length"):
        predictive_metrics(np.array([0, 1]), np.array([0.5]))
    with pytest.raises(ValueError, match=r"\[0, 1\]"):
        predictive_metrics(np.array([0, 1]), np.array([0.5, 1.4]))
    with pytest.raises(ValueError, match="binary"):
        predictive_metrics(np.array([0, 2]), np.array([0.5, 0.5]))
    with pytest.raises(ValueError, match="empty"):
        predictive_metrics(np.zeros(0), np.zeros(0))


# --------------------------------------------------------------------------- #
# Economic
# --------------------------------------------------------------------------- #


def test_standing_aside_costs_nothing_and_reports_no_trades() -> None:
    prices = _prices(50, drift=0.001)
    signals = prices.select("open_time").with_columns(pl.lit(0.0).alias("side"))
    metrics = economic_metrics(
        run_backtest(
            signals, prices, timeframe="1h", fee_bps_per_side=4.0, slippage_bps_per_side=1.0
        )
    )
    assert metrics.net_return == pytest.approx(0.0)
    assert metrics.n_trades == 0
    assert metrics.total_cost == pytest.approx(0.0)
    assert metrics.turnover == pytest.approx(0.0)
    assert np.isnan(metrics.profit_factor)


def test_the_scorecard_is_read_from_the_engine_ledger_not_reconstructed() -> None:
    prices = _prices(60, drift=0.002)
    side = np.zeros(60)
    side[10:30] = 1.0
    signals = prices.select("open_time").with_columns(pl.Series("side", side))
    result = run_backtest(
        signals, prices, timeframe="1h", fee_bps_per_side=4.0, slippage_bps_per_side=1.0
    )
    metrics = economic_metrics(result)
    assert metrics.net_return == pytest.approx(result.metrics["total_return"])
    assert metrics.total_cost == pytest.approx(float(result.ledger["cost"].sum()))
    assert metrics.n_trades == result.trades().height
    assert metrics.turnover == pytest.approx(2.0, abs=1e-9), "one round trip moves 2 units"
