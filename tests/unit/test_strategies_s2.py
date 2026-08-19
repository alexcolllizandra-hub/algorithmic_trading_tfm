"""Gate S2-A: technical validity of the pre-specified S2 order-flow families.

The S2 batch is the first to read the taker aggressor side, so beyond the usual
S1-A properties (truncation invariance, warm-up flatness, known-behaviour
synthetic data) these tests carry two obligations specific to this batch:

* **the flow lag is real** -- a family must not react on the bar whose flow
  triggered it, because ``docs/methodology/experimental_design.md`` freezes the
  rule that contemporaneous flow variables are lagged by at least one bar;
* **material difference is measured, not asserted** -- the pre-specification
  claims each S2 family triggers on a different subset of bars than its nearest
  earlier relative. That claim is checked numerically here, so a future
  reparameterisation that quietly collapses one family into another fails a test
  rather than passing review.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import numpy as np
import polars as pl
import pytest

from perp_lab.strategies.base import SIDE_COL
from perp_lab.strategies.flow_price_divergence import FlowPriceDivergence
from perp_lab.strategies.illiquidity_reversion import IlliquidityReversion
from perp_lab.strategies.mean_reversion import MeanReversion
from perp_lab.strategies.taker_flow_extreme import TakerFlowExtreme

START = datetime(2021, 1, 1, tzinfo=UTC)


def _flow_frame(
    n: int,
    *,
    close: np.ndarray,
    quote_volume: np.ndarray,
    buy_share: np.ndarray,
) -> pl.DataFrame:
    """A minimal kline frame carrying the aggressor side.

    ``buy_share`` is the fraction of quote volume that lifted the ask, so
    ``taker_buy_quote = buy_share * quote_volume`` by construction.
    """
    return pl.DataFrame(
        {
            "open_time": pl.Series(
                "open_time",
                [START + timedelta(hours=i) for i in range(n)],
                dtype=pl.Datetime("us", "UTC"),
            ),
            "close": pl.Series(close, dtype=pl.Float64),
            "quote_volume": pl.Series(quote_volume, dtype=pl.Float64),
            "taker_buy_quote": pl.Series(buy_share * quote_volume, dtype=pl.Float64),
        }
    )


def _random_flow_frame(n: int, seed: int = 11) -> pl.DataFrame:
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, 0.004, size=n)))
    quote_volume = np.exp(rng.normal(14.0, 0.6, size=n))
    buy_share = np.clip(rng.normal(0.5, 0.08, size=n), 0.02, 0.98)
    return _flow_frame(n, close=close, quote_volume=quote_volume, buy_share=buy_share)


def _taker() -> TakerFlowExtreme:
    return TakerFlowExtreme(
        flow_window=4,
        rank_window=48,
        extreme_pct=0.9,
        holding_bars=4,
        response="continuation",
    )


def _illiquidity() -> IlliquidityReversion:
    return IlliquidityReversion(
        impact_window=4,
        rank_window=48,
        entry_pct=0.9,
        exit_pct=0.5,
        max_holding_bars=12,
    )


def _divergence() -> FlowPriceDivergence:
    return FlowPriceDivergence(
        window=4,
        rank_window=48,
        flow_pct=0.5,
        move_pct=0.5,
        holding_bars=4,
        response="follow_absorber",
    )


def _families() -> list[tuple[str, object]]:
    return [
        ("taker_flow_extreme", _taker()),
        ("illiquidity_reversion", _illiquidity()),
        ("flow_price_divergence", _divergence()),
    ]


# --------------------------------------------------------------------------- #
# Shared properties
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(("name", "strategy"), _families())
def test_signals_are_truncation_invariant(name: str, strategy) -> None:
    frame = _random_flow_frame(400)
    cut = 300
    full = strategy.signals(frame)[SIDE_COL].to_list()
    truncated = strategy.signals(frame.head(cut))[SIDE_COL].to_list()
    assert truncated == full[:cut], (
        f"{name} changed its past signals when future bars were appended: it reads the future."
    )


@pytest.mark.parametrize(("name", "strategy"), _families())
def test_future_bars_cannot_change_past_signals(name: str, strategy) -> None:
    """Mutating only the tail must leave every earlier signal untouched."""
    frame = _random_flow_frame(400)
    cut = 300
    mutated = frame.with_columns(
        pl.when(pl.int_range(pl.len()) >= cut)
        .then(pl.col("close") * 5.0)
        .otherwise(pl.col("close"))
        .alias("close"),
        pl.when(pl.int_range(pl.len()) >= cut)
        .then(pl.col("quote_volume") * 100.0)
        .otherwise(pl.col("quote_volume"))
        .alias("quote_volume"),
    )
    before = strategy.signals(frame)[SIDE_COL].to_list()[:cut]
    after = strategy.signals(mutated)[SIDE_COL].to_list()[:cut]
    assert before == after, f"{name} let a future bar rewrite a past decision."


@pytest.mark.parametrize(("name", "strategy"), _families())
def test_signals_are_valid_sides(name: str, strategy) -> None:
    frame = _random_flow_frame(400)
    out = strategy.signals(frame)
    assert out.columns == ["open_time", SIDE_COL]
    assert out.height == frame.height
    assert set(out[SIDE_COL].unique().to_list()) <= {-1, 0, 1}


@pytest.mark.parametrize(("name", "strategy"), _families())
def test_warmup_bars_are_flat(name: str, strategy) -> None:
    """Before the ranking window is full there is no threshold, so no exposure."""
    frame = _random_flow_frame(400)
    side = strategy.signals(frame)[SIDE_COL].to_list()
    assert set(side[:48]) == {0}, f"{name} took a position before its ranking window filled."


@pytest.mark.parametrize(("name", "strategy"), _families())
def test_missing_flow_columns_are_a_hard_error(name: str, strategy) -> None:
    frame = _random_flow_frame(100).drop("taker_buy_quote")
    with pytest.raises(ValueError, match="aggressor side"):
        strategy.signals(frame)


@pytest.mark.parametrize(("name", "strategy"), _families())
def test_zero_volume_bars_do_not_produce_infinities(name: str, strategy) -> None:
    frame = _random_flow_frame(400).with_columns(
        pl.when(pl.int_range(pl.len()) % 17 == 0)
        .then(0.0)
        .otherwise(pl.col("quote_volume"))
        .alias("quote_volume"),
        pl.when(pl.int_range(pl.len()) % 17 == 0)
        .then(0.0)
        .otherwise(pl.col("taker_buy_quote"))
        .alias("taker_buy_quote"),
    )
    side = strategy.signals(frame)[SIDE_COL]
    assert set(side.unique().to_list()) <= {-1, 0, 1}


# --------------------------------------------------------------------------- #
# The flow lag is real
# --------------------------------------------------------------------------- #


def test_flow_lag_delays_the_reaction_to_the_triggering_bar() -> None:
    """A single flow spike must move the position on the bar *after* the spike.

    Built so bar 200 is the only lopsided bar in an otherwise balanced series.
    With ``flow_lag=1`` and ``flow_window=1`` the earliest bar that may carry
    exposure is 201; bar 200 itself must still be flat.
    """
    n = 400
    spike = 200
    close = np.full(n, 100.0)
    quote_volume = np.full(n, 1_000.0)
    buy_share = np.full(n, 0.5)
    buy_share[spike] = 0.99

    frame = _flow_frame(n, close=close, quote_volume=quote_volume, buy_share=buy_share)
    strategy = TakerFlowExtreme(
        flow_window=1,
        rank_window=48,
        extreme_pct=0.9,
        holding_bars=3,
        response="continuation",
        flow_lag=1,
    )
    side = strategy.signals(frame)[SIDE_COL].to_list()

    assert side[spike] == 0, "the strategy reacted on the very bar whose flow triggered it"
    assert side[spike + 1] == 1, "the strategy failed to react on the bar after the flow spike"


def test_a_zero_flow_lag_is_rejected_at_construction() -> None:
    with pytest.raises(ValueError, match="flow_lag must be >= 1"):
        TakerFlowExtreme(
            flow_window=4,
            rank_window=48,
            extreme_pct=0.9,
            holding_bars=4,
            response="continuation",
            flow_lag=0,
        )


# --------------------------------------------------------------------------- #
# Known-behaviour synthetic data
# --------------------------------------------------------------------------- #


def _one_sided_buying_frame(n: int = 400, spike: int = 200) -> pl.DataFrame:
    """Balanced flow everywhere except a sustained burst of aggressive buying."""
    rng = np.random.default_rng(3)
    close = np.full(n, 100.0)
    quote_volume = np.full(n, 1_000.0)
    buy_share = np.clip(rng.normal(0.5, 0.01, size=n), 0.4, 0.6)
    buy_share[spike : spike + 4] = 0.95
    return _flow_frame(n, close=close, quote_volume=quote_volume, buy_share=buy_share)


def test_taker_flow_continuation_buys_into_aggressive_buying() -> None:
    side = _taker().signals(_one_sided_buying_frame())[SIDE_COL].to_list()
    assert 1 in side[201:210], "aggressive buying must produce a long under 'continuation'"
    assert -1 not in side[201:210]


def test_taker_flow_reversal_is_the_exact_mirror_of_continuation() -> None:
    """The two response arms must differ only in sign, never in when they fire."""
    frame = _one_sided_buying_frame()
    base = {"flow_window": 4, "rank_window": 48, "extreme_pct": 0.9, "holding_bars": 4}
    long_arm = TakerFlowExtreme(**base, response="continuation").signals(frame)[SIDE_COL].to_numpy()
    short_arm = TakerFlowExtreme(**base, response="reversal").signals(frame)[SIDE_COL].to_numpy()
    assert np.array_equal(long_arm, -short_arm), (
        "the two response arms are meant to be the same trigger with opposite signs"
    )


def test_taker_flow_never_holds_without_a_recent_trigger() -> None:
    """Every exposed bar must have a trigger within the preceding holding window."""
    strategy = _taker()
    frame = _random_flow_frame(600)
    prepared = strategy.indicators(frame)
    magnitude = prepared["abs_imbalance"].to_numpy()
    threshold = prepared["threshold"].to_numpy()
    fired = np.nan_to_num(magnitude, nan=-1.0) >= np.nan_to_num(threshold, nan=np.inf)
    side = strategy.signals(frame)[SIDE_COL].to_numpy()

    for t in np.flatnonzero(side != 0):
        window = fired[max(0, t - strategy.holding_bars + 1) : t + 1]
        assert window.any(), f"bar {t} carried exposure with no trigger in the holding window"


def test_illiquidity_reversion_fades_a_move_made_on_thin_volume() -> None:
    """A jump delivered on unusually small traded value must be faded."""
    n = 400
    jump = 200
    rng = np.random.default_rng(5)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, 0.0005, size=n)))
    close[jump:] *= 1.05  # a 5% step up
    quote_volume = np.full(n, 1_000.0)
    quote_volume[jump] = 1.0  # delivered on almost no traded value
    buy_share = np.full(n, 0.5)

    frame = _flow_frame(n, close=close, quote_volume=quote_volume, buy_share=buy_share)
    side = _illiquidity().signals(frame)[SIDE_COL].to_list()
    assert -1 in side[jump + 1 : jump + 8], "an up-move on a thin book must be sold, not bought"


def test_illiquidity_reversion_ignores_the_same_move_on_heavy_volume() -> None:
    """The identical price path with ample traded value must not trigger.

    This is the whole economic claim: the move is not the signal, the move *per
    unit of traded value* is.
    """
    n = 400
    jump = 200
    rng = np.random.default_rng(5)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, 0.0005, size=n)))
    close[jump:] *= 1.05
    quote_volume = np.full(n, 1_000.0)
    quote_volume[jump] = 5_000_000.0  # the same move, absorbed by real volume
    buy_share = np.full(n, 0.5)

    frame = _flow_frame(n, close=close, quote_volume=quote_volume, buy_share=buy_share)
    side = _illiquidity().signals(frame)[SIDE_COL].to_list()
    assert set(side[jump + 1 : jump + 5]) == {0}, (
        "a large move delivered on heavy volume is information, not illiquidity, and must be "
        "ignored by this family"
    )


def test_illiquidity_reversion_respects_the_holding_cap() -> None:
    strategy = IlliquidityReversion(
        impact_window=4,
        rank_window=48,
        entry_pct=0.9,
        exit_pct=0.5,
        max_holding_bars=6,
    )
    side = strategy.signals(_random_flow_frame(800))[SIDE_COL].to_numpy()
    longest = 0
    run = 0
    for t in range(side.shape[0]):
        if side[t] != 0 and (t > 0 and side[t] == side[t - 1]):
            run += 1
        elif side[t] != 0:
            run = 1
        else:
            run = 0
        longest = max(longest, run)
    assert longest <= strategy.max_holding_bars, (
        f"a position ran for {longest} bars against a cap of {strategy.max_holding_bars}"
    )


def test_divergence_follows_the_absorber_when_buying_fails_to_lift_price() -> None:
    """Heavy aggressive buying while price falls means the passive seller won."""
    n = 400
    event = 200
    rng = np.random.default_rng(9)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, 0.003, size=n)))
    quote_volume = np.full(n, 1_000.0)
    buy_share = np.clip(rng.normal(0.5, 0.05, size=n), 0.1, 0.9)

    # Four bars of one-sided buying delivered into a falling price.
    buy_share[event : event + 4] = 0.95
    close[event : event + 4] = close[event - 1] * np.array([0.99, 0.98, 0.97, 0.96])
    close[event + 4 :] = close[event + 3]

    frame = _flow_frame(n, close=close, quote_volume=quote_volume, buy_share=buy_share)
    side = _divergence().signals(frame)[SIDE_COL].to_list()
    assert -1 in side[event + 4 : event + 12], (
        "buying absorbed by a falling price should be traded with the absorbing seller"
    )


def test_divergence_stays_flat_when_flow_and_price_agree() -> None:
    """The mechanical case -- buying lifts price -- must never trigger this family."""
    n = 400
    event = 200
    rng = np.random.default_rng(9)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, 0.003, size=n)))
    quote_volume = np.full(n, 1_000.0)
    buy_share = np.clip(rng.normal(0.5, 0.05, size=n), 0.1, 0.9)

    buy_share[event : event + 4] = 0.95
    close[event : event + 4] = close[event - 1] * np.array([1.01, 1.02, 1.03, 1.04])
    close[event + 4 :] = close[event + 3]

    frame = _flow_frame(n, close=close, quote_volume=quote_volume, buy_share=buy_share)
    prepared = _divergence().indicators(frame)
    imbalance = prepared["imbalance"].to_numpy()[event + 1 : event + 5]
    move = prepared["move"].to_numpy()[event + 1 : event + 5]
    assert np.all(np.sign(imbalance) * np.sign(move) >= 0), (
        "flow and price agree here, so no divergence trigger may exist on these bars"
    )


# --------------------------------------------------------------------------- #
# Direction constraints
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("direction", ["long", "short"])
def test_direction_constrains_every_family(direction: str) -> None:
    frame = _random_flow_frame(600)
    forbidden = -1 if direction == "long" else 1
    strategies = [
        TakerFlowExtreme(
            flow_window=4,
            rank_window=48,
            extreme_pct=0.9,
            holding_bars=4,
            response="continuation",
            direction=direction,
        ),
        IlliquidityReversion(
            impact_window=4,
            rank_window=48,
            entry_pct=0.9,
            exit_pct=0.5,
            max_holding_bars=12,
            direction=direction,
        ),
        FlowPriceDivergence(
            window=4,
            rank_window=48,
            flow_pct=0.5,
            move_pct=0.5,
            holding_bars=4,
            response="follow_absorber",
            direction=direction,
        ),
    ]
    for strategy in strategies:
        side = strategy.signals(frame)[SIDE_COL].to_list()
        assert forbidden not in side, (
            f"{type(strategy).__name__} took a {forbidden} position under direction={direction!r}"
        )


# --------------------------------------------------------------------------- #
# Material difference from earlier families (measured, not asserted)
# --------------------------------------------------------------------------- #


def _trigger_mask(prepared: pl.DataFrame, value: str, level: str) -> np.ndarray:
    values = prepared[value].fill_null(float("nan")).to_numpy()
    levels = prepared[level].fill_null(float("nan")).to_numpy()
    return np.nan_to_num(values, nan=-np.inf) >= np.nan_to_num(levels, nan=np.inf)


def _jaccard(a: np.ndarray, b: np.ndarray) -> float:
    union = int((a | b).sum())
    return 0.0 if union == 0 else float((a & b).sum()) / union


def test_illiquidity_reversion_is_materially_different_from_mean_reversion() -> None:
    """The R3 family fires on price alone; this one fires on price per unit volume.

    Both are run on the same bars and their trigger sets are compared. A high
    overlap would mean the S2 family is the rejected R3 family wearing a new
    name, which the Gate S2 pre-specification forbids.
    """
    frame = _random_flow_frame(3_000)
    prepared = _illiquidity().indicators(frame)
    illiquidity_fires = _trigger_mask(prepared, "impact", "entry_level")

    window = 48
    z = (
        frame.select(
            (
                (pl.col("close") - pl.col("close").rolling_mean(window, min_samples=window))
                / pl.col("close").rolling_std(window, min_samples=window)
            ).alias("z")
        )["z"]
        .fill_null(0.0)
        .to_numpy()
    )
    mean_reversion_fires = np.abs(z) >= 2.0

    overlap = _jaccard(illiquidity_fires, mean_reversion_fires)
    assert illiquidity_fires.sum() > 0 and mean_reversion_fires.sum() > 0
    assert overlap < 0.25, (
        f"illiquidity_reversion and the R3 mean_reversion trigger set overlap at "
        f"Jaccard {overlap:.3f}; this family would be a rename, not a new hypothesis"
    )
    # And the R3 family cannot see the case this one is built for at all.
    assert MeanReversion(zscore_window=48, entry_z=2.0, exit_z=0.5).required_features() == (
        "zscore_48",
    )


def test_s2_families_trigger_on_different_bars() -> None:
    """The three S2 families must not be three names for one trigger."""
    frame = _random_flow_frame(3_000)

    taker = _taker()
    taker_fires = _trigger_mask(taker.indicators(frame), "abs_imbalance", "threshold")

    illiquidity_fires = _trigger_mask(_illiquidity().indicators(frame), "impact", "entry_level")

    divergence = _divergence()
    prepared = divergence.indicators(frame)
    imbalance = prepared["imbalance"].fill_null(0.0).to_numpy()
    move = prepared["move"].fill_null(0.0).to_numpy()
    divergence_fires = (
        _trigger_mask(prepared, "abs_imbalance", "flow_level")
        & _trigger_mask(prepared, "abs_move", "move_level")
        & (np.sign(imbalance) * np.sign(move) < 0)
    )

    masks = {
        "taker_flow_extreme": taker_fires,
        "illiquidity_reversion": illiquidity_fires,
        "flow_price_divergence": divergence_fires,
    }
    for name, mask in masks.items():
        assert mask.sum() > 0, f"{name} never triggered on 3000 synthetic bars"

    names = list(masks)
    for i, left in enumerate(names):
        for right in names[i + 1 :]:
            overlap = _jaccard(masks[left], masks[right])
            assert overlap < 0.5, (
                f"{left} and {right} share {overlap:.1%} of their triggers (Jaccard); "
                "they are not materially distinct hypotheses"
            )


# --------------------------------------------------------------------------- #
# Construction-time validation
# --------------------------------------------------------------------------- #


def test_taker_flow_rejects_a_two_sided_percentile() -> None:
    with pytest.raises(ValueError, match="extreme_pct"):
        TakerFlowExtreme(
            flow_window=4,
            rank_window=48,
            extreme_pct=0.4,
            holding_bars=4,
            response="continuation",
        )


def test_taker_flow_rejects_an_unknown_response() -> None:
    with pytest.raises(ValueError, match="response must be one of"):
        TakerFlowExtreme(
            flow_window=4,
            rank_window=48,
            extreme_pct=0.9,
            holding_bars=4,
            response="momentum",
        )


def test_illiquidity_reversion_rejects_an_exit_at_or_above_the_entry() -> None:
    with pytest.raises(ValueError, match="exit_pct"):
        IlliquidityReversion(
            impact_window=4,
            rank_window=48,
            entry_pct=0.9,
            exit_pct=0.9,
            max_holding_bars=12,
        )


def test_divergence_rejects_a_below_median_materiality_floor() -> None:
    with pytest.raises(ValueError, match="move_pct"):
        FlowPriceDivergence(
            window=4,
            rank_window=48,
            flow_pct=0.6,
            move_pct=0.3,
            holding_bars=4,
            response="follow_absorber",
        )
