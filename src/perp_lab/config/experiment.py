"""Strict Pydantic models for ``configs/experiment.yaml`` (Chapter 5 contract).

These models validate the experiment configuration and enforce the
cross-field invariants that protect research integrity: consistent temporal
boundaries, development/holdout isolation, positive causal feature windows,
Random-Search / Genetic-Algorithm budget parity, and purge/embargo lengths
*derived* from the maximum label horizon / holding period (never arbitrary).

All models forbid unknown keys (``extra="forbid"``) so a typo in the YAML is a
hard error rather than a silently ignored setting.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from perp_lab.features.spec import resolve_spec, validate_feature_item
from perp_lab.utils.timeutils import TIMEFRAME_TO_MS

_PosIntTuple = tuple[int, ...]


class _Strict(BaseModel):
    """Base model: immutable and rejecting unknown keys."""

    model_config = ConfigDict(frozen=True, extra="forbid")


def _ensure_positive(values: tuple[int, ...], field_name: str) -> tuple[int, ...]:
    if not values:
        raise ValueError(f"{field_name} must be a non-empty list of windows.")
    if any(v <= 0 for v in values):
        raise ValueError(f"{field_name} must contain strictly positive integers.")
    return values


def _ensure_positive_floats(
    values: tuple[float, ...], field_name: str, *, allow_zero: bool = False
) -> tuple[float, ...]:
    if not values:
        raise ValueError(f"{field_name} must be a non-empty list.")
    bound_ok = (v >= 0 for v in values) if allow_zero else (v > 0 for v in values)
    if not all(bound_ok):
        rel = ">= 0" if allow_zero else "> 0"
        raise ValueError(f"{field_name} must contain values {rel}.")
    return values


class Timeframes(_Strict):
    primary: str = "1h"
    secondary: str = "15m"
    base: str = "5m"

    @field_validator("primary", "secondary", "base")
    @classmethod
    def _known(cls, v: str) -> str:
        if v not in TIMEFRAME_TO_MS:
            raise ValueError(f"Unknown timeframe {v!r}. Known: {sorted(TIMEFRAME_TO_MS)}")
        return v


class Periods(_Strict):
    development_start: datetime
    development_end_exclusive: datetime
    holdout_start: datetime
    cutoff_exclusive: datetime

    @field_validator(
        "development_start", "development_end_exclusive", "holdout_start", "cutoff_exclusive"
    )
    @classmethod
    def _utc(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            return v.replace(tzinfo=UTC)
        return v.astimezone(UTC)

    @model_validator(mode="after")
    def _ordered(self) -> Periods:
        if not (self.development_start < self.development_end_exclusive):
            raise ValueError("development_start must precede development_end_exclusive.")
        if self.development_end_exclusive != self.holdout_start:
            raise ValueError(
                "development_end_exclusive must equal holdout_start so the two "
                "partitions are contiguous and disjoint."
            )
        if not (self.holdout_start < self.cutoff_exclusive):
            raise ValueError("holdout_start must precede cutoff_exclusive.")
        return self


class FeatureItem(_Strict):
    """One requested feature: a registered kind plus its parameters.

    Validated against ``perp_lab.features.spec.KIND_REGISTRY`` so an unknown
    kind, a missing/superfluous window or an invalid lag is a hard error at load
    time, *before* any computation runs.
    """

    kind: str
    window: int | None = None
    window_slow: int | None = None
    lag: int | None = None
    source: str | None = None

    @model_validator(mode="after")
    def _valid(self) -> FeatureItem:
        validate_feature_item(
            self.kind,
            window=self.window,
            window_slow=self.window_slow,
            lag=self.lag,
            source=self.source,
        )
        return self


# The concrete causal feature set built by the development pipeline / baseline.
# Windows are drawn from the search-space lists below and justified in
# docs/methodology/feature_catalogue.md. This is distinct from those lists,
# which describe the wider space later searched by Random Search and the GA.
_DEFAULT_FEATURE_SET: tuple[FeatureItem, ...] = (
    FeatureItem(kind="log_return"),
    FeatureItem(kind="momentum", window=12),
    FeatureItem(kind="momentum", window=24),
    FeatureItem(kind="sma", window=24),
    FeatureItem(kind="sma", window=96),
    FeatureItem(kind="price_dist_sma", window=48),
    FeatureItem(kind="zscore", window=48),
    FeatureItem(kind="rvol", window=96),
    FeatureItem(kind="atr", window=14),
    FeatureItem(kind="range_norm"),
    FeatureItem(kind="rel_volume", window=24),
    FeatureItem(kind="hour_cyclical"),
    FeatureItem(kind="taker_buy_imbalance", lag=1),
)


class Features(_Strict):
    return_windows: _PosIntTuple = (1, 3, 6, 12, 24)
    ma_windows: _PosIntTuple = (12, 24, 48, 96, 168)
    momentum_windows: _PosIntTuple = (12, 24, 72)
    breakout_windows: _PosIntTuple = (24, 48, 96)
    rsi_windows: _PosIntTuple = (14, 24)
    zscore_windows: _PosIntTuple = (24, 48, 96)
    atr_windows: _PosIntTuple = (14, 24, 48)
    volatility_windows: _PosIntTuple = (24, 96, 168)
    relative_volume_windows: _PosIntTuple = (24, 96)
    regime_vol_windows: _PosIntTuple = (96, 168)
    funding_change_windows: _PosIntTuple = (3, 8, 24)
    corr_windows: _PosIntTuple = (168, 336)
    min_lookback_shift_bars: int = Field(default=1, ge=1)
    feature_set: tuple[FeatureItem, ...] = _DEFAULT_FEATURE_SET

    @model_validator(mode="after")
    def _feature_set_unique(self) -> Features:
        if not self.feature_set:
            raise ValueError("features.feature_set must list at least one feature.")
        seen: set[str] = set()
        for item in self.feature_set:
            spec = resolve_spec(
                item.kind,
                window=item.window,
                window_slow=item.window_slow,
                lag=item.lag,
                source=item.source,
            )
            for col in spec.columns:
                if col in seen:
                    raise ValueError(f"Duplicate feature column {col!r} in features.feature_set.")
                seen.add(col)
        return self

    @field_validator(
        "return_windows",
        "ma_windows",
        "momentum_windows",
        "breakout_windows",
        "rsi_windows",
        "zscore_windows",
        "atr_windows",
        "volatility_windows",
        "relative_volume_windows",
        "regime_vol_windows",
        "funding_change_windows",
        "corr_windows",
    )
    @classmethod
    def _positive(cls, v: tuple[int, ...]) -> tuple[int, ...]:
        return _ensure_positive(v, "feature windows")


class MomentumFamily(_Strict):
    fast_ma: _PosIntTuple = (6, 12, 24, 48)
    slow_ma: _PosIntTuple = (48, 96, 168, 336)
    trend_filter_ma: _PosIntTuple = (168, 336)

    @field_validator("fast_ma", "slow_ma", "trend_filter_ma")
    @classmethod
    def _positive(cls, v: tuple[int, ...]) -> tuple[int, ...]:
        return _ensure_positive(v, "momentum moving-average windows")

    @model_validator(mode="after")
    def _fast_below_slow(self) -> MomentumFamily:
        # The fastest MA must be able to be strictly faster than the slowest one.
        if min(self.fast_ma) >= max(self.slow_ma):
            raise ValueError("momentum fast_ma must offer values below slow_ma.")
        return self


class BreakoutFamily(_Strict):
    channel_window: _PosIntTuple = (24, 48, 96)
    confirmation_bars: _PosIntTuple = (1, 2, 3)

    @field_validator("channel_window", "confirmation_bars")
    @classmethod
    def _positive(cls, v: tuple[int, ...]) -> tuple[int, ...]:
        return _ensure_positive(v, "breakout windows")


class MeanReversionFamily(_Strict):
    zscore_window: _PosIntTuple = (24, 48, 96)
    entry_z: tuple[float, ...] = (1.5, 2.0, 2.5, 3.0)
    exit_z: tuple[float, ...] = (0.0, 0.5, 1.0)

    @field_validator("zscore_window")
    @classmethod
    def _positive(cls, v: tuple[int, ...]) -> tuple[int, ...]:
        return _ensure_positive(v, "mean-reversion zscore_window")

    @field_validator("entry_z")
    @classmethod
    def _entry_positive(cls, v: tuple[float, ...]) -> tuple[float, ...]:
        return _ensure_positive_floats(v, "mean-reversion entry_z")

    @field_validator("exit_z")
    @classmethod
    def _exit_nonneg(cls, v: tuple[float, ...]) -> tuple[float, ...]:
        return _ensure_positive_floats(v, "mean-reversion exit_z", allow_zero=True)

    @model_validator(mode="after")
    def _entry_beyond_exit(self) -> MeanReversionFamily:
        # Entry must be able to sit strictly outside the exit band.
        if max(self.entry_z) <= min(self.exit_z):
            raise ValueError("mean-reversion entry_z must exceed exit_z.")
        return self


class VolatilityBreakoutFamily(_Strict):
    """Breakout thresholds scaled by recent true-range volatility."""

    level_window: _PosIntTuple = (24, 48, 96)
    atr_window: _PosIntTuple = (14, 24, 48)
    entry_atr: tuple[float, ...] = (0.25, 0.5, 1.0)
    exit_atr: tuple[float, ...] = (0.1, 0.25, 0.5)
    exit_mode: tuple[str, ...] = ("reenter_level", "opposite_break", "volatility_stop")
    min_atr_pct: tuple[float, ...] = (0.25, 0.5)

    @field_validator("level_window", "atr_window")
    @classmethod
    def _positive(cls, v: tuple[int, ...]) -> tuple[int, ...]:
        return _ensure_positive(v, "volatility-breakout windows")

    @field_validator("entry_atr", "exit_atr")
    @classmethod
    def _multiples_positive(cls, v: tuple[float, ...]) -> tuple[float, ...]:
        if any(x <= 0 for x in v):
            raise ValueError("volatility-breakout ATR multiples must be strictly positive.")
        return v

    @field_validator("min_atr_pct")
    @classmethod
    def _quantiles(cls, v: tuple[float, ...]) -> tuple[float, ...]:
        if any(not 0.0 <= x < 1.0 for x in v):
            raise ValueError("min_atr_pct entries are quantiles and must lie in [0, 1).")
        return v

    @model_validator(mode="after")
    def _an_exit_below_an_entry_must_exist(self) -> VolatilityBreakoutFamily:
        # A volatility stop at or beyond the entry threshold closes the position on
        # the bar that opened it, so at least one admissible pair must exist.
        if min(self.exit_atr) >= max(self.entry_atr):
            raise ValueError(
                "No admissible (entry_atr, exit_atr) pair: every exit multiple is at or "
                "beyond every entry multiple, so the volatility stop can never be valid."
            )
        return self


class FundingFamily(_Strict):
    """Trades the published funding rate as a signal, never as a cashflow."""

    signal_window: _PosIntTuple = (24, 48, 168)
    entry_z: tuple[float, ...] = (1.0, 1.5, 2.0)
    exit_z: tuple[float, ...] = (0.0, 0.25, 0.5)
    stance: tuple[str, ...] = ("fade", "follow")
    min_abs_rate: tuple[float, ...] = (0.0, 0.00005)

    @field_validator("signal_window")
    @classmethod
    def _windows(cls, v: tuple[int, ...]) -> tuple[int, ...]:
        if any(w <= 1 for w in v):
            raise ValueError("funding signal_window must exceed 1 bar for a deviation to exist.")
        return v

    @field_validator("entry_z")
    @classmethod
    def _entry_positive(cls, v: tuple[float, ...]) -> tuple[float, ...]:
        if any(x <= 0 for x in v):
            raise ValueError("funding entry_z must be strictly positive.")
        return v

    @model_validator(mode="after")
    def _an_exit_inside_an_entry_must_exist(self) -> FundingFamily:
        if min(self.exit_z) >= max(self.entry_z):
            raise ValueError(
                "No admissible (entry_z, exit_z) pair: every exit band is at or outside "
                "every entry band, so a position would close on the bar that opened it."
            )
        return self


class CrossAssetFamily(_Strict):
    """One asset traded only when the other confirms, with a causal alignment lag."""

    lookback: _PosIntTuple = (6, 12, 24, 48)
    entry_threshold: tuple[float, ...] = (0.003, 0.005, 0.01)
    reference_threshold: tuple[float, ...] = (0.0, 0.002, 0.005)
    exit_threshold: tuple[float, ...] = (0.0, 0.001)
    reference_lag: _PosIntTuple = (1, 2, 4)
    mode: tuple[str, ...] = ("agree", "lead_lag", "divergence")
    reference_symbol: dict[str, str] = {"BTCUSDT": "ETHUSDT", "ETHUSDT": "BTCUSDT"}

    @field_validator("lookback")
    @classmethod
    def _positive(cls, v: tuple[int, ...]) -> tuple[int, ...]:
        return _ensure_positive(v, "cross-asset lookback")

    @field_validator("reference_lag")
    @classmethod
    def _lag_at_least_one_bar(cls, v: tuple[int, ...]) -> tuple[int, ...]:
        # Bars are labelled by open time and left-closed, so the reference bar
        # sharing the decision bar's timestamp is still being formed.
        if any(lag < 1 for lag in v):
            raise ValueError(
                "cross-asset reference_lag must be >= 1 bar; a zero lag lets an "
                "incomplete reference bar confirm a decision taken at the same time."
            )
        return v

    @field_validator("entry_threshold")
    @classmethod
    def _entry_positive(cls, v: tuple[float, ...]) -> tuple[float, ...]:
        if any(x <= 0 for x in v):
            raise ValueError("cross-asset entry_threshold must be strictly positive.")
        return v

    @model_validator(mode="after")
    def _reference_is_never_the_target(self) -> CrossAssetFamily:
        for target, reference in self.reference_symbol.items():
            if target == reference:
                raise ValueError(
                    f"{target} cannot be its own reference; that is a single-asset "
                    "strategy wearing a cross-asset label."
                )
        if min(self.exit_threshold) >= max(self.entry_threshold):
            raise ValueError(
                "No admissible (entry_threshold, exit_threshold) pair for the cross-asset family."
            )
        return self


class MultiHorizonTrendFamily(_Strict):
    """Gate S1: drift traded only when several separated horizons agree."""

    horizon_sets: tuple[tuple[int, ...], ...] = (
        (12, 48, 168),
        (6, 24, 96),
        (24, 96, 336),
        (6, 24, 96, 336),
    )
    min_agreement: _PosIntTuple = (2, 3)
    min_strength: tuple[float, ...] = (0.0, 0.25, 0.5)
    strength_window: _PosIntTuple = (48, 168)
    exit_agreement: _PosIntTuple = (1, 2)

    @field_validator("horizon_sets")
    @classmethod
    def _horizon_sets_usable(cls, v: tuple[tuple[int, ...], ...]) -> tuple[tuple[int, ...], ...]:
        if not v:
            raise ValueError("mtf_trend_consensus needs at least one horizon set.")
        for horizons in v:
            if len(horizons) < 2:
                raise ValueError(f"horizon set {horizons} needs at least two horizons.")
            if len(set(horizons)) != len(horizons):
                raise ValueError(f"horizon set {horizons} repeats a horizon.")
            _ensure_positive(horizons, "mtf_trend_consensus horizons")
        return v

    @field_validator("min_agreement", "strength_window", "exit_agreement")
    @classmethod
    def _positive(cls, v: tuple[int, ...]) -> tuple[int, ...]:
        return _ensure_positive(v, "mtf_trend_consensus counts and windows")

    @field_validator("min_strength")
    @classmethod
    def _strength_non_negative(cls, v: tuple[float, ...]) -> tuple[float, ...]:
        return _ensure_positive_floats(v, "mtf_trend_consensus min_strength", allow_zero=True)

    @field_validator("strength_window")
    @classmethod
    def _strength_window_admits_deviation(cls, v: tuple[int, ...]) -> tuple[int, ...]:
        if any(w <= 1 for w in v):
            raise ValueError("mtf_trend_consensus strength_window must exceed 1 bar.")
        return v

    @model_validator(mode="after")
    def _an_admissible_combination_exists(self) -> MultiHorizonTrendFamily:
        widest = max(len(h) for h in self.horizon_sets)
        if min(self.min_agreement) > widest:
            raise ValueError(
                f"No admissible min_agreement: the smallest option "
                f"({min(self.min_agreement)}) exceeds the widest horizon set ({widest})."
            )
        if min(self.exit_agreement) > max(self.min_agreement):
            raise ValueError(
                "No admissible (min_agreement, exit_agreement) pair: every exit threshold is "
                "at or above every entry threshold, so a position closes on the bar it opened."
            )
        return self


class FundingReversalFamily(_Strict):
    """Gate S1: bounded-horizon reversal after a trailing funding extreme."""

    rank_window: _PosIntTuple = (168, 336, 720)
    extreme_pct: tuple[float, ...] = (0.9, 0.95, 0.99)
    holding_bars: _PosIntTuple = (4, 8, 24, 48)
    min_abs_rate: tuple[float, ...] = (0.0, 0.00005)

    @field_validator("rank_window")
    @classmethod
    def _rank_windows(cls, v: tuple[int, ...]) -> tuple[int, ...]:
        if any(w <= 1 for w in v):
            raise ValueError("funding_reversal rank_window must exceed 1 bar.")
        return v

    @field_validator("holding_bars")
    @classmethod
    def _holding(cls, v: tuple[int, ...]) -> tuple[int, ...]:
        return _ensure_positive(v, "funding_reversal holding_bars")

    @field_validator("extreme_pct")
    @classmethod
    def _upper_tail(cls, v: tuple[float, ...]) -> tuple[float, ...]:
        if any(not 0.5 < x < 1.0 for x in v):
            raise ValueError(
                "funding_reversal extreme_pct entries are upper-tail quantiles and must lie "
                "strictly inside (0.5, 1.0); the lower tail is taken as 1 - pct."
            )
        return v

    @field_validator("min_abs_rate")
    @classmethod
    def _rate_floor(cls, v: tuple[float, ...]) -> tuple[float, ...]:
        return _ensure_positive_floats(v, "funding_reversal min_abs_rate", allow_zero=True)


class IntradaySeasonalityFamily(_Strict):
    """Gate S1: calendar-only entry at a fixed UTC hour, exit on a bar count."""

    entry_hour: tuple[int, ...] = tuple(range(24))
    holding_bars: _PosIntTuple = (1, 2, 4, 8)
    side_mode: tuple[str, ...] = ("long", "short")
    trend_filter_ma: _PosIntTuple = (168, 336)

    @field_validator("entry_hour")
    @classmethod
    def _hours(cls, v: tuple[int, ...]) -> tuple[int, ...]:
        if not v:
            raise ValueError("intraday_seasonality needs at least one entry_hour.")
        if any(not 0 <= h <= 23 for h in v):
            raise ValueError("intraday_seasonality entry_hour entries must lie in [0, 23] UTC.")
        return v

    @field_validator("holding_bars", "trend_filter_ma")
    @classmethod
    def _positive(cls, v: tuple[int, ...]) -> tuple[int, ...]:
        return _ensure_positive(v, "intraday_seasonality windows")

    @field_validator("side_mode")
    @classmethod
    def _sides(cls, v: tuple[str, ...]) -> tuple[str, ...]:
        bad = [s for s in v if s not in {"long", "short"}]
        if bad:
            raise ValueError(f"intraday_seasonality side_mode has unknown entries {bad}.")
        return v


class CrossAssetSpreadFamily(_Strict):
    """Gate S1: reversion of the target leg's relative move versus its reference."""

    lookback: _PosIntTuple = (6, 12, 24, 48)
    entry_spread: tuple[float, ...] = (0.005, 0.01, 0.02)
    exit_spread: tuple[float, ...] = (0.0, 0.002, 0.005)
    min_corr: tuple[float, ...] = (0.3, 0.5, 0.7)
    corr_window: _PosIntTuple = (48, 168)
    reference_symbol: dict[str, str] = {"BTCUSDT": "ETHUSDT", "ETHUSDT": "BTCUSDT"}

    @field_validator("lookback", "corr_window")
    @classmethod
    def _positive(cls, v: tuple[int, ...]) -> tuple[int, ...]:
        return _ensure_positive(v, "xasset_spread_reversion windows")

    @field_validator("corr_window")
    @classmethod
    def _corr_window_admits_correlation(cls, v: tuple[int, ...]) -> tuple[int, ...]:
        if any(w < 2 for w in v):
            raise ValueError("xasset_spread_reversion corr_window must be at least 2 bars.")
        return v

    @field_validator("entry_spread")
    @classmethod
    def _entry_positive(cls, v: tuple[float, ...]) -> tuple[float, ...]:
        return _ensure_positive_floats(v, "xasset_spread_reversion entry_spread")

    @field_validator("exit_spread")
    @classmethod
    def _exit_non_negative(cls, v: tuple[float, ...]) -> tuple[float, ...]:
        return _ensure_positive_floats(v, "xasset_spread_reversion exit_spread", allow_zero=True)

    @field_validator("min_corr")
    @classmethod
    def _correlations(cls, v: tuple[float, ...]) -> tuple[float, ...]:
        if any(not -1.0 <= x <= 1.0 for x in v):
            raise ValueError("xasset_spread_reversion min_corr entries must lie in [-1, 1].")
        return v

    @model_validator(mode="after")
    def _spread_is_between_two_legs(self) -> CrossAssetSpreadFamily:
        if min(self.exit_spread) >= max(self.entry_spread):
            raise ValueError(
                "No admissible (entry_spread, exit_spread) pair: every exit band is at or "
                "outside every entry band."
            )
        for target, reference in self.reference_symbol.items():
            if target == reference:
                raise ValueError(
                    f"{target} cannot be its own reference leg; there would be no spread."
                )
        return self


class Families(_Strict):
    momentum: MomentumFamily = MomentumFamily()
    breakout: BreakoutFamily = BreakoutFamily()
    mean_reversion: MeanReversionFamily = MeanReversionFamily()
    volatility_breakout: VolatilityBreakoutFamily = VolatilityBreakoutFamily()
    funding: FundingFamily = FundingFamily()
    cross_asset: CrossAssetFamily = CrossAssetFamily()
    # -- Gate S1 batch (pre-specified 2026-08-11; see docs/roadmap/gate_s1.md) --
    mtf_trend_consensus: MultiHorizonTrendFamily = MultiHorizonTrendFamily()
    funding_reversal: FundingReversalFamily = FundingReversalFamily()
    intraday_seasonality: IntradaySeasonalityFamily = IntradaySeasonalityFamily()
    xasset_spread_reversion: CrossAssetSpreadFamily = CrossAssetSpreadFamily()


class VolatilityFilter(_Strict):
    enabled_options: tuple[bool, ...] = (True, False)
    regime_gate_options: tuple[tuple[str, ...], ...] = (
        ("low", "medium"),
        ("medium", "high"),
        ("low", "medium", "high"),
    )


class PositionSizing(_Strict):
    method: str = "volatility_target"
    provisional: bool = True
    annual_vol_target_pct: float = Field(default=20.0, gt=0)
    max_leverage: float = Field(default=3.0, gt=0)
    fixed_fraction: float = Field(default=1.0, gt=0)

    @field_validator("method")
    @classmethod
    def _known(cls, v: str) -> str:
        if v not in {"volatility_target", "fixed_fraction"}:
            raise ValueError("method must be 'volatility_target' or 'fixed_fraction'.")
        return v


class Strategies(_Strict):
    execution: str = "next_bar_open"
    allowed_directions: tuple[str, ...] = ("long", "short", "both")
    families: Families = Families()
    stop_loss_atr: tuple[float, ...] = (1.0, 1.5, 2.0, 3.0)
    take_profit_atr: tuple[float, ...] = (1.0, 2.0, 3.0, 4.0)
    max_holding_bars: _PosIntTuple = (24, 48, 96)
    volatility_filter: VolatilityFilter = VolatilityFilter()
    position_sizing: PositionSizing = PositionSizing()

    @field_validator("execution")
    @classmethod
    def _exec(cls, v: str) -> str:
        if v != "next_bar_open":
            raise ValueError("Only 'next_bar_open' execution is supported (no same-bar fills).")
        return v

    @field_validator("max_holding_bars")
    @classmethod
    def _positive(cls, v: tuple[int, ...]) -> tuple[int, ...]:
        return _ensure_positive(v, "max_holding_bars")

    @field_validator("stop_loss_atr", "take_profit_atr")
    @classmethod
    def _positive_atr_multiples(cls, v: tuple[float, ...]) -> tuple[float, ...]:
        return _ensure_positive_floats(v, "ATR stop/target multiples")

    @field_validator("allowed_directions")
    @classmethod
    def _known_directions(cls, v: tuple[str, ...]) -> tuple[str, ...]:
        valid = {"long", "short", "both"}
        bad = [d for d in v if d not in valid]
        if bad:
            raise ValueError(f"allowed_directions has unknown entries {bad}; valid: {valid}.")
        return v


class MetaLabeling(_Strict):
    task: str = "binary"
    models: tuple[str, ...] = ("logistic_regression", "random_forest", "lightgbm")
    calibration: str = "isotonic"
    decision_threshold: str = "tuned_on_validation"

    @field_validator("decision_threshold")
    @classmethod
    def _no_holdout_tuning(cls, v: str) -> str:
        if "holdout" in v.lower():
            raise ValueError("The meta-label threshold must never be tuned on the holdout.")
        return v


class Labeling(_Strict):
    upper_barrier_atr: float = Field(default=2.0, gt=0)
    lower_barrier_atr: float = Field(default=2.0, gt=0)
    vertical_barrier_bars: int = Field(default=24, ge=1)
    provisional: bool = True
    min_return_bps: float = Field(default=0.0, ge=0)
    meta_labeling: MetaLabeling = MetaLabeling()


class Purge(_Strict):
    derive_from: str = "max(label_horizon, max_holding)"
    bars: int | None = None  # computed at runtime; see ExperimentConfig.purge_bars


class Embargo(_Strict):
    derive_from: str = "max(label_horizon, max_holding)"
    fraction_of_test: float = Field(default=0.01, ge=0)
    bars: int | None = None  # computed at runtime; see ExperimentConfig.embargo_bars


class WalkForward(_Strict):
    scheme: str = "expanding"
    initial_train_days: int = Field(default=730, ge=1)
    validation_days: int = Field(default=90, ge=1)
    test_days: int = Field(default=90, ge=1)
    step_days: int = Field(default=90, ge=1)
    min_folds: int = Field(default=8, ge=1)
    purge: Purge = Purge()
    embargo: Embargo = Embargo()

    @field_validator("scheme")
    @classmethod
    def _known(cls, v: str) -> str:
        if v not in {"expanding", "sliding"}:
            raise ValueError("walk_forward.scheme must be 'expanding' or 'sliding'.")
        return v


class Slippage(_Strict):
    baseline_bps: float = Field(default=1.0, ge=0)
    scenarios_bps: tuple[float, ...] = (0.0, 1.0, 2.0, 5.0)


class Funding(_Strict):
    treatment: str = "realized"
    align: str = "as_of_past"

    @field_validator("align")
    @classmethod
    def _as_of_past(cls, v: str) -> str:
        if v != "as_of_past":
            raise ValueError("funding.align must be 'as_of_past' (no look-ahead).")
        return v


class Costs(_Strict):
    provisional: bool = True
    fee_model: str = "taker"
    taker_fee_bps: float = Field(default=4.0, ge=0)
    maker_fee_bps: float = Field(default=2.0, ge=0)
    slippage: Slippage = Slippage()
    funding: Funding = Funding()
    min_notional_usdt: float = Field(default=100.0, ge=0)

    @field_validator("fee_model")
    @classmethod
    def _known(cls, v: str) -> str:
        if v not in {"taker", "maker"}:
            raise ValueError("costs.fee_model must be 'taker' or 'maker'.")
        return v

    @property
    def fee_bps_per_side(self) -> float:
        return self.taker_fee_bps if self.fee_model == "taker" else self.maker_fee_bps


def ga_unique_evaluations(population_size: int, generations: int, elitism: int) -> int:
    """Upper bound on unique objective evaluations within ``generations``.

    Generation 0 evaluates a full population. Every later generation carries the
    ``elitism`` best individuals over with cached fitness, so it can add at most
    ``population_size - elitism`` new genotypes. ``population_size * generations``
    therefore overstates the count whenever ``elitism > 0``.

    This is a *bound*, not a prediction: offspring frequently rediscover genotypes
    scored in earlier generations, which hit the evaluator cache and consume no
    budget. That is precisely why the budget must drive the loop rather than the
    generation count -- the shortfall varies with the seed.
    """
    return population_size + (generations - 1) * (population_size - elitism)


class RandomSearch(_Strict):
    sampler: str = "uniform_over_space"


class GeneticAlgorithm(_Strict):
    population_size: int = Field(default=100, ge=2)
    # A safety cap, not the target: the GA evolves until evaluation_budget unique
    # evaluations are spent. 100 + (60 - 1) * (100 - 5) = 5705 reachable >= 2000.
    max_generations: int = Field(default=60, ge=1)
    crossover_rate: float = Field(default=0.7, ge=0, le=1)
    mutation_rate: float = Field(default=0.2, ge=0, le=1)
    elitism: int = Field(default=5, ge=0)
    selection: str = "tournament"
    tournament_size: int = Field(default=3, ge=2)
    chromosome: str = "fixed_length"


class Search(_Strict):
    evaluation_budget: int = Field(default=2000, ge=1)
    provisional: bool = True
    random_search: RandomSearch = RandomSearch()
    genetic_algorithm: GeneticAlgorithm = GeneticAlgorithm()

    @model_validator(mode="after")
    def _budget_parity(self) -> Search:
        """The budget is the target; the GA's cap must be able to reach it.

        Both engines run until they have spent exactly ``evaluation_budget`` unique,
        valid, non-cached objective evaluations. The genetic algorithm can only do
        that if its generation cap allows enough new genotypes, so an unreachable
        combination is rejected here rather than discovered mid-study.
        """
        ga = self.genetic_algorithm
        if ga.elitism >= ga.population_size:
            raise ValueError("genetic_algorithm.elitism must be smaller than population_size.")
        reachable = ga_unique_evaluations(ga.population_size, ga.max_generations, ga.elitism)
        if reachable < self.evaluation_budget:
            raise ValueError(
                f"evaluation_budget={self.evaluation_budget} is unreachable: with "
                f"population_size={ga.population_size}, elitism={ga.elitism} and "
                f"max_generations={ga.max_generations} the genetic algorithm can "
                f"perform at most {reachable} unique evaluations. Raise "
                "max_generations or population_size, or lower evaluation_budget."
            )
        return self


class FitnessWeights(_Strict):
    sharpe: float = 1.0
    max_drawdown_penalty: float = Field(default=0.5, ge=0)
    turnover_penalty: float = Field(default=0.2, ge=0)
    fold_instability_penalty: float = Field(default=0.3, ge=0)
    complexity_penalty: float = Field(default=0.1, ge=0)


class FitnessConstraints(_Strict):
    min_trades_total: int = Field(default=50, ge=0)
    min_trades_per_fold: int = Field(default=3, ge=0)
    max_leverage: float = Field(default=3.0, gt=0)


class Fitness(_Strict):
    primary_objective: str = "walk_forward_sharpe"
    weights: FitnessWeights = FitnessWeights()
    constraints: FitnessConstraints = FitnessConstraints()
    # Contiguous sub-blocks each fold's validation window is cut into to measure
    # within-fold stability. Under the per-outer-fold protocol (ADR 0012) this
    # replaces the across-fold spread, which a single fold cannot observe without
    # reading later folds.
    stability_blocks: int = Field(default=4, ge=2)
    provisional: bool = True


class MonteCarlo(_Strict):
    method: str = "trade_order_bootstrap"
    resamples: int = Field(default=1000, ge=1)


class Robustness(_Strict):
    higher_cost_scenarios_bps: tuple[float, ...] = (2.0, 5.0, 10.0)
    parameter_perturbation_pct: tuple[float, ...] = (5.0, 10.0, 20.0)
    delayed_execution_bars: tuple[int, ...] = (1, 2)
    subperiod_stability: str = "per_year"
    asset_transfer: bool = True
    regime_conditioned: bool = True
    monte_carlo: MonteCarlo = MonteCarlo()
    deflated_sharpe: bool = True
    benchmarks: tuple[str, ...] = ("buy_and_hold", "flat_cash", "random_entry_matched_exposure")


class Risk(_Strict):
    max_position_leverage: float = Field(default=3.0, gt=0)
    max_gross_exposure: float = Field(default=1.0, gt=0)
    max_daily_loss_pct: float | None = None
    provisional: bool = True


class ExperimentConfig(_Strict):
    """The full, validated Chapter 5 experiment contract."""

    version: str = "0.1.0"
    random_seed: int = 42
    assets: tuple[str, ...] = ("BTCUSDT", "ETHUSDT")
    timeframes: Timeframes = Timeframes()
    annualization_days: int = Field(default=365, ge=1)
    periods: Periods
    features: Features = Features()
    strategies: Strategies = Strategies()
    labeling: Labeling = Labeling()
    walk_forward: WalkForward = WalkForward()
    costs: Costs = Costs()
    search: Search = Search()
    fitness: Fitness = Fitness()
    robustness: Robustness = Robustness()
    risk: Risk = Risk()

    @field_validator("assets")
    @classmethod
    def _upper_nonempty(cls, v: tuple[str, ...]) -> tuple[str, ...]:
        if not v:
            raise ValueError("assets must be non-empty.")
        return tuple(a.strip().upper() for a in v)

    # -- derived, leakage-relevant horizons --------------------------------- #
    @property
    def bars_per_day(self) -> int:
        step = TIMEFRAME_TO_MS[self.timeframes.primary]
        return TIMEFRAME_TO_MS["1d"] // step

    @property
    def max_holding_bars(self) -> int:
        return max(self.strategies.max_holding_bars)

    @property
    def label_horizon_bars(self) -> int:
        return self.labeling.vertical_barrier_bars

    @property
    def purge_bars(self) -> int:
        """Purge length = max(label horizon, max holding). Not arbitrary."""
        return max(self.label_horizon_bars, self.max_holding_bars)

    @property
    def embargo_bars(self) -> int:
        """Embargo = purge + a small fraction of the test window (in bars)."""
        test_bars = self.walk_forward.test_days * self.bars_per_day
        extra = math.ceil(self.walk_forward.embargo.fraction_of_test * test_bars)
        return self.purge_bars + extra

    @model_validator(mode="after")
    def _embargo_ge_purge(self) -> ExperimentConfig:
        if self.embargo_bars < self.purge_bars:
            raise ValueError("Derived embargo_bars must be >= purge_bars.")
        return self

    def check_against_contract(self, *, holdout_start: datetime, cutoff: datetime) -> None:
        """Cross-check the experiment periods against the data contract.

        Enforces holdout isolation: the experiment must not extend its
        development window into (or past) the data-contract holdout, and the
        boundaries must agree exactly. Raises ``ValueError`` on any mismatch.
        """

        def _utc(dt: datetime) -> datetime:
            return dt.astimezone(UTC) if dt.tzinfo else dt.replace(tzinfo=UTC)

        hs = _utc(holdout_start)
        co = _utc(cutoff)
        if self.periods.holdout_start != hs:
            raise ValueError(
                f"experiment holdout_start {self.periods.holdout_start} != data-contract "
                f"holdout start {hs}."
            )
        if self.periods.cutoff_exclusive != co:
            raise ValueError(
                f"experiment cutoff {self.periods.cutoff_exclusive} != data-contract cutoff {co}."
            )
        if self.periods.development_end_exclusive > hs:
            raise ValueError("Experiment development window must not enter the frozen holdout.")
