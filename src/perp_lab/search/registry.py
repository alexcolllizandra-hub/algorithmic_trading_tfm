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
from perp_lab.strategies.mean_reversion import MeanReversion
from perp_lab.strategies.momentum import MomentumCrossover

SPACE_VERSION = "1.0.0"

FAMILIES: tuple[str, ...] = ("momentum", "breakout", "mean_reversion")


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


def _momentum_space(exp: ExperimentConfig) -> SearchSpace:
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


def _breakout_space(exp: ExperimentConfig) -> SearchSpace:
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


def _mean_reversion_space(exp: ExperimentConfig) -> SearchSpace:
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


_BUILDERS: dict[str, Callable[[ExperimentConfig], SearchSpace]] = {
    "momentum": _momentum_space,
    "breakout": _breakout_space,
    "mean_reversion": _mean_reversion_space,
}


def build_search_space(exp: ExperimentConfig, family: str) -> SearchSpace:
    """Construct the :class:`SearchSpace` for ``family`` from validated config."""
    if family not in _BUILDERS:
        raise ValueError(f"Unknown strategy family {family!r}; known: {sorted(_BUILDERS)}.")
    return _BUILDERS[family](exp)


def available_families() -> tuple[str, ...]:
    return tuple(sorted(_BUILDERS))
