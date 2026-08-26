"""Macro-event risk gating over the momentum carrier (Gate S3 family).

Economic hypothesis
-------------------
Scheduled US macro releases (CPI prints, FOMC decisions) carry 2.5-3.2 times
the absolute hourly return of seasonality-matched non-event hours in the
development window, with no measurable directional drift (descriptive annex,
figures A3-A4). If those windows contain outsized, directionless variance,
a directional carrier should have a better net risk profile when it is flat
inside them: identical exposure elsewhere, none during unpriceable event risk.

Why this is a distinct hypothesis
---------------------------------
No family evaluated at R2/R3/S1/S2 conditions on the macro calendar. The
carrier is the study's best-understood failed family (momentum crossover),
so any improvement is attributable to the calendar gate alone.

Causality
---------
Only *scheduled* events gate: CPI release dates are published by the BLS and
FOMC meeting dates by the Federal Reserve well in advance, so membership of a
bar in an event window is known before the window opens. The two March-2020
emergency FOMC actions in the committed calendar are explicitly EXCLUDED from
the gate — they were not scheduled and gating on them would be look-ahead.
The calendar itself is frozen and committed
(``configs/altdata/us_macro_events.csv``).
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np
import polars as pl

from perp_lab.strategies.base import SIDE_COL
from perp_lab.strategies.momentum import MomentumCrossover

EVENT_SETS = ("cpi", "fomc", "both")
_CALENDAR_PATH = Path("configs/altdata/us_macro_events.csv")
_NS_PER_HOUR = 3_600_000_000_000


@lru_cache(maxsize=4)
def _scheduled_event_ns(event_set: str, calendar_path: str) -> tuple[int, ...]:
    """Scheduled event timestamps (UTC ns) for the requested set, sorted.

    Emergency (unscheduled) rows never gate — they were not knowable in
    advance. Cached because every candidate in a search shares the calendar.
    """
    frame = (
        pl.read_csv(calendar_path)
        .with_columns(pl.col("datetime_utc").str.to_datetime("%Y-%m-%dT%H:%M:%SZ", time_zone="UTC"))
        .filter(~pl.col("note").str.contains("emergency"))
    )
    if event_set == "cpi":
        frame = frame.filter(pl.col("event_type") == "cpi_release")
    elif event_set == "fomc":
        frame = frame.filter(pl.col("event_type") == "fomc_decision")
    elif event_set != "both":
        raise ValueError(f"event_set must be one of {EVENT_SETS}, got {event_set!r}.")
    stamps = (
        frame.sort("datetime_utc")["datetime_utc"].dt.cast_time_unit("ns").cast(pl.Int64).to_list()
    )
    return tuple(stamps)


def event_window_mask(
    open_times_ns: np.ndarray,
    event_ns: np.ndarray,
    *,
    pre_bars: int,
    post_bars: int,
    bar_ns: int = _NS_PER_HOUR,
) -> np.ndarray:
    """True for bars whose interval intersects any gated event window.

    A bar covers ``[open, open + bar)``; the gated window around an event is
    ``[event - pre_bars * bar, event + post_bars * bar)``. Vectorised with a
    two-sided searchsorted over the sorted event stamps.
    """
    if event_ns.size == 0:
        return np.zeros(open_times_ns.size, dtype=bool)
    # Intersection <=> exists event with open - post*bar < event AND
    # event <= open + (1 + pre)*bar  (half-open arithmetic on both sides).
    lo = np.searchsorted(event_ns, open_times_ns - post_bars * bar_ns, side="right")
    hi = np.searchsorted(event_ns, open_times_ns + (1 + pre_bars) * bar_ns, side="left")
    return hi > lo


@dataclass(frozen=True)
class MacroEventBrake:
    """Momentum crossover forced flat around scheduled US macro events."""

    fast: int
    slow: int
    event_set: str
    pre_bars: int
    post_bars: int
    direction: str = "both"
    trend_filter_ma: int | None = None
    regime_gate: tuple[str, ...] | None = None
    calendar_path: str = str(_CALENDAR_PATH)

    def __post_init__(self) -> None:
        if self.event_set not in EVENT_SETS:
            raise ValueError(f"event_set must be one of {EVENT_SETS}, got {self.event_set!r}.")
        if self.pre_bars < 0 or self.post_bars < 0:
            raise ValueError("pre_bars and post_bars must be non-negative bar counts.")
        # Carrier validation (fast < slow, direction, trend window) happens here.
        self._carrier()

    def _carrier(self) -> MomentumCrossover:
        return MomentumCrossover(
            fast=self.fast,
            slow=self.slow,
            direction=self.direction,
            trend_filter_ma=self.trend_filter_ma,
            regime_gate=self.regime_gate,
        )

    @property
    def name(self) -> str:
        return (
            f"macro_event_brake_{self.fast}_{self.slow}_{self.event_set}"
            f"_pre{self.pre_bars}_post{self.post_bars}_{self.direction}"
        )

    def params(self) -> dict[str, object]:
        return {
            "family": "macro_event_brake",
            "fast": self.fast,
            "slow": self.slow,
            "event_set": self.event_set,
            "pre_bars": self.pre_bars,
            "post_bars": self.post_bars,
            "direction": self.direction,
            "trend_filter_ma": self.trend_filter_ma,
            "regime_gate": list(self.regime_gate) if self.regime_gate else None,
        }

    def required_features(self) -> tuple[str, ...]:
        return self._carrier().required_features()

    def signals(self, features: pl.DataFrame) -> pl.DataFrame:
        out = self._carrier().signals(features)
        open_ns = out["open_time"].dt.cast_time_unit("ns").cast(pl.Int64).to_numpy()
        event_ns = np.asarray(
            _scheduled_event_ns(self.event_set, self.calendar_path), dtype=np.int64
        )
        gated = event_window_mask(
            open_ns, event_ns, pre_bars=self.pre_bars, post_bars=self.post_bars
        )
        side = out[SIDE_COL].to_numpy().copy()
        side[gated] = 0
        return out.with_columns(pl.Series(SIDE_COL, side, dtype=pl.Int8))
