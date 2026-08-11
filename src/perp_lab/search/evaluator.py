"""Shared, leakage-safe candidate evaluator used by Random Search and the GA.

The evaluator is the single place where a candidate strategy is turned into
performance numbers, so both algorithms are compared under identical conditions
and no second, simplified backtester is introduced.

Temporal protocol (per walk-forward fold, all built in
:func:`build_folds_data`):

1. Features are built **once** on the full development frame (causal, stateless).
2. For every fold the frame is split into disjoint ``train`` / ``val`` / ``test``
   (purge + embargo already baked into the fold boundaries).
3. A regime model + scaler are fitted **only on train** and applied causally to
   validation and test.
4. Candidate *selection* uses **validation** metrics only
   (:meth:`CandidateEvaluator.evaluate`).
5. The chosen fold winner is scored **once** on that fold's ``test`` slice
   (:meth:`CandidateEvaluator.evaluate_on_test`) -- never used to guide search.

**Fold isolation (ADR 0012).** An evaluator sees exactly the folds inside the
bundle it was constructed with. The search runner builds one evaluator per outer
fold from :func:`single_fold_bundle`, so a candidate's fitness is physically
incapable of depending on a chronologically later fold: the later fold's frames
are not reachable from the object. Asking an evaluator for a fold it does not
hold raises :class:`FoldIsolationError` rather than silently resolving to a
neighbour.

The frozen holdout is excluded up front and never materialised here.
"""

from __future__ import annotations

import time
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

import numpy as np
import polars as pl

from perp_lab.backtesting.engine import BacktestResult, run_backtest
from perp_lab.backtesting.metrics import bars_per_year
from perp_lab.config.experiment import ExperimentConfig
from perp_lab.features.context import FeatureContext
from perp_lab.features.manifest import build_feature_manifest
from perp_lab.features.registry import build_feature_frame, feature_columns, resolve_feature_set
from perp_lab.features.spec import FeatureItemLike, FeatureSpec
from perp_lab.regimes.models import GMMRegime, KMeansRegime, ThresholdRegime
from perp_lab.search.candidate import Candidate, CandidateStatus
from perp_lab.search.objective import ObjectiveConfig, aggregate_objective
from perp_lab.search.registry import _FeatureItem, build_search_space
from perp_lab.search.space import SearchSpace
from perp_lab.strategies.base import Strategy
from perp_lab.utils.seeds import SeedScheduler
from perp_lab.validation.walk_forward import (
    WalkForwardFold,
    assert_folds_exclude_holdout,
    split_fold,
)


class FoldIsolationError(RuntimeError):
    """An evaluator was asked for a fold outside the bundle it was built with.

    Under the per-outer-fold search protocol this is the signature of leakage:
    something is trying to read a fold whose data that search environment is not
    entitled to see.
    """


_VOLATILITY_PREFIXES = ("rvol_", "roll_std_", "atr_")
_REGIME_PRIORITY: tuple[tuple[str, ...], ...] = (
    _VOLATILITY_PREFIXES,
    ("momentum_", "ma_distance_", "price_dist_sma_"),
    ("zscore_",),
    ("rel_volume_", "volume_zscore_"),
)


def _select_regime_inputs(feature_names: Sequence[str]) -> list[str]:
    chosen: list[str] = []
    for prefixes in _REGIME_PRIORITY:
        match = next((n for n in feature_names if n.startswith(prefixes)), None)
        if match is not None and match not in chosen:
            chosen.append(match)
    return chosen


def _make_regime_model(
    kind: str, inputs: tuple[str, ...], seed: int
) -> ThresholdRegime | KMeansRegime | GMMRegime:
    if kind == "threshold":
        return ThresholdRegime(inputs=inputs, seed=seed)
    if kind == "kmeans":
        return KMeansRegime(inputs=inputs, seed=seed)
    if kind == "gmm":
        return GMMRegime(inputs=inputs, seed=seed)
    raise ValueError(f"Unknown regime_model {kind!r}; use threshold|kmeans|gmm.")


@dataclass
class FoldData:
    """One fold's train/val/test frames with regime labels already attached."""

    index: int
    train: pl.DataFrame
    val: pl.DataFrame
    test: pl.DataFrame
    regime_params: dict[str, object]
    fold: WalkForwardFold


@dataclass
class FoldsBundle:
    """Everything a search run needs about the temporal partitions + features."""

    folds: list[FoldData]
    feature_specs: list[FeatureSpec]
    feature_manifest: dict[str, object]
    regime_inputs: list[str]
    funding: pl.DataFrame | None
    symbol: str
    timeframe: str


def single_fold_bundle(bundle: FoldsBundle, fold_index: int) -> FoldsBundle:
    """A bundle holding exactly one outer fold, for an isolated search environment.

    Restricting the data rather than trusting the caller to index correctly is
    what makes fold isolation verifiable: an evaluator built from this bundle has
    no reference to any other fold's train, validation or test frames, so no
    amount of downstream indexing can reach them.
    """
    match = [fd for fd in bundle.folds if fd.index == fold_index]
    if not match:
        raise FoldIsolationError(
            f"Fold {fold_index} is not in this bundle (holds {[f.index for f in bundle.folds]})."
        )
    return FoldsBundle(
        folds=match,
        feature_specs=bundle.feature_specs,
        feature_manifest=bundle.feature_manifest,
        regime_inputs=bundle.regime_inputs,
        funding=bundle.funding,
        symbol=bundle.symbol,
        timeframe=bundle.timeframe,
    )


def _regime_feature_items(exp: ExperimentConfig) -> list[_FeatureItem]:
    f = exp.features
    return [
        _FeatureItem("rvol", window=f.regime_vol_windows[0]),
        _FeatureItem("momentum", window=f.momentum_windows[0]),
        _FeatureItem("zscore", window=f.zscore_windows[0]),
        _FeatureItem("rel_volume", window=f.relative_volume_windows[0]),
    ]


def build_folds_data(
    dev_frame: pl.DataFrame,
    folds: list[WalkForwardFold],
    *,
    exp: ExperimentConfig,
    family: str,
    symbol: str,
    timeframe: str,
    regime_model: str,
    seed: int,
    funding: pl.DataFrame | None,
    holdout_start: datetime,
    seeds: SeedScheduler | None = None,
    reference_bars: pl.DataFrame | None = None,
    reference_symbol: str | None = None,
) -> FoldsBundle:
    """Build the causal feature frame once and pre-split leakage-safe folds.

    When ``seeds`` is given, each fold's regime model is fitted from its own
    stream keyed by symbol and fold index, so a stochastic regime model (k-means,
    GMM) cannot make one fold's initialisation depend on another's. Without it the
    single ``seed`` is reused for every fold, which is only adequate for the
    deterministic threshold model.
    """
    if not folds:
        raise ValueError("build_folds_data received no walk-forward folds.")
    assert_folds_exclude_holdout(folds, holdout_start)

    space = build_search_space(exp, family, symbol)
    requested: list[FeatureItemLike] = [*space.feature_items, *_regime_feature_items(exp)]
    specs = resolve_feature_set(requested)
    # A family that declares a feature must actually receive it. Building the
    # frame without the auxiliary inputs would leave the funding family, for
    # instance, signalling on a column that was never attached.
    context = FeatureContext(funding=funding, peer=reference_bars, peer_symbol=reference_symbol)
    feats, resolved = build_feature_frame(
        dev_frame, specs, holdout_start=holdout_start, context=context
    )
    names = feature_columns(resolved)
    manifest = build_feature_manifest(
        resolved, symbol=symbol, timeframe=timeframe, dataset_id=symbol
    )

    regime_inputs = _select_regime_inputs(names)
    if not regime_inputs or not regime_inputs[0].startswith(_VOLATILITY_PREFIXES):
        raise ValueError("No volatility proxy available to fit regime models for the search.")
    input_tuple = tuple(regime_inputs)

    fold_data: list[FoldData] = []
    for fold in folds:
        parts = split_fold(feats, fold)
        train = parts["train"]
        fold_seed = (
            seeds.stream("regime", symbol=symbol, timeframe=timeframe, fold=fold.index)
            if seeds is not None
            else seed
        )
        model = _make_regime_model(regime_model, input_tuple, fold_seed)
        model.fit(train)
        fold_data.append(
            FoldData(
                index=fold.index,
                train=model.attach(train),
                val=model.attach(parts["validation"]),
                test=model.attach(parts["test"]),
                regime_params=model.params(),
                fold=fold,
            )
        )
    return FoldsBundle(
        folds=fold_data,
        feature_specs=resolved,
        feature_manifest=manifest,
        regime_inputs=regime_inputs,
        funding=funding,
        symbol=symbol,
        timeframe=timeframe,
    )


def _fold_metrics(result: BacktestResult) -> dict[str, float]:
    m = dict(result.metrics)
    n_bars = float(m.get("n_bars", 0.0))
    turnover = float(m.get("turnover", 0.0))
    m["turnover_per_bar"] = (turnover / n_bars) if n_bars > 0 else 0.0
    m["funding_applied"] = 1.0 if result.funding_applied else 0.0
    return m


class CandidateEvaluator:
    """Evaluate candidates on validation (for search) and test (for winners).

    Instances are bound to one :class:`FoldsBundle` + cost/objective settings, so
    the internal cache is never shared across incompatible datasets, folds,
    feature manifests or configurations. The search runner binds one evaluator per
    outer fold, which is what makes a candidate's fitness independent of every
    other fold.
    """

    def __init__(
        self,
        bundle: FoldsBundle,
        space: SearchSpace,
        *,
        timeframe: str,
        fee_bps_per_side: float,
        slippage_bps_per_side: float,
        days_per_year: int,
        require_funding: bool,
        objective_cfg: ObjectiveConfig,
        reference_bars: pl.DataFrame | None = None,
    ) -> None:
        self.bundle = bundle
        self.space = space
        self.timeframe = timeframe
        self.fee_bps_per_side = fee_bps_per_side
        self.slippage_bps_per_side = slippage_bps_per_side
        self.days_per_year = days_per_year
        self.require_funding = require_funding
        self.objective_cfg = objective_cfg
        # Only the cross-asset family consumes this. It is passed explicitly rather
        # than merged into the feature frame so the dependency stays visible in the
        # specification instead of becoming an anonymous column.
        self.reference_bars = reference_bars
        self._cache: dict[
            str, tuple[list[dict[str, float]], dict[str, float], float, str | None, bool]
        ] = {}

    def _build_strategy(self, candidate: Candidate) -> Strategy:
        strat = self.space.build(candidate.params)
        return strat  # type: ignore[return-value]

    def _signals(self, strategy: Strategy, frame: pl.DataFrame) -> pl.DataFrame:
        """Generate signals, supplying the reference asset's bars when required.

        Two cross-asset conventions coexist and must not be confused.
        ``CrossAssetConfirmation`` joins the peer's *bars* itself and announces
        that with ``consumes_reference_bars``. ``CrossAssetSpreadReversion`` reads
        the peer through the causal ``xasset_*`` columns the feature engine has
        already built from the peer frame, so handing it raw bars would be an
        error. Routing on the explicit flag rather than on the mere presence of a
        ``reference_symbol`` attribute — which both declare, because both record
        their second leg — keeps the two apart.
        """
        if not getattr(strategy, "consumes_reference_bars", False):
            return strategy.signals(frame)
        if self.reference_bars is None:
            reference_symbol = getattr(strategy, "reference_symbol", None)
            raise ValueError(
                f"{type(strategy).__name__} consumes the bars of reference_symbol="
                f"{reference_symbol!r} but the evaluator was built without reference bars. "
                "Load the reference asset for this fold; this family cannot be evaluated "
                "without it."
            )
        # Slice the reference to the fold's own window. Handing over the whole
        # history would let a fold read reference bars from beyond its own end.
        window = self.reference_bars.filter(
            pl.col("open_time") <= frame["open_time"].max()  # type: ignore[operator]
        )
        return strategy.signals(frame, reference=window)  # type: ignore[call-arg]

    @property
    def fold_indices(self) -> list[int]:
        """Global indices of the folds this evaluator is entitled to touch."""
        return [fd.index for fd in self.bundle.folds]

    def _fold_by_index(self, fold_index: int) -> FoldData:
        for fd in self.bundle.folds:
            if fd.index == fold_index:
                return fd
        raise FoldIsolationError(
            f"This evaluator holds folds {self.fold_indices} and was asked for fold "
            f"{fold_index}. Under the per-outer-fold protocol a search environment may "
            "only read its own fold."
        )

    def _block_sharpes(self, result: BacktestResult) -> list[float] | None:
        """Annualised Sharpe of contiguous sub-blocks of one validation window.

        Computed from the ledger the backtest already produced, so the stability
        term costs no extra backtests. Returns ``None`` when the window is too
        short to split into blocks that still carry a meaningful variance.
        """
        blocks = self.objective_cfg.stability_blocks
        if result.ledger.height == 0 or "net_return" not in result.ledger.columns:
            return None
        r = result.ledger["net_return"].to_numpy()
        # Each block needs at least two observations for a standard deviation.
        if r.size < blocks * 2:
            return None
        bpy = bars_per_year(self.timeframe, self.days_per_year)
        out: list[float] = []
        for chunk in np.array_split(r, blocks):
            std = float(np.std(chunk, ddof=1)) if chunk.size > 1 else 0.0
            out.append(float(np.mean(chunk) / std * np.sqrt(bpy)) if std > 0 else 0.0)
        return out

    def _backtest(self, strategy: Strategy, frame: pl.DataFrame) -> BacktestResult:
        signals = self._signals(strategy, frame)
        return run_backtest(
            signals,
            frame,
            timeframe=self.timeframe,
            fee_bps_per_side=self.fee_bps_per_side,
            slippage_bps_per_side=self.slippage_bps_per_side,
            days_per_year=self.days_per_year,
            asset=self.bundle.symbol,
            funding=self.bundle.funding,
            require_funding=self.require_funding,
        )

    def evaluate(self, candidate: Candidate) -> bool:
        """Fill ``candidate`` with validation metrics + objective. Returns cached?"""
        key = candidate.candidate_id
        if key in self._cache:
            fold_metrics, components, fitness, reason, feasible = self._cache[key]
            candidate.fold_metrics = fold_metrics
            candidate.objective_components = components
            candidate.fitness = fitness
            candidate.failure_reason = reason
            candidate.status = CandidateStatus.EVALUATED if feasible else CandidateStatus.FAILED
            candidate.eval_seconds = 0.0
            return True

        t0 = time.perf_counter()
        try:
            strategy = self._build_strategy(candidate)
        except (ValueError, TypeError) as exc:
            candidate.status = CandidateStatus.FAILED
            candidate.failure_reason = f"strategy build failed: {exc}"
            candidate.fitness = float("-inf")
            candidate.eval_seconds = time.perf_counter() - t0
            self._cache[key] = ([], {}, float("-inf"), candidate.failure_reason, False)
            return False

        fold_metrics: list[dict[str, float]] = []
        funding_applied_all = True
        stability: list[float] | None = None
        for fold in self.bundle.folds:
            result = self._backtest(strategy, fold.val)
            fold_metrics.append(_fold_metrics(result))
            funding_applied_all = funding_applied_all and result.funding_applied
            # Cross-fold dispersion is unobservable inside an isolated fold, so a
            # single-fold evaluator measures fragility within its own window.
            if len(self.bundle.folds) == 1:
                stability = self._block_sharpes(result)

        obj = aggregate_objective(
            fold_metrics,
            n_active_params=len(candidate.active_params),
            cfg=self.objective_cfg,
            funding_applied=funding_applied_all,
            stability_sharpes=stability,
        )
        candidate.fold_metrics = fold_metrics
        candidate.objective_components = obj.components
        candidate.fitness = obj.fitness
        candidate.failure_reason = obj.reason
        candidate.status = CandidateStatus.EVALUATED if obj.feasible else CandidateStatus.FAILED
        candidate.eval_seconds = time.perf_counter() - t0
        self._cache[key] = (
            fold_metrics,
            obj.components,
            obj.fitness,
            obj.reason,
            obj.feasible,
        )
        return False

    def evaluate_on_test(self, candidate: Candidate, fold_index: int) -> BacktestResult:
        """Score an already-frozen fold winner **once** on that fold's test slice.

        ``fold_index`` is the *global* walk-forward index, resolved against the
        folds this evaluator holds rather than used as a list position, so a
        mismatch raises instead of silently scoring the wrong window.
        """
        strategy = self._build_strategy(candidate)
        return self._backtest(strategy, self._fold_by_index(fold_index).test)
