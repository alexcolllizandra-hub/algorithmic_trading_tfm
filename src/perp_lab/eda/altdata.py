"""Alternative-data annex analyses: Fear & Greed and macro-event studies.

Descriptive machinery only: none of this enters the canonical study. Three
questions, each answered with uncertainty attached:

* does the daily Fear & Greed level condition subsequent returns or realized
  volatility (quintile analysis with moving-block bootstrap CIs)?
* what happens to hourly volatility around scheduled US macro events (event
  study with a seasonality-matched control: same UTC hour on non-event days)?
* how large is the event-hour move compared with its own baseline?

All functions are pure ``(frames, params) -> tidy frame / dict`` transforms;
loading is gated through the same development-partition discipline as the
market data (`load_fear_greed` clips and guards).
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import numpy as np
import polars as pl

from perp_lab.eda.datasets import assert_no_holdout


def load_fear_greed(
    path: str | Path, *, holdout_start: datetime, time_col: str = "date"
) -> pl.DataFrame:
    """Load the Fear & Greed parquet clipped to the development partition.

    The guard raises :class:`~perp_lab.eda.datasets.HoldoutLeakageError` if any
    row at or after ``holdout_start`` survives the clip, mirroring the market
    DataLake contract.
    """
    frame = pl.read_parquet(path).filter(pl.col(time_col) < holdout_start).sort(time_col)
    assert_no_holdout(frame, holdout_start, time_col=time_col)
    return frame


def load_macro_events(
    path: str | Path, *, holdout_start: datetime, time_col: str = "datetime_utc"
) -> pl.DataFrame:
    """Load the curated macro-events parquet clipped to development."""
    frame = pl.read_parquet(path).filter(pl.col(time_col) < holdout_start).sort(time_col)
    assert_no_holdout(frame, holdout_start, time_col=time_col)
    return frame


def _block_bootstrap_mean(
    sample: np.ndarray, *, n_boot: int, block: int, rng: np.random.Generator
) -> tuple[float, float]:
    """95% moving-block bootstrap CI for the mean of ``sample``."""
    n = sample.size
    if n == 0:
        return (np.nan, np.nan)
    block = min(block, n)
    n_blocks = max(1, n // block)
    starts_max = max(1, n - block)
    boots = np.empty(n_boot)
    for b in range(n_boot):
        starts = rng.integers(0, starts_max, n_blocks)
        idx = (starts[:, None] + np.arange(block)[None, :]).ravel()[:n]
        boots[b] = sample[idx].mean()
    return (float(np.quantile(boots, 0.025)), float(np.quantile(boots, 0.975)))


def fear_greed_conditional(
    fg: pl.DataFrame,
    bars: pl.DataFrame,
    *,
    horizon_bars: int = 24,
    n_quantiles: int = 5,
    n_boot: int = 500,
    block: int = 7,
    seed: int = 42,
    time_col: str = "open_time",
    ret_col: str = "log_return",
) -> pl.DataFrame:
    """Forward return and realized volatility conditional on the F&G quantile.

    The index published for day *d* (00:00 UTC stamp) conditions the window
    that STARTS at the next day's first bar — a one-day availability lag that
    keeps the analysis causal even under the provider's end-of-day ambiguity.
    Quantile bins are rank-based; CIs come from a moving-block bootstrap over
    the (chronologically ordered) daily observations.
    """
    ret = bars[ret_col].to_numpy()
    csum = np.concatenate([[0.0], np.cumsum(np.nan_to_num(ret))])
    sq = np.nan_to_num(ret) ** 2
    csq = np.concatenate([[0.0], np.cumsum(sq)])
    times = bars[time_col]

    # First bar strictly AFTER the F&G day ends (day d stamp -> day d+1 00:00).
    day_end = fg["date"].dt.offset_by("1d")
    start_idx = times.search_sorted(day_end, side="left").to_numpy()
    valid = start_idx + horizon_bars < len(ret)
    values = fg["value"].to_numpy()[valid]
    start_idx = start_idx[valid]
    fwd_ret = csum[start_idx + horizon_bars] - csum[start_idx]
    fwd_vol = np.sqrt(csq[start_idx + horizon_bars] - csq[start_idx])

    order = np.argsort(values, kind="stable")
    which = np.empty(values.size, dtype=int)
    which[order] = np.arange(values.size) * n_quantiles // values.size

    rng = np.random.default_rng(seed)
    rows = []
    for q in range(n_quantiles):
        mask = which == q
        r = fwd_ret[mask] * 1e4
        v = fwd_vol[mask] * 1e4
        r_lo, r_hi = _block_bootstrap_mean(r, n_boot=n_boot, block=block, rng=rng)
        rows.append(
            {
                "quantile": q + 1,
                "n_days": int(mask.sum()),
                "fg_min": float(values[mask].min()),
                "fg_max": float(values[mask].max()),
                "fwd_ret_bps": float(r.mean()),
                "fwd_ret_lo": r_lo,
                "fwd_ret_hi": r_hi,
                "fwd_vol_bps": float(v.mean()),
            }
        )
    return pl.DataFrame(rows)


def event_study(
    bars: pl.DataFrame,
    event_times: pl.Series,
    *,
    window_bars: int = 12,
    time_col: str = "open_time",
    ret_col: str = "log_return",
) -> pl.DataFrame:
    """Mean |return| and cumulative return around events, bar-aligned.

    Offset 0 is the first bar whose interval CONTAINS the event timestamp
    (the bar in which the release lands). Events too close to the sample
    edges are dropped. Returns a tidy frame with one row per offset.
    """
    ret = np.nan_to_num(bars[ret_col].to_numpy())
    times = bars[time_col]
    # Bar containing the event: last bar with open_time <= event time.
    pos = times.search_sorted(event_times, side="right").to_numpy() - 1
    pos = pos[(pos - window_bars >= 0) & (pos + window_bars < len(ret))]
    offsets = np.arange(-window_bars, window_bars + 1)
    matrix = ret[pos[:, None] + offsets[None, :]]
    cum = np.cumsum(matrix, axis=1)
    cum -= cum[:, [window_bars - 1]]  # anchor cumret at the pre-event bar
    return pl.DataFrame(
        {
            "offset_bars": offsets.tolist(),
            "mean_absret_bps": (np.abs(matrix).mean(axis=0) * 1e4).tolist(),
            "median_absret_bps": (np.median(np.abs(matrix), axis=0) * 1e4).tolist(),
            "mean_cumret_bps": (cum.mean(axis=0) * 1e4).tolist(),
            "n_events": [int(pos.size)] * offsets.size,
        }
    )


def event_hour_vs_matched_control(
    bars: pl.DataFrame,
    event_times: pl.Series,
    *,
    n_boot: int = 2000,
    seed: int = 42,
    time_col: str = "open_time",
    ret_col: str = "log_return",
) -> dict[str, float]:
    """Event-bar |return| against a seasonality-matched control.

    The control set is every bar at the SAME UTC hour on non-event days, so
    the comparison is immune to the intraday activity profile (US macro
    releases land in the busiest hours by construction). Returns the two
    means, their ratio and a permutation p-value for equality of means.
    """
    frame = bars.with_columns(pl.col(time_col).dt.hour().alias("_hour")).with_columns(
        pl.col(ret_col).abs().alias("_absret")
    )
    times = frame[time_col]
    pos = times.search_sorted(event_times, side="right").to_numpy() - 1
    pos = pos[(pos >= 0) & (pos < frame.height)]
    hours = frame["_hour"].to_numpy()
    absret = np.nan_to_num(frame["_absret"].to_numpy())

    event_mask = np.zeros(frame.height, dtype=bool)
    event_mask[pos] = True
    event_hours = set(hours[pos].tolist())
    control_mask = np.isin(hours, list(event_hours)) & ~event_mask

    ev = absret[event_mask]
    ctrl = absret[control_mask]
    observed = float(ev.mean() / ctrl.mean())

    rng = np.random.default_rng(seed)
    pooled = np.concatenate([ev, ctrl])
    n_ev = ev.size
    count = 0
    for _ in range(n_boot):
        rng.shuffle(pooled)
        if pooled[:n_ev].mean() / pooled[n_ev:].mean() >= observed:
            count += 1
    return {
        "n_events": float(n_ev),
        "n_control": float(ctrl.size),
        "event_mean_bps": float(ev.mean() * 1e4),
        "control_mean_bps": float(ctrl.mean() * 1e4),
        "ratio": observed,
        "p_value": (count + 1) / (n_boot + 1),
    }
