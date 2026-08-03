"""Ranked extreme-return events with leak-free pre-event context.

For the largest absolute returns we attach only information available *before*
the event: the rolling volatility and median volume computed up to the previous
bar, and the last-known funding rate. Whether the other asset moved
simultaneously is evaluated on the same bar (a contemporaneous, descriptive
co-movement flag, not a predictive one).
"""

from __future__ import annotations

import numpy as np
import polars as pl

from perp_lab.eda.funding import attach_funding


def rank_extreme_events(
    df: pl.DataFrame,
    *,
    symbol: str,
    other: pl.DataFrame | None = None,
    other_symbol: str = "other",
    funding: pl.DataFrame | None = None,
    k: int = 20,
    ret_col: str = "log_return",
    vol_window: int = 24,
    time_col: str = "open_time",
    other_extreme_q: float = 0.995,
) -> pl.DataFrame:
    """Return the ``k`` largest absolute-return events with pre-event context."""
    work = df.sort(time_col).with_columns(pl.col(ret_col).abs().alias("abs_ret"))
    # Pre-event rolling volatility and median volume use only PAST bars (shift 1).
    work = work.with_columns(
        pl.col(ret_col).rolling_std(vol_window, min_samples=vol_window).shift(1).alias("pre_vol"),
        (
            pl.col("volume")
            / pl.col("volume").rolling_median(vol_window, min_samples=vol_window).shift(1)
        ).alias("rel_volume"),
    )
    if funding is not None:
        work = attach_funding(work, funding, tolerance="8h").rename(
            {"funding_rate": "funding_known"}
        )
    else:
        work = work.with_columns(pl.lit(None, dtype=pl.Float64).alias("funding_known"))

    if other is not None:
        other_abs = (
            other.sort(time_col)
            .with_columns(pl.col(ret_col).abs().alias("other_abs"))
            .select(time_col, "other_abs")
        )
        thr = other_abs.select(pl.col("other_abs").quantile(other_extreme_q)).item()
        work = work.join(other_abs, on=time_col, how="left").with_columns(
            (pl.col("other_abs") >= thr).fill_null(False).alias("other_simultaneous_extreme")
        )
    else:
        work = work.with_columns(
            pl.lit(None, dtype=pl.Float64).alias("other_abs"),
            pl.lit(None, dtype=pl.Boolean).alias("other_simultaneous_extreme"),
        )

    top = work.sort("abs_ret", descending=True, nulls_last=True).head(k)
    return top.select(
        pl.lit(symbol).alias("symbol"),
        pl.col(time_col).alias("timestamp"),
        pl.col(ret_col).alias("log_return"),
        "abs_ret",
        "rel_volume",
        "pre_vol",
        "funding_known",
        pl.lit(other_symbol).alias("other_symbol"),
        "other_simultaneous_extreme",
    )


def coexceedance_rate(events: pl.DataFrame, flag_col: str = "other_simultaneous_extreme") -> float:
    """Share of ranked events for which the other asset was also extreme."""
    vals = events.select(pl.col(flag_col)).drop_nulls().to_series().to_numpy()
    return float(np.mean(vals)) if vals.size else float("nan")
