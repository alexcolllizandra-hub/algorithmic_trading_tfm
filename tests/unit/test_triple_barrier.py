"""Triple-barrier labeling: causality, barrier precedence, purging and weights."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import numpy as np
import polars as pl
import pytest

from perp_lab.backtesting.engine import run_backtest
from perp_lab.labeling import (
    FREE_LABELS,
    LabelCosts,
    LabelSpans,
    TripleBarrierSpec,
    average_uniqueness,
    concurrency,
    label_spans,
    purged_embargoed_mask,
    return_attributed_weights,
    triple_barrier_labels,
)

START = datetime(2024, 1, 1, tzinfo=UTC)


def _bars(closes: list[float], *, vol: float = 0.01) -> pl.DataFrame:
    n = len(closes)
    times = [START + timedelta(hours=i) for i in range(n)]
    prices = np.asarray(closes, dtype=float)
    return pl.DataFrame(
        {
            "open_time": times,
            "open": prices,
            "high": prices * 1.0005,
            "low": prices * 0.9995,
            "close": prices,
            "vol_frac": [vol] * n,
        }
    )


def _events(indices: list[int], side: int, bars: pl.DataFrame) -> pl.DataFrame:
    times = bars["open_time"].to_list()
    return pl.DataFrame({"event_time": [times[i] for i in indices], "side": [side] * len(indices)})


def _spec(**kwargs: float | int) -> TripleBarrierSpec:
    base: dict[str, float | int] = {
        "upper_barrier_atr": 2.0,
        "lower_barrier_atr": 2.0,
        "vertical_barrier_bars": 5,
    }
    base.update(kwargs)
    return TripleBarrierSpec(**base)  # type: ignore[arg-type]


def test_a_rising_market_touches_the_profit_barrier_of_a_long() -> None:
    bars = _bars([100.0 * (1.01**i) for i in range(12)])
    labels = triple_barrier_labels(bars, _events([0], 1, bars), _spec(), volatility_col="vol_frac")
    row = labels.row(0, named=True)
    assert row["barrier_touched"] == "upper"
    assert row["label"] == 1
    assert row["meta_label"] == 1
    assert row["ret"] > 0


def test_the_same_rise_is_a_loss_for_a_short() -> None:
    bars = _bars([100.0 * (1.01**i) for i in range(12)])
    labels = triple_barrier_labels(bars, _events([0], -1, bars), _spec(), volatility_col="vol_frac")
    row = labels.row(0, named=True)
    assert row["barrier_touched"] == "upper"
    assert row["label"] == -1
    assert row["meta_label"] == 0
    assert row["ret"] < 0


def test_a_flat_market_exits_on_the_vertical_barrier() -> None:
    bars = _bars([100.0] * 12)
    labels = triple_barrier_labels(bars, _events([0], 1, bars), _spec(), volatility_col="vol_frac")
    row = labels.row(0, named=True)
    assert row["barrier_touched"] == "vertical"
    assert row["holding_bars"] == 5
    assert row["label"] == 0


def test_entry_is_the_next_bar_open_matching_backtest_execution() -> None:
    bars = _bars([100.0] * 12)
    labels = triple_barrier_labels(bars, _events([3], 1, bars), _spec(), volatility_col="vol_frac")
    row = labels.row(0, named=True)
    assert row["entry_index"] == 4, "an event at bar t must be entered at bar t+1"
    assert row["entry_time"] == bars["open_time"][4]


def test_an_ambiguous_bar_resolves_against_the_position() -> None:
    # Both barriers sit inside the first holding bar's range. Intrabar order is
    # unknowable, so the label must not assume the favourable one.
    bars = _bars([100.0] * 12)
    bars = bars.with_columns(
        pl.when(pl.arange(0, bars.height) == 1)
        .then(pl.lit(130.0))
        .otherwise(pl.col("high"))
        .alias("high"),
        pl.when(pl.arange(0, bars.height) == 1)
        .then(pl.lit(70.0))
        .otherwise(pl.col("low"))
        .alias("low"),
    )
    long_row = triple_barrier_labels(
        bars, _events([0], 1, bars), _spec(), volatility_col="vol_frac"
    ).row(0, named=True)
    short_row = triple_barrier_labels(
        bars, _events([0], -1, bars), _spec(), volatility_col="vol_frac"
    ).row(0, named=True)
    assert long_row["barrier_touched"] == "lower"
    assert long_row["ret"] < 0
    assert short_row["barrier_touched"] == "upper"
    assert short_row["ret"] < 0


def test_labels_are_truncation_invariant() -> None:
    rng = np.random.default_rng(0)
    closes = list(100.0 * np.cumprod(1.0 + rng.normal(0.0, 0.004, size=80)))
    bars = _bars(closes)
    events = _events(list(range(0, 60, 3)), 1, bars)
    spec = _spec()

    full = triple_barrier_labels(bars, events, spec, volatility_col="vol_frac")
    truncated_bars = bars.head(40)
    truncated_events = events.filter(pl.col("event_time") <= truncated_bars["open_time"].max())
    truncated = triple_barrier_labels(
        truncated_bars, truncated_events, spec, volatility_col="vol_frac"
    )

    overlap = full.filter(pl.col("event_time").is_in(truncated["event_time"].implode()))
    assert truncated.height > 0
    assert overlap.select(truncated.columns).head(truncated.height).equals(truncated)


def test_events_whose_horizon_runs_past_the_data_are_dropped_not_guessed() -> None:
    bars = _bars([100.0] * 10)
    labels = triple_barrier_labels(
        bars, _events([0, 3, 8], 1, bars), _spec(), volatility_col="vol_frac"
    )
    # bar 8 would need bars up to index 14, which do not exist.
    assert labels["event_time"].to_list() == [bars["open_time"][0], bars["open_time"][3]]


def test_a_dead_zone_keeps_negligible_moves_unlabelled() -> None:
    bars = _bars([100.0 * (1.00005**i) for i in range(12)])
    labels = triple_barrier_labels(
        bars, _events([0], 1, bars), _spec(min_return_bps=50.0), volatility_col="vol_frac"
    )
    assert labels.row(0, named=True)["label"] == 0


# --------------------------------------------------------------------------- #
# Costs: the label answers "profitable AFTER costs", not "moved the right way"
# --------------------------------------------------------------------------- #


def test_costs_turn_a_marginal_gross_winner_into_a_labelled_loss() -> None:
    # +5 bps gross over the holding window against a 10 bps round trip.
    bars = _bars([100.0 * (1.0001**i) for i in range(12)])
    events = _events([0], 1, bars)
    free = triple_barrier_labels(bars, events, _spec(), volatility_col="vol_frac").row(
        0, named=True
    )
    charged = triple_barrier_labels(
        bars,
        events,
        _spec(),
        volatility_col="vol_frac",
        costs=LabelCosts(fee_bps_per_side=4.0, slippage_bps_per_side=1.0),
    ).row(0, named=True)

    assert free["label"] == 1, "the move is favourable before costs"
    assert charged["label"] == -1, "and unprofitable after them"
    assert charged["gross_ret"] == pytest.approx(free["ret"])
    assert charged["cost"] == pytest.approx(10.0 / 1e4)
    assert charged["ret"] == pytest.approx(charged["gross_ret"] - charged["cost"])


def test_funding_is_charged_over_the_bars_the_position_is_held() -> None:
    bars = _bars([100.0] * 12).with_columns(pl.lit(0.0001).alias("funding_rate_in_bar"))
    costs = LabelCosts(funding_rate_col="funding_rate_in_bar")
    spec = _spec(vertical_barrier_bars=5)

    long_row = triple_barrier_labels(
        bars, _events([0], 1, bars), spec, volatility_col="vol_frac", costs=costs
    ).row(0, named=True)
    short_row = triple_barrier_labels(
        bars, _events([0], -1, bars), spec, volatility_col="vol_frac", costs=costs
    ).row(0, named=True)

    # Five held bars at 1 bp each; the long pays it and the short receives it.
    assert long_row["funding"] == pytest.approx(5e-4)
    assert short_row["funding"] == pytest.approx(-5e-4)
    assert long_row["label"] == -1
    assert short_row["label"] == 1


def test_a_costed_label_matches_what_the_backtester_would_have_earned() -> None:
    # The label and the engine must agree, or the model is trained on a return
    # the strategy could never have realised.
    rng = np.random.default_rng(11)
    closes = list(100.0 * np.cumprod(1.0 + rng.normal(0.0002, 0.003, size=40)))
    bars = _bars(closes)
    costs = LabelCosts(fee_bps_per_side=4.0, slippage_bps_per_side=1.0)
    label = triple_barrier_labels(
        bars, _events([2], 1, bars), _spec(), volatility_col="vol_frac", costs=costs
    ).row(0, named=True)

    # The engine holds the position while the signal was on the previous bar, so
    # a signal on [event, exit - 2] is filled at the entry open and closed at the
    # exit open.
    signal = np.zeros(bars.height)
    signal[2 : label["exit_index"] - 1] = 1.0
    result = run_backtest(
        bars.select("open_time").with_columns(pl.Series("side", signal)),
        bars,
        timeframe="1h",
        fee_bps_per_side=4.0,
        slippage_bps_per_side=1.0,
    )
    engine_net = float(result.ledger["net_return"].sum())
    assert engine_net == pytest.approx(label["ret"], abs=5e-5)


def test_costless_labels_are_the_documented_default() -> None:
    bars = _bars([100.0] * 12)
    labels = triple_barrier_labels(bars, _events([0], 1, bars), _spec(), volatility_col="vol_frac")
    row = labels.row(0, named=True)
    assert row["cost"] == 0.0
    assert row["funding"] == 0.0
    assert row["ret"] == row["gross_ret"]
    assert FREE_LABELS.round_trip_cost == 0.0


def test_negative_costs_are_refused() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        LabelCosts(fee_bps_per_side=-1.0)


def test_labeling_rejects_malformed_inputs() -> None:
    bars = _bars([100.0] * 12)
    with pytest.raises(ValueError, match="side must be"):
        triple_barrier_labels(
            bars,
            pl.DataFrame({"event_time": [bars["open_time"][0]], "side": [0]}),
            _spec(),
            volatility_col="vol_frac",
        )
    with pytest.raises(ValueError, match="not a bar"):
        triple_barrier_labels(
            bars,
            pl.DataFrame({"event_time": [START - timedelta(days=5)], "side": [1]}),
            _spec(),
            volatility_col="vol_frac",
        )
    with pytest.raises(ValueError, match="missing required column"):
        triple_barrier_labels(
            bars.drop("high"), _events([0], 1, bars), _spec(), volatility_col="vol_frac"
        )


def test_barrier_spec_rejects_impossible_geometry() -> None:
    with pytest.raises(ValueError, match="strictly positive"):
        TripleBarrierSpec(upper_barrier_atr=0.0, lower_barrier_atr=1.0, vertical_barrier_bars=5)
    with pytest.raises(ValueError, match="vertical_barrier_bars"):
        TripleBarrierSpec(upper_barrier_atr=1.0, lower_barrier_atr=1.0, vertical_barrier_bars=0)


# --------------------------------------------------------------------------- #
# Spans, purging, embargo and weights
# --------------------------------------------------------------------------- #


def test_label_spans_cover_entry_through_exit_inclusive() -> None:
    bars = _bars([100.0] * 12)
    labels = triple_barrier_labels(bars, _events([0], 1, bars), _spec(), volatility_col="vol_frac")
    spans = label_spans(labels)
    assert spans.start.tolist() == [1]
    assert spans.end.tolist() == [7], "exit bar 6 is observed, so the span ends at 7"


def test_purging_removes_training_labels_that_overlap_the_evaluation_block() -> None:
    spans = LabelSpans(start=np.array([0, 10, 18, 30]), end=np.array([5, 21, 25, 35]))
    keep = purged_embargoed_mask(spans, evaluation_start=20, evaluation_end=28, embargo_bars=0)
    assert keep.tolist() == [True, False, False, True]


def test_the_embargo_also_removes_labels_starting_just_after_the_block() -> None:
    spans = LabelSpans(start=np.array([0, 30, 40]), end=np.array([5, 35, 45]))
    keep = purged_embargoed_mask(spans, evaluation_start=20, evaluation_end=28, embargo_bars=5)
    assert keep.tolist() == [True, False, True]


def test_purging_validates_its_window() -> None:
    spans = LabelSpans(start=np.array([0]), end=np.array([5]))
    with pytest.raises(ValueError, match="strictly after"):
        purged_embargoed_mask(spans, evaluation_start=10, evaluation_end=10, embargo_bars=0)
    with pytest.raises(ValueError, match="non-negative"):
        purged_embargoed_mask(spans, evaluation_start=10, evaluation_end=12, embargo_bars=-1)


def test_concurrency_counts_overlapping_labels_per_bar() -> None:
    spans = LabelSpans(start=np.array([0, 2]), end=np.array([4, 6]))
    assert concurrency(spans, 8).tolist() == [1, 1, 2, 2, 1, 1, 0, 0]


def test_an_isolated_label_is_fully_unique_and_a_crowded_one_is_not() -> None:
    isolated = LabelSpans(start=np.array([0]), end=np.array([4]))
    assert float(average_uniqueness(isolated, 8)[0]) == pytest.approx(1.0)

    stacked = LabelSpans(start=np.array([0, 0, 0, 0]), end=np.array([4, 4, 4, 4]))
    assert average_uniqueness(stacked, 8).tolist() == pytest.approx([0.25] * 4)


def test_return_attribution_splits_a_move_between_concurrent_labels() -> None:
    returns = np.full(8, 0.01)
    solo = return_attributed_weights(
        LabelSpans(start=np.array([0]), end=np.array([4])), returns, normalise=False
    )
    shared = return_attributed_weights(
        LabelSpans(start=np.array([0, 0]), end=np.array([4, 4])), returns, normalise=False
    )
    assert solo[0] == pytest.approx(0.04)
    assert shared.tolist() == pytest.approx([0.02, 0.02])


def test_normalised_weights_average_to_one() -> None:
    rng = np.random.default_rng(3)
    starts = np.arange(0, 40, 2)
    spans = LabelSpans(start=starts, end=starts + 6)
    weights = return_attributed_weights(spans, rng.normal(0.0, 0.01, size=50))
    assert float(weights.mean()) == pytest.approx(1.0)


def test_spans_must_be_well_formed() -> None:
    with pytest.raises(ValueError, match="at least one bar"):
        LabelSpans(start=np.array([5]), end=np.array([5]))
    with pytest.raises(ValueError, match="same shape"):
        LabelSpans(start=np.array([1, 2]), end=np.array([3]))
