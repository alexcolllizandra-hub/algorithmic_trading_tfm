"""External market-context annotations and a data-driven stress proxy.

Two clearly-separated things live here:

1. :data:`CRYPTO_MARKET_EVENTS` - a small, curated list of *widely documented,
   publicly reported* crypto-market events (crashes, halvings, major adoption or
   collapse dates). These are **qualitative external annotations** used only to
   label the price chart; they are never used to compute a statistic, threshold,
   feature or model input. No proprietary "sentiment feed" is available in this
   repository, so market mood is illustrated with the data-driven proxy below.

2. :func:`market_stress_index` - a transparent stress/"risk-off" proxy computed
   **only from price and volatility** (rolling annualised volatility percentile
   combined with drawdown depth). It is a within-data proxy, not an external
   sentiment index, and is used for visualisation and description only.
"""

from __future__ import annotations

from datetime import UTC, datetime

import numpy as np
import polars as pl

# Publicly documented, verifiable dates (UTC). Category is descriptive only.
CRYPTO_MARKET_EVENTS: tuple[dict[str, str], ...] = (
    {"date": "2020-03-12", "label": "COVID 'Black Thursday' crash", "category": "crash"},
    {"date": "2020-05-11", "label": "Bitcoin third halving", "category": "protocol"},
    {"date": "2021-04-14", "label": "Coinbase direct listing (local top)", "category": "adoption"},
    {"date": "2021-05-19", "label": "China mining crackdown sell-off", "category": "crash"},
    {"date": "2021-09-07", "label": "El Salvador BTC legal tender", "category": "adoption"},
    {"date": "2021-11-10", "label": "Bitcoin all-time high (~$69k)", "category": "top"},
    {"date": "2022-05-09", "label": "Terra/LUNA collapse", "category": "collapse"},
    {"date": "2022-06-13", "label": "Celsius halts / 3AC stress", "category": "collapse"},
    {"date": "2022-11-08", "label": "FTX collapse", "category": "collapse"},
    {"date": "2023-03-10", "label": "USDC depeg / SVB failure", "category": "crash"},
    {"date": "2023-06-15", "label": "BlackRock spot-ETF filing", "category": "adoption"},
    {"date": "2024-01-10", "label": "US spot BTC ETFs approved", "category": "adoption"},
    {"date": "2024-04-20", "label": "Bitcoin fourth halving", "category": "protocol"},
    {"date": "2024-08-05", "label": "Yen carry-unwind sell-off", "category": "crash"},
)


def market_events_frame(start: datetime | None = None, end: datetime | None = None) -> pl.DataFrame:
    """Return the curated events as a typed frame, optionally clipped to a window.

    ``date`` is parsed to a tz-aware UTC ``datetime``. When ``start``/``end`` are
    given, only events inside ``[start, end)`` are returned so the holdout window
    is never annotated.
    """
    rows = [
        {
            "date": datetime.strptime(e["date"], "%Y-%m-%d").replace(tzinfo=UTC),
            "label": e["label"],
            "category": e["category"],
        }
        for e in CRYPTO_MARKET_EVENTS
    ]
    frame = pl.DataFrame(rows).sort("date")
    if start is not None:
        frame = frame.filter(pl.col("date") >= start)
    if end is not None:
        frame = frame.filter(pl.col("date") < end)
    return frame


def market_stress_index(
    df: pl.DataFrame,
    *,
    ret_col: str = "log_return",
    price_col: str = "close",
    vol_window: int = 24,
    time_col: str = "open_time",
) -> pl.DataFrame:
    """Data-driven risk-off proxy in ``[0, 1]`` from volatility and drawdown.

    The index is the average of two components, each mapped to ``[0, 1]``:

    - the empirical percentile of the rolling ``vol_window`` return volatility
      (high volatility -> high stress);
    - the current drawdown depth from the running peak, normalised by the
      deepest drawdown observed in the sample.

    It is a transparent, price-only proxy for market stress/"fear"; it is not an
    external sentiment measure and is used for visualisation and description
    only. Returns ``time_col`` and ``stress_index``.
    """
    ordered = df.sort(time_col)
    vol = (
        ordered.select(pl.col(ret_col).rolling_std(window_size=vol_window, min_samples=vol_window))
        .to_series()
        .to_numpy()
    )
    close = ordered.select(price_col).to_series().to_numpy().astype(float)
    running_peak = np.maximum.accumulate(np.where(np.isnan(close), -np.inf, close))
    drawdown = np.where(running_peak > 0, 1.0 - close / running_peak, 0.0)

    vol_pct = np.full(vol.size, np.nan)
    finite_mask = np.isfinite(vol)
    n_finite = int(finite_mask.sum())
    if n_finite:
        ranks = vol[finite_mask].argsort().argsort().astype(float)
        vol_pct[finite_mask] = ranks / max(n_finite - 1, 1)

    max_dd = float(np.nanmax(drawdown)) if np.isfinite(drawdown).any() else 0.0
    dd_norm = drawdown / max_dd if max_dd > 0 else np.zeros_like(drawdown)

    stress = np.nanmean(np.vstack([vol_pct, dd_norm]), axis=0)
    return ordered.select(time_col).with_columns(pl.Series("stress_index", stress))
