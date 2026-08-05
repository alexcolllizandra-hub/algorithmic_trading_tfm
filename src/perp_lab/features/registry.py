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
from perp_lab.features import context as context_mod
from perp_lab.features.context import FeatureContext
from perp_lab.features.spec import FeatureItemLike, FeatureSpec, resolve_spec


def _require_columns(df: pl.DataFrame, columns: Iterable[str]) -> None:
    missing = [c for c in columns if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required input columns: {sorted(set(missing))}")


def _apply_spec(df: pl.DataFrame, spec: FeatureSpec) -> pl.DataFrame:
    """Dispatch one resolved single-asset spec to its pure column builder."""
    kind = spec.kind
    p = spec.params
    window = int(p["window"]) if "window" in p else None
    window_slow = int(p["window_slow"]) if "window_slow" in p else None
    lag = int(p["lag"]) if "lag" in p else None
    source = str(p["source"]) if "source" in p else None
    out = spec.columns[0]

    if kind == "log_return":
        return causal.add_log_return(
            df, k=int(p.get("window", 1)), price_col=source or "close", out_col=out
        )
    if kind == "cum_return":
        return causal.add_cum_return(df, price_col=source or "close", out_col=out)
    if kind == "momentum":
        assert window is not None
        return causal.add_momentum(df, window, price_col=source or "close", out_col=out)
    if kind == "sma":
        assert window is not None
        return causal.add_sma(df, window, price_col=source or "close", out_col=out)
    if kind == "ema":
        assert window is not None
        return causal.add_ema(df, window, price_col=source or "close", out_col=out)
    if kind == "ma_distance":
        assert window is not None and window_slow is not None
        return causal.add_ma_distance(
            df, window, window_slow, price_col=source or "close", out_col=out
        )
    if kind == "price_dist_sma":
        assert window is not None
        return causal.add_price_distance_ma(df, window, price_col=source or "close", out_col=out)
    if kind == "zscore":
        assert window is not None
        return causal.add_zscore(df, window, price_col=source or "close", out_col=out)
    if kind == "roll_std":
        assert window is not None
        return causal.add_rolling_std(df, window, price_col=source or "close", out_col=out)
    if kind == "rvol":
        assert window is not None
        return causal.add_rolling_volatility(df, window, price_col=source or "close", out_col=out)
    if kind == "atr":
        assert window is not None
        return causal.add_atr(df, window, out_col=out)
    if kind == "true_range":
        return causal.add_true_range(df, out_col=out)
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
    if kind == "taker_buy_ratio":
        assert lag is not None
        return causal.add_taker_buy_ratio(df, lag=lag, out_col=out)
    if kind == "taker_buy_imbalance":
        assert lag is not None
        return causal.add_taker_buy_imbalance(df, lag=lag, out_col=out)
    raise ValueError(f"No single-asset builder registered for feature kind {kind!r}.")


def _apply_context_spec(
    df: pl.DataFrame, spec: FeatureSpec, ctx: FeatureContext | None
) -> pl.DataFrame:
    """Dispatch one resolved context (cross-asset / derivatives) spec.

    Raises ``ValueError`` when the required auxiliary input is missing, so an
    unavailable feature is reported explicitly instead of being fabricated.
    """
    kind = spec.kind
    p = spec.params
    window = int(p["window"]) if "window" in p else None
    out = spec.columns[0]
    if ctx is None or not ctx.has(spec.context_kind):
        raise ValueError(
            f"Feature {spec.name!r} (kind {kind!r}) requires the {spec.context_kind!r} "
            "context input, which is unavailable; not fabricating values."
        )

    if kind == "funding_rate":
        assert ctx.funding is not None
        return context_mod.attach_funding_rate(df, ctx.funding, out_col=out)
    if kind == "basis":
        assert ctx.mark is not None and ctx.index is not None
        return context_mod.add_basis(df, ctx.mark, ctx.index, out_col=out)
    if kind == "oi_change":
        assert ctx.open_interest is not None and window is not None
        return context_mod.add_open_interest_change(df, ctx.open_interest, window, out_col=out)
    if kind == "xasset_rel_return":
        assert ctx.peer is not None
        return context_mod.add_relative_return(df, ctx.peer, out_col=out)
    if kind == "xasset_rel_momentum":
        assert ctx.peer is not None and window is not None
        return context_mod.add_relative_momentum(df, ctx.peer, window, out_col=out)
    if kind == "xasset_corr":
        assert ctx.peer is not None and window is not None
        return context_mod.add_rolling_xcorr(df, ctx.peer, window, out_col=out)
    raise ValueError(f"No context builder registered for feature kind {kind!r}.")


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
        spec = resolve_spec(
            item.kind,
            window=item.window,
            window_slow=getattr(item, "window_slow", None),
            lag=item.lag,
            source=item.source,
        )
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
    context: FeatureContext | None = None,
    time_col: str = "open_time",
) -> tuple[pl.DataFrame, list[FeatureSpec]]:
    """Build every requested feature causally and return ``(frame, specs)``.

    * Validates that all declared input columns exist before computing.
    * Context features (cross-asset / derivatives) are built from ``context``;
      requesting one without the required auxiliary input is a hard error.
    * Applies the holdout guard when ``holdout_start`` is provided.
    * Sorts by ``time_col`` and appends columns without mutating the input.
    """
    required = {time_col}
    for spec in specs:
        if not spec.requires_context:
            required.update(spec.inputs)
    _require_columns(df, required)

    if holdout_start is not None:
        from datetime import datetime

        from perp_lab.eda.datasets import assert_no_holdout

        if isinstance(holdout_start, datetime):
            assert_no_holdout(df, holdout_start, time_col=time_col)

    out = df.sort(time_col)
    for spec in specs:
        if spec.requires_context:
            out = _apply_context_spec(out, spec, context)
        else:
            out = _apply_spec(out, spec)
    return out, list(specs)


def feature_columns(specs: Sequence[FeatureSpec]) -> list[str]:
    """Flat, ordered list of every output column produced by ``specs``."""
    return [col for spec in specs for col in spec.columns]


def specs_to_metadata(specs: Sequence[FeatureSpec]) -> list[dict[str, object]]:
    """Serialise resolved specs for the run ``feature_metadata`` artifact."""
    return [spec.to_dict() for spec in specs]
