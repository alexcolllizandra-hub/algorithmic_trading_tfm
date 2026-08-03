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

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

# Bump when the numerical definition of any feature changes so that older run
# artifacts remain interpretable and comparisons across versions are explicit.
IMPL_VERSION = "0.2.0"

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
    requires_window: bool = False
    requires_lag: bool = False
    output_dtype: str = "Float64"
    null_policy: str = "warm-up rows are null"
    inf_policy: str = "guarded: zero denominators map to null (never +/-inf)"
    asset_dependency: str = "single"  # a single symbol's own history
    timeframe_dependency: str = "primary"  # bars of the primary timeframe
    allowed_sources: tuple[str, ...] = ()


# --------------------------------------------------------------------------- #
# The registry. Windows are in bars of the primary timeframe.
# --------------------------------------------------------------------------- #
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
    "sma": KindDef(
        family="trend",
        inputs=("close",),
        availability="close t",
        consumers=("BS", "GA"),
        leakage_risk="low (trailing mean)",
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
        requires_window=True,
        allowed_sources=("volume", "quote_volume"),
    ),
    "volume_zscore": KindDef(
        family="volume",
        inputs=("volume",),
        availability="close t",
        consumers=("GA", "ML", "RG"),
        leakage_risk="low (trailing mean/std; std=0 -> null)",
        requires_window=True,
        allowed_sources=("volume", "quote_volume"),
    ),
    "hour_cyclical": KindDef(
        family="time",
        inputs=("open_time",),
        availability="open t (known ex-ante)",
        consumers=("ML", "RG"),
        leakage_risk="none (calendar clock, known in advance)",
        inf_policy="not applicable (bounded sine/cosine)",
    ),
    "dow_cyclical": KindDef(
        family="time",
        inputs=("open_time",),
        availability="open t (known ex-ante)",
        consumers=("ML", "RG"),
        leakage_risk="none (calendar clock, known in advance)",
        inf_policy="not applicable (bounded sine/cosine)",
    ),
    "taker_buy_imbalance": KindDef(
        family="order_flow",
        inputs=("taker_buy_quote", "quote_volume"),
        availability="close t (contextual microstructure)",
        consumers=("ML",),
        leakage_risk="high if contemporaneous -> must be lagged >= 1 bar",
        requires_lag=True,
    ),
}


def known_kinds() -> tuple[str, ...]:
    """Sorted tuple of every registered feature kind."""
    return tuple(sorted(KIND_REGISTRY))


def validate_feature_item(
    kind: str,
    *,
    window: int | None = None,
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


def _columns_for(kind: str, *, window: int | None) -> tuple[str, ...]:
    if kind == "log_return":
        return ("log_return",) if window in (None, 1) else (f"log_return_{window}",)
    if kind == "range_norm":
        return ("range_norm",)
    if kind == "hour_cyclical":
        return ("hour_sin", "hour_cos")
    if kind == "dow_cyclical":
        return ("dow_sin", "dow_cos")
    if kind == "taker_buy_imbalance":
        return ("taker_buy_imbalance",)
    return (f"{kind}_{window}",)


def _warmup_for(kind: str, *, window: int | None, lag: int | None) -> int:
    """Number of leading rows that are deterministically null for this feature."""
    if kind == "log_return":
        return int(window or 1)
    if kind == "momentum":
        assert window is not None
        return window
    if kind == "rvol":
        # rolling std of the (already 1-lagged) log return needs ``window``
        # non-null returns; the first return is null, so warm-up == window.
        assert window is not None
        return window
    if kind in {"sma", "price_dist_sma", "zscore", "atr", "rel_volume", "volume_zscore"}:
        assert window is not None
        return window - 1
    if kind == "taker_buy_imbalance":
        assert lag is not None
        return lag
    # range_norm and cyclical time encodings are pointwise (no warm-up).
    return 0


def _lookback_for(kind: str, *, window: int | None, lag: int | None) -> int:
    if kind == "log_return":
        return int(window or 1)
    if kind == "taker_buy_imbalance":
        return int(lag or 1)
    if kind in {"range_norm", "hour_cyclical", "dow_cyclical"}:
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
            "impl_version": self.impl_version,
        }


def resolve_spec(
    kind: str,
    *,
    window: int | None = None,
    lag: int | None = None,
    source: str | None = None,
) -> FeatureSpec:
    """Resolve a requested kind + parameters into a full :class:`FeatureSpec`."""
    validate_feature_item(kind, window=window, lag=lag, source=source)
    kd = KIND_REGISTRY[kind]

    columns = _columns_for(kind, window=window)
    params: dict[str, int | str] = {}
    if window is not None:
        params["window"] = window
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
        lookback=_lookback_for(kind, window=window, lag=lag),
        availability=kd.availability,
        shift=shift,
        warmup=_warmup_for(kind, window=window, lag=lag),
        null_policy=kd.null_policy,
        inf_policy=kd.inf_policy,
        consumers=kd.consumers,
        leakage_risk=kd.leakage_risk,
        output_dtype=kd.output_dtype,
    )


@runtime_checkable
class FeatureItemLike(Protocol):
    """Structural type for a requested feature (matches the config model)."""

    kind: str
    window: int | None
    lag: int | None
    source: str | None
