"""Feature contract: a small, explicit registry of causal feature *kinds*.

This module is intentionally dependency-light (standard library only) so the
experiment configuration can validate a requested feature set against the same
contract the engine uses, without importing Polars or creating an import cycle.

Each *kind* (e.g. ``momentum``, ``sma``, ``zscore``) is described once by a
:class:`KindDef`. A concrete request (a kind plus its parameters) resolves to a
fully-specified, serialisable :class:`FeatureSpec` that documents everything a
run artifact and the feature catalogue need: canonical name(s), family, input
columns, asset/timeframe dependency, parameters and lookback, decision-time
availability, mandatory shift, warm-up length, null and infinity policy,
permitted consumers, leakage risk, output dtype and a deterministic
implementation version.

The registry is deliberately small; it is not a feature-store framework.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

# Bump when the numerical definition of any feature changes so that older run
# artifacts remain interpretable and comparisons across versions are explicit.
IMPL_VERSION = "0.3.0"

# Consumer codes used throughout the methodology docs:
# BS = baseline strategy, GA = genetic strategy, ML = meta-label model,
# RG = regime model, RK = risk sizing.


@dataclass(frozen=True)
class KindDef:
    """Static description of one feature *kind* (shared by all its instances)."""

    family: str
    inputs: tuple[str, ...]
    availability: str
    consumers: tuple[str, ...]
    leakage_risk: str
    # Overfitting control: a search is configured with a set of packs, never with
    # "every registered kind". See :data:`PACKS`.
    pack: str = "core"
    # Set for measures that approximate an unobserved quantity (e.g. liquidity
    # without an order book). Such features must never be reported as observed.
    is_proxy: bool = False
    proxy_note: str = ""
    requires_window: bool = False
    requires_window_slow: bool = False
    requires_lag: bool = False
    requires_context: bool = False
    # For context features: which auxiliary input is needed
    # ("peer", "funding", "mark_index" or "open_interest").
    context_kind: str = ""
    output_dtype: str = "Float64"
    null_policy: str = "warm-up rows are null"
    inf_policy: str = "guarded: zero denominators map to null (never +/-inf)"
    asset_dependency: str = "single"  # a single symbol's own history
    timeframe_dependency: str = "primary"  # bars of the primary timeframe
    allowed_sources: tuple[str, ...] = ()


# The registry. Windows are in bars of the primary timeframe.
KIND_REGISTRY: dict[str, KindDef] = {
    "log_return": KindDef(
        family="returns",
        inputs=("close",),
        availability="close t",
        consumers=("BS", "GA", "ML", "RG"),
        leakage_risk="low (past-only difference)",
        allowed_sources=("close", "open"),
    ),
    "momentum": KindDef(
        family="momentum",
        inputs=("close",),
        availability="close t",
        consumers=("BS", "GA", "ML"),
        leakage_risk="low (past-only difference)",
        requires_window=True,
        allowed_sources=("close",),
    ),
    "cum_return": KindDef(
        family="returns",
        inputs=("close",),
        availability="close t",
        consumers=("ML", "RG"),
        leakage_risk="low (expanding sum of past log returns)",
        null_policy="no warm-up (first row is 0.0)",
        allowed_sources=("close",),
    ),
    "sma": KindDef(
        family="trend",
        inputs=("close",),
        availability="close t",
        consumers=("BS", "GA"),
        leakage_risk="low (trailing mean)",
        requires_window=True,
        allowed_sources=("close",),
    ),
    "ema": KindDef(
        family="trend",
        inputs=("close",),
        availability="close t",
        consumers=("BS", "GA"),
        leakage_risk="low (recursive past-only mean)",
        requires_window=True,
        allowed_sources=("close",),
    ),
    "ma_distance": KindDef(
        family="trend",
        inputs=("close",),
        availability="close t",
        consumers=("BS", "GA", "ML"),
        leakage_risk="low (ratio of two trailing means; scale-free)",
        requires_window=True,
        requires_window_slow=True,
        allowed_sources=("close",),
    ),
    "roll_std": KindDef(
        family="mean_reversion",
        inputs=("close",),
        availability="close t",
        consumers=("BS", "GA", "ML", "RG"),
        leakage_risk="low (trailing std of the price level)",
        requires_window=True,
        allowed_sources=("close",),
    ),
    "price_dist_sma": KindDef(
        family="trend",
        inputs=("close",),
        availability="close t",
        consumers=("BS", "GA", "ML"),
        leakage_risk="low (trailing mean; scale-free)",
        requires_window=True,
        allowed_sources=("close",),
    ),
    "zscore": KindDef(
        family="trend",
        inputs=("close",),
        availability="close t",
        consumers=("BS", "GA", "ML"),
        leakage_risk="low (trailing mean/std; std=0 -> null)",
        requires_window=True,
        allowed_sources=("close",),
    ),
    "rvol": KindDef(
        family="volatility",
        inputs=("close",),
        availability="close t",
        consumers=("BS", "GA", "RG", "RK"),
        leakage_risk="low (trailing std of past returns)",
        requires_window=True,
        allowed_sources=("close",),
    ),
    "atr": KindDef(
        family="volatility",
        inputs=("high", "low", "close"),
        availability="close t",
        consumers=("BS", "GA", "RK"),
        leakage_risk="low (uses current bar range + previous close)",
        requires_window=True,
    ),
    "true_range": KindDef(
        family="range",
        inputs=("high", "low", "close"),
        availability="close t",
        consumers=("BS", "GA", "RK"),
        leakage_risk="low (current-bar range + previous close)",
        null_policy="no warm-up (first row falls back to high-low)",
    ),
    "range_norm": KindDef(
        family="range",
        inputs=("high", "low", "close"),
        availability="close t",
        consumers=("BS", "GA", "ML", "RG"),
        leakage_risk="low (current-bar range, scale-free)",
    ),
    "rel_volume": KindDef(
        family="volume",
        inputs=("volume",),
        availability="close t",
        consumers=("BS", "GA", "ML"),
        leakage_risk="low (ratio to trailing mean; mean=0 -> null)",
        pack="extended",
        requires_window=True,
        allowed_sources=("volume", "quote_volume"),
    ),
    "volume_zscore": KindDef(
        family="volume",
        inputs=("volume",),
        availability="close t",
        consumers=("GA", "ML", "RG"),
        leakage_risk="low (trailing mean/std; std=0 -> null)",
        pack="extended",
        requires_window=True,
        allowed_sources=("volume", "quote_volume"),
    ),
    "hour_cyclical": KindDef(
        family="time",
        inputs=("open_time",),
        availability="open t (known ex-ante)",
        consumers=("ML", "RG"),
        leakage_risk="none (calendar clock, known in advance)",
        pack="extended",
        inf_policy="not applicable (bounded sine/cosine)",
    ),
    "dow_cyclical": KindDef(
        family="time",
        inputs=("open_time",),
        availability="open t (known ex-ante)",
        consumers=("ML", "RG"),
        leakage_risk="none (calendar clock, known in advance)",
        pack="extended",
        inf_policy="not applicable (bounded sine/cosine)",
    ),
    "taker_buy_ratio": KindDef(
        family="order_flow",
        inputs=("taker_buy_quote", "quote_volume"),
        availability="close t (contextual microstructure)",
        consumers=("ML", "RG"),
        leakage_risk="high if contemporaneous -> must be lagged >= 1 bar",
        pack="experimental",
        is_proxy=True,
        proxy_note=(
            "aggressor-flow share derived from aggregated trade data; it is not an "
            "order-book imbalance and must not be reported as one"
        ),
        requires_lag=True,
    ),
    "taker_buy_imbalance": KindDef(
        family="order_flow",
        inputs=("taker_buy_quote", "quote_volume"),
        availability="close t (contextual microstructure)",
        consumers=("ML",),
        leakage_risk="high if contemporaneous -> must be lagged >= 1 bar",
        pack="experimental",
        is_proxy=True,
        proxy_note=(
            "signed aggressor-flow proxy from aggregated trades; no order book is "
            "available at this data tier"
        ),
        requires_lag=True,
    ),
    # -- Derivatives (need an auxiliary stream; backward as-of aligned) ------ #
    "funding_rate": KindDef(
        family="derivatives",
        inputs=(),
        availability="as-of past (funding known before it is charged)",
        consumers=("ML", "RG", "RK"),
        leakage_risk="low (backward as-of join; never forward)",
        pack="extended",
        requires_context=True,
        context_kind="funding",
        null_policy="null before the first funding observation (never filled with 0)",
    ),
    "basis": KindDef(
        family="derivatives",
        inputs=(),
        availability="close t (mark/index aligned to bar grid)",
        consumers=("ML", "RG"),
        leakage_risk="low (contemporaneous mark vs index; scale-free)",
        pack="extended",
        is_proxy=True,
        proxy_note=(
            "relative deviation between the mark price and the exchange index, not a "
            "spot basis: no independent spot price is ingested at this data tier"
        ),
        requires_context=True,
        context_kind="mark_index",
    ),
    "oi_change": KindDef(
        family="derivatives",
        inputs=(),
        availability="as-of past (open interest snapshot <= open_time)",
        consumers=("ML", "RG"),
        leakage_risk="low (backward as-of join + past-only difference)",
        pack="extended",
        requires_window=True,
        requires_context=True,
        context_kind="open_interest",
    ),
    # -- Cross-asset (need a peer symbol on the same timeframe grid) --------- #
    "xasset_rel_return": KindDef(
        family="cross_asset",
        inputs=("close",),
        availability="close t (peer bar closes simultaneously)",
        consumers=("ML", "RG"),
        leakage_risk="low (exact join; peer bar closes with own bar)",
        pack="extended",
        requires_context=True,
        context_kind="peer",
        asset_dependency="pair",
    ),
    "xasset_rel_momentum": KindDef(
        family="cross_asset",
        inputs=("close",),
        availability="close t (peer bar closes simultaneously)",
        consumers=("ML", "RG"),
        leakage_risk="low (exact join; past-only momentum difference)",
        pack="extended",
        requires_window=True,
        requires_context=True,
        context_kind="peer",
        asset_dependency="pair",
    ),
    "xasset_corr": KindDef(
        family="cross_asset",
        inputs=("close",),
        availability="close t (peer bar closes simultaneously)",
        consumers=("ML", "RG", "RK"),
        leakage_risk="low (trailing correlation of past returns)",
        pack="extended",
        requires_window=True,
        requires_context=True,
        context_kind="peer",
        asset_dependency="pair",
    ),
}


# Ordered from least to most speculative. A pack implies the ones before it, so
# requesting "extended" means core + extended.
PACKS: tuple[str, ...] = ("core", "extended", "experimental")


def known_kinds() -> tuple[str, ...]:
    """Sorted tuple of every registered feature kind."""
    return tuple(sorted(KIND_REGISTRY))


def validate_packs(packs: Sequence[str]) -> tuple[str, ...]:
    """Reject unknown pack names instead of silently returning an empty set."""
    unknown = [p for p in packs if p not in PACKS]
    if unknown:
        raise ValueError(f"Unknown feature pack(s) {unknown}; known packs: {list(PACKS)}.")
    return tuple(packs)


def kinds_in_packs(packs: Sequence[str]) -> tuple[str, ...]:
    """Every feature kind admitted by the requested packs (cumulative).

    Packs are the primary defence against searching a space so wide that some
    parameterisation is bound to look good by chance. A run declares the packs it
    is allowed to use; anything outside them is not merely unused, it is
    unavailable.
    """
    validate_packs(packs)
    allowed = set()
    for pack in packs:
        allowed.update(PACKS[: PACKS.index(pack) + 1])
    return tuple(sorted(k for k, kd in KIND_REGISTRY.items() if kd.pack in allowed))


def catalogue() -> list[dict[str, object]]:
    """The full registry as serialisable rows, for artifacts and the dashboard."""
    return [
        {
            "kind": kind,
            "family": kd.family,
            "pack": kd.pack,
            "inputs": list(kd.inputs),
            "availability": kd.availability,
            "leakage_risk": kd.leakage_risk,
            "consumers": list(kd.consumers),
            "asset_dependency": kd.asset_dependency,
            "timeframe_dependency": kd.timeframe_dependency,
            "requires_context": kd.requires_context,
            "context_kind": kd.context_kind,
            "is_proxy": kd.is_proxy,
            "proxy_note": kd.proxy_note,
            "parameterised": kd.requires_window or kd.requires_window_slow or kd.requires_lag,
            "impl_version": IMPL_VERSION,
        }
        for kind, kd in sorted(KIND_REGISTRY.items())
    ]


def catalogue_counts() -> dict[str, dict[str, int]]:
    """Counts of registered *kinds* by family and by pack.

    These count distinct information sources, not columns: one parameterised kind
    can produce many columns, and reporting the column count as if it were the
    number of independent signals would overstate the breadth of the study.
    """
    by_family: dict[str, int] = {}
    by_pack: dict[str, int] = {}
    for kd in KIND_REGISTRY.values():
        by_family[kd.family] = by_family.get(kd.family, 0) + 1
        by_pack[kd.pack] = by_pack.get(kd.pack, 0) + 1
    return {
        "by_family": dict(sorted(by_family.items())),
        "by_pack": {p: by_pack.get(p, 0) for p in PACKS},
        "total_kinds": {"kinds": len(KIND_REGISTRY)},
    }


def proxy_kinds() -> tuple[str, ...]:
    """Kinds that approximate an unobserved quantity and must be labelled as such."""
    return tuple(sorted(k for k, kd in KIND_REGISTRY.items() if kd.is_proxy))


def validate_feature_item(
    kind: str,
    *,
    window: int | None = None,
    window_slow: int | None = None,
    lag: int | None = None,
    source: str | None = None,
) -> None:
    """Validate a requested feature *before* any computation.

    Rejects unknown kinds, missing/superfluous windows, invalid lags and
    unknown source columns with a clear ``ValueError``.
    """
    kd = KIND_REGISTRY.get(kind)
    if kd is None:
        raise ValueError(f"Unknown feature kind {kind!r}. Known kinds: {list(known_kinds())}.")

    if kd.requires_window:
        if window is None or window <= 0:
            raise ValueError(f"Feature kind {kind!r} requires a strictly positive window.")
    elif window is not None:
        raise ValueError(f"Feature kind {kind!r} does not take a window (got {window!r}).")

    if kd.requires_window_slow:
        if window_slow is None or window_slow <= 0:
            raise ValueError(f"Feature kind {kind!r} requires a strictly positive window_slow.")
        if window is not None and window >= window_slow:
            raise ValueError(
                f"Feature kind {kind!r} requires window ({window}) < window_slow ({window_slow})."
            )
    elif window_slow is not None:
        raise ValueError(
            f"Feature kind {kind!r} does not take a window_slow (got {window_slow!r})."
        )

    if kd.requires_lag:
        if lag is None or lag < 1:
            raise ValueError(f"Feature kind {kind!r} requires an integer lag >= 1.")
    elif lag is not None:
        raise ValueError(f"Feature kind {kind!r} does not take a lag (got {lag!r}).")

    if source is not None and source not in kd.allowed_sources:
        raise ValueError(
            f"Feature kind {kind!r} does not accept source {source!r}; "
            f"allowed: {list(kd.allowed_sources)}."
        )


def _columns_for(
    kind: str, *, window: int | None, window_slow: int | None = None
) -> tuple[str, ...]:
    if kind == "log_return":
        return ("log_return",) if window in (None, 1) else (f"log_return_{window}",)
    if kind == "ma_distance":
        return (f"ma_distance_{window}_{window_slow}",)
    if kind in {"range_norm", "true_range", "cum_return", "basis", "xasset_rel_return"}:
        return (kind,)
    if kind == "hour_cyclical":
        return ("hour_sin", "hour_cos")
    if kind == "dow_cyclical":
        return ("dow_sin", "dow_cos")
    if kind in {"taker_buy_imbalance", "taker_buy_ratio", "funding_rate"}:
        return (kind,)
    return (f"{kind}_{window}",)


def _warmup_for(kind: str, *, window: int | None, window_slow: int | None, lag: int | None) -> int:
    """Number of leading rows that are deterministically null for this feature."""
    if kind == "log_return":
        return int(window or 1)
    if kind in {"momentum", "rvol", "oi_change", "xasset_rel_momentum", "xasset_corr"}:
        # rolling/diff quantities over ``window`` (the first return is null for
        # rvol/corr, so warm-up == window rather than window - 1).
        assert window is not None
        return window
    if kind in {
        "sma",
        "ema",
        "price_dist_sma",
        "zscore",
        "atr",
        "rel_volume",
        "volume_zscore",
        "roll_std",
    }:
        assert window is not None
        return window - 1
    if kind == "ma_distance":
        assert window_slow is not None
        return window_slow - 1
    if kind in {"taker_buy_imbalance", "taker_buy_ratio"}:
        assert lag is not None
        return lag
    if kind == "xasset_rel_return":
        return 1
    # cum_return, true_range, range_norm, basis, funding_rate and cyclical time
    # encodings are pointwise / expanding (no deterministic warm-up nulls).
    return 0


def _lookback_for(
    kind: str, *, window: int | None, window_slow: int | None, lag: int | None
) -> int:
    if kind == "log_return":
        return int(window or 1)
    if kind in {"taker_buy_imbalance", "taker_buy_ratio"}:
        return int(lag or 1)
    if kind == "ma_distance":
        return int(window_slow or 1)
    if kind in {
        "range_norm",
        "true_range",
        "cum_return",
        "basis",
        "funding_rate",
        "xasset_rel_return",
        "hour_cyclical",
        "dow_cyclical",
    }:
        return 1
    assert window is not None
    return window


@dataclass(frozen=True)
class FeatureSpec:
    """A fully-resolved, serialisable description of one requested feature."""

    name: str
    kind: str
    family: str
    columns: tuple[str, ...]
    inputs: tuple[str, ...]
    asset_dependency: str
    timeframe_dependency: str
    params: dict[str, int | str] = field(default_factory=dict)
    lookback: int = 0
    availability: str = ""
    shift: int = 0
    warmup: int = 0
    null_policy: str = ""
    inf_policy: str = ""
    consumers: tuple[str, ...] = ()
    leakage_risk: str = ""
    output_dtype: str = "Float64"
    requires_context: bool = False
    context_kind: str = ""
    pack: str = "core"
    is_proxy: bool = False
    proxy_note: str = ""
    impl_version: str = IMPL_VERSION

    def to_dict(self) -> dict[str, object]:
        """A JSON-serialisable mapping for the run ``feature_metadata`` artifact."""
        return {
            "name": self.name,
            "kind": self.kind,
            "family": self.family,
            "columns": list(self.columns),
            "inputs": list(self.inputs),
            "asset_dependency": self.asset_dependency,
            "timeframe_dependency": self.timeframe_dependency,
            "params": dict(self.params),
            "lookback": self.lookback,
            "availability": self.availability,
            "shift": self.shift,
            "warmup": self.warmup,
            "null_policy": self.null_policy,
            "inf_policy": self.inf_policy,
            "consumers": list(self.consumers),
            "leakage_risk": self.leakage_risk,
            "output_dtype": self.output_dtype,
            "requires_context": self.requires_context,
            "context_kind": self.context_kind,
            "pack": self.pack,
            "is_proxy": self.is_proxy,
            "proxy_note": self.proxy_note,
            "impl_version": self.impl_version,
        }


def resolve_spec(
    kind: str,
    *,
    window: int | None = None,
    window_slow: int | None = None,
    lag: int | None = None,
    source: str | None = None,
) -> FeatureSpec:
    """Resolve a requested kind + parameters into a full :class:`FeatureSpec`."""
    validate_feature_item(kind, window=window, window_slow=window_slow, lag=lag, source=source)
    kd = KIND_REGISTRY[kind]

    columns = _columns_for(kind, window=window, window_slow=window_slow)
    params: dict[str, int | str] = {}
    if window is not None:
        params["window"] = window
    if window_slow is not None:
        params["window_slow"] = window_slow
    if lag is not None:
        params["lag"] = lag
    if source is not None:
        params["source"] = source

    inputs = kd.inputs
    if source is not None:
        # A custom source column replaces the default first input (e.g. volume).
        inputs = (source, *[c for c in kd.inputs if c != kd.inputs[0]])

    shift = int(lag) if (kd.requires_lag and lag is not None) else 0
    name = columns[0] if len(columns) == 1 else f"{kind}"
    return FeatureSpec(
        name=name,
        kind=kind,
        family=kd.family,
        columns=columns,
        inputs=inputs,
        asset_dependency=kd.asset_dependency,
        timeframe_dependency=kd.timeframe_dependency,
        params=params,
        lookback=_lookback_for(kind, window=window, window_slow=window_slow, lag=lag),
        availability=kd.availability,
        shift=shift,
        warmup=_warmup_for(kind, window=window, window_slow=window_slow, lag=lag),
        null_policy=kd.null_policy,
        inf_policy=kd.inf_policy,
        consumers=kd.consumers,
        leakage_risk=kd.leakage_risk,
        output_dtype=kd.output_dtype,
        requires_context=kd.requires_context,
        context_kind=kd.context_kind,
        pack=kd.pack,
        is_proxy=kd.is_proxy,
        proxy_note=kd.proxy_note,
    )


@runtime_checkable
class FeatureItemLike(Protocol):
    """Structural type for a requested feature (matches the config model)."""

    kind: str
    window: int | None
    window_slow: int | None
    lag: int | None
    source: str | None
