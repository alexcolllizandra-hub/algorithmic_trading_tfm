"""Causality and validation tests for the three new strategy families.

The single property that matters is prefix invariance: appending future bars must
not change any signal already produced. A strategy that fails it is not merely
optimistic, it is unimplementable -- it needs data that did not exist when the
decision was taken. Each family is tested for it directly, plus the failure mode
specific to that family.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import numpy as np
import polars as pl
import pytest

from perp_lab.strategies.base import SIDE_COL
from perp_lab.strategies.cross_asset import MIN_REFERENCE_LAG, CrossAssetConfirmation
from perp_lab.strategies.funding import FundingTilt
from perp_lab.strategies.volatility_breakout import VolatilityBreakout


def _bars(n: int = 700, *, seed: int = 0, drift: float = 0.0002) -> pl.DataFrame:
    rng = np.random.default_rng(seed)
    t0 = datetime(2022, 1, 1, tzinfo=UTC)
    steps = rng.normal(drift, 0.01, size=n)
    # A volatility burst so breakout thresholds actually move.
    steps[n // 3 : n // 3 + 40] *= 6.0
    close = 100.0 * np.exp(np.cumsum(steps))
    spread = np.abs(rng.normal(0.0, 0.004, size=n)) * close
    return pl.DataFrame(
        {
            "open_time": [t0 + timedelta(hours=i) for i in range(n)],
            "open": close * (1 - 0.0005),
            "high": close + spread,
            "low": close - spread,
            "close": close,
        }
    )


def _funding_bars(n: int = 700, *, seed: int = 1) -> pl.DataFrame:
    rng = np.random.default_rng(seed)
    bars = _bars(n, seed=seed)
    # Funding updates every 8 hours and is constant in between, as published.
    settlements = rng.normal(0.0001, 0.00025, size=n // 8 + 1)
    rate = np.repeat(settlements, 8)[:n]
    return bars.with_columns(pl.Series("funding_rate", rate))


def _assert_prefix_invariant(strategy, frame: pl.DataFrame, cut: int, **kwargs) -> None:
    """Signals over a prefix must equal the first `cut` signals over the full frame."""
    full = strategy.signals(frame, **kwargs)
    prefix_kwargs = {k: v.head(cut) for k, v in kwargs.items()}
    partial = strategy.signals(frame.head(cut), **prefix_kwargs)
    assert partial.height == cut
    expected = full.head(cut)[SIDE_COL].to_list()
    assert partial[SIDE_COL].to_list() == expected, (
        "signals changed when future bars were appended: the strategy reads data "
        "that did not exist at decision time"
    )


# --------------------------------------------------------------------------- #
# volatility_breakout
# --------------------------------------------------------------------------- #


def _volbreak(**over) -> VolatilityBreakout:
    kwargs = {"level_window": 24, "atr_window": 14, "entry_atr": 0.5, "exit_atr": 0.2}
    kwargs.update(over)
    return VolatilityBreakout(**kwargs)


@pytest.mark.parametrize("exit_mode", ["reenter_level", "opposite_break", "volatility_stop"])
def test_volatility_breakout_is_prefix_invariant(exit_mode: str) -> None:
    _assert_prefix_invariant(_volbreak(exit_mode=exit_mode), _bars(), cut=500)


def test_volatility_breakout_threshold_excludes_the_decision_bar() -> None:
    """A channel that includes the current high can never be broken by it."""
    bars = _bars(200)
    thresholds = _volbreak(level_window=10).thresholds(bars)
    upper = thresholds["upper_level"].to_numpy()
    high = bars["high"].to_numpy()
    # The level at bar t must be the max of highs in [t-10, t-1], never touching t.
    for t in range(20, 60):
        expected = float(np.max(high[t - 10 : t]))
        assert upper[t] == pytest.approx(expected)


def test_volatility_breakout_threshold_is_prefix_invariant() -> None:
    bars = _bars(400)
    strategy = _volbreak()
    full = strategy.thresholds(bars).head(300)
    partial = strategy.thresholds(bars.head(300))
    for column in ("upper_level", "lower_level", "atr"):
        a = full[column].to_numpy()
        b = partial[column].to_numpy()
        assert np.allclose(a, b, equal_nan=True), f"{column} used future bars"


def test_volatility_breakout_warm_up_is_flat_not_guessed() -> None:
    side = _volbreak(level_window=50, atr_window=30).signals(_bars(300))[SIDE_COL].to_numpy()
    assert (side[:50] == 0).all(), "a position was taken before the threshold existed"


def test_volatility_breakout_atr_floor_uses_a_trailing_quantile() -> None:
    """An expanding full-sample quantile would be a look-ahead filter."""
    bars = _bars(900)
    strategy = _volbreak(min_atr_pct=0.5)
    full = strategy.thresholds(bars).head(700)["atr_floor"].to_numpy()
    partial = strategy.thresholds(bars.head(700))["atr_floor"].to_numpy()
    assert np.allclose(full, partial, equal_nan=True)


def test_volatility_breakout_rejects_incoherent_entry_and_exit() -> None:
    with pytest.raises(ValueError, match="closes the position on the bar that opened it"):
        _volbreak(exit_mode="volatility_stop", entry_atr=1.0, exit_atr=1.0)


@pytest.mark.parametrize(
    ("field", "value"),
    [("level_window", 0), ("atr_window", -1), ("entry_atr", 0.0), ("exit_atr", 0.0)],
)
def test_volatility_breakout_requires_positive_windows_and_thresholds(field, value) -> None:
    with pytest.raises(ValueError):
        _volbreak(**{field: value})


def test_volatility_breakout_rejects_an_unknown_exit_mode() -> None:
    with pytest.raises(ValueError, match="exit_mode"):
        _volbreak(exit_mode="whatever")


# --------------------------------------------------------------------------- #
# funding
# --------------------------------------------------------------------------- #


def _funding(**over) -> FundingTilt:
    kwargs = {"signal_window": 48, "entry_z": 1.0, "exit_z": 0.2}
    kwargs.update(over)
    return FundingTilt(**kwargs)


@pytest.mark.parametrize("stance", ["fade", "follow"])
def test_funding_strategy_is_prefix_invariant(stance: str) -> None:
    _assert_prefix_invariant(_funding(stance=stance), _funding_bars(), cut=500)


def test_funding_zscore_never_uses_a_later_settlement() -> None:
    bars = _funding_bars(600)
    strategy = _funding(signal_window=24)
    full = strategy.standardised_funding(bars).head(400)["z"].to_numpy()
    partial = strategy.standardised_funding(bars.head(400))["z"].to_numpy()
    assert np.allclose(full, partial, equal_nan=True)


def test_funding_fade_takes_the_opposite_side_of_the_payer() -> None:
    """High funding means longs are paying, so `fade` must go short."""
    bars = _funding_bars(600)
    strategy = _funding(stance="fade")
    z = strategy.standardised_funding(bars)["z"].to_numpy()
    side = strategy.signals(bars)[SIDE_COL].to_numpy()
    extreme_high = np.where(np.isfinite(z) & (z >= 1.0))[0]
    assert extreme_high.size > 0, "fixture produced no extreme funding"
    assert side[extreme_high[0]] == -1


def test_funding_follow_is_the_mirror_of_fade() -> None:
    bars = _funding_bars(600)
    fade = _funding(stance="fade").signals(bars)[SIDE_COL].to_numpy()
    follow = _funding(stance="follow").signals(bars)[SIDE_COL].to_numpy()
    assert not np.array_equal(fade, follow)


def test_funding_declares_the_feature_it_reads() -> None:
    assert _funding().required_features() == ("funding_rate",)


def test_funding_strategy_adds_no_cashflow_of_its_own() -> None:
    """Funding is charged once, by the backtester. Double-counting it is silent."""
    params = _funding().params()
    assert params["funding_role"] == "feature_only"
    assert "backtester" in str(params["funding_cashflow_note"])


def test_funding_without_the_rate_column_fails_loudly() -> None:
    with pytest.raises(ValueError, match="funding_rate"):
        _funding().signals(_bars(200))


def test_funding_rejects_an_exit_band_outside_the_entry_band() -> None:
    with pytest.raises(ValueError, match="must be < entry_z"):
        _funding(entry_z=1.0, exit_z=1.5)


def test_funding_requires_a_window_long_enough_for_a_deviation() -> None:
    with pytest.raises(ValueError, match="signal_window"):
        _funding(signal_window=1)


# --------------------------------------------------------------------------- #
# BTC_ETH_confirmation
# --------------------------------------------------------------------------- #


def _cross(**over) -> CrossAssetConfirmation:
    kwargs = {
        "lookback": 12,
        "entry_threshold": 0.005,
        "reference_threshold": 0.002,
        "target_symbol": "ETHUSDT",
        "reference_symbol": "BTCUSDT",
    }
    kwargs.update(over)
    return CrossAssetConfirmation(**kwargs)


@pytest.mark.parametrize("mode", ["agree", "lead_lag", "divergence"])
def test_cross_asset_is_prefix_invariant(mode: str) -> None:
    target, ref = _bars(seed=2), _bars(seed=3)
    _assert_prefix_invariant(_cross(mode=mode), target, cut=500, reference=ref)


def test_reference_bar_is_always_strictly_before_the_decision_bar() -> None:
    """The core cross-asset invariant, asserted from the output rather than assumed."""
    target, ref = _bars(400, seed=2), _bars(400, seed=3)
    for lag in (1, 2, 6):
        aligned = _cross(reference_lag=lag).align_reference(target, ref)
        rows = aligned.drop_nulls("reference_time")
        assert rows.height > 0
        gap = (rows["open_time"] - rows["reference_time"]).dt.total_hours().to_numpy()
        assert (gap >= lag).all(), (
            f"a reference bar was used less than {lag} bar(s) before the decision bar"
        )


def test_the_reference_bar_sharing_the_decision_timestamp_is_never_used() -> None:
    """Bars are left-closed: BTC's 12:00 bar is still forming when ETH's 12:00 closes."""
    target, ref = _bars(300, seed=2), _bars(300, seed=3)
    aligned = _cross(reference_lag=MIN_REFERENCE_LAG).align_reference(target, ref)
    rows = aligned.drop_nulls("reference_time")
    assert (rows["reference_time"] < rows["open_time"]).all()


def test_appending_future_reference_bars_cannot_change_past_signals() -> None:
    """The symmetric error: a later BTC bar confirming an earlier ETH trade."""
    target, ref = _bars(600, seed=2), _bars(600, seed=3)
    strategy = _cross()
    full = strategy.signals(target, reference=ref)
    truncated = strategy.signals(target.head(400), reference=ref.head(400))
    assert truncated[SIDE_COL].to_list() == full.head(400)[SIDE_COL].to_list()


def test_a_shorter_reference_history_does_not_change_earlier_signals() -> None:
    """Reference bars beyond the decision point must be irrelevant, not merely unused."""
    target, ref = _bars(600, seed=2), _bars(600, seed=3)
    strategy = _cross()
    with_all = strategy.signals(target.head(400), reference=ref)
    with_some = strategy.signals(target.head(400), reference=ref.head(400))
    assert with_all[SIDE_COL].to_list() == with_some[SIDE_COL].to_list()


def test_cross_asset_records_both_symbols_and_the_alignment_rule() -> None:
    params = _cross(reference_lag=3).params()
    assert params["target_symbol"] == "ETHUSDT"
    assert params["reference_symbol"] == "BTCUSDT"
    assert params["reference_lag"] == 3
    assert "reference_timestamp <= decision_timestamp" in str(params["alignment_rule"])


def test_cross_asset_refuses_a_zero_lag() -> None:
    with pytest.raises(ValueError, match="still being formed"):
        _cross(reference_lag=0)


def test_cross_asset_refuses_an_asset_confirming_itself() -> None:
    with pytest.raises(ValueError, match="must differ"):
        _cross(target_symbol="ETHUSDT", reference_symbol="ETHUSDT")


def test_cross_asset_refuses_to_run_without_the_reference_asset() -> None:
    with pytest.raises(ValueError, match="cross-asset dependency"):
        _cross().signals(_bars(200))


def test_cross_asset_agree_requires_both_assets_to_move_together() -> None:
    """`agree` must be a strict subset of the unconditional target signal."""
    target, ref = _bars(600, seed=2), _bars(600, seed=3)
    agreeing = _cross(mode="agree").signals(target, reference=ref)[SIDE_COL].to_numpy()
    permissive = (
        _cross(mode="agree", reference_threshold=0.0)
        .signals(target, reference=ref)[SIDE_COL]
        .to_numpy()
    )
    assert int((agreeing != 0).sum()) <= int((permissive != 0).sum())


def test_cross_asset_rejects_an_exit_at_or_above_the_entry_threshold() -> None:
    with pytest.raises(ValueError, match="exit_threshold"):
        _cross(entry_threshold=0.005, exit_threshold=0.005)
