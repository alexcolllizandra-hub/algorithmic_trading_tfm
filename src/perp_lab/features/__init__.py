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
    add_cum_return,
    add_cyclical_time,
    add_ema,
    add_log_return,
    add_ma_distance,
    add_momentum,
    add_price_distance_ma,
    add_relative_volume,
    add_rolling_std,
    add_rolling_volatility,
    add_sma,
    add_taker_buy_imbalance,
    add_taker_buy_ratio,
    add_true_range,
    add_true_range_norm,
    add_volume_zscore,
    add_zscore,
)
from perp_lab.features.context import (
    FeatureContext,
    add_basis,
    add_open_interest_change,
    add_relative_momentum,
    add_relative_return,
    add_rolling_xcorr,
    attach_funding_rate,
)
from perp_lab.features.manifest import (
    MANIFEST_SCHEMA_VERSION,
    build_feature_manifest,
    spec_manifest_entry,
)
from perp_lab.features.predictors import build_predictor_rows
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
    "MANIFEST_SCHEMA_VERSION",
    "FeatureContext",
    "FeatureSpec",
    "add_atr",
    "add_basis",
    "add_cum_return",
    "add_cyclical_time",
    "add_ema",
    "add_log_return",
    "add_ma_distance",
    "add_momentum",
    "add_open_interest_change",
    "add_price_distance_ma",
    "add_relative_momentum",
    "add_relative_return",
    "add_relative_volume",
    "add_rolling_std",
    "add_rolling_volatility",
    "add_rolling_xcorr",
    "add_sma",
    "add_taker_buy_imbalance",
    "add_taker_buy_ratio",
    "add_true_range",
    "add_true_range_norm",
    "add_volume_zscore",
    "add_zscore",
    "attach_funding_rate",
    "build_feature_frame",
    "build_feature_manifest",
    "build_predictor_rows",
    "feature_columns",
    "known_kinds",
    "resolve_feature_set",
    "resolve_spec",
    "spec_manifest_entry",
    "specs_to_metadata",
    "validate_feature_item",
]
