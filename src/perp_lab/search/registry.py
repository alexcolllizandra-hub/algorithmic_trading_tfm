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

from perp_lab.config.experiment import CrtIntradayGrid, ExperimentConfig
from perp_lab.crt.strategies import (
    CRT_ROUND_TAG,
    FamilyMechanics,
    crt_htf_range_reversal,
    crt_three_candle_model,
    double_sweep_reversal,
    failed_breakout_reversal,
    opening_range_breakout_retest,
    pdh_reclaim_short,
    pdl_reclaim_long,
    session_liquidity_sweep,
    session_range_rotation,
)
from perp_lab.features.spec import FeatureItemLike
from perp_lab.search.space import (
    BoolParam,
    CategoricalParam,
    Param,
    ParamValue,
    SearchSpace,
)
from perp_lab.strategies.base import Strategy
from perp_lab.strategies.breakout import Breakout
from perp_lab.strategies.cross_asset import CrossAssetConfirmation
from perp_lab.strategies.funding import FundingTilt
from perp_lab.strategies.funding_reversal import FundingReversal
from perp_lab.strategies.intraday_seasonality import IntradaySeasonality
from perp_lab.strategies.mean_reversion import MeanReversion
from perp_lab.strategies.momentum import MomentumCrossover
from perp_lab.strategies.mtf_trend_consensus import MultiHorizonTrendConsensus
from perp_lab.strategies.volatility_breakout import VolatilityBreakout
from perp_lab.strategies.xasset_spread_reversion import CrossAssetSpreadReversion

SPACE_VERSION = "1.1.0"

# Families closed at Gate R3 (momentum at R2). They are recorded here because
# the registry must still be able to *reproduce* a historical run; they are not
# re-searched. See docs/decisions/0013 and 0015.
R3_CLOSED_FAMILIES: tuple[str, ...] = (
    "momentum",
    "breakout",
    "mean_reversion",
    "volatility_breakout",
    "funding",
    "BTC_ETH_confirmation",
)

# Gate S1 batch, pre-specified and frozen before any S1 result was observed.
S1_FAMILIES: tuple[str, ...] = (
    "mtf_trend_consensus",
    "funding_reversal",
    "intraday_seasonality",
    "xasset_spread_reversion",
)

# Round CRT_INTRADAY_V1: the Candle Range Theory batch, pre-specified as a
# separate round. Registered here so both engines can reach it; deliberately not
# added to R2 or R3, whose family sets are closed.
CRT_INTRADAY_V1_FAMILIES: tuple[str, ...] = (
    "crt_htf_range_reversal",
    "pdl_reclaim_long",
    "pdh_reclaim_short",
    "session_liquidity_sweep",
    "session_range_rotation",
    "opening_range_breakout_retest",
    "failed_breakout_reversal",
    "double_sweep_reversal",
    "crt_three_candle_model",
)

ROUND_TAGS: dict[str, str] = {
    **dict.fromkeys(R3_CLOSED_FAMILIES, "R3"),
    **dict.fromkeys(S1_FAMILIES, "S1"),
    **dict.fromkeys(CRT_INTRADAY_V1_FAMILIES, CRT_ROUND_TAG),
}

FAMILIES: tuple[str, ...] = (*R3_CLOSED_FAMILIES, *S1_FAMILIES, *CRT_INTRADAY_V1_FAMILIES)


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


def _mtf_trend_consensus_space(exp: ExperimentConfig, symbol: str) -> SearchSpace:
    fam = exp.strategies.families.mtf_trend_consensus
    directions = exp.strategies.allowed_directions
    gates = exp.strategies.volatility_filter.regime_gate_options

    params = (
        CategoricalParam("horizons", tuple(fam.horizon_sets)),
        CategoricalParam("min_agreement", tuple(fam.min_agreement)),
        CategoricalParam("exit_agreement", tuple(fam.exit_agreement)),
        CategoricalParam("min_strength", tuple(fam.min_strength)),
        CategoricalParam("strength_window", tuple(fam.strength_window)),
        CategoricalParam("direction", tuple(directions)),
        BoolParam("use_regime_gate"),
        CategoricalParam("regime_gate", tuple(gates), active_when=("use_regime_gate", True)),
    )

    agreement_choices = sorted(fam.min_agreement)
    exit_choices = sorted(fam.exit_agreement)

    def _horizons(v: Mapping[str, ParamValue]) -> tuple[int, ...]:
        raw = v["horizons"]
        assert isinstance(raw, tuple)
        return tuple(int(h) for h in raw)  # type: ignore[arg-type]

    def repair(v: dict[str, ParamValue]) -> dict[str, ParamValue]:
        width = len(_horizons(v))
        agreement = int(v["min_agreement"])  # type: ignore[arg-type]
        if agreement > width:
            feasible = [a for a in agreement_choices if a <= width]
            if feasible:
                v["min_agreement"] = feasible[-1]
                agreement = feasible[-1]
        if int(v["exit_agreement"]) > agreement:  # type: ignore[arg-type]
            feasible_exit = [e for e in exit_choices if e <= agreement]
            if feasible_exit:
                v["exit_agreement"] = feasible_exit[-1]
        return v

    def validate(v: Mapping[str, ParamValue]) -> tuple[bool, str | None]:
        width = len(_horizons(v))
        agreement = int(v["min_agreement"])  # type: ignore[arg-type]
        exit_agreement = int(v["exit_agreement"])  # type: ignore[arg-type]
        if agreement > width:
            return False, f"min_agreement ({agreement}) exceeds the {width} horizons available"
        if exit_agreement > agreement:
            return False, f"exit_agreement ({exit_agreement}) must be <= min_agreement"
        return True, None

    def build(v: Mapping[str, ParamValue]) -> Strategy:
        return MultiHorizonTrendConsensus(
            horizons=_horizons(v),
            min_agreement=int(v["min_agreement"]),  # type: ignore[arg-type]
            min_strength=float(v["min_strength"]),  # type: ignore[arg-type]
            strength_window=int(v["strength_window"]),  # type: ignore[arg-type]
            exit_agreement=int(v["exit_agreement"]),  # type: ignore[arg-type]
            direction=str(v["direction"]),
            regime_gate=_regime_gate(v),
        )

    horizons = sorted({h for horizon_set in fam.horizon_sets for h in horizon_set})
    items: tuple[FeatureItemLike, ...] = (
        *(_FeatureItem("momentum", window=h) for h in horizons),
        *(_FeatureItem("roll_std", window=w) for w in sorted(set(fam.strength_window))),
    )
    return SearchSpace("mtf_trend_consensus", SPACE_VERSION, params, build, repair, validate, items)


def _funding_reversal_space(exp: ExperimentConfig, symbol: str) -> SearchSpace:
    fam = exp.strategies.families.funding_reversal
    directions = exp.strategies.allowed_directions
    gates = exp.strategies.volatility_filter.regime_gate_options

    params = (
        CategoricalParam("rank_window", tuple(fam.rank_window)),
        CategoricalParam("extreme_pct", tuple(fam.extreme_pct)),
        CategoricalParam("holding_bars", tuple(fam.holding_bars)),
        CategoricalParam("min_abs_rate", tuple(fam.min_abs_rate)),
        CategoricalParam("direction", tuple(directions)),
        BoolParam("use_regime_gate"),
        CategoricalParam("regime_gate", tuple(gates), active_when=("use_regime_gate", True)),
    )

    def repair(v: dict[str, ParamValue]) -> dict[str, ParamValue]:
        return v

    def validate(v: Mapping[str, ParamValue]) -> tuple[bool, str | None]:
        window = int(v["rank_window"])  # type: ignore[arg-type]
        holding = int(v["holding_bars"])  # type: ignore[arg-type]
        if holding >= window:
            return False, (
                f"holding_bars ({holding}) must be shorter than the rank_window ({window}); "
                "otherwise a single episode spans the whole distribution it is measured against"
            )
        return True, None

    def build(v: Mapping[str, ParamValue]) -> Strategy:
        return FundingReversal(
            rank_window=int(v["rank_window"]),  # type: ignore[arg-type]
            extreme_pct=float(v["extreme_pct"]),  # type: ignore[arg-type]
            holding_bars=int(v["holding_bars"]),  # type: ignore[arg-type]
            min_abs_rate=float(v["min_abs_rate"]),  # type: ignore[arg-type]
            direction=str(v["direction"]),
            regime_gate=_regime_gate(v),
        )

    items: tuple[FeatureItemLike, ...] = (_FeatureItem("funding_rate"),)
    return SearchSpace("funding_reversal", SPACE_VERSION, params, build, repair, validate, items)


def _intraday_seasonality_space(exp: ExperimentConfig, symbol: str) -> SearchSpace:
    fam = exp.strategies.families.intraday_seasonality
    gates = exp.strategies.volatility_filter.regime_gate_options

    # ``side_mode`` already fixes the traded direction, so exposing the shared
    # ``direction`` parameter as well would spend budget on empty combinations.
    params = (
        CategoricalParam("entry_hour", tuple(fam.entry_hour)),
        CategoricalParam("holding_bars", tuple(fam.holding_bars)),
        CategoricalParam("side_mode", tuple(fam.side_mode)),
        BoolParam("use_trend_filter"),
        CategoricalParam(
            "trend_filter_ma", tuple(fam.trend_filter_ma), active_when=("use_trend_filter", True)
        ),
        BoolParam("use_regime_gate"),
        CategoricalParam("regime_gate", tuple(gates), active_when=("use_regime_gate", True)),
    )

    def repair(v: dict[str, ParamValue]) -> dict[str, ParamValue]:
        return v

    def validate(v: Mapping[str, ParamValue]) -> tuple[bool, str | None]:
        hour = int(v["entry_hour"])  # type: ignore[arg-type]
        if not 0 <= hour <= 23:
            return False, f"entry_hour ({hour}) must lie in [0, 23] UTC"
        return True, None

    def build(v: Mapping[str, ParamValue]) -> Strategy:
        return IntradaySeasonality(
            entry_hour=int(v["entry_hour"]),  # type: ignore[arg-type]
            holding_bars=int(v["holding_bars"]),  # type: ignore[arg-type]
            side_mode=str(v["side_mode"]),
            trend_filter_ma=int(v["trend_filter_ma"]) if v.get("use_trend_filter") else None,  # type: ignore[arg-type]
            direction="both",
            regime_gate=_regime_gate(v),
        )

    items: tuple[FeatureItemLike, ...] = tuple(
        _FeatureItem("sma", window=w) for w in sorted(set(fam.trend_filter_ma))
    )
    return SearchSpace(
        "intraday_seasonality", SPACE_VERSION, params, build, repair, validate, items
    )


def _xasset_spread_reversion_space(exp: ExperimentConfig, symbol: str) -> SearchSpace:
    fam = exp.strategies.families.xasset_spread_reversion
    directions = exp.strategies.allowed_directions
    gates = exp.strategies.volatility_filter.regime_gate_options
    target = symbol
    reference = fam.reference_symbol.get(target)
    if reference is None:
        raise ValueError(
            f"No reference leg configured for {target!r} in "
            f"strategies.families.xasset_spread_reversion.reference_symbol "
            f"(known: {sorted(fam.reference_symbol)}). A spread needs two legs; this family "
            "cannot fall back to a single-asset strategy."
        )

    params = (
        CategoricalParam("lookback", tuple(fam.lookback)),
        CategoricalParam("entry_spread", tuple(fam.entry_spread)),
        CategoricalParam("exit_spread", tuple(fam.exit_spread)),
        BoolParam("use_corr_floor"),
        CategoricalParam("min_corr", tuple(fam.min_corr), active_when=("use_corr_floor", True)),
        CategoricalParam(
            "corr_window", tuple(fam.corr_window), active_when=("use_corr_floor", True)
        ),
        CategoricalParam("direction", tuple(directions)),
        BoolParam("use_regime_gate"),
        CategoricalParam("regime_gate", tuple(gates), active_when=("use_regime_gate", True)),
    )

    exit_choices = sorted(fam.exit_spread)

    def repair(v: dict[str, ParamValue]) -> dict[str, ParamValue]:
        entry, exit_ = float(v["entry_spread"]), float(v["exit_spread"])  # type: ignore[arg-type]
        if exit_ >= entry:
            smaller = [e for e in exit_choices if e < entry]
            if smaller:
                v["exit_spread"] = smaller[-1]
        return v

    def validate(v: Mapping[str, ParamValue]) -> tuple[bool, str | None]:
        if float(v["exit_spread"]) >= float(v["entry_spread"]):  # type: ignore[arg-type]
            return False, "exit_spread must be < entry_spread"
        return True, None

    def build(v: Mapping[str, ParamValue]) -> Strategy:
        use_floor = bool(v.get("use_corr_floor"))
        return CrossAssetSpreadReversion(
            lookback=int(v["lookback"]),  # type: ignore[arg-type]
            entry_spread=float(v["entry_spread"]),  # type: ignore[arg-type]
            exit_spread=float(v["exit_spread"]),  # type: ignore[arg-type]
            min_corr=float(v["min_corr"]) if use_floor else None,  # type: ignore[arg-type]
            corr_window=int(v["corr_window"]) if use_floor else None,  # type: ignore[arg-type]
            target_symbol=target,
            reference_symbol=reference,
            direction=str(v["direction"]),
            regime_gate=_regime_gate(v),
        )

    items: tuple[FeatureItemLike, ...] = (
        *(_FeatureItem("xasset_rel_momentum", window=w) for w in sorted(set(fam.lookback))),
        *(_FeatureItem("xasset_corr", window=w) for w in sorted(set(fam.corr_window))),
    )
    return SearchSpace(
        "xasset_spread_reversion", SPACE_VERSION, params, build, repair, validate, items
    )


# --------------------------------------------------------------------------- #
# Round CRT_INTRADAY_V1
#
# Nine families, one engine. Each space is the shared grid plus the one or two
# dimensions that actually distinguish the family, because every extra
# configuration is paid for in the multiple-testing correction.
# --------------------------------------------------------------------------- #


def _crt_mechanics(exp: ExperimentConfig) -> FamilyMechanics:
    mech = exp.strategies.families.crt_intraday.mechanics
    return FamilyMechanics(
        stop_buffer_bps=mech.stop_buffer_bps,
        stop_atr_multiple=mech.stop_atr_multiple,
        max_wait_bars=mech.max_wait_bars,
        reclaim_within_bars=mech.reclaim_within_bars,
        reclaim_confirmation_closes=mech.reclaim_confirmation_closes,
        acceptance_closes=mech.acceptance_closes,
        acceptance_bps=mech.acceptance_bps,
        retest_tolerance_bps=mech.retest_tolerance_bps,
        max_bars_active=mech.max_bars_active,
        displacement_atr=mech.displacement_atr,
        cost_bps_per_side=exp.costs.fee_bps_per_side + exp.costs.slippage.baseline_bps,
        breakeven_after_first_target=mech.breakeven_after_first_target,
        atr_window=mech.atr_window,
    )


def _crt_shared_params(
    grid: CrtIntradayGrid,
    *,
    directions: tuple[str, ...] | None,
    include_sweep: bool = True,
    target_plans: tuple[str, ...] | None = None,
) -> tuple[Param, ...]:
    params: list[Param] = []
    if include_sweep:
        params.append(CategoricalParam("sweep_bps", tuple(grid.sweep_bps)))
    params.extend(
        (
            CategoricalParam("stop_kind", tuple(grid.stop_kind)),
            CategoricalParam("target_plan", tuple(target_plans or grid.target_plan)),
            CategoricalParam("time_stop_bars", tuple(grid.time_stop_bars)),
            CategoricalParam("min_net_reward_risk", tuple(grid.min_net_reward_risk)),
        )
    )
    if directions is not None:
        params.append(CategoricalParam("direction", tuple(directions)))
    return tuple(params)


def _crt_shared_kwargs(v: Mapping[str, ParamValue]) -> dict[str, ParamValue]:
    shared: dict[str, ParamValue] = {
        "stop_kind": str(v["stop_kind"]),
        "target_plan": str(v["target_plan"]),
        "time_stop_bars": int(v["time_stop_bars"]),  # type: ignore[arg-type]
        "min_net_reward_risk": float(v["min_net_reward_risk"]),  # type: ignore[arg-type]
    }
    if "sweep_bps" in v:
        shared["sweep_bps"] = float(v["sweep_bps"])  # type: ignore[arg-type]
    if "direction" in v:
        shared["direction"] = str(v["direction"])
    return shared


def _no_repair(v: dict[str, ParamValue]) -> dict[str, ParamValue]:
    return v


def _always_valid(v: Mapping[str, ParamValue]) -> tuple[bool, str | None]:
    return True, None


def _crt_htf_range_reversal_space(exp: ExperimentConfig, symbol: str) -> SearchSpace:
    crt = exp.strategies.families.crt_intraday
    fam = crt.htf_range_reversal
    mechanics = _crt_mechanics(exp)
    params = (
        *_crt_shared_params(crt.grid, directions=exp.strategies.allowed_directions),
        CategoricalParam("candle_timeframe", tuple(fam.candle_timeframe)),
        CategoricalParam("entry_rule", tuple(fam.entry_rule)),
    )

    def build(v: Mapping[str, ParamValue]) -> Strategy:
        return crt_htf_range_reversal(
            candle_timeframe=str(v["candle_timeframe"]),
            entry_rule=str(v["entry_rule"]),
            mechanics=mechanics,
            **_crt_shared_kwargs(v),  # type: ignore[arg-type]
        )

    return SearchSpace(
        "crt_htf_range_reversal", SPACE_VERSION, params, build, _no_repair, _always_valid, ()
    )


def _crt_previous_day_space(exp: ExperimentConfig, family: str) -> SearchSpace:
    """PDL long and PDH short share one space; only the fixed side differs."""
    crt = exp.strategies.families.crt_intraday
    fam = crt.previous_day_reclaim
    mechanics = _crt_mechanics(exp)
    builder = pdl_reclaim_long if family == "pdl_reclaim_long" else pdh_reclaim_short
    params = (
        *_crt_shared_params(crt.grid, directions=None),
        CategoricalParam("entry_rule", tuple(fam.entry_rule)),
        CategoricalParam("min_sweep_bps", tuple(fam.min_sweep_bps)),
    )

    def build(v: Mapping[str, ParamValue]) -> Strategy:
        return builder(
            entry_rule=str(v["entry_rule"]),
            min_sweep_bps=float(v["min_sweep_bps"]),  # type: ignore[arg-type]
            mechanics=mechanics,
            **_crt_shared_kwargs(v),
        )

    return SearchSpace(family, SPACE_VERSION, params, build, _no_repair, _always_valid, ())


def _crt_session_liquidity_sweep_space(exp: ExperimentConfig, symbol: str) -> SearchSpace:
    crt = exp.strategies.families.crt_intraday
    fam = crt.session_liquidity_sweep
    mechanics = _crt_mechanics(exp)
    params = (
        *_crt_shared_params(crt.grid, directions=exp.strategies.allowed_directions),
        CategoricalParam("session_pair", tuple(fam.session_pairs)),
        CategoricalParam("entry_rule", tuple(fam.entry_rule)),
    )

    def build(v: Mapping[str, ParamValue]) -> Strategy:
        pair = v["session_pair"]
        assert isinstance(pair, tuple)
        return session_liquidity_sweep(
            swept_session=str(pair[0]),
            trading_session=str(pair[1]),
            entry_rule=str(v["entry_rule"]),
            mechanics=mechanics,
            **_crt_shared_kwargs(v),  # type: ignore[arg-type]
        )

    def validate(v: Mapping[str, ParamValue]) -> tuple[bool, str | None]:
        pair = v["session_pair"]
        if not isinstance(pair, tuple) or len(pair) != 2 or pair[0] == pair[1]:
            return False, "a session cannot sweep its own range"
        return True, None

    return SearchSpace(
        "session_liquidity_sweep", SPACE_VERSION, params, build, _no_repair, validate, ()
    )


def _crt_session_range_rotation_space(exp: ExperimentConfig, symbol: str) -> SearchSpace:
    crt = exp.strategies.families.crt_intraday
    fam = crt.session_range_rotation
    mechanics = _crt_mechanics(exp)
    params = (
        *_crt_shared_params(crt.grid, directions=exp.strategies.allowed_directions),
        CategoricalParam("session", tuple(fam.session)),
        CategoricalParam("entry_rule", tuple(fam.entry_rule)),
    )

    def build(v: Mapping[str, ParamValue]) -> Strategy:
        return session_range_rotation(
            session=str(v["session"]),
            entry_rule=str(v["entry_rule"]),
            mechanics=mechanics,
            **_crt_shared_kwargs(v),  # type: ignore[arg-type]
        )

    return SearchSpace(
        "session_range_rotation", SPACE_VERSION, params, build, _no_repair, _always_valid, ()
    )


def _crt_opening_range_space(exp: ExperimentConfig, symbol: str) -> SearchSpace:
    crt = exp.strategies.families.crt_intraday
    fam = crt.opening_range_breakout_retest
    mechanics = _crt_mechanics(exp)
    # No sweep depth: a continuation setup is defined by a close beyond the
    # level, not by how far the wick went.
    params = (
        *_crt_shared_params(
            crt.grid,
            directions=exp.strategies.allowed_directions,
            include_sweep=False,
            target_plans=tuple(fam.target_plan),
        ),
        CategoricalParam("minutes", tuple(fam.minutes)),
        CategoricalParam("session", tuple(fam.session)),
        CategoricalParam("entry_rule", tuple(fam.entry_rule)),
    )

    def build(v: Mapping[str, ParamValue]) -> Strategy:
        return opening_range_breakout_retest(
            minutes=int(v["minutes"]),  # type: ignore[arg-type]
            session=str(v["session"]),
            entry_rule=str(v["entry_rule"]),
            mechanics=mechanics,
            **_crt_shared_kwargs(v),  # type: ignore[arg-type]
        )

    return SearchSpace(
        "opening_range_breakout_retest", SPACE_VERSION, params, build, _no_repair, _always_valid, ()
    )


def _crt_failed_breakout_space(exp: ExperimentConfig, symbol: str) -> SearchSpace:
    crt = exp.strategies.families.crt_intraday
    fam = crt.failed_breakout_reversal
    mechanics = _crt_mechanics(exp)
    params = (
        *_crt_shared_params(crt.grid, directions=exp.strategies.allowed_directions),
        CategoricalParam("reference_kind", tuple(fam.reference_kind)),
        CategoricalParam(
            "candle_timeframe",
            tuple(fam.candle_timeframe),
            active_when=("reference_kind", "previous_candle"),
        ),
        CategoricalParam("entry_rule", tuple(fam.entry_rule)),
    )

    def build(v: Mapping[str, ParamValue]) -> Strategy:
        return failed_breakout_reversal(
            reference_kind=str(v["reference_kind"]),
            candle_timeframe=str(v.get("candle_timeframe", fam.candle_timeframe[0])),
            entry_rule=str(v["entry_rule"]),
            mechanics=mechanics,
            **_crt_shared_kwargs(v),  # type: ignore[arg-type]
        )

    return SearchSpace(
        "failed_breakout_reversal", SPACE_VERSION, params, build, _no_repair, _always_valid, ()
    )


def _crt_double_sweep_space(exp: ExperimentConfig, symbol: str) -> SearchSpace:
    crt = exp.strategies.families.crt_intraday
    fam = crt.double_sweep_reversal
    mechanics = _crt_mechanics(exp)
    params = (
        *_crt_shared_params(crt.grid, directions=exp.strategies.allowed_directions),
        CategoricalParam("reference_kind", tuple(fam.reference_kind)),
        CategoricalParam(
            "candle_timeframe",
            tuple(fam.candle_timeframe),
            active_when=("reference_kind", "previous_candle"),
        ),
        CategoricalParam("entry_rule", tuple(fam.entry_rule)),
    )

    def build(v: Mapping[str, ParamValue]) -> Strategy:
        return double_sweep_reversal(
            reference_kind=str(v["reference_kind"]),
            candle_timeframe=str(v.get("candle_timeframe", fam.candle_timeframe[0])),
            entry_rule=str(v["entry_rule"]),
            mechanics=mechanics,
            **_crt_shared_kwargs(v),  # type: ignore[arg-type]
        )

    return SearchSpace(
        "double_sweep_reversal", SPACE_VERSION, params, build, _no_repair, _always_valid, ()
    )


def _crt_three_candle_space(exp: ExperimentConfig, symbol: str) -> SearchSpace:
    crt = exp.strategies.families.crt_intraday
    fam = crt.three_candle_model
    mechanics = _crt_mechanics(exp)
    params = (
        *_crt_shared_params(crt.grid, directions=exp.strategies.allowed_directions),
        CategoricalParam("candle_timeframe", tuple(fam.candle_timeframe)),
        CategoricalParam("displacement_atr", tuple(fam.displacement_atr)),
    )

    def build(v: Mapping[str, ParamValue]) -> Strategy:
        return crt_three_candle_model(
            candle_timeframe=str(v["candle_timeframe"]),
            displacement_atr=float(v["displacement_atr"]),  # type: ignore[arg-type]
            mechanics=mechanics,
            **_crt_shared_kwargs(v),  # type: ignore[arg-type]
        )

    return SearchSpace(
        "crt_three_candle_model", SPACE_VERSION, params, build, _no_repair, _always_valid, ()
    )


_BUILDERS: dict[str, Callable[[ExperimentConfig, str], SearchSpace]] = {
    "momentum": _momentum_space,
    "breakout": _breakout_space,
    "mean_reversion": _mean_reversion_space,
    "volatility_breakout": _volatility_breakout_space,
    "funding": _funding_space,
    "BTC_ETH_confirmation": _cross_asset_space,
    "mtf_trend_consensus": _mtf_trend_consensus_space,
    "funding_reversal": _funding_reversal_space,
    "intraday_seasonality": _intraday_seasonality_space,
    "xasset_spread_reversion": _xasset_spread_reversion_space,
    "crt_htf_range_reversal": _crt_htf_range_reversal_space,
    "pdl_reclaim_long": lambda exp, _symbol: _crt_previous_day_space(exp, "pdl_reclaim_long"),
    "pdh_reclaim_short": lambda exp, _symbol: _crt_previous_day_space(exp, "pdh_reclaim_short"),
    "session_liquidity_sweep": _crt_session_liquidity_sweep_space,
    "session_range_rotation": _crt_session_range_rotation_space,
    "opening_range_breakout_retest": _crt_opening_range_space,
    "failed_breakout_reversal": _crt_failed_breakout_space,
    "double_sweep_reversal": _crt_double_sweep_space,
    "crt_three_candle_model": _crt_three_candle_space,
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
