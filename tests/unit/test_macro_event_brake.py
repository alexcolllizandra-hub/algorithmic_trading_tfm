"""Gate S3 family: the calendar gate's causality and window arithmetic."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import numpy as np
import polars as pl

from perp_lab.strategies.base import SIDE_COL
from perp_lab.strategies.macro_event_brake import (
    MacroEventBrake,
    _scheduled_event_ns,
    event_window_mask,
)
from perp_lab.strategies.momentum import MomentumCrossover

START = datetime(2022, 3, 1, tzinfo=UTC)
HOUR_NS = 3_600_000_000_000


def _features(n: int) -> pl.DataFrame:
    # A trending close so the carrier is long throughout after warm-up.
    close = np.linspace(100.0, 200.0, n)
    frame = pl.DataFrame(
        {
            "open_time": [START + timedelta(hours=i) for i in range(n)],
            "close": close,
        }
    )
    return frame.with_columns(
        pl.col("close").rolling_mean(window_size=12).alias("sma_12"),
        pl.col("close").rolling_mean(window_size=96).alias("sma_96"),
    )


def test_window_mask_extents() -> None:
    opens = np.arange(0, 48, dtype=np.int64) * HOUR_NS
    event = np.array([10 * HOUR_NS + HOUR_NS // 2], dtype=np.int64)  # 10:30
    mask = event_window_mask(opens, event, pre_bars=1, post_bars=2)
    gated = np.where(mask)[0].tolist()
    # 10:30 event, pre=1, post=2 -> window [09:30, 12:30): bars 9..12 intersect.
    assert gated == [9, 10, 11, 12]

    none = event_window_mask(opens, np.array([], dtype=np.int64), pre_bars=4, post_bars=8)
    assert not none.any()


def test_gate_flattens_only_event_windows() -> None:
    n = 24 * 30
    features = _features(n)
    event_time = START + timedelta(days=10, hours=13, minutes=30)
    import csv
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmp:
        cal = Path(tmp) / "cal.csv"
        with cal.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(
                fh, fieldnames=["event_type", "datetime_utc", "local_time", "note", "source"]
            )
            writer.writeheader()
            writer.writerow(
                {
                    "event_type": "cpi_release",
                    "datetime_utc": event_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "local_time": "x",
                    "note": "reference month",
                    "source": "test",
                }
            )
            writer.writerow(
                {
                    "event_type": "fomc_decision",
                    "datetime_utc": (event_time + timedelta(days=5)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "local_time": "x",
                    "note": "emergency action (unscheduled)",
                    "source": "test",
                }
            )
        gated = MacroEventBrake(
            fast=12,
            slow=96,
            event_set="both",
            pre_bars=1,
            post_bars=2,
            calendar_path=str(cal),
        ).signals(features)
        carrier = MomentumCrossover(fast=12, slow=96).signals(features)

        diff = (gated[SIDE_COL] != carrier[SIDE_COL]).to_numpy()
        changed = np.where(diff)[0]
        # Only the scheduled event's window changed; the emergency row never gates.
        event_idx = int(features["open_time"].search_sorted(event_time, side="right")) - 1
        assert changed.tolist() == [event_idx - 1, event_idx, event_idx + 1, event_idx + 2]
        assert (gated[SIDE_COL].to_numpy()[changed] == 0).all()


def test_real_calendar_excludes_emergencies() -> None:
    both = _scheduled_event_ns("both", "configs/altdata/us_macro_events.csv")
    cpi = _scheduled_event_ns("cpi", "configs/altdata/us_macro_events.csv")
    fomc = _scheduled_event_ns("fomc", "configs/altdata/us_macro_events.csv")
    assert len(cpi) == 71
    assert len(fomc) == 47  # 49 decisions minus the two 2020 emergency actions
    assert len(both) == 118
    assert set(both) == set(cpi) | set(fomc)


def test_signals_deterministic_and_flat_share_reasonable() -> None:
    features = _features(24 * 200)
    strat = MacroEventBrake(fast=12, slow=96, event_set="both", pre_bars=4, post_bars=8)
    first = strat.signals(features)[SIDE_COL].to_numpy()
    second = strat.signals(features)[SIDE_COL].to_numpy()
    assert (first == second).all()
