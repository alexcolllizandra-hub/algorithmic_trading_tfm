"""The walk-forward meta-label study: fold geometry, purging, and no test leakage.

The tests that matter here are the negative ones. A meta-label layer that is
allowed to see its own test block will look excellent and mean nothing, so the
selection stage is checked for indifference to the test block, and the arms are
checked against the backtester rather than against a reimplementation of it.
"""

from __future__ import annotations

from itertools import pairwise

import numpy as np
import polars as pl
import pytest

from perp_lab.backtesting.engine import run_backtest
from perp_lab.labeling.triple_barrier import LabelSpans
from perp_lab.meta_labeling.study import (
    MetaLabelStudyConfig,
    build_dataset,
    event_block_masks,
    event_signal_series,
    run_meta_label_study,
    study_from_market,
    walk_forward_folds,
)
from perp_lab.meta_labeling.synthetic import (
    GROUND_TRUTH_COL,
    REGIME_COL,
    VOLATILITY_COL,
    SyntheticSpec,
    generate_noise_market,
    generate_signal_market,
)

SPEC = SyntheticSpec(n_bars=6_000, seed=5)
FAST = MetaLabelStudyConfig(
    models=("logistic_regression",),
    n_folds=2,
    test_bars=1_000,
    validation_bars=1_000,
    min_train_bars=2_000,
)


def _dataset(market, config: MetaLabelStudyConfig = FAST):
    return build_dataset(
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


# --------------------------------------------------------------------------- #
# Fold geometry
# --------------------------------------------------------------------------- #


def test_folds_are_chronological_and_their_test_blocks_never_overlap() -> None:
    folds = walk_forward_folds(
        10_000, n_folds=4, test_bars=1_000, validation_bars=1_000, min_train_bars=2_000
    )
    assert len(folds) == 4
    for fold in folds:
        assert fold.train_end == fold.validation_start
        assert fold.validation_end == fold.test_start
        assert fold.validation_start < fold.test_start < fold.test_end
    starts = [f.test_start for f in folds]
    assert starts == sorted(starts)
    for earlier, later in pairwise(folds):
        assert earlier.test_end <= later.test_start


def test_the_training_window_expands_fold_after_fold() -> None:
    folds = walk_forward_folds(
        10_000, n_folds=4, test_bars=1_000, validation_bars=1_000, min_train_bars=2_000
    )
    ends = [f.train_end for f in folds]
    assert ends == sorted(ends) and ends[0] < ends[-1]


def test_a_geometry_that_does_not_fit_the_data_is_refused() -> None:
    with pytest.raises(ValueError, match="cannot hold"):
        walk_forward_folds(
            3_000, n_folds=4, test_bars=1_000, validation_bars=1_000, min_train_bars=2_000
        )


# --------------------------------------------------------------------------- #
# Purging and embargo
# --------------------------------------------------------------------------- #


def test_no_training_label_reads_a_bar_that_validation_or_test_will_price() -> None:
    dataset = _dataset(generate_signal_market(SPEC))
    folds = walk_forward_folds(
        dataset.n_bars,
        n_folds=FAST.n_folds,
        test_bars=FAST.test_bars,
        validation_bars=FAST.validation_bars,
        min_train_bars=FAST.min_train_bars,
    )
    for fold in folds:
        masks = event_block_masks(dataset, fold, FAST.embargo_bars)
        train = masks["train"]
        assert train.any()
        # A training span may not reach into the evaluation stretch at all.
        assert np.all(dataset.spans.end[train] <= fold.validation_start)


def test_validation_labels_stop_short_of_the_test_block_by_the_embargo() -> None:
    dataset = _dataset(generate_signal_market(SPEC))
    folds = walk_forward_folds(
        dataset.n_bars,
        n_folds=FAST.n_folds,
        test_bars=FAST.test_bars,
        validation_bars=FAST.validation_bars,
        min_train_bars=FAST.min_train_bars,
    )
    for fold in folds:
        masks = event_block_masks(dataset, fold, FAST.embargo_bars)
        validation = masks["validation"]
        assert validation.any()
        assert np.all(dataset.spans.end[validation] + FAST.embargo_bars <= fold.test_start)
        assert np.all(dataset.spans.start[validation] >= fold.validation_start)


def test_the_three_blocks_share_no_event() -> None:
    dataset = _dataset(generate_signal_market(SPEC))
    fold = walk_forward_folds(
        dataset.n_bars,
        n_folds=FAST.n_folds,
        test_bars=FAST.test_bars,
        validation_bars=FAST.validation_bars,
        min_train_bars=FAST.min_train_bars,
    )[-1]
    masks = event_block_masks(dataset, fold, FAST.embargo_bars)
    assert not np.any(masks["train"] & masks["validation"])
    assert not np.any(masks["train"] & masks["test"])
    assert not np.any(masks["validation"] & masks["test"])


# --------------------------------------------------------------------------- #
# The position series the arms are backtested on
# --------------------------------------------------------------------------- #


def test_one_event_is_held_from_its_entry_open_to_its_exit_open() -> None:
    spans = LabelSpans(start=np.array([5]), end=np.array([11]))
    signal = event_signal_series(20, spans, np.array([1.0]), np.array([1.0]))
    # The engine shifts by one bar, so the signal runs from the bar before entry.
    assert np.flatnonzero(signal).tolist() == [4, 5, 6, 7, 8]


def test_a_refused_trade_lowers_exposure_instead_of_levering_the_other_one() -> None:
    spans = LabelSpans(start=np.array([5, 6]), end=np.array([11, 12]))
    both = event_signal_series(20, spans, np.array([1.0, 1.0]), np.array([1.0, 1.0]))
    one_refused = event_signal_series(20, spans, np.array([1.0, 1.0]), np.array([1.0, 0.0]))
    assert both[6] == pytest.approx(1.0)
    assert one_refused[6] == pytest.approx(0.5), "declining a trade must not resize the other"


def test_the_filter_cannot_reverse_the_primary() -> None:
    spans = LabelSpans(start=np.array([5]), end=np.array([11]))
    with pytest.raises(ValueError, match="non-negative"):
        event_signal_series(20, spans, np.array([1.0]), np.array([-1.0]))


def test_the_arm_earns_exactly_what_the_label_says_it_would() -> None:
    market = generate_signal_market(SPEC)
    dataset = _dataset(market)
    # An isolated event: no other event overlaps it, so no capital is shared.
    starts, ends = dataset.spans.start, dataset.spans.end
    isolated = next(
        i
        for i in range(1, len(starts) - 1)
        if starts[i] > ends[i - 1] + 2 and ends[i] + 2 < starts[i + 1]
    )
    spans = LabelSpans(start=starts[isolated : isolated + 1], end=ends[isolated : isolated + 1])
    signal = event_signal_series(
        dataset.n_bars, spans, dataset.sides[isolated : isolated + 1], np.array([1.0])
    )
    result = run_backtest(
        market.bars.select("open_time").with_columns(pl.Series("side", signal)),
        market.bars,
        timeframe="1h",
        fee_bps_per_side=FAST.costs.fee_bps_per_side,
        slippage_bps_per_side=FAST.costs.slippage_bps_per_side,
        funding=market.funding,
    )
    assert float(result.ledger["net_return"].sum()) == pytest.approx(
        dataset.returns[isolated], abs=2e-4
    )


# --------------------------------------------------------------------------- #
# No test data reaches a decision
# --------------------------------------------------------------------------- #


def test_rewriting_the_test_block_changes_no_model_no_threshold_no_choice() -> None:
    market = generate_signal_market(SPEC)
    baseline = run_meta_label_study(_dataset(market), FAST, market="signal", planted_edge=True)

    # Replace the last quarter of the history with a different market. Anything
    # the selection stage learnt from the test block would move now.
    corrupted_bars = market.bars.with_columns(
        pl.when(pl.arange(0, market.bars.height) >= 4_500)
        .then(pl.col("close") * 1.5)
        .otherwise(pl.col("close"))
        .alias("close"),
        pl.when(pl.arange(0, market.bars.height) >= 4_500)
        .then(pl.col("open") * 1.5)
        .otherwise(pl.col("open"))
        .alias("open"),
        pl.when(pl.arange(0, market.bars.height) >= 4_500)
        .then(pl.col("high") * 1.5)
        .otherwise(pl.col("high"))
        .alias("high"),
        pl.when(pl.arange(0, market.bars.height) >= 4_500)
        .then(pl.col("low") * 1.5)
        .otherwise(pl.col("low"))
        .alias("low"),
    )
    corrupted = run_meta_label_study(
        _dataset(
            type(market)(
                name=market.name,
                planted_edge=market.planted_edge,
                spec=market.spec,
                bars=corrupted_bars,
                events=market.events,
                features=market.features,
                funding=market.funding,
            )
        ),
        FAST,
        market="signal",
        planted_edge=True,
    )

    for original, altered in zip(baseline.folds, corrupted.folds, strict=True):
        assert original.selected_model == altered.selected_model
        assert original.abstained == altered.abstained
        for left, right in zip(original.candidates, altered.candidates, strict=True):
            if left.fitted is None or right.fitted is None:
                continue
            assert left.fitted.threshold.threshold == pytest.approx(
                right.fitted.threshold.threshold
            )


def test_the_study_is_reproducible_from_its_seed() -> None:
    dataset = _dataset(generate_signal_market(SPEC))
    first = run_meta_label_study(dataset, FAST, market="signal", planted_edge=True)
    second = run_meta_label_study(dataset, FAST, market="signal", planted_edge=True)
    assert first.summary() == second.summary()


# --------------------------------------------------------------------------- #
# Declining to act
# --------------------------------------------------------------------------- #


def test_an_abstaining_fold_holds_no_position_and_pays_no_cost() -> None:
    # A configuration that can never satisfy the acceptance rule: no scale at all.
    config = MetaLabelStudyConfig(**{**FAST.__dict__, "min_scale": 0.0, "max_scale": 0.0})
    study = study_from_market(generate_noise_market(SPEC), config)
    assert all(fold.abstained for fold in study.folds)
    for fold in study.folds:
        assert fold.test_meta.net_return == pytest.approx(0.0)
        assert fold.test_meta.n_trades == 0
        assert fold.test_meta.total_cost == pytest.approx(0.0)
        assert fold.test_signal_rate == 0.0
        assert fold.abstention_reason is not None


def test_the_primary_arm_is_identical_whether_the_layer_acts_or_abstains() -> None:
    acting = study_from_market(generate_noise_market(SPEC), FAST)
    abstaining = study_from_market(
        generate_noise_market(SPEC),
        MetaLabelStudyConfig(**{**FAST.__dict__, "min_scale": 0.0, "max_scale": 0.0}),
    )
    for left, right in zip(acting.folds, abstaining.folds, strict=True):
        assert left.test_primary.net_return == pytest.approx(right.test_primary.net_return)


def test_every_fold_reports_its_drift_and_regime_diagnostics() -> None:
    market = generate_signal_market(SPEC)
    study = study_from_market(market, FAST)
    for fold in study.folds:
        assert set(fold.feature_drift["feature"].to_list()) == set(market.feature_names)
        assert "psi" in fold.feature_drift.columns
        if not fold.abstained:
            assert fold.per_regime.height >= 1
            assert fold.prediction_drift_psi is not None
            assert fold.permutation_importance.height == len(market.feature_names)
            assert fold.calibration["n"].sum() == fold.n_test


def test_the_arms_pay_the_costs_and_the_funding_the_engine_charges() -> None:
    fold = study_from_market(generate_signal_market(SPEC), FAST).folds[0]
    assert fold.test_primary.n_trades > 0
    assert fold.test_primary.total_cost > 0.0
    assert fold.test_primary.total_funding != 0.0, "funding must reach the arms"
