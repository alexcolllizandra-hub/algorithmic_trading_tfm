"""Deterministic construction of coarser bars from a finer base timeframe.

15-minute and 1-hour bars are built by aggregating the 5-minute base bars. This
matches the thesis claim that all higher timeframes are derived from a single
consistent 5-minute source. The result is cross-checked against Binance native
klines in the data-quality step.
"""

from __future__ import annotations

import polars as pl

from perp_lab.data.providers.base import KLINE_SCHEMA
from perp_lab.utils.timeutils import TIMEFRAME_TO_MS

# Polars duration strings are identical to our timeframe tokens ("15m", "1h").
_AGGREGATIONS = [
    pl.col("open").first(),
    pl.col("high").max(),
    pl.col("low").min(),
    pl.col("close").last(),
    pl.col("volume").sum(),
    pl.col("quote_volume").sum(),
    pl.col("trade_count").sum(),
    pl.col("taker_buy_base").sum(),
    pl.col("taker_buy_quote").sum(),
]


def _validate_timeframes(source_tf: str, target_tf: str) -> None:
    if source_tf not in TIMEFRAME_TO_MS or target_tf not in TIMEFRAME_TO_MS:
        raise ValueError(f"Unknown timeframe(s): {source_tf!r} -> {target_tf!r}")
    src, tgt = TIMEFRAME_TO_MS[source_tf], TIMEFRAME_TO_MS[target_tf]
    if tgt <= src:
        raise ValueError(f"Target {target_tf} must be coarser than source {source_tf}.")
    if tgt % src != 0:
        raise ValueError(f"Target {target_tf} must be an integer multiple of source {source_tf}.")


def resample_klines(
    df: pl.DataFrame,
    source_tf: str,
    target_tf: str,
    *,
    drop_incomplete: bool = False,
) -> pl.DataFrame:
    """Aggregate base-timeframe klines into ``target_tf`` bars.

    Parameters
    ----------
    df:
        Klines with the canonical :data:`KLINE_SCHEMA`.
    source_tf, target_tf:
        Source and target timeframes (target must be an integer multiple).
    drop_incomplete:
        When ``True``, drop target bars that contain fewer than the expected
        number of source bars (e.g. an unfinished current bar or a bar sitting
        on top of a data gap). When ``False`` (default) partial bars are kept
        and can be inspected by the QC step via ``n_source_bars``.
    """
    _validate_timeframes(source_tf, target_tf)
    if df.is_empty():
        return df.select(list(KLINE_SCHEMA.keys()))

    ratio = TIMEFRAME_TO_MS[target_tf] // TIMEFRAME_TO_MS[source_tf]
    grouped = (
        df.sort("open_time")
        .group_by_dynamic("open_time", every=target_tf, closed="left", label="left")
        .agg(*_AGGREGATIONS, pl.len().alias("n_source_bars"))
    )
    if drop_incomplete:
        grouped = grouped.filter(pl.col("n_source_bars") == ratio)
    return grouped.drop("n_source_bars").select(list(KLINE_SCHEMA.keys()))
