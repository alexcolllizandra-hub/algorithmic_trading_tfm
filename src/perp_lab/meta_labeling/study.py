"""Walk-forward meta-labeling study: fit, select, decide, and only then evaluate.

The whole point of this module is the order in which things are allowed to
happen. Each fold splits the bars into three chronological blocks:

``train`` -> fits the classifiers;
``validation`` -> calibrates them, picks each one's decision threshold, and picks
the winning model **and whether to act at all**;
``test`` -> is read exactly once, to score the decision that was already made.

No test observation reaches a hyper-parameter, a threshold, a calibrator, a
feature or the model choice. That is enforced structurally: :func:`_select`
receives no test data, and the test block is only touched afterwards, in
:func:`_score_fold`.

Declining to act
----------------
A meta-label layer that always trades cannot fail. This one may abstain: if the
best candidate does not raise net return against the unfiltered primary **on
validation**, the fold is marked :attr:`FoldResult.abstained` and the filtered
arm holds no position through the test block. On a market with no edge that is
the correct behaviour and the only defence against a pipeline that manufactures
one. The decision uses validation data alone, so abstention is a prediction, not
a post-hoc excuse.

Concurrency and sizing
----------------------
When several primary signals overlap, capital is split equally between them. The
denominator is the *primary's* concurrency in both arms, so refusing a trade
reduces exposure instead of levering up the remaining one: the filter can veto or
shrink a position, never enlarge the book beyond what the primary asked for.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import polars as pl

from perp_lab.backtesting.engine import BacktestResult, run_backtest
from perp_lab.labeling.triple_barrier import (
    EVENT_TIME_COL,
    SIDE_COL,
    LabelCosts,
    LabelSpans,
    TripleBarrierSpec,
    label_spans,
    purged_embargoed_mask,
    return_attributed_weights,
    triple_barrier_labels,
)
from perp_lab.meta_labeling.diagnostics import (
    feature_drift,
    meta_position_scale,
    permutation_importance_scores,
    population_stability_index,
)
from perp_lab.meta_labeling.metrics import (
    EconomicMetrics,
    PredictiveMetrics,
    calibration_table,
    economic_metrics,
    predictive_metrics,
)
from perp_lab.meta_labeling.model import (
    CalibrationMethod,
    FittedMetaModel,
    MissingBackendError,
    ThresholdCriterion,
    fit_meta_model,
    shap_feature_importance,
)

PRIMARY_ARM = "primary_only"
META_ARM = "primary_plus_meta_labeling"

_MIN_EVENTS_PER_BLOCK = 30


@dataclass(frozen=True)
class MetaLabelStudyConfig:
    """Everything that is fixed before the study runs.

    ``models`` is the pre-registered candidate list from ``experiment.yaml``.
    A backend that is not installed is recorded as unavailable rather than
    silently replaced, so a study run without LightGBM cannot be mistaken for
    one where LightGBM lost.
    """

    # next_open fills: the label and the backtested arm must describe the same
    # trade, and the engine cannot fill inside a bar.
    barriers: TripleBarrierSpec = field(
        default_factory=lambda: TripleBarrierSpec(
            upper_barrier_atr=2.0,
            lower_barrier_atr=2.0,
            vertical_barrier_bars=24,
            exit_fill="next_open",
        )
    )
    costs: LabelCosts = field(
        default_factory=lambda: LabelCosts(
            fee_bps_per_side=4.0,
            slippage_bps_per_side=1.0,
            funding_rate_col="funding_rate_in_bar",
        )
    )
    models: tuple[str, ...] = ("logistic_regression", "random_forest", "lightgbm")
    calibration: CalibrationMethod = "isotonic"
    calibration_fraction: float = 0.5
    threshold_criterion: ThresholdCriterion = "expected_return"
    min_signal_rate: float = 0.05
    min_scale: float = 0.5
    max_scale: float = 1.0
    n_folds: int = 6
    test_bars: int = 2000
    validation_bars: int = 2000
    min_train_bars: int = 4000
    embargo_bars: int = 48
    timeframe: str = "1h"
    seed: int = 42

    def to_dict(self) -> dict[str, object]:
        return {
            "barriers": self.barriers.to_dict(),
            "costs": self.costs.to_dict(),
            "models": list(self.models),
            "calibration": self.calibration,
            "calibration_fraction": self.calibration_fraction,
            "threshold_criterion": self.threshold_criterion,
            "min_signal_rate": self.min_signal_rate,
            "position_scale": {"min": self.min_scale, "max": self.max_scale},
            "n_folds": self.n_folds,
            "test_bars": self.test_bars,
            "validation_bars": self.validation_bars,
            "min_train_bars": self.min_train_bars,
            "embargo_bars": self.embargo_bars,
            "timeframe": self.timeframe,
            "seed": self.seed,
        }


@dataclass(frozen=True)
class FoldGeometry:
    """Bar index ranges of one fold, all half-open ``[start, end)``."""

    index: int
    train_end: int
    validation_start: int
    validation_end: int
    test_start: int
    test_end: int

    def to_dict(self) -> dict[str, int]:
        return {
            "fold": self.index,
            "train_end": self.train_end,
            "validation_start": self.validation_start,
            "validation_end": self.validation_end,
            "test_start": self.test_start,
            "test_end": self.test_end,
        }


def walk_forward_folds(
    n_bars: int, *, n_folds: int, test_bars: int, validation_bars: int, min_train_bars: int
) -> tuple[FoldGeometry, ...]:
    """Expanding-window folds: train grows, validation and test roll forward.

    The last fold ends at the last bar, and earlier folds are laid out backwards
    from there, so the most recent data is always evaluated. Chronological by
    construction; there is no shuffling anywhere in this module.
    """
    if n_folds < 1 or test_bars < 1 or validation_bars < 1:
        raise ValueError("n_folds, test_bars and validation_bars must all be positive.")
    needed = min_train_bars + validation_bars + n_folds * test_bars
    if n_bars < needed:
        raise ValueError(
            f"{n_bars} bars cannot hold {n_folds} folds: {needed} are required "
            f"({min_train_bars} train + {validation_bars} validation + "
            f"{n_folds} x {test_bars} test)."
        )

    folds: list[FoldGeometry] = []
    for k in range(n_folds):
        test_end = n_bars - (n_folds - 1 - k) * test_bars
        test_start = test_end - test_bars
        validation_end = test_start
        validation_start = validation_end - validation_bars
        folds.append(
            FoldGeometry(
                index=k,
                train_end=validation_start,
                validation_start=validation_start,
                validation_end=validation_end,
                test_start=test_start,
                test_end=test_end,
            )
        )
    return tuple(folds)


@dataclass(frozen=True)
class MetaLabelDataset:
    """Labelled events, their features and the bars they were priced on.

    Built once per market. ``spans`` are bar intervals, which is what purging,
    embargo and the position series all operate on; timestamps are kept only for
    reporting.
    """

    bars: pl.DataFrame
    labels: pl.DataFrame
    features: np.ndarray
    feature_names: tuple[str, ...]
    spans: LabelSpans
    sides: np.ndarray
    returns: np.ndarray
    meta_labels: np.ndarray
    regimes: np.ndarray
    funding: pl.DataFrame | None
    ground_truth: np.ndarray | None = None

    @property
    def n_events(self) -> int:
        return int(self.meta_labels.size)

    @property
    def n_bars(self) -> int:
        return int(self.bars.height)


def build_dataset(
    bars: pl.DataFrame,
    events: pl.DataFrame,
    features: pl.DataFrame,
    *,
    feature_names: tuple[str, ...],
    config: MetaLabelStudyConfig,
    volatility_col: str,
    regime_col: str | None = None,
    funding: pl.DataFrame | None = None,
    ground_truth_col: str | None = None,
    time_col: str = "open_time",
) -> MetaLabelDataset:
    """Label the primary's signals and align features to the surviving events.

    Events whose holding window runs past the end of the data are dropped by the
    labeler; the feature matrix is joined afterwards so the two can never fall
    out of alignment.
    """
    labels = triple_barrier_labels(
        bars,
        events.select(EVENT_TIME_COL, SIDE_COL),
        config.barriers,
        volatility_col=volatility_col,
        costs=config.costs,
        time_col=time_col,
    )
    if labels.height == 0:
        raise ValueError("No event could be labelled; check the barrier geometry and the history.")

    aligned = labels.join(features, on=EVENT_TIME_COL, how="inner").sort(EVENT_TIME_COL)
    if aligned.height != labels.height:
        raise ValueError("Every labelled event needs a feature row; the join lost events.")

    if regime_col is not None:
        regime_map = bars.select(time_col, regime_col)
        aligned = aligned.join(regime_map, left_on=EVENT_TIME_COL, right_on=time_col, how="left")
        regimes = aligned[regime_col].fill_null("unknown").to_numpy().astype(str)
    else:
        regimes = np.full(aligned.height, "all", dtype=object).astype(str)

    truth = None
    if ground_truth_col is not None:
        truth_frame = events.select(EVENT_TIME_COL, ground_truth_col)
        truth = (
            aligned.select(EVENT_TIME_COL)
            .join(truth_frame, on=EVENT_TIME_COL, how="left")[ground_truth_col]
            .to_numpy()
        )

    return MetaLabelDataset(
        bars=bars,
        labels=aligned,
        features=aligned.select(feature_names).to_numpy().astype(float),
        feature_names=feature_names,
        spans=label_spans(aligned),
        sides=aligned[SIDE_COL].to_numpy().astype(float),
        returns=aligned["ret"].to_numpy().astype(float),
        meta_labels=aligned["meta_label"].to_numpy().astype(int),
        regimes=regimes,
        funding=funding,
        ground_truth=truth,
    )


def event_signal_series(
    n_bars: int, spans: LabelSpans, sides: np.ndarray, scales: np.ndarray
) -> np.ndarray:
    """Target-position series the backtester consumes, from event spans.

    An event signalled at bar ``t`` is entered at the open of ``t + 1`` and
    exited at the open of its exit bar. The engine shifts the signal by one bar,
    so the signal must be held over ``[t, exit - 2]`` for the position to run
    from the entry open to the exit open. Concurrent events share the book
    equally, using the *primary's* concurrency in both arms.
    """
    sides = np.asarray(sides, dtype=float).ravel()
    scales = np.asarray(scales, dtype=float).ravel()
    if not (len(spans) == sides.size == scales.size):
        raise ValueError("spans, sides and scales must describe the same events.")
    if np.any(scales < 0.0):
        raise ValueError("position scales must be non-negative; the filter cannot reverse a trade.")

    numerator = np.zeros(n_bars, dtype=float)
    concurrent = np.zeros(n_bars, dtype=float)
    for start, end, side, scale in zip(spans.start, spans.end, sides, scales, strict=True):
        signal_start = int(start) - 1
        signal_end = int(end) - 2  # exclusive; end == exit_index + 1
        if signal_end <= signal_start:
            continue
        lo, hi = max(signal_start, 0), min(signal_end, n_bars)
        if hi <= lo:
            continue
        numerator[lo:hi] += side * scale
        concurrent[lo:hi] += 1.0
    return np.divide(numerator, concurrent, out=np.zeros_like(numerator), where=concurrent > 0)


def _run_arm(
    dataset: MetaLabelDataset,
    config: MetaLabelStudyConfig,
    *,
    block: tuple[int, int],
    mask: np.ndarray,
    scales: np.ndarray,
    time_col: str = "open_time",
) -> BacktestResult:
    """Backtest one arm over one bar block, with the project's cost model."""
    start, end = block
    bars = dataset.bars[start:end]
    spans = LabelSpans(start=dataset.spans.start[mask] - start, end=dataset.spans.end[mask] - start)
    signal = event_signal_series(bars.height, spans, dataset.sides[mask], scales)
    signals = bars.select(time_col).with_columns(pl.Series(SIDE_COL, signal))
    return run_backtest(
        signals,
        bars,
        timeframe=config.timeframe,
        fee_bps_per_side=config.costs.fee_bps_per_side,
        slippage_bps_per_side=config.costs.slippage_bps_per_side,
        funding=dataset.funding,
    )


def event_block_masks(
    dataset: MetaLabelDataset, fold: FoldGeometry, embargo_bars: int
) -> dict[str, np.ndarray]:
    """Which events belong to train, validation and test under purge + embargo.

    Training events are purged against the whole evaluation stretch
    ``[validation_start, test_end)`` and embargoed after it, so no training label
    was computed from a bar that validation or test will also price. Validation
    events must close before the test block starts, with the same embargo as a
    gap, so the threshold cannot be fitted on a label that peeked into test.
    """
    spans = dataset.spans
    inside_validation = (spans.start >= fold.validation_start) & (spans.end <= fold.validation_end)
    clear_of_test = spans.end + embargo_bars <= fold.test_start
    # test_end is exclusive and the engine drops the block's final bar, so an
    # event closing exactly at the boundary would lose its last return.
    inside_test = (spans.start >= fold.test_start) & (spans.end < fold.test_end)

    train = (spans.end <= fold.train_end) & purged_embargoed_mask(
        spans,
        evaluation_start=fold.validation_start,
        evaluation_end=fold.test_end,
        embargo_bars=embargo_bars,
    )
    return {
        "train": train,
        "validation": inside_validation & clear_of_test,
        "test": inside_test,
    }


@dataclass(frozen=True)
class CandidateResult:
    """One model's validation evidence. Never contains a test number."""

    model: str
    fitted: FittedMetaModel | None
    validation_primary: EconomicMetrics | None
    validation_meta: EconomicMetrics | None
    unavailable_reason: str | None = None

    @property
    def validation_delta(self) -> float:
        """Net-return improvement over the unfiltered primary, on validation."""
        if self.validation_primary is None or self.validation_meta is None:
            return float("-inf")
        return self.validation_meta.net_return - self.validation_primary.net_return

    def to_dict(self) -> dict[str, object]:
        return {
            "model": self.model,
            "available": self.fitted is not None,
            "unavailable_reason": self.unavailable_reason,
            "validation_delta": self.validation_delta if self.fitted is not None else None,
            "threshold": self.fitted.threshold.to_dict() if self.fitted else None,
            "validation_metrics": dict(self.fitted.validation_metrics) if self.fitted else None,
        }


@dataclass(frozen=True)
class FoldResult:
    """Everything one fold produced, with selection and scoring kept apart."""

    fold: FoldGeometry
    n_train: int
    n_validation: int
    n_test: int
    candidates: tuple[CandidateResult, ...]
    selected_model: str | None
    abstained: bool
    abstention_reason: str | None
    test_predictive: PredictiveMetrics | None
    test_primary: EconomicMetrics
    test_meta: EconomicMetrics
    test_signal_rate: float
    per_regime: pl.DataFrame
    feature_drift: pl.DataFrame
    prediction_drift_psi: float | None
    permutation_importance: pl.DataFrame
    calibration: pl.DataFrame

    @property
    def net_return_delta(self) -> float:
        return self.test_meta.net_return - self.test_primary.net_return

    def to_dict(self) -> dict[str, object]:
        return {
            **self.fold.to_dict(),
            "n_train": self.n_train,
            "n_validation": self.n_validation,
            "n_test": self.n_test,
            "candidates": [c.to_dict() for c in self.candidates],
            "selected_model": self.selected_model,
            "abstained": self.abstained,
            "abstention_reason": self.abstention_reason,
            "test_signal_rate": self.test_signal_rate,
            "test_predictive": self.test_predictive.to_dict() if self.test_predictive else None,
            "test_primary": self.test_primary.to_dict(),
            "test_meta": self.test_meta.to_dict(),
            "net_return_delta": self.net_return_delta,
            "prediction_drift_psi": self.prediction_drift_psi,
            "per_regime": self.per_regime.to_dicts(),
            "feature_drift": self.feature_drift.to_dicts(),
            "permutation_importance": self.permutation_importance.to_dicts(),
            "calibration": self.calibration.to_dicts(),
        }


@dataclass(frozen=True)
class MarketStudy:
    """The full walk-forward result for one synthetic market."""

    market: str
    planted_edge: bool
    config: MetaLabelStudyConfig
    folds: tuple[FoldResult, ...]
    shap_importance: pl.DataFrame | None = None
    notes: tuple[str, ...] = field(default_factory=tuple)

    @property
    def n_folds(self) -> int:
        return len(self.folds)

    @property
    def abstention_rate(self) -> float:
        return float(np.mean([f.abstained for f in self.folds])) if self.folds else float("nan")

    @property
    def deltas(self) -> np.ndarray:
        return np.array([f.net_return_delta for f in self.folds], dtype=float)

    @property
    def folds_improved(self) -> int:
        """Folds where the filter beat the primary — including by losing less."""
        return int(np.sum(self.deltas > 0.0))

    @property
    def folds_profitable(self) -> int:
        """Folds where the filtered arm actually made money out of sample.

        This is the statistic that separates a real edge from a smaller loss.
        On a market with no edge, filtering a cost-bleeding primary improves the
        return in most folds while never turning it positive, so
        :attr:`folds_improved` looks encouraging and this one does not.
        """
        return int(np.sum([f.test_meta.net_return > 0.0 for f in self.folds]))

    @property
    def folds_acted(self) -> int:
        return int(np.sum([not f.abstained for f in self.folds]))

    def arm_total(self, arm: str) -> float:
        """Compounded net return of an arm across the test blocks.

        The test blocks are disjoint and chronological, so compounding them is
        the return of holding the arm through the whole out-of-sample stretch.
        """
        picker = (lambda f: f.test_meta) if arm == META_ARM else (lambda f: f.test_primary)
        growth = np.prod([1.0 + picker(f).net_return for f in self.folds])
        return float(growth - 1.0)

    def _median(self, arm_attribute: str) -> float:
        if not self.folds:
            return float("nan")
        arms: list[EconomicMetrics] = [getattr(f, arm_attribute) for f in self.folds]
        return float(np.median([a.net_return for a in arms]))

    def _median_sharpe(self, arm_attribute: str) -> float:
        if not self.folds:
            return float("nan")
        arms: list[EconomicMetrics] = [getattr(f, arm_attribute) for f in self.folds]
        return float(np.median([a.sharpe for a in arms]))

    def summary(self) -> dict[str, object]:
        predictive = [f.test_predictive for f in self.folds if f.test_predictive is not None]
        return {
            "market": self.market,
            "planted_edge": self.planted_edge,
            "n_folds": self.n_folds,
            "folds_acted": self.folds_acted,
            "abstention_rate": self.abstention_rate,
            "folds_improved": self.folds_improved,
            "folds_profitable": self.folds_profitable,
            "median_net_return_delta": float(np.median(self.deltas))
            if self.folds
            else float("nan"),
            "delta_stability_sd": float(np.std(self.deltas, ddof=1))
            if len(self.folds) > 1
            else 0.0,
            "median_primary_net_return": self._median("test_primary"),
            "median_meta_net_return": self._median("test_meta"),
            "primary_only_total_return": self.arm_total(PRIMARY_ARM),
            "primary_plus_meta_total_return": self.arm_total(META_ARM),
            "primary_only_median_sharpe": self._median_sharpe("test_primary"),
            "primary_plus_meta_median_sharpe": self._median_sharpe("test_meta"),
            "median_pr_auc": float(np.median([p.pr_auc for p in predictive]))
            if predictive
            else None,
            "median_pr_auc_lift": (
                float(np.median([p.pr_auc_lift for p in predictive])) if predictive else None
            ),
            "median_roc_auc": (
                float(np.median([p.roc_auc for p in predictive])) if predictive else None
            ),
            "median_brier": float(np.median([p.brier_score for p in predictive]))
            if predictive
            else None,
            "selected_models": [f.selected_model for f in self.folds],
            "notes": list(self.notes),
        }

    def to_dict(self) -> dict[str, object]:
        return {
            "summary": self.summary(),
            "config": self.config.to_dict(),
            "folds": [f.to_dict() for f in self.folds],
            "shap_importance": (
                self.shap_importance.to_dicts() if self.shap_importance is not None else None
            ),
        }


def _bar_returns(bars: pl.DataFrame) -> np.ndarray:
    """Per-bar simple returns, used to attribute weight by the size of the move."""
    column = "close" if "close" in bars.columns else "open"
    prices = bars[column].to_numpy().astype(float)
    returns = np.zeros_like(prices)
    returns[1:] = prices[1:] / prices[:-1] - 1.0
    return returns


def _flat_result(
    dataset: MetaLabelDataset, config: MetaLabelStudyConfig, block: tuple[int, int]
) -> BacktestResult:
    """The backtest of standing aside: same bars, no position, no cost."""
    empty = np.zeros(0, dtype=np.int64)
    return _run_arm(
        dataset,
        config,
        block=block,
        mask=np.zeros(dataset.n_events, dtype=bool),
        scales=empty.astype(float),
    )


def _fit_candidate(
    name: str,
    dataset: MetaLabelDataset,
    config: MetaLabelStudyConfig,
    fold: FoldGeometry,
    masks: dict[str, np.ndarray],
    weights: np.ndarray,
) -> CandidateResult:
    """Fit one candidate and price it on validation. No test data is touched."""
    train, validation = masks["train"], masks["validation"]
    try:
        fitted = fit_meta_model(
            name,
            features_train=dataset.features[train],
            labels_train=dataset.meta_labels[train],
            features_validation=dataset.features[validation],
            labels_validation=dataset.meta_labels[validation],
            seed=config.seed,
            sample_weight_train=weights,
            calibration=config.calibration,
            calibration_fraction=config.calibration_fraction,
            threshold_criterion=config.threshold_criterion,
            returns_validation=dataset.returns[validation],
            min_signal_rate=config.min_signal_rate,
        )
    except MissingBackendError as exc:
        return CandidateResult(name, None, None, None, unavailable_reason=str(exc).split(".")[0])
    except ValueError as exc:
        return CandidateResult(name, None, None, None, unavailable_reason=f"not fittable: {exc}")

    block = (fold.validation_start, fold.validation_end)
    probability = fitted.predict_proba(dataset.features[validation])
    scales = meta_position_scale(
        probability,
        threshold=fitted.threshold.threshold,
        min_scale=config.min_scale,
        max_scale=config.max_scale,
    )
    primary = economic_metrics(
        _run_arm(
            dataset,
            config,
            block=block,
            mask=validation,
            scales=np.ones(int(validation.sum())),
        )
    )
    meta = economic_metrics(_run_arm(dataset, config, block=block, mask=validation, scales=scales))
    return CandidateResult(name, fitted, primary, meta)


def _select(candidates: tuple[CandidateResult, ...]) -> tuple[CandidateResult | None, str | None]:
    """Pick the winner on validation net return, or decline to act.

    Two conditions, both on validation, both necessary:

    1. the filtered arm must **beat the unfiltered primary** — otherwise the
       filter is not doing anything worth its complexity;
    2. the filtered arm must be **profitable after costs in absolute terms**.

    The second condition is what makes abstention possible at all. Filtering a
    primary that merely bleeds costs always "improves" the return, because
    trading less loses less; without condition 2 the layer would report an
    improvement on a market with no edge whatsoever and call it a success. An
    arm that loses less money is still not one you would run.

    Selection deliberately ignores AUC. A filter that classifies better while
    losing money is not a better filter.
    """
    usable = [c for c in candidates if c.fitted is not None]
    if not usable:
        return None, "no candidate could be fitted on this fold"
    best = max(usable, key=lambda c: c.validation_delta)
    if best.validation_delta <= 0.0:
        return best, (
            "no candidate improved net return on validation "
            f"(best delta {best.validation_delta:+.4f})"
        )
    filtered = best.validation_meta
    if filtered is None or filtered.net_return <= 0.0:
        net = float("nan") if filtered is None else filtered.net_return
        return best, (
            "the filtered arm improved on the primary but still lost money on "
            f"validation (net return {net:+.4f}); trading less than a losing rule "
            "is not an edge"
        )
    return best, None


def _per_regime(
    dataset: MetaLabelDataset,
    mask: np.ndarray,
    probability: np.ndarray,
    *,
    threshold: float,
) -> pl.DataFrame:
    """Test-block behaviour split by the causal volatility regime.

    Descriptive. A regime breakdown computed after the fact cannot be used to
    choose a regime filter without becoming another round of selection.
    """
    regimes = dataset.regimes[mask]
    labels = dataset.meta_labels[mask]
    returns = dataset.returns[mask]
    accepted = probability >= threshold
    rows = []
    for regime in sorted(set(regimes.tolist())):
        where = regimes == regime
        if not where.any():
            continue
        taken = accepted & where
        rows.append(
            {
                "regime": regime,
                "n_events": int(where.sum()),
                "base_rate": float(labels[where].mean()),
                "accepted": int(taken.sum()),
                "precision": float(labels[taken].mean()) if taken.any() else float("nan"),
                "mean_return_primary": float(returns[where].mean()),
                "mean_return_accepted": float(returns[taken].mean())
                if taken.any()
                else float("nan"),
            }
        )
    return pl.DataFrame(
        rows,
        schema={
            "regime": pl.String,
            "n_events": pl.Int64,
            "base_rate": pl.Float64,
            "accepted": pl.Int64,
            "precision": pl.Float64,
            "mean_return_primary": pl.Float64,
            "mean_return_accepted": pl.Float64,
        },
    )


def _score_fold(
    dataset: MetaLabelDataset,
    config: MetaLabelStudyConfig,
    fold: FoldGeometry,
    masks: dict[str, np.ndarray],
    candidates: tuple[CandidateResult, ...],
    winner: CandidateResult | None,
    abstention_reason: str | None,
) -> FoldResult:
    """Read the test block, once, to score decisions already taken."""
    train, validation, test = masks["train"], masks["validation"], masks["test"]
    block = (fold.test_start, fold.test_end)
    primary = economic_metrics(
        _run_arm(dataset, config, block=block, mask=test, scales=np.ones(int(test.sum())))
    )

    acting = winner if winner is not None and abstention_reason is None else None
    model = acting.fitted if acting is not None else None
    if acting is None or model is None:
        # Threshold above 1 so nothing is accepted: the layer stood aside.
        empty_regime = _per_regime(dataset, test, np.zeros(int(test.sum())), threshold=2.0)
        return FoldResult(
            fold=fold,
            n_train=int(train.sum()),
            n_validation=int(validation.sum()),
            n_test=int(test.sum()),
            candidates=candidates,
            selected_model=winner.model if winner is not None else None,
            abstained=True,
            abstention_reason=abstention_reason or "no candidate could be fitted",
            test_predictive=None,
            test_primary=primary,
            test_meta=economic_metrics(_flat_result(dataset, config, block)),
            test_signal_rate=0.0,
            per_regime=empty_regime,
            feature_drift=feature_drift(
                dataset.features[train], dataset.features[test], dataset.feature_names
            ),
            prediction_drift_psi=None,
            permutation_importance=pl.DataFrame(),
            calibration=pl.DataFrame(),
        )

    probability = model.predict_proba(dataset.features[test])
    scales = meta_position_scale(
        probability,
        threshold=model.threshold.threshold,
        min_scale=config.min_scale,
        max_scale=config.max_scale,
    )
    meta = economic_metrics(_run_arm(dataset, config, block=block, mask=test, scales=scales))
    train_probability = model.predict_proba(dataset.features[train])

    return FoldResult(
        fold=fold,
        n_train=int(train.sum()),
        n_validation=int(validation.sum()),
        n_test=int(test.sum()),
        candidates=candidates,
        selected_model=acting.model,
        abstained=False,
        abstention_reason=None,
        test_predictive=predictive_metrics(dataset.meta_labels[test], probability),
        test_primary=primary,
        test_meta=meta,
        test_signal_rate=float((scales > 0).mean()) if scales.size else 0.0,
        per_regime=_per_regime(dataset, test, probability, threshold=model.threshold.threshold),
        feature_drift=feature_drift(
            dataset.features[train], dataset.features[test], dataset.feature_names
        ),
        prediction_drift_psi=population_stability_index(train_probability, probability),
        permutation_importance=permutation_importance_scores(
            model.estimator,
            dataset.features[validation],
            dataset.meta_labels[validation],
            dataset.feature_names,
            seed=config.seed,
        ),
        calibration=calibration_table(dataset.meta_labels[test], probability),
    )


def run_meta_label_study(
    dataset: MetaLabelDataset,
    config: MetaLabelStudyConfig,
    *,
    market: str,
    planted_edge: bool,
    explain_winner: bool = False,
    shap_max_events: int = 200,
) -> MarketStudy:
    """Run the walk-forward study over one market.

    ``explain_winner`` computes SHAP values for the last fold's winning model,
    on at most ``shap_max_events`` of its test events (the most recent ones, so
    the sample stays contiguous in time). It is interpretation only and is
    computed after every decision has been taken, so it cannot influence the
    result.
    """
    folds = walk_forward_folds(
        dataset.n_bars,
        n_folds=config.n_folds,
        test_bars=config.test_bars,
        validation_bars=config.validation_bars,
        min_train_bars=config.min_train_bars,
    )
    results: list[FoldResult] = []
    notes: list[str] = []
    last_winner: CandidateResult | None = None
    last_test: np.ndarray | None = None
    bar_returns = _bar_returns(dataset.bars)

    for fold in folds:
        masks = event_block_masks(dataset, fold, config.embargo_bars)
        if min(int(masks["train"].sum()), int(masks["validation"].sum())) < _MIN_EVENTS_PER_BLOCK:
            notes.append(
                f"fold {fold.index}: skipped, fewer than {_MIN_EVENTS_PER_BLOCK} events in "
                "train or validation after purging."
            )
            continue

        train_spans = LabelSpans(
            start=dataset.spans.start[masks["train"]], end=dataset.spans.end[masks["train"]]
        )
        weights = return_attributed_weights(train_spans, bar_returns)

        candidates = tuple(
            _fit_candidate(name, dataset, config, fold, masks, weights) for name in config.models
        )
        winner, abstention_reason = _select(candidates)
        results.append(
            _score_fold(dataset, config, fold, masks, candidates, winner, abstention_reason)
        )
        if winner is not None and winner.fitted is not None and abstention_reason is None:
            last_winner, last_test = winner, masks["test"]

    shap_table: pl.DataFrame | None = None
    explainable = last_winner.fitted if last_winner is not None else None
    if explain_winner and explainable is not None and last_test is not None:
        try:
            sample = dataset.features[last_test][-shap_max_events:]
            shap_table = shap_feature_importance(explainable, sample, dataset.feature_names)
        except MissingBackendError as exc:  # pragma: no cover - environment dependent
            notes.append(f"SHAP unavailable: {exc}")

    return MarketStudy(
        market=market,
        planted_edge=planted_edge,
        config=config,
        folds=tuple(results),
        shap_importance=shap_table,
        notes=tuple(notes),
    )


def study_from_market(market: Any, config: MetaLabelStudyConfig, **kwargs: Any) -> MarketStudy:
    """Run the study on a :class:`~perp_lab.meta_labeling.synthetic.SyntheticMarket`.

    Imported lazily so :mod:`perp_lab.meta_labeling.study` stays usable with any
    dataset; nothing here is specific to synthetic data beyond the column names.
    """
    from perp_lab.meta_labeling.synthetic import (
        GROUND_TRUTH_COL,
        REGIME_COL,
        VOLATILITY_COL,
    )

    dataset = build_dataset(
        market.bars,
        market.events,
        market.features,
        feature_names=market.feature_names,
        config=config,
        volatility_col=VOLATILITY_COL,
        regime_col=REGIME_COL,
        funding=market.funding,
        ground_truth_col=GROUND_TRUTH_COL,
    )
    return run_meta_label_study(
        dataset, config, market=market.name, planted_edge=market.planted_edge, **kwargs
    )
