"""Synthetic markets: determinism, causality and a ground truth worth trusting.

If the generator is wrong, every conclusion drawn from it is wrong in a way no
downstream test can catch, so the planted edge and its absence are checked here
directly against the hidden state.
"""

from __future__ import annotations

import numpy as np
import pytest

from perp_lab.labeling import LabelCosts, TripleBarrierSpec, triple_barrier_labels
from perp_lab.meta_labeling.synthetic import (
    FEATURE_NAMES,
    GROUND_TRUTH_COL,
    REGIME_COL,
    VOLATILITY_COL,
    SyntheticSpec,
    _causal_columns,  # causality is the contract
    generate_noise_market,
    generate_signal_market,
)

SPEC = SyntheticSpec(n_bars=4_000, seed=11)
COSTS = LabelCosts(fee_bps_per_side=4.0, slippage_bps_per_side=1.0)
BARRIERS = TripleBarrierSpec(
    upper_barrier_atr=2.0, lower_barrier_atr=2.0, vertical_barrier_bars=24, exit_fill="next_open"
)


def _labels_with_truth(market) -> tuple[np.ndarray, np.ndarray]:
    labels = triple_barrier_labels(
        market.bars,
        market.events.select("event_time", "side"),
        BARRIERS,
        volatility_col=VOLATILITY_COL,
        costs=COSTS,
    )
    truth = labels.join(
        market.events.select("event_time", GROUND_TRUTH_COL), on="event_time", how="left"
    )
    return labels["meta_label"].to_numpy(), truth[GROUND_TRUTH_COL].to_numpy()


def test_generation_is_reproducible_from_the_seed() -> None:
    first, second = generate_signal_market(SPEC), generate_signal_market(SPEC)
    assert first.bars.equals(second.bars)
    assert first.events.equals(second.events)
    assert first.features.equals(second.features)


def test_a_different_seed_produces_a_different_market() -> None:
    other = generate_signal_market(SyntheticSpec(n_bars=SPEC.n_bars, seed=12))
    assert not generate_signal_market(SPEC).bars.equals(other.bars)


def test_the_planted_edge_is_real_and_sits_where_the_hidden_state_says() -> None:
    labels, favourable = _labels_with_truth(generate_signal_market(SPEC))
    assert labels[favourable].mean() > labels[~favourable].mean() + 0.2, (
        "signals fired in the favourable state must be profitable far more often"
    )


def test_the_control_market_has_no_edge_to_find() -> None:
    labels, favourable = _labels_with_truth(generate_noise_market(SPEC))
    gap = abs(labels[favourable].mean() - labels[~favourable].mean())
    assert gap < 0.1, "the hidden state must not predict anything on the control"


def test_the_control_market_pays_nothing_but_costs() -> None:
    market = generate_noise_market(SPEC)
    labels = triple_barrier_labels(
        market.bars,
        market.events.select("event_time", "side"),
        BARRIERS,
        volatility_col=VOLATILITY_COL,
        costs=COSTS,
    )
    assert float(labels["ret"].to_numpy().mean()) < 0.0
    assert float(labels["cost"].to_numpy().mean()) == pytest.approx(COSTS.round_trip_cost)


def test_the_hidden_state_is_never_handed_to_the_model() -> None:
    market = generate_signal_market(SPEC)
    assert GROUND_TRUTH_COL not in market.features.columns
    assert tuple(c for c in market.features.columns if c != "event_time") == FEATURE_NAMES


def test_features_and_events_stay_aligned_one_to_one() -> None:
    market = generate_signal_market(SPEC)
    assert market.features.height == market.events.height
    assert market.features["event_time"].to_list() == market.events["event_time"].to_list()


def test_every_event_sits_on_a_bar_with_a_usable_barrier_width() -> None:
    market = generate_signal_market(SPEC)
    joined = market.events.join(
        market.bars.select("open_time", VOLATILITY_COL),
        left_on="event_time",
        right_on="open_time",
        how="left",
    )
    widths = joined[VOLATILITY_COL].to_numpy()
    assert np.all(np.isfinite(widths)) and np.all(widths > 0)


def test_the_regime_label_and_barrier_width_are_truncation_invariant() -> None:
    # Recomputing the causal columns on half the history must reproduce the
    # first half exactly: an expanding statistic that used future bars would not.
    bars = generate_signal_market(SPEC).bars
    raw = bars.select("open_time", "open", "high", "low", "close", "volume", "funding_rate_in_bar")
    half = SPEC.n_bars // 2
    truncated = _causal_columns(raw.head(half))
    assert truncated[REGIME_COL].to_list() == bars.head(half)[REGIME_COL].to_list()
    assert truncated[VOLATILITY_COL].to_list() == bars.head(half)[VOLATILITY_COL].to_list()


def test_bars_carry_wicks_beyond_the_body() -> None:
    bars = generate_signal_market(SPEC).bars
    body_high = np.maximum(bars["open"].to_numpy(), bars["close"].to_numpy())
    body_low = np.minimum(bars["open"].to_numpy(), bars["close"].to_numpy())
    assert np.all(bars["high"].to_numpy() >= body_high)
    assert np.all(bars["low"].to_numpy() <= body_low)


def test_funding_settles_periodically_and_is_charged_to_the_right_bars() -> None:
    market = generate_signal_market(SPEC)
    settle_times = set(market.funding["funding_time"].to_list())
    charged = market.bars.filter(market.bars["funding_rate_in_bar"] != 0.0)["open_time"].to_list()
    assert settle_times == set(charged)
    assert market.funding.height == pytest.approx(SPEC.n_bars / 8, rel=0.05)


def test_impossible_specifications_are_refused() -> None:
    with pytest.raises(ValueError, match="n_bars"):
        SyntheticSpec(n_bars=100)
    with pytest.raises(ValueError, match="hidden_persistence"):
        SyntheticSpec(hidden_persistence=1.0)
    with pytest.raises(ValueError, match="favourable_share"):
        SyntheticSpec(favourable_share=0.0)
