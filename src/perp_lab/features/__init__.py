"""Causal feature engine (Chapter 5.3).

Every feature is computed from information available at or before its own bar's
close (rolling / expanding, never full-sample or centred), so future rows can
never change a past feature value. Contextual microstructure features that are
only fully known at a bar's close (e.g. taker-buy imbalance) are explicitly
lagged before use. The next-bar execution delay itself is applied later by the
backtester, not here.

This initial slice implements a small, justified subset sufficient for a
momentum baseline on BTCUSDT 1h: log returns, moving averages, ATR, rolling
volatility, and a lagged taker-buy imbalance context feature.
"""

from perp_lab.features.causal import (
    FEATURE_INPUT_COLUMNS,
    add_atr,
    add_log_return,
    add_momentum,
    add_moving_averages,
    add_relative_volume,
    add_rolling_volatility,
    add_taker_buy_imbalance,
    build_features,
    feature_metadata,
)

__all__ = [
    "FEATURE_INPUT_COLUMNS",
    "add_atr",
    "add_log_return",
    "add_momentum",
    "add_moving_averages",
    "add_relative_volume",
    "add_rolling_volatility",
    "add_taker_buy_imbalance",
    "build_features",
    "feature_metadata",
]
