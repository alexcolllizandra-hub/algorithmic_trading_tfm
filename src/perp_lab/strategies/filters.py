"""Optional, causal entry filters shared by the baseline strategies.

Filters never *create* exposure; they only *remove* it. Each returns a boolean
mask (per bar) that is combined with a strategy's raw side to flatten positions
that the filter disallows. All inputs are causal feature columns available at the
bar's close, so filters introduce no look-ahead.
"""

from __future__ import annotations

import numpy as np
import polars as pl

# Regime label column produced by perp_lab.regimes (human-readable names).
DEFAULT_REGIME_COL = "regime"


def regime_mask(
    features: pl.DataFrame,
    allowed: tuple[str, ...],
    *,
    regime_col: str = DEFAULT_REGIME_COL,
) -> np.ndarray:
    """Boolean mask: ``True`` where the bar's regime is in ``allowed``.

    A missing regime column is a hard error (the caller must attach regimes
    first). Null / unknown regimes are disallowed (``False``).
    """
    if regime_col not in features.columns:
        raise ValueError(
            f"regime gate requires a {regime_col!r} column; attach regimes before signalling."
        )
    labels = features[regime_col].to_list()
    allowed_set = set(allowed)
    return np.array([lab in allowed_set for lab in labels], dtype=bool)


def trend_masks(
    features: pl.DataFrame,
    trend_col: str,
    *,
    price_col: str = "close",
) -> tuple[np.ndarray, np.ndarray]:
    """Return ``(long_ok, short_ok)`` masks for a trend gate.

    Longs are allowed only when ``price > trend_ma`` and shorts only when
    ``price < trend_ma``. Bars where the trend MA is null disallow both sides.
    """
    if trend_col not in features.columns:
        raise ValueError(f"trend gate requires a {trend_col!r} column.")
    price = features[price_col].cast(pl.Float64).to_numpy().astype(float)
    trend = features[trend_col].cast(pl.Float64).to_numpy().astype(float)
    valid = np.isfinite(trend) & np.isfinite(price)
    long_ok = valid & (price > trend)
    short_ok = valid & (price < trend)
    return long_ok, short_ok


def apply_regime_gate(
    side: np.ndarray,
    features: pl.DataFrame,
    allowed: tuple[str, ...],
    *,
    regime_col: str = DEFAULT_REGIME_COL,
) -> np.ndarray:
    """Flatten the side to 0 on bars whose regime is not in ``allowed``."""
    mask = regime_mask(features, allowed, regime_col=regime_col)
    return np.where(mask, side, 0).astype(np.int8)


def apply_trend_gate(
    side: np.ndarray,
    features: pl.DataFrame,
    trend_col: str,
    *,
    price_col: str = "close",
) -> np.ndarray:
    """Flatten longs below / shorts above the trend MA (keep only aligned side)."""
    long_ok, short_ok = trend_masks(features, trend_col, price_col=price_col)
    keep_long = (side > 0) & long_ok
    keep_short = (side < 0) & short_ok
    return np.where(keep_long, 1, np.where(keep_short, -1, 0)).astype(np.int8)
