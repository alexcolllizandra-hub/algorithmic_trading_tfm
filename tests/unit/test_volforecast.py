"""Volatility-forecasting annex: estimators and models on synthetic series.

* the dataset builder aligns targets causally (a planted future spike never
  leaks into the features of earlier bars);
* HAR beats naive on a GARCH-like series (persistent volatility);
* QLIKE is minimised by the true variance;
* the DM test does not reject for identical forecasts and rejects for a
  clearly better one;
* the LSTM (optional torch) trains deterministically for a fixed seed.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import numpy as np
import polars as pl
import pytest

from perp_lab.volforecast.data import build_vol_dataset, slice_by_time
from perp_lab.volforecast.metrics import diebold_mariano, oos_metrics, qlike
from perp_lab.volforecast.models import fit_har, predict_har, predict_naive

RNG = np.random.default_rng(42)
START = datetime(2021, 1, 1, tzinfo=UTC)


def _garch_returns(n: int, seed: int = 42) -> np.ndarray:
    rng = np.random.default_rng(seed)
    omega, alpha, beta = 4e-8, 0.1, 0.87
    z = rng.standard_normal(n)
    sigma2 = np.empty(n)
    r = np.empty(n)
    sigma2[0] = omega / (1 - alpha - beta)
    r[0] = np.sqrt(sigma2[0]) * z[0]
    for i in range(1, n):
        sigma2[i] = omega + alpha * r[i - 1] ** 2 + beta * sigma2[i - 1]
        r[i] = np.sqrt(sigma2[i]) * z[i]
    return r


def _bars(returns: np.ndarray) -> pl.DataFrame:
    return pl.DataFrame(
        {
            "open_time": [START + timedelta(hours=i) for i in range(returns.size)],
            "log_return": returns,
        }
    )


def test_dataset_alignment_is_causal() -> None:
    n = 3000
    ret = np.full(n, 1e-4)
    spike_at = 2000
    ret[spike_at] = 0.5  # one enormous bar
    dataset = build_vol_dataset(_bars(ret))
    # Times are the bar times of the FEATURE rows; find the row for bar 1975.
    row = np.searchsorted(dataset.times, np.datetime64(START + timedelta(hours=1975), "ns"))
    # Its 24h-forward target window (1976..1999) ends before the spike: small.
    assert dataset.target_log_rv[row] < -5
    # The row at 1976 has the spike inside its window (1977..2000): large.
    row2 = np.searchsorted(dataset.times, np.datetime64(START + timedelta(hours=1976), "ns"))
    assert dataset.target_log_rv[row2] > -2
    # And the trailing HAR feature at 1975 knows nothing of the spike.
    assert dataset.har_features[row, 0] < -5


def test_har_beats_naive_on_garch() -> None:
    ret = _garch_returns(30_000)
    dataset = build_vol_dataset(_bars(ret))
    n = dataset.n
    train = np.zeros(n, dtype=bool)
    test = np.zeros(n, dtype=bool)
    train[: int(n * 0.7)] = True
    test[int(n * 0.7) :] = True

    model = fit_har(dataset, train)
    har = predict_har(model, dataset, test)
    naive = predict_naive(dataset, test)
    true = dataset.target_log_rv[test]
    har_metrics = oos_metrics(har, true, naive)
    assert har_metrics["r2_oos_vs_naive"] > 0.05
    assert har_metrics["qlike"] < oos_metrics(naive, true, naive)["qlike"]


def test_qlike_minimised_by_truth() -> None:
    true = RNG.normal(-4.0, 0.5, 5000)
    assert qlike(true, true) == pytest.approx(0.0, abs=1e-9)
    assert qlike(true + 0.3, true) > 0.01
    assert qlike(true - 0.3, true) > 0.01


def test_diebold_mariano_calibration() -> None:
    true = RNG.normal(-4.0, 0.5, 5000)
    noise_a = true + RNG.normal(0, 0.30, true.size)
    same = diebold_mariano(noise_a, noise_a + 1e-9, true)
    assert same["p_value"] > 0.5
    better = true + RNG.normal(0, 0.10, true.size)
    verdict = diebold_mariano(noise_a, better, true)
    assert verdict["dm_stat"] > 2.0  # positive: model B (better) has lower loss
    assert verdict["p_value"] < 0.01


def test_slice_by_time_bounds() -> None:
    ret = _garch_returns(5000)
    dataset = build_vol_dataset(_bars(ret))
    mask = slice_by_time(
        dataset,
        np.datetime64(START + timedelta(hours=1000), "ns"),
        np.datetime64(START + timedelta(hours=2000), "ns"),
    )
    times = dataset.times[mask]
    assert times.min() >= np.datetime64(START + timedelta(hours=1000), "ns")
    assert times.max() < np.datetime64(START + timedelta(hours=2000), "ns")


def test_lstm_trains_and_is_seed_deterministic() -> None:
    torch = pytest.importorskip("torch")
    del torch
    from perp_lab.volforecast.models import fit_predict_lstm

    ret = _garch_returns(8_000)
    dataset = build_vol_dataset(_bars(ret))
    n = dataset.n
    train = np.zeros(n, dtype=bool)
    val = np.zeros(n, dtype=bool)
    test = np.zeros(n, dtype=bool)
    train[: int(n * 0.6)] = True
    val[int(n * 0.6) : int(n * 0.8)] = True
    test[int(n * 0.8) :] = True

    first = fit_predict_lstm(dataset, train, val, test, seed=42, max_epochs=3)
    second = fit_predict_lstm(dataset, train, val, test, seed=42, max_epochs=3)
    assert np.allclose(first, second)
    assert np.isfinite(first).all()
    assert first.size == int(test.sum())
