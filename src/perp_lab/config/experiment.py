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


class Families(_Strict):
    momentum: MomentumFamily = MomentumFamily()
    breakout: BreakoutFamily = BreakoutFamily()
    mean_reversion: MeanReversionFamily = MeanReversionFamily()


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
    """Unique objective evaluations a generational GA with elitism actually performs.

    Generation 0 evaluates a full population. Every later generation carries the
    ``elitism`` best individuals over with cached fitness, so it only evaluates
    ``population_size - elitism`` new offspring. ``population_size * generations``
    therefore *overstates* the GA's evaluation count whenever ``elitism > 0``, and
    using it as the shared budget silently gives Random Search more evaluations.
    """
    return population_size + (generations - 1) * (population_size - elitism)


class RandomSearch(_Strict):
    sampler: str = "uniform_over_space"


class GeneticAlgorithm(_Strict):
    population_size: int = Field(default=100, ge=2)
    # 100 + (21 - 1) * (100 - 5) = 2000 unique evaluations == evaluation_budget.
    generations: int = Field(default=21, ge=1)
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
        ga = self.genetic_algorithm
        if ga.elitism >= ga.population_size:
            raise ValueError("genetic_algorithm.elitism must be smaller than population_size.")
        ga_evals = ga_unique_evaluations(ga.population_size, ga.generations, ga.elitism)
        if ga_evals != self.evaluation_budget:
            raise ValueError(
                "Search-budget parity violated: the genetic algorithm performs "
                f"population_size + (generations - 1) * (population_size - elitism) = "
                f"{ga_evals} unique evaluations, which must equal evaluation_budget = "
                f"{self.evaluation_budget} so Random Search and the GA are compared "
                "at an identical number of candidate evaluations."
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
