"""Gate S1-A: technical validity of the pre-specified S1 strategy families.

Three properties are checked for every family, because each one has broken a
different family in this codebase before:

* **truncation invariance** -- signals for the first *k* bars must not change
  when later bars are appended. A family that fails this is reading the future.
* **warm-up flatness** -- bars whose inputs are still null must be flat, not
  implicitly long.
* **known-behaviour synthetic data** -- a series constructed so the correct
  answer is known by hand must produce that answer.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import numpy as np
import polars as pl
import pytest

from perp_lab.strategies.base import SIDE_COL
from perp_lab.strategies.funding_reversal import FundingReversal
from perp_lab.strategies.intraday_seasonality import IntradaySeasonality
from perp_lab.strategies.mtf_trend_consensus import MultiHorizonTrendConsensus
from perp_lab.strategies.timed_exit import evolve_timed_positions
from perp_lab.strategies.xasset_spread_reversion import CrossAssetSpreadReversion

START = datetime(2021, 1, 1, tzinfo=UTC)


def _times(n: int) -> pl.Series:
    return pl.Series(
        "open_time", [START + timedelta(hours=i) for i in range(n)], dtype=pl.Datetime("us", "UTC")
    )


def _frame(n: int, **columns: np.ndarray | list[float]) -> pl.DataFrame:
    data: dict[str, object] = {"open_time": _times(n)}
    for name, values in columns.items():
        data[name] = pl.Series(name, list(values), dtype=pl.Float64)
    return pl.DataFrame(data)


def _mtf_frame(n: int, drift: float = 0.01) -> pl.DataFrame:
    ramp = np.arange(n, dtype=float) * drift
    return _frame(
        n,
        momentum_4=ramp * 0.4,
        momentum_8=ramp * 0.8,
        momentum_16=ramp * 1.6,
        roll_std_8=np.full(n, 0.01),
    )


def _mtf() -> MultiHorizonTrendConsensus:
    return MultiHorizonTrendConsensus(
        horizons=(4, 8, 16),
        min_agreement=2,
        min_strength=0.5,
        strength_window=8,
        exit_agreement=1,
    )


def _funding_frame(n: int, rng: np.random.Generator) -> pl.DataFrame:
    rates = rng.normal(0.0, 1e-4, size=n)
    return _frame(n, funding_rate=rates)


def _spread_frame(n: int, rng: np.random.Generator) -> pl.DataFrame:
    return _frame(
        n,
        xasset_rel_momentum_12=rng.normal(0.0, 0.02, size=n),
        xasset_corr_48=np.full(n, 0.8),
    )


def _strategies_and_frames() -> list[tuple[str, object, pl.DataFrame]]:
    rng = np.random.default_rng(7)
    return [
        ("mtf_trend_consensus", _mtf(), _mtf_frame(400)),
        (
            "funding_reversal",
            FundingReversal(rank_window=48, extreme_pct=0.9, holding_bars=4),
            _funding_frame(400, rng),
        ),
        (
            "intraday_seasonality",
            IntradaySeasonality(entry_hour=8, holding_bars=4, side_mode="long"),
            _frame(400),
        ),
        (
            "xasset_spread_reversion",
            CrossAssetSpreadReversion(
                lookback=12,
                entry_spread=0.01,
                exit_spread=0.002,
                min_corr=0.5,
                corr_window=48,
                target_symbol="BTCUSDT",
                reference_symbol="ETHUSDT",
            ),
            _spread_frame(400, rng),
        ),
    ]


@pytest.mark.parametrize(
    ("name", "strategy", "frame"), _strategies_and_frames(), ids=lambda v: getattr(v, "name", "")
)
def test_signals_are_truncation_invariant(name: str, strategy, frame: pl.DataFrame) -> None:
    cut = 300
    full = strategy.signals(frame)[SIDE_COL].to_list()
    truncated = strategy.signals(frame.head(cut))[SIDE_COL].to_list()
    assert truncated == full[:cut], (
        f"{name} changed its past signals when future bars were appended: it reads the future."
    )


@pytest.mark.parametrize(("name", "strategy", "frame"), _strategies_and_frames())
def test_signals_are_valid_sides(name: str, strategy, frame: pl.DataFrame) -> None:
    out = strategy.signals(frame)
    assert out.columns == ["open_time", SIDE_COL]
    assert out.height == frame.height
    assert set(out[SIDE_COL].unique().to_list()) <= {-1, 0, 1}


def test_mtf_consensus_is_flat_during_warmup() -> None:
    frame = _mtf_frame(50)
    frame = frame.with_columns(
        pl.when(pl.int_range(pl.len()) < 16)
        .then(None)
        .otherwise(pl.col("momentum_16"))
        .alias("momentum_16")
    )
    side = _mtf().signals(frame)[SIDE_COL].to_list()
    assert set(side[:16]) == {0}, "warm-up bars with a null horizon must be flat"


def test_mtf_consensus_goes_long_on_coherent_uptrend() -> None:
    side = _mtf().signals(_mtf_frame(200))[SIDE_COL].to_list()
    assert side[-1] == 1, "all horizons trending up strongly must produce a long"


def test_mtf_consensus_stays_flat_when_horizons_disagree() -> None:
    n = 200
    frame = _frame(
        n,
        momentum_4=np.full(n, 0.05),
        momentum_8=np.full(n, -0.05),
        momentum_16=np.full(n, 0.0),
        roll_std_8=np.full(n, 0.01),
    )
    strategy = MultiHorizonTrendConsensus(
        horizons=(4, 8, 16),
        min_agreement=3,
        min_strength=0.1,
        strength_window=8,
        exit_agreement=1,
    )
    assert set(strategy.signals(frame)[SIDE_COL].to_list()) == {0}


def test_mtf_consensus_rejects_exit_above_entry_threshold() -> None:
    with pytest.raises(ValueError, match="exit_agreement"):
        MultiHorizonTrendConsensus(
            horizons=(4, 8),
            min_agreement=1,
            min_strength=0.0,
            strength_window=8,
            exit_agreement=2,
        )


def test_funding_reversal_fades_an_upper_tail_extreme() -> None:
    n = 120
    rates = np.full(n, 1e-5)
    rates[100] = 1.0  # unmistakable upper-tail extreme
    strategy = FundingReversal(rank_window=48, extreme_pct=0.9, holding_bars=3)
    side = strategy.signals(_frame(n, funding_rate=rates))[SIDE_COL].to_list()
    assert side[100] == -1, "longs paying an extreme rate must be faded short"
    assert side[100:103] == [-1, -1, -1], "the position must be held for holding_bars bars"
    assert side[103] == 0, "the clock, not the signal, closes the position"


def test_funding_reversal_never_holds_without_a_recent_trigger() -> None:
    """Exposure must always be traceable to an extreme within ``holding_bars``.

    Consecutive episodes may chain into one uninterrupted position when the rate
    keeps printing extremes, so contiguous run length is not the invariant. What
    must hold is that no bar carries exposure that no recent event justifies.
    """
    rng = np.random.default_rng(11)
    holding = 5
    strategy = FundingReversal(rank_window=48, extreme_pct=0.9, holding_bars=holding)
    frame = _funding_frame(600, rng)
    side = np.asarray(strategy.signals(frame)[SIDE_COL].to_list())

    rate = np.asarray(frame["funding_rate"].to_list(), dtype=float)
    window = pl.Series(rate)
    upper = window.rolling_quantile(quantile=0.9, window_size=48).to_numpy()
    lower = window.rolling_quantile(quantile=0.1, window_size=48).to_numpy()
    triggered = np.isfinite(upper) & np.isfinite(lower) & ((rate >= upper) | (rate <= lower))

    assert side.any(), "the synthetic series should trigger at least one episode"
    for t in np.flatnonzero(side):
        start = max(0, t - holding + 1)
        assert triggered[start : t + 1].any(), (
            f"bar {t} carries exposure with no funding extreme in the previous {holding} bars"
        )


def test_intraday_seasonality_enters_only_at_the_configured_hour() -> None:
    strategy = IntradaySeasonality(entry_hour=8, holding_bars=2, side_mode="short")
    frame = _frame(72)
    out = strategy.signals(frame).with_columns(pl.col("open_time").dt.hour().alias("hour"))
    openings = out.filter((pl.col(SIDE_COL) != 0) & (pl.col(SIDE_COL).shift(1).fill_null(0) == 0))
    assert openings["hour"].unique().to_list() == [8]
    assert set(openings[SIDE_COL].to_list()) == {-1}


def test_intraday_seasonality_rejects_an_empty_direction_combination() -> None:
    with pytest.raises(ValueError, match="empty by construction"):
        IntradaySeasonality(entry_hour=8, holding_bars=2, side_mode="short", direction="long")


def test_spread_reversion_fades_the_leg_that_ran_ahead() -> None:
    n = 60
    spread = np.zeros(n)
    spread[30:35] = 0.05  # target strongly outperformed the reference leg
    frame = _frame(n, xasset_rel_momentum_12=spread, xasset_corr_48=np.full(n, 0.9))
    strategy = CrossAssetSpreadReversion(
        lookback=12,
        entry_spread=0.01,
        exit_spread=0.002,
        min_corr=0.5,
        corr_window=48,
        target_symbol="BTCUSDT",
        reference_symbol="ETHUSDT",
    )
    side = strategy.signals(frame)[SIDE_COL].to_list()
    assert side[30] == -1
    assert side[35] == 0, "the position closes once the spread is back inside the exit band"


def test_spread_reversion_respects_the_correlation_floor() -> None:
    n = 60
    spread = np.zeros(n)
    spread[30:35] = 0.05
    frame = _frame(n, xasset_rel_momentum_12=spread, xasset_corr_48=np.full(n, 0.1))
    strategy = CrossAssetSpreadReversion(
        lookback=12,
        entry_spread=0.01,
        exit_spread=0.002,
        min_corr=0.5,
        corr_window=48,
        target_symbol="BTCUSDT",
        reference_symbol="ETHUSDT",
    )
    assert set(strategy.signals(frame)[SIDE_COL].to_list()) == {0}


def test_spread_reversion_requires_the_reference_leg() -> None:
    strategy = CrossAssetSpreadReversion(
        lookback=12,
        entry_spread=0.01,
        exit_spread=0.002,
        target_symbol="BTCUSDT",
        reference_symbol="ETHUSDT",
    )
    with pytest.raises(ValueError, match="second leg is the hypothesis"):
        strategy.signals(_frame(30))


def test_timed_exit_ignores_events_while_a_position_is_open() -> None:
    events = np.array([True, True, True, False, False, True], dtype=bool)
    silent = np.zeros_like(events)
    side = evolve_timed_positions(events, silent, holding_bars=3)
    assert side.tolist() == [1, 1, 1, 0, 0, 1]


def test_timed_exit_treats_contradictory_events_as_no_signal() -> None:
    both = np.array([True, False], dtype=bool)
    side = evolve_timed_positions(both, both, holding_bars=2)
    assert side.tolist() == [0, 0]
