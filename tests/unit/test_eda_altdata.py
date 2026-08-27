"""Alternative-data annex: estimators validated on synthetics + data contracts.

* event_study recovers a planted volatility spike at offset 0 and stays flat
  elsewhere; with no planted effect the event/control ratio is ~1 and the
  permutation test does not reject.
* fear_greed_conditional recovers a planted monotone dependence and covers
  zero when there is none.
* the loaders enforce the development-partition guard.
* the curated macro-events CSV has the verified counts and correct
  ET->UTC conversion on both sides of a DST change.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import cast

import numpy as np
import polars as pl
import pytest

from perp_lab.eda.altdata import (
    event_hour_vs_matched_control,
    event_study,
    fear_greed_conditional,
    load_fear_greed,
)
from perp_lab.eda.datasets import HoldoutLeakageError

RNG = np.random.default_rng(42)
N_BARS = 20_000
START = datetime(2021, 1, 1, tzinfo=UTC)


def _bars(returns: np.ndarray) -> pl.DataFrame:
    return pl.DataFrame(
        {
            "open_time": [START + timedelta(hours=i) for i in range(returns.size)],
            "log_return": returns,
        }
    )


def _event_times(step_hours: int = 500, count: int = 30) -> pl.Series:
    # Events at 30-minute past the hour, inside a bar's interval.
    return pl.Series(
        [START + timedelta(hours=step_hours * (i + 1), minutes=30) for i in range(count)]
    )


def test_event_study_recovers_planted_spike() -> None:
    ret = RNG.standard_normal(N_BARS) * 0.001
    events = _event_times()
    pos = (
        pl.Series([START + timedelta(hours=h) for h in range(N_BARS)])
        .search_sorted(events, side="right")
        .to_numpy()
        - 1
    )
    ret[pos] += np.where(RNG.random(pos.size) > 0.5, 0.02, -0.02)

    study = event_study(_bars(ret), events, window_bars=6)
    at_zero = study.filter(pl.col("offset_bars") == 0)["mean_absret_bps"].item()
    away = float(
        cast(
            "float", study.filter(pl.col("offset_bars").abs() >= 3)["mean_absret_bps"].mean() or 0.0
        )
    )
    assert at_zero > 5 * away
    assert study.filter(pl.col("offset_bars") == 0)["n_events"].item() == events.len()


def test_event_study_flat_without_effect() -> None:
    ret = RNG.standard_normal(N_BARS) * 0.001
    study = event_study(_bars(ret), _event_times(), window_bars=6)
    ratio = (
        study.filter(pl.col("offset_bars") == 0)["mean_absret_bps"].item()
        / study["mean_absret_bps"].mean()
    )
    assert 0.5 < ratio < 1.6


def test_matched_control_permutation() -> None:
    ret = RNG.standard_normal(N_BARS) * 0.001
    events = _event_times()
    null_result = event_hour_vs_matched_control(_bars(ret), events, n_boot=300)
    assert null_result["p_value"] > 0.05

    pos = (
        pl.Series([START + timedelta(hours=h) for h in range(N_BARS)])
        .search_sorted(events, side="right")
        .to_numpy()
        - 1
    )
    ret2 = ret.copy()
    ret2[pos] += 0.02
    spike = event_hour_vs_matched_control(_bars(ret2), events, n_boot=300)
    assert spike["ratio"] > 3.0
    assert spike["p_value"] < 0.05


def _fg_frame(values: np.ndarray) -> pl.DataFrame:
    return pl.DataFrame(
        {
            "date": [START + timedelta(days=i) for i in range(values.size)],
            "value": values,
            "classification": ["x"] * values.size,
        }
    )


def test_fear_greed_conditional_recovers_dependence() -> None:
    n_days = 700
    values = RNG.integers(5, 96, n_days)
    # Plant: higher F&G -> higher next-day drift.
    ret = np.zeros(n_days * 24 + 48)
    for day, value in enumerate(values):
        start = (day + 1) * 24
        ret[start : start + 24] += (value - 50) / 50 * 0.002
    ret += RNG.standard_normal(ret.size) * 0.0005
    table = fear_greed_conditional(_fg_frame(values), _bars(ret), n_boot=200)
    assert table.height == 5
    assert table["fwd_ret_bps"][4] > table["fwd_ret_bps"][0]
    assert table["fwd_ret_lo"][4] > 0 > table["fwd_ret_hi"][0]


def test_fear_greed_conditional_null_covers_zero() -> None:
    n_days = 700
    values = RNG.integers(5, 96, n_days)
    ret = RNG.standard_normal(n_days * 24 + 48) * 0.002
    table = fear_greed_conditional(_fg_frame(values), _bars(ret), n_boot=200)
    covering = ((table["fwd_ret_lo"] <= 0) & (table["fwd_ret_hi"] >= 0)).sum()
    assert covering >= 4


def test_load_fear_greed_guard(tmp_path: Path) -> None:
    frame = _fg_frame(np.arange(10))
    path = tmp_path / "fg.parquet"
    frame.write_parquet(path)
    holdout = START + timedelta(days=5)
    clipped = load_fear_greed(path, holdout_start=holdout)
    assert clipped.height == 5
    # A frame that somehow bypasses the clip must raise.
    with pytest.raises(HoldoutLeakageError):
        from perp_lab.eda.datasets import assert_no_holdout

        assert_no_holdout(frame, holdout, time_col="date")


def test_macro_events_csv_contract() -> None:
    csv_path = Path("configs/altdata/us_macro_events.csv")
    frame = pl.read_csv(csv_path).with_columns(
        pl.col("datetime_utc").str.to_datetime("%Y-%m-%dT%H:%M:%SZ", time_zone="UTC")
    )
    assert frame.height == 120
    counts = dict(frame.group_by("event_type").agg(pl.len()).iter_rows())
    assert counts == {"cpi_release": 71, "fomc_decision": 49}
    # All inside the development window.
    dt_min, dt_max = frame["datetime_utc"].min(), frame["datetime_utc"].max()
    assert isinstance(dt_min, datetime) and isinstance(dt_max, datetime)
    assert dt_min >= datetime(2020, 1, 1, tzinfo=UTC)
    assert dt_max < datetime(2026, 1, 1, tzinfo=UTC)
    # DST conversion: 08:30 ET is 13:30 UTC in winter, 12:30 UTC in summer.
    jan = frame.filter(pl.col("local_time") == "2020-01-14 08:30 ET")["datetime_utc"].item()
    jul = frame.filter(pl.col("local_time") == "2020-07-14 08:30 ET")["datetime_utc"].item()
    assert (jan.hour, jan.minute) == (13, 30)
    assert (jul.hour, jul.minute) == (12, 30)
    # The two 2020 emergency FOMC actions carry non-standard times.
    emergencies = frame.filter(pl.col("note").str.contains("emergency"))
    assert emergencies.height == 2
