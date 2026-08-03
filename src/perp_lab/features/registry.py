"""Feature engine: resolve a requested feature set and build it causally.

This ties the pure column builders in :mod:`perp_lab.features.causal` to the
declarative contract in :mod:`perp_lab.features.spec`. Callers pass a list of
requested features (typically ``ExperimentConfig.features.feature_set``); the
engine validates them, checks input-column dependencies, builds the columns in
a deterministic order and returns the frame together with the resolved,
serialisable specs used for run artifacts and the feature catalogue.

The engine is stateless (pure functions only), so building features for one
symbol can never contaminate another, and repeating a build is bit-for-bit
identical.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

import polars as pl

from perp_lab.features import causal
from perp_lab.features.spec import FeatureItemLike, FeatureSpec, resolve_spec


def _require_columns(df: pl.DataFrame, columns: Iterable[str]) -> None:
    missing = [c for c in columns if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required input columns: {sorted(set(missing))}")


def _apply_spec(df: pl.DataFrame, spec: FeatureSpec) -> pl.DataFrame:
    """Dispatch one resolved spec to its pure column builder."""
    kind = spec.kind
    p = spec.params
    window = int(p["window"]) if "window" in p else None
    lag = int(p["lag"]) if "lag" in p else None
    source = str(p["source"]) if "source" in p else None
    out = spec.columns[0]

    if kind == "log_return":
        return causal.add_log_return(
            df, k=int(p.get("window", 1)), price_col=source or "close", out_col=out
        )
    if kind == "momentum":
        assert window is not None
        return causal.add_momentum(df, window, price_col=source or "close", out_col=out)
    if kind == "sma":
        assert window is not None
        return causal.add_sma(df, window, price_col=source or "close", out_col=out)
    if kind == "price_dist_sma":
        assert window is not None
        return causal.add_price_distance_ma(df, window, price_col=source or "close", out_col=out)
    if kind == "zscore":
        assert window is not None
        return causal.add_zscore(df, window, price_col=source or "close", out_col=out)
    if kind == "rvol":
        assert window is not None
        return causal.add_rolling_volatility(df, window, price_col=source or "close", out_col=out)
    if kind == "atr":
        assert window is not None
        return causal.add_atr(df, window, out_col=out)
    if kind == "range_norm":
        return causal.add_true_range_norm(df, out_col=out)
    if kind == "rel_volume":
        assert window is not None
        return causal.add_relative_volume(df, window, vol_col=source or "volume", out_col=out)
    if kind == "volume_zscore":
        assert window is not None
        return causal.add_volume_zscore(df, window, vol_col=source or "volume", out_col=out)
    if kind == "hour_cyclical":
        return causal.add_cyclical_time(df, "hour")
    if kind == "dow_cyclical":
        return causal.add_cyclical_time(df, "dow")
    if kind == "taker_buy_imbalance":
        assert lag is not None
        return causal.add_taker_buy_imbalance(df, lag=lag, out_col=out)
    raise ValueError(f"No builder registered for feature kind {kind!r}.")


def resolve_feature_set(
    items: Iterable[FeatureItemLike],
    *,
    ensure_sma: Sequence[int] = (),
) -> list[FeatureSpec]:
    """Resolve requested feature items into ordered, de-duplicated specs.

    ``ensure_sma`` guarantees that ``sma_{w}`` columns needed by the momentum
    baseline are present even if not listed explicitly, without duplicating a
    column already requested. Order is deterministic: requested items first, in
    order, then any injected SMAs by ascending window.
    """
    specs: list[FeatureSpec] = []
    seen: set[str] = set()
    for item in items:
        spec = resolve_spec(item.kind, window=item.window, lag=item.lag, source=item.source)
        key = ",".join(spec.columns)
        if key in seen:
            continue
        seen.add(key)
        specs.append(spec)

    have_cols = {c for s in specs for c in s.columns}
    for w in sorted({int(w) for w in ensure_sma}):
        col = f"sma_{w}"
        if col not in have_cols:
            spec = resolve_spec("sma", window=w)
            specs.append(spec)
            have_cols.add(col)
    return specs


def build_feature_frame(
    df: pl.DataFrame,
    specs: Sequence[FeatureSpec],
    *,
    holdout_start: object | None = None,
    time_col: str = "open_time",
) -> tuple[pl.DataFrame, list[FeatureSpec]]:
    """Build every requested feature causally and return ``(frame, specs)``.

    * Validates that all declared input columns exist before computing.
    * Applies the holdout guard when ``holdout_start`` is provided.
    * Sorts by ``time_col`` and appends columns without mutating the input.
    """
    required = {time_col}
    for spec in specs:
        required.update(spec.inputs)
    _require_columns(df, required)

    if holdout_start is not None:
        from datetime import datetime

        from perp_lab.eda.datasets import assert_no_holdout

        if isinstance(holdout_start, datetime):
            assert_no_holdout(df, holdout_start, time_col=time_col)

    out = df.sort(time_col)
    for spec in specs:
        out = _apply_spec(out, spec)
    return out, list(specs)


def feature_columns(specs: Sequence[FeatureSpec]) -> list[str]:
    """Flat, ordered list of every output column produced by ``specs``."""
    return [col for spec in specs for col in spec.columns]


def specs_to_metadata(specs: Sequence[FeatureSpec]) -> list[dict[str, object]]:
    """Serialise resolved specs for the run ``feature_metadata`` artifact."""
    return [spec.to_dict() for spec in specs]
