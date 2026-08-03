"""Causal feature engine (Chapter 5.3).

Every feature is computed from information available at or before its own bar's
close (rolling / expanding, never full-sample or centred), so future rows can
never change a past feature value. Contextual microstructure features that are
only fully known at a bar's close (e.g. taker-buy imbalance) are explicitly
lagged before use. Cyclical calendar encodings are known ex-ante and need no
lag. The next-bar execution delay itself is applied later by the backtester.

The engine is **configuration-driven**: a requested feature set (validated
against :data:`perp_lab.features.spec.KIND_REGISTRY`) resolves to serialisable
:class:`~perp_lab.features.spec.FeatureSpec` records and is built by
:func:`~perp_lab.features.registry.build_feature_frame`.
"""

from perp_lab.features.causal import (
    FEATURE_INPUT_COLUMNS,
    add_atr,
    add_cyclical_time,
    add_log_return,
    add_momentum,
    add_price_distance_ma,
    add_relative_volume,
    add_rolling_volatility,
    add_sma,
    add_taker_buy_imbalance,
    add_true_range_norm,
    add_volume_zscore,
    add_zscore,
)
from perp_lab.features.registry import (
    build_feature_frame,
    feature_columns,
    resolve_feature_set,
    specs_to_metadata,
)
from perp_lab.features.spec import (
    IMPL_VERSION,
    KIND_REGISTRY,
    FeatureSpec,
    known_kinds,
    resolve_spec,
    validate_feature_item,
)

__all__ = [
    "FEATURE_INPUT_COLUMNS",
    "IMPL_VERSION",
    "KIND_REGISTRY",
    "FeatureSpec",
    "add_atr",
    "add_cyclical_time",
    "add_log_return",
    "add_momentum",
    "add_price_distance_ma",
    "add_relative_volume",
    "add_rolling_volatility",
    "add_sma",
    "add_taker_buy_imbalance",
    "add_true_range_norm",
    "add_volume_zscore",
    "add_zscore",
    "build_feature_frame",
    "feature_columns",
    "known_kinds",
    "resolve_feature_set",
    "resolve_spec",
    "specs_to_metadata",
    "validate_feature_item",
]
