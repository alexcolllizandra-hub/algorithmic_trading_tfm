"""Dataset construction for the volatility-forecasting annex.

Everything is bar-aligned and causal: the feature row at bar *t* uses
information up to and including bar *t*'s close, and the target is the log
realized volatility of the NEXT ``horizon`` bars. Rows whose feature or
target windows are incomplete are dropped.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import polars as pl

HORIZON = 24
RV_WINDOWS = (24, 168, 720)  # HAR components: day, week, month (in 1h bars)
_EPS = 1e-12


@dataclass(frozen=True)
class VolDataset:
    """Aligned arrays for one symbol over the development window."""

    times: np.ndarray  # bar open_time (datetime64[ns]), aligned to features
    target_log_rv: np.ndarray  # log RV of the NEXT `HORIZON` bars
    har_features: np.ndarray  # (n, 3) log RV over the past 24/168/720 bars
    bar_features: np.ndarray  # (n, 3) per-bar inputs for the sequence model

    @property
    def n(self) -> int:
        return int(self.target_log_rv.size)


def _trailing_log_rv(sq: np.ndarray, window: int) -> np.ndarray:
    """log sqrt(sum of squared returns over the TRAILING ``window`` bars)."""
    csum = np.concatenate([[0.0], np.cumsum(sq)])
    out = np.full(sq.size, np.nan)
    out[window - 1 :] = np.log(np.sqrt(csum[window:] - csum[:-window]) + _EPS)
    return out


def build_vol_dataset(
    bars: pl.DataFrame,
    *,
    horizon: int = HORIZON,
    time_col: str = "open_time",
    ret_col: str = "log_return",
) -> VolDataset:
    """Build the aligned target/feature arrays from an hourly bar frame."""
    frame = bars.sort(time_col)
    ret = np.nan_to_num(frame[ret_col].to_numpy().astype(float))
    sq = ret**2

    # Forward target: log RV of bars t+1 .. t+horizon.
    csum = np.concatenate([[0.0], np.cumsum(sq)])
    fwd = np.full(ret.size, np.nan)
    fwd[: ret.size - horizon] = np.log(np.sqrt(csum[1 + horizon :] - csum[1:-horizon]) + _EPS)

    har = np.column_stack([_trailing_log_rv(sq, w) for w in RV_WINDOWS])
    bar_feats = np.column_stack(
        [
            np.log(np.abs(ret) + _EPS),
            ret,
            _trailing_log_rv(sq, RV_WINDOWS[0]),
        ]
    )

    valid = np.isfinite(fwd) & np.isfinite(har).all(axis=1) & np.isfinite(bar_feats).all(axis=1)
    times = frame[time_col].dt.cast_time_unit("ns").to_numpy()
    return VolDataset(
        times=times[valid],
        target_log_rv=fwd[valid],
        har_features=har[valid],
        bar_features=bar_feats[valid],
    )


def slice_by_time(
    dataset: VolDataset, start: np.datetime64, end_exclusive: np.datetime64
) -> np.ndarray:
    """Boolean mask of rows whose bar time lies in [start, end_exclusive)."""
    return (dataset.times >= start) & (dataset.times < end_exclusive)
