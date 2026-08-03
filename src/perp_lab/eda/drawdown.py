"""Drawdown curves and episode analysis (depth, duration, recovery).

A drawdown at time ``t`` is ``price_t / running_peak_t - 1`` (<= 0). An episode
runs from the peak that precedes a decline to the bar at which the price first
recovers that peak; episodes still under water at the end of the sample are
reported as unrecovered.
"""

from __future__ import annotations

import polars as pl


def add_drawdown(
    df: pl.DataFrame,
    price_col: str = "close",
    time_col: str = "open_time",
    peak_col: str = "running_peak",
    out_col: str = "drawdown",
) -> pl.DataFrame:
    """Append running-peak and drawdown columns (drawdown <= 0)."""
    out = df.sort(time_col)
    return out.with_columns(pl.col(price_col).cum_max().alias(peak_col)).with_columns(
        (pl.col(price_col) / pl.col(peak_col) - 1.0).alias(out_col)
    )


def max_drawdown(df: pl.DataFrame, price_col: str = "close", time_col: str = "open_time") -> float:
    """Return the maximum (most negative) drawdown over the sample."""
    dd = add_drawdown(df, price_col=price_col, time_col=time_col)
    if dd.height == 0:
        return 0.0
    return float(dd.select(pl.col("drawdown").min()).item())


def drawdown_episodes(
    df: pl.DataFrame,
    price_col: str = "close",
    time_col: str = "open_time",
    *,
    min_depth: float = 0.0,
) -> pl.DataFrame:
    """Return one row per drawdown episode.

    Columns: ``peak_time``, ``trough_time``, ``recovery_time`` (null if never
    recovered within the sample), ``depth`` (negative), ``drawdown_bars`` (peak
    to trough) and ``recovery_bars`` (trough to recovery, null if unrecovered),
    plus ``recovered`` (bool). Episodes shallower than ``abs(min_depth)`` are
    dropped.
    """
    schema = {
        "peak_time": df.schema.get(time_col, pl.Datetime("ms", "UTC")),
        "trough_time": df.schema.get(time_col, pl.Datetime("ms", "UTC")),
        "recovery_time": df.schema.get(time_col, pl.Datetime("ms", "UTC")),
        "depth": pl.Float64,
        "drawdown_bars": pl.Int64,
        "recovery_bars": pl.Int64,
        "recovered": pl.Boolean,
    }
    if df.height == 0:
        return pl.DataFrame(schema=schema)

    ordered = df.sort(time_col)
    price = ordered[price_col].to_numpy()
    times = ordered[time_col].to_list()
    n = len(price)

    peak = price[0]
    peak_idx = 0
    trough = price[0]
    trough_idx = 0
    in_dd = False
    episodes: list[dict[str, object]] = []

    for i in range(1, n):
        p = price[i]
        if p >= peak:
            if in_dd:
                episodes.append(
                    {
                        "peak_time": times[peak_idx],
                        "trough_time": times[trough_idx],
                        "recovery_time": times[i],
                        "depth": float(trough / peak - 1.0),
                        "drawdown_bars": int(trough_idx - peak_idx),
                        "recovery_bars": int(i - trough_idx),
                        "recovered": True,
                    }
                )
                in_dd = False
            peak = p
            peak_idx = i
            trough = p
            trough_idx = i
        else:
            in_dd = True
            if p < trough:
                trough = p
                trough_idx = i

    if in_dd:
        episodes.append(
            {
                "peak_time": times[peak_idx],
                "trough_time": times[trough_idx],
                "recovery_time": None,
                "depth": float(trough / peak - 1.0),
                "drawdown_bars": int(trough_idx - peak_idx),
                "recovery_bars": None,
                "recovered": False,
            }
        )

    result = pl.DataFrame(episodes, schema=schema) if episodes else pl.DataFrame(schema=schema)
    if min_depth:
        result = result.filter(pl.col("depth") <= -abs(min_depth))
    return result.sort("depth")


def underwater_fraction(
    df: pl.DataFrame, price_col: str = "close", time_col: str = "open_time"
) -> float:
    """Fraction of bars spent below the running peak (drawdown < 0)."""
    dd = add_drawdown(df, price_col=price_col, time_col=time_col)
    if dd.height == 0:
        return 0.0
    return float(dd.select((pl.col("drawdown") < 0).mean()).item())


def top_drawdowns(
    df: pl.DataFrame,
    n: int = 5,
    price_col: str = "close",
    time_col: str = "open_time",
) -> pl.DataFrame:
    """Return the ``n`` deepest drawdown episodes (most negative first)."""
    episodes = drawdown_episodes(df, price_col=price_col, time_col=time_col)
    return episodes.head(n)
