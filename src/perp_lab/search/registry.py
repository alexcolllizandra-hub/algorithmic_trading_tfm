"""Strategy / search-space registry.

Both Random Search and the Genetic Algorithm build strategies through this
single registry, so adding a new strategy family (or new parameter types) never
requires touching either search algorithm: register a builder here and both
algorithms pick it up.

Every :class:`SearchSpace` is constructed from the **validated**
``ExperimentConfig`` (``strategies.families`` and ``strategies.volatility_filter``)
so parameter choices are never duplicated as constants inside the search code.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping

from perp_lab.config.experiment import ExperimentConfig
from perp_lab.features.spec import FeatureItemLike
from perp_lab.search.space import (
    BoolParam,
    CategoricalParam,
    ParamValue,
    SearchSpace,
)
from perp_lab.strategies.base import Strategy
from perp_lab.strategies.breakout import Breakout
from perp_lab.strategies.cross_asset import CrossAssetConfirmation
from perp_lab.strategies.funding import FundingTilt
from perp_lab.strategies.mean_reversion import MeanReversion
from perp_lab.strategies.momentum import MomentumCrossover
from perp_lab.strategies.volatility_breakout import VolatilityBreakout

SPACE_VERSION = "1.0.0"

FAMILIES: tuple[str, ...] = (
    "momentum",
    "breakout",
    "mean_reversion",
    "volatility_breakout",
    "funding",
    "BTC_ETH_confirmation",
)


class _FeatureItem:
    """Lightweight feature request compatible with ``resolve_feature_set``."""

    def __init__(self, kind: str, *, window: int | None = None, lag: int | None = None) -> None:
        self.kind = kind
        self.window = window
        self.window_slow: int | None = None
        self.lag = lag
        self.source: str | None = None


def _regime_gate(values: Mapping[str, ParamValue]) -> tuple[str, ...] | None:
    if not values.get("use_regime_gate", False):
        return None
    gate = values.get("regime_gate")
    return tuple(gate) if isinstance(gate, tuple) else None


def _momentum_space(exp: ExperimentConfig, symbol: str) -> SearchSpace:
    fam = exp.strategies.families.momentum
    directions = exp.strategies.allowed_directions
    gates = exp.strategies.volatility_filter.regime_gate_options

    params = (
        CategoricalParam("fast", tuple(fam.fast_ma)),
        CategoricalParam("slow", tuple(fam.slow_ma)),
        CategoricalParam("direction", tuple(directions)),
        BoolParam("use_trend_filter"),
        CategoricalParam(
            "trend_filter_ma", tuple(fam.trend_filter_ma), active_when=("use_trend_filter", True)
        ),
        BoolParam("use_regime_gate"),
        CategoricalParam("regime_gate", tuple(gates), active_when=("use_regime_gate", True)),
    )

    fast_choices = sorted(fam.fast_ma)
    slow_choices = sorted(fam.slow_ma)

    def repair(v: dict[str, ParamValue]) -> dict[str, ParamValue]:
        fast, slow = int(v["fast"]), int(v["slow"])  # type: ignore[arg-type]
        if fast >= slow:
            faster = [f for f in fast_choices if f < slow]
            if faster:
                v["fast"] = faster[-1]
            else:
                slower = [s for s in slow_choices if s > fast]
                if slower:
                    v["slow"] = slower[0]
        return v

    def validate(v: Mapping[str, ParamValue]) -> tuple[bool, str | None]:
        if int(v["fast"]) >= int(v["slow"]):  # type: ignore[arg-type]
            return False, f"fast ({v['fast']}) must be < slow ({v['slow']})"
        return True, None

    def build(v: Mapping[str, ParamValue]) -> Strategy:
        return MomentumCrossover(
            fast=int(v["fast"]),  # type: ignore[arg-type]
            slow=int(v["slow"]),  # type: ignore[arg-type]
            direction=str(v["direction"]),
            trend_filter_ma=int(v["trend_filter_ma"]) if v.get("use_trend_filter") else None,  # type: ignore[arg-type]
            regime_gate=_regime_gate(v),
        )

    windows = sorted(set(fam.fast_ma) | set(fam.slow_ma) | set(fam.trend_filter_ma))
    items: tuple[FeatureItemLike, ...] = tuple(_FeatureItem("sma", window=w) for w in windows)
    return SearchSpace("momentum", SPACE_VERSION, params, build, repair, validate, items)


def _breakout_space(exp: ExperimentConfig, symbol: str) -> SearchSpace:
    fam = exp.strategies.families.breakout
    directions = exp.strategies.allowed_directions
    gates = exp.strategies.volatility_filter.regime_gate_options

    params = (
        CategoricalParam("channel_window", tuple(fam.channel_window)),
        CategoricalParam("confirmation_bars", tuple(fam.confirmation_bars)),
        CategoricalParam("direction", tuple(directions)),
        BoolParam("use_regime_gate"),
        CategoricalParam("regime_gate", tuple(gates), active_when=("use_regime_gate", True)),
    )

    def repair(v: dict[str, ParamValue]) -> dict[str, ParamValue]:
        return v

    def validate(v: Mapping[str, ParamValue]) -> tuple[bool, str | None]:
        if int(v["channel_window"]) <= 0:  # type: ignore[arg-type]
            return False, "channel_window must be positive"
        if int(v["confirmation_bars"]) < 1:  # type: ignore[arg-type]
            return False, "confirmation_bars must be >= 1"
        return True, None

    def build(v: Mapping[str, ParamValue]) -> Strategy:
        return Breakout(
            channel_window=int(v["channel_window"]),  # type: ignore[arg-type]
            confirmation_bars=int(v["confirmation_bars"]),  # type: ignore[arg-type]
            direction=str(v["direction"]),
            regime_gate=_regime_gate(v),
        )

    # Breakout uses raw OHLC only; no engine feature columns are required.
    return SearchSpace("breakout", SPACE_VERSION, params, build, repair, validate, ())


def _mean_reversion_space(exp: ExperimentConfig, symbol: str) -> SearchSpace:
    fam = exp.strategies.families.mean_reversion
    directions = exp.strategies.allowed_directions
    gates = exp.strategies.volatility_filter.regime_gate_options

    params = (
        CategoricalParam("zscore_window", tuple(fam.zscore_window)),
        CategoricalParam("entry_z", tuple(fam.entry_z)),
        CategoricalParam("exit_z", tuple(fam.exit_z)),
        CategoricalParam("direction", tuple(directions)),
        BoolParam("use_regime_gate"),
        CategoricalParam("regime_gate", tuple(gates), active_when=("use_regime_gate", True)),
    )

    entry_choices = sorted(fam.entry_z)
    exit_choices = sorted(fam.exit_z)

    def repair(v: dict[str, ParamValue]) -> dict[str, ParamValue]:
        entry, exit_ = float(v["entry_z"]), float(v["exit_z"])  # type: ignore[arg-type]
        if exit_ >= entry:
            lower = [e for e in exit_choices if e < entry]
            if lower:
                v["exit_z"] = lower[-1]
            else:
                higher = [e for e in entry_choices if e > exit_]
                if higher:
                    v["entry_z"] = higher[0]
        return v

    def validate(v: Mapping[str, ParamValue]) -> tuple[bool, str | None]:
        if float(v["exit_z"]) >= float(v["entry_z"]):  # type: ignore[arg-type]
            return False, f"exit_z ({v['exit_z']}) must be < entry_z ({v['entry_z']})"
        return True, None

    def build(v: Mapping[str, ParamValue]) -> Strategy:
        return MeanReversion(
            zscore_window=int(v["zscore_window"]),  # type: ignore[arg-type]
            entry_z=float(v["entry_z"]),  # type: ignore[arg-type]
            exit_z=float(v["exit_z"]),  # type: ignore[arg-type]
            direction=str(v["direction"]),
            regime_gate=_regime_gate(v),
        )

    items: tuple[FeatureItemLike, ...] = tuple(
        _FeatureItem("zscore", window=w) for w in sorted(set(fam.zscore_window))
    )
    return SearchSpace("mean_reversion", SPACE_VERSION, params, build, repair, validate, items)


def _volatility_breakout_space(exp: ExperimentConfig, symbol: str) -> SearchSpace:
    fam = exp.strategies.families.volatility_breakout
    directions = exp.strategies.allowed_directions
    gates = exp.strategies.volatility_filter.regime_gate_options

    params = (
        CategoricalParam("level_window", tuple(fam.level_window)),
        CategoricalParam("atr_window", tuple(fam.atr_window)),
        CategoricalParam("entry_atr", tuple(fam.entry_atr)),
        CategoricalParam("exit_atr", tuple(fam.exit_atr)),
        CategoricalParam("exit_mode", tuple(fam.exit_mode)),
        BoolParam("use_atr_floor"),
        CategoricalParam(
            "min_atr_pct", tuple(fam.min_atr_pct), active_when=("use_atr_floor", True)
        ),
        CategoricalParam("direction", tuple(directions)),
        BoolParam("use_regime_gate"),
        CategoricalParam("regime_gate", tuple(gates), active_when=("use_regime_gate", True)),
    )

    exit_choices = sorted(fam.exit_atr)

    def repair(v: dict[str, ParamValue]) -> dict[str, ParamValue]:
        # Only the volatility stop compares the two multiples; the other exit
        # modes leave exit_atr inert, so repairing them would be meaningless churn.
        if v.get("exit_mode") != "volatility_stop":
            return v
        entry, exit_ = float(v["entry_atr"]), float(v["exit_atr"])  # type: ignore[arg-type]
        if exit_ >= entry:
            smaller = [e for e in exit_choices if e < entry]
            if smaller:
                v["exit_atr"] = smaller[-1]
        return v

    def validate(v: Mapping[str, ParamValue]) -> tuple[bool, str | None]:
        if int(v["level_window"]) <= 0 or int(v["atr_window"]) <= 0:  # type: ignore[arg-type]
            return False, "level_window and atr_window must be positive"
        if float(v["entry_atr"]) <= 0:  # type: ignore[arg-type]
            return False, "entry_atr must be strictly positive"
        if v.get("exit_mode") == "volatility_stop" and float(v["exit_atr"]) >= float(  # type: ignore[arg-type]
            v["entry_atr"]  # type: ignore[arg-type]
        ):
            return False, f"exit_atr ({v['exit_atr']}) must be < entry_atr ({v['entry_atr']})"
        return True, None

    def build(v: Mapping[str, ParamValue]) -> Strategy:
        return VolatilityBreakout(
            level_window=int(v["level_window"]),  # type: ignore[arg-type]
            atr_window=int(v["atr_window"]),  # type: ignore[arg-type]
            entry_atr=float(v["entry_atr"]),  # type: ignore[arg-type]
            exit_atr=float(v["exit_atr"]),  # type: ignore[arg-type]
            exit_mode=str(v["exit_mode"]),
            min_atr_pct=float(v["min_atr_pct"]) if v.get("use_atr_floor") else None,  # type: ignore[arg-type]
            direction=str(v["direction"]),
            regime_gate=_regime_gate(v),
        )

    # Built from raw OHLC; no engine feature columns are required.
    return SearchSpace("volatility_breakout", SPACE_VERSION, params, build, repair, validate, ())


def _funding_space(exp: ExperimentConfig, symbol: str) -> SearchSpace:
    fam = exp.strategies.families.funding
    directions = exp.strategies.allowed_directions
    gates = exp.strategies.volatility_filter.regime_gate_options

    params = (
        CategoricalParam("signal_window", tuple(fam.signal_window)),
        CategoricalParam("entry_z", tuple(fam.entry_z)),
        CategoricalParam("exit_z", tuple(fam.exit_z)),
        CategoricalParam("stance", tuple(fam.stance)),
        CategoricalParam("min_abs_rate", tuple(fam.min_abs_rate)),
        CategoricalParam("direction", tuple(directions)),
        BoolParam("use_regime_gate"),
        CategoricalParam("regime_gate", tuple(gates), active_when=("use_regime_gate", True)),
    )

    exit_choices = sorted(fam.exit_z)

    def repair(v: dict[str, ParamValue]) -> dict[str, ParamValue]:
        entry, exit_ = float(v["entry_z"]), float(v["exit_z"])  # type: ignore[arg-type]
        if exit_ >= entry:
            smaller = [e for e in exit_choices if e < entry]
            if smaller:
                v["exit_z"] = smaller[-1]
        return v

    def validate(v: Mapping[str, ParamValue]) -> tuple[bool, str | None]:
        if float(v["exit_z"]) >= float(v["entry_z"]):  # type: ignore[arg-type]
            return False, f"exit_z ({v['exit_z']}) must be < entry_z ({v['entry_z']})"
        if int(v["signal_window"]) <= 1:  # type: ignore[arg-type]
            return False, "signal_window must exceed 1 bar"
        return True, None

    def build(v: Mapping[str, ParamValue]) -> Strategy:
        return FundingTilt(
            signal_window=int(v["signal_window"]),  # type: ignore[arg-type]
            entry_z=float(v["entry_z"]),  # type: ignore[arg-type]
            exit_z=float(v["exit_z"]),  # type: ignore[arg-type]
            stance=str(v["stance"]),
            min_abs_rate=float(v["min_abs_rate"]),  # type: ignore[arg-type]
            direction=str(v["direction"]),
            regime_gate=_regime_gate(v),
        )

    # The funding rate must reach the signal, so it is requested explicitly. A
    # family that names a feature it never receives would silently trade on nulls.
    items: tuple[FeatureItemLike, ...] = (_FeatureItem("funding_rate"),)
    return SearchSpace("funding", SPACE_VERSION, params, build, repair, validate, items)


def _cross_asset_space(exp: ExperimentConfig, symbol: str) -> SearchSpace:
    fam = exp.strategies.families.cross_asset
    directions = exp.strategies.allowed_directions
    gates = exp.strategies.volatility_filter.regime_gate_options
    target = symbol
    reference = fam.reference_symbol.get(target)
    if reference is None:
        raise ValueError(
            f"No reference symbol configured for {target!r} in "
            f"strategies.families.cross_asset.reference_symbol "
            f"(known: {sorted(fam.reference_symbol)}). This family cannot fall back to "
            "a single-asset strategy; the dependency is the point."
        )

    params = (
        CategoricalParam("lookback", tuple(fam.lookback)),
        CategoricalParam("entry_threshold", tuple(fam.entry_threshold)),
        CategoricalParam("reference_threshold", tuple(fam.reference_threshold)),
        CategoricalParam("exit_threshold", tuple(fam.exit_threshold)),
        CategoricalParam("reference_lag", tuple(fam.reference_lag)),
        CategoricalParam("mode", tuple(fam.mode)),
        CategoricalParam("direction", tuple(directions)),
        BoolParam("use_regime_gate"),
        CategoricalParam("regime_gate", tuple(gates), active_when=("use_regime_gate", True)),
    )

    exit_choices = sorted(fam.exit_threshold)

    def repair(v: dict[str, ParamValue]) -> dict[str, ParamValue]:
        entry, exit_ = float(v["entry_threshold"]), float(v["exit_threshold"])  # type: ignore[arg-type]
        if exit_ >= entry:
            smaller = [e for e in exit_choices if e < entry]
            if smaller:
                v["exit_threshold"] = smaller[-1]
        return v

    def validate(v: Mapping[str, ParamValue]) -> tuple[bool, str | None]:
        if float(v["exit_threshold"]) >= float(v["entry_threshold"]):  # type: ignore[arg-type]
            return False, "exit_threshold must be < entry_threshold"
        if int(v["reference_lag"]) < 1:  # type: ignore[arg-type]
            return False, "reference_lag must be >= 1 bar (left-closed bars)"
        return True, None

    def build(v: Mapping[str, ParamValue]) -> Strategy:
        return CrossAssetConfirmation(
            lookback=int(v["lookback"]),  # type: ignore[arg-type]
            entry_threshold=float(v["entry_threshold"]),  # type: ignore[arg-type]
            reference_threshold=float(v["reference_threshold"]),  # type: ignore[arg-type]
            exit_threshold=float(v["exit_threshold"]),  # type: ignore[arg-type]
            reference_lag=int(v["reference_lag"]),  # type: ignore[arg-type]
            mode=str(v["mode"]),
            target_symbol=target,
            reference_symbol=reference,
            direction=str(v["direction"]),
            regime_gate=_regime_gate(v),
        )

    return SearchSpace("BTC_ETH_confirmation", SPACE_VERSION, params, build, repair, validate, ())


_BUILDERS: dict[str, Callable[[ExperimentConfig, str], SearchSpace]] = {
    "momentum": _momentum_space,
    "breakout": _breakout_space,
    "mean_reversion": _mean_reversion_space,
    "volatility_breakout": _volatility_breakout_space,
    "funding": _funding_space,
    "BTC_ETH_confirmation": _cross_asset_space,
}


def build_search_space(exp: ExperimentConfig, family: str, symbol: str = "") -> SearchSpace:
    """Construct the :class:`SearchSpace` for ``family`` from validated config.

    ``symbol`` is the asset being traded. Only the cross-asset family needs it, to
    resolve which asset confirms which, but it is passed uniformly so no builder
    has to reach for global state to find out what it is trading.
    """
    if family not in _BUILDERS:
        raise ValueError(f"Unknown strategy family {family!r}; known: {sorted(_BUILDERS)}.")
    return _BUILDERS[family](exp, symbol)


def available_families() -> tuple[str, ...]:
    return tuple(sorted(_BUILDERS))
