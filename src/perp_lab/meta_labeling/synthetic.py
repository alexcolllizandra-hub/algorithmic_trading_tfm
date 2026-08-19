"""Synthetic markets with a known ground truth, for validating the ML layer.

EXPLORATORY / INFRASTRUCTURE-ONLY. Nothing generated here is market data and no
number computed on it may be reported as evidence about BTC or ETH. These
markets exist to answer one question: **does the meta-labeling machinery behave
correctly when we already know the answer?**

Two markets, deliberately paired
--------------------------------
:func:`generate_signal_market` plants an edge. A hidden two-state process decides
whether the primary rule is currently right: in the favourable state the bars
after a signal drift *with* the signal, in the unfavourable state *against* it.
The hidden state is never a feature. What the model may see is a noisy
observation of it, mixed with price-derived features and pure decoys. A working
meta-label layer must recover enough of that state to refuse the unfavourable
signals; a broken one cannot.

:func:`generate_noise_market` plants nothing. Prices are geometric Brownian
motion (:mod:`perp_lab.stochastic.processes`), so increments are independent and
**no filter can add value** — the best attainable behaviour is to decline to act.
The same primary rule, the same feature construction and the same hidden state
are kept, but the state no longer touches the price path. Any "edge" a pipeline
reports here is manufactured by the pipeline.

Reporting one without the other is what makes a machine-learning result
unfalsifiable, so both are always run.

Causality
---------
The primary rule reads past returns only. Every feature at bar ``t`` is computed
from bars up to and including ``t``, and the decision it feeds is executed at the
open of ``t + 1``, matching :mod:`perp_lab.backtesting.engine`. The planted drift
is injected into bars strictly after the signal bar, so a favourable state is
never visible in the prices that generated the signal.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

import numpy as np
import polars as pl

from perp_lab.labeling.triple_barrier import EVENT_TIME_COL, SIDE_COL
from perp_lab.stochastic.processes import GbmParameters, simulate_gbm
from perp_lab.utils.timeutils import timeframe_to_timedelta

VOLATILITY_COL = "vol_frac"
FUNDING_RATE_COL = "funding_rate_in_bar"
REGIME_COL = "vol_regime"
GROUND_TRUTH_COL = "favourable"

#: Features the model is allowed to see. ``state_proxy_*`` are noisy readings of
#: the hidden state, ``momentum``/``volatility`` are ordinary causal price
#: features, and ``decoy_*`` are pure noise that must not dominate a healthy fit.
FEATURE_NAMES: tuple[str, ...] = (
    "state_proxy_fast",
    "state_proxy_slow",
    "momentum_12",
    "volatility_24",
    "decoy_0",
    "decoy_1",
    "decoy_2",
)

_WARMUP_BARS = 240
_FUNDING_INTERVAL_BARS = 8


@dataclass(frozen=True)
class SyntheticSpec:
    """Generation parameters. Both markets are generated from the same spec."""

    n_bars: int = 20_000
    seed: int = 42
    timeframe: str = "1h"
    bar_volatility: float = 0.004
    wick_noise: float = 0.0008
    #: Bars between consecutive primary signals; the rule cannot fire while a
    #: previous signal is still inside its planted-drift window.
    event_spacing: int = 8
    momentum_window: int = 12
    #: Probability the hidden state stays where it is, i.e. how persistent the
    #: favourable regime is. Persistence is what makes it learnable at all.
    hidden_persistence: float = 0.97
    favourable_share: float = 0.5
    #: Per-bar drift added in the signal's direction while favourable, and
    #: subtracted while unfavourable. 6 bps/bar is small against a 40 bps bar
    #: volatility — the edge has to be real but must not be trivially visible,
    #: or the study would only prove that the machinery can find a giveaway.
    edge_per_bar: float = 0.0006
    edge_bars: int = 12
    #: Standard deviation of the noise on the observable state proxies. Larger
    #: means a harder, more realistic recovery problem.
    proxy_noise: float = 1.6
    funding_rate: float = 0.00001
    start: datetime = field(default_factory=lambda: datetime(2019, 1, 1, tzinfo=UTC))

    def __post_init__(self) -> None:
        if self.n_bars < _WARMUP_BARS * 4:
            raise ValueError(f"n_bars must be at least {_WARMUP_BARS * 4} for a usable study.")
        if not 0.0 < self.hidden_persistence < 1.0:
            raise ValueError("hidden_persistence must lie strictly inside (0, 1).")
        if not 0.0 < self.favourable_share < 1.0:
            raise ValueError("favourable_share must lie strictly inside (0, 1).")
        if self.bar_volatility <= 0 or self.edge_bars < 1 or self.event_spacing < 1:
            raise ValueError("bar_volatility, edge_bars and event_spacing must be positive.")

    def to_dict(self) -> dict[str, float | int | str]:
        return {
            "n_bars": self.n_bars,
            "seed": self.seed,
            "timeframe": self.timeframe,
            "bar_volatility": self.bar_volatility,
            "event_spacing": self.event_spacing,
            "momentum_window": self.momentum_window,
            "hidden_persistence": self.hidden_persistence,
            "favourable_share": self.favourable_share,
            "edge_per_bar": self.edge_per_bar,
            "edge_bars": self.edge_bars,
            "proxy_noise": self.proxy_noise,
            "funding_rate": self.funding_rate,
            "start": self.start.isoformat(),
        }


@dataclass(frozen=True)
class SyntheticMarket:
    """Bars, primary signals, features and the ground truth behind them."""

    name: str
    planted_edge: bool
    spec: SyntheticSpec
    bars: pl.DataFrame
    events: pl.DataFrame
    features: pl.DataFrame
    funding: pl.DataFrame

    @property
    def feature_names(self) -> tuple[str, ...]:
        return FEATURE_NAMES

    @property
    def favourable_share(self) -> float:
        """Fraction of signals fired in the favourable hidden state.

        Ground truth. It is reported to describe the generated market and must
        never be joined onto the feature matrix.
        """
        if self.events.height == 0:
            return float("nan")
        return float(self.events[GROUND_TRUTH_COL].to_numpy().mean())

    def to_dict(self) -> dict[str, object]:
        return {
            "market": self.name,
            "planted_edge": self.planted_edge,
            "n_bars": self.bars.height,
            "n_events": self.events.height,
            "favourable_share": self.favourable_share,
            "spec": self.spec.to_dict(),
        }


def _hidden_state(spec: SyntheticSpec, rng: np.random.Generator) -> np.ndarray:
    """A persistent two-state Markov chain: 1 favourable, 0 unfavourable."""
    stay = spec.hidden_persistence
    state = np.empty(spec.n_bars, dtype=np.int8)
    state[0] = 1 if rng.random() < spec.favourable_share else 0
    draws = rng.random(spec.n_bars)
    for t in range(1, spec.n_bars):
        if draws[t] < stay:
            state[t] = state[t - 1]
        else:
            state[t] = 1 if rng.random() < spec.favourable_share else 0
    return state


def _signal_side(log_prices: np.ndarray, t: int, window: int) -> int:
    """The primary rule: follow the sign of the last ``window`` bars' return.

    An ordinary, interpretable momentum rule. It reads ``log_prices`` up to bar
    ``t`` only. Its direction is deliberately *not* skilful by itself — that is
    what leaves room for a meta-label to add or remove value.
    """
    move = log_prices[t] - log_prices[t - window]
    return 1 if move >= 0.0 else -1


def _ohlc_from_closes(
    closes: np.ndarray, spec: SyntheticSpec, rng: np.random.Generator
) -> dict[str, np.ndarray]:
    """Bars whose wicks extend beyond the body, as a real bar's do.

    The wick noise matters: barrier touches are scanned on highs and lows, so a
    generator that set ``high = max(open, close)`` would make every barrier
    touch a function of the close alone and flatter the labeler.
    """
    opens = np.concatenate([[closes[0]], closes[:-1]])
    body_high = np.maximum(opens, closes)
    body_low = np.minimum(opens, closes)
    high = body_high * (1.0 + np.abs(rng.normal(0.0, spec.wick_noise, closes.size)))
    low = body_low * (1.0 - np.abs(rng.normal(0.0, spec.wick_noise, closes.size)))
    return {"open": opens, "high": high, "low": low, "close": closes}


def _causal_columns(bars: pl.DataFrame) -> pl.DataFrame:
    """Attach the causal volatility, funding and regime columns.

    ``vol_frac`` is a rolling standard deviation of past returns and sets the
    barrier width. ``vol_regime`` splits bars against the *expanding* median of
    that volatility, so the regime label at bar ``t`` uses no bar after ``t``;
    an unconditional median would leak the whole sample into every label.
    """
    with_returns = bars.with_columns(
        (pl.col("close") / pl.col("close").shift(1) - 1.0).alias("_ret")
    )
    with_vol = with_returns.with_columns(
        pl.col("_ret").rolling_std(window_size=24, min_samples=24).alias(VOLATILITY_COL)
    )
    volatility = with_vol[VOLATILITY_COL].to_numpy().astype(float)
    observed = np.isfinite(volatility)
    running_sum = np.cumsum(np.where(observed, volatility, 0.0))
    running_count = np.maximum(np.cumsum(observed), 1)
    expanding_mean = running_sum / running_count
    return (
        with_vol.with_columns(pl.Series("_expanding_mean_vol", expanding_mean))
        .with_columns(
            pl.when(pl.col(VOLATILITY_COL) > pl.col("_expanding_mean_vol"))
            .then(pl.lit("high"))
            .otherwise(pl.lit("low"))
            .alias(REGIME_COL)
        )
        .drop("_ret", "_expanding_mean_vol")
    )


def _features(
    log_prices: np.ndarray,
    state: np.ndarray,
    volatility: np.ndarray,
    spec: SyntheticSpec,
    rng: np.random.Generator,
) -> pl.DataFrame:
    """Everything the model may see, all of it available at bar ``t``.

    The two state proxies are noisy readings of the hidden state: ``fast`` is a
    single noisy draw, ``slow`` a trailing mean of independent draws, which is
    less noisy but stale. Neither is the state itself, so perfect classification
    is impossible by construction — the ceiling is set by ``proxy_noise``.
    """
    n = spec.n_bars
    signed_state = 2.0 * state.astype(float) - 1.0
    fast = signed_state + rng.normal(0.0, spec.proxy_noise, n)
    raw_slow = signed_state + rng.normal(0.0, spec.proxy_noise, n)

    window = spec.momentum_window
    momentum = np.zeros(n, dtype=float)
    momentum[window:] = log_prices[window:] - log_prices[:-window]

    frame = pl.DataFrame(
        {
            "state_proxy_fast": fast,
            "_slow_raw": raw_slow,
            "momentum_12": momentum,
            "volatility_24": np.nan_to_num(volatility, nan=0.0),
            "decoy_0": rng.normal(0.0, 1.0, n),
            "decoy_1": rng.normal(0.0, 1.0, n),
            "decoy_2": rng.standard_t(4, n),
        }
    )
    return frame.with_columns(
        pl.col("_slow_raw").rolling_mean(window_size=12, min_samples=1).alias("state_proxy_slow")
    ).select(FEATURE_NAMES)


def _funding_path(spec: SyntheticSpec, rng: np.random.Generator) -> np.ndarray:
    """Funding settling every eight bars, as on an hourly USDT-M perpetual."""
    rates = np.zeros(spec.n_bars, dtype=float)
    settle = np.arange(0, spec.n_bars, _FUNDING_INTERVAL_BARS)
    rates[settle] = spec.funding_rate + rng.normal(0.0, spec.funding_rate, settle.size)
    return rates


def _assemble(
    name: str,
    *,
    planted_edge: bool,
    spec: SyntheticSpec,
    closes: np.ndarray,
    state: np.ndarray,
    event_index: list[int],
    event_side: list[int],
    event_favourable: list[bool],
    rng: np.random.Generator,
) -> SyntheticMarket:
    step = timeframe_to_timedelta(spec.timeframe)
    times = [spec.start + i * step for i in range(spec.n_bars)]
    ohlc = _ohlc_from_closes(closes, spec, rng)
    funding_rates = _funding_path(spec, rng)

    bars = _causal_columns(
        pl.DataFrame(
            {
                "open_time": times,
                **ohlc,
                "volume": rng.uniform(100.0, 1000.0, spec.n_bars),
                FUNDING_RATE_COL: funding_rates,
            }
        )
    )
    volatility = bars[VOLATILITY_COL].to_numpy().astype(float)
    log_prices = np.log(closes)
    features = _features(log_prices, state, volatility, spec, rng)

    keep = [
        i
        for i in event_index
        if i >= _WARMUP_BARS and np.isfinite(volatility[i]) and volatility[i] > 0
    ]
    keep_set = set(keep)
    selected = [k for k, i in enumerate(event_index) if i in keep_set]
    events = pl.DataFrame(
        {
            EVENT_TIME_COL: [times[event_index[k]] for k in selected],
            SIDE_COL: [event_side[k] for k in selected],
            GROUND_TRUTH_COL: [event_favourable[k] for k in selected],
        }
    )
    event_features = features[[event_index[k] for k in selected]].with_columns(
        pl.Series(EVENT_TIME_COL, events[EVENT_TIME_COL])
    )
    settle = funding_rates != 0.0
    funding = pl.DataFrame(
        {
            "funding_time": [t for t, s in zip(times, settle, strict=True) if s],
            "funding_rate": funding_rates[settle],
        }
    )
    return SyntheticMarket(
        name=name,
        planted_edge=planted_edge,
        spec=spec,
        bars=bars,
        events=events,
        features=event_features.select(EVENT_TIME_COL, *FEATURE_NAMES),
        funding=funding,
    )


def generate_signal_market(spec: SyntheticSpec | None = None) -> SyntheticMarket:
    """A market where the primary rule is genuinely right part of the time.

    The path is built one bar at a time because the planted drift is *caused* by
    a signal that is itself a function of the path so far. Vectorising it would
    require knowing the signals before the prices that produce them.
    """
    spec = spec or SyntheticSpec()
    rng = np.random.default_rng(spec.seed)
    state = _hidden_state(spec, rng)
    shocks = rng.normal(0.0, spec.bar_volatility, spec.n_bars)

    injected = np.zeros(spec.n_bars, dtype=float)
    log_prices = np.empty(spec.n_bars, dtype=float)
    log_prices[0] = np.log(10_000.0)
    event_index: list[int] = []
    event_side: list[int] = []
    event_favourable: list[bool] = []
    last_event = -spec.event_spacing

    for t in range(1, spec.n_bars):
        log_prices[t] = log_prices[t - 1] + shocks[t] + injected[t]
        if t < spec.momentum_window or t - last_event < spec.event_spacing:
            continue
        side = _signal_side(log_prices, t, spec.momentum_window)
        favourable = bool(state[t])
        # The drift lands on bars strictly after the signal bar, so it cannot
        # have influenced the prices the signal was computed from.
        direction = 1.0 if favourable else -1.0
        stop = min(spec.n_bars, t + 1 + spec.edge_bars)
        injected[t + 1 : stop] += side * direction * spec.edge_per_bar
        event_index.append(t)
        event_side.append(side)
        event_favourable.append(favourable)
        last_event = t

    return _assemble(
        "signal",
        planted_edge=True,
        spec=spec,
        closes=np.exp(log_prices),
        state=state,
        event_index=event_index,
        event_side=event_side,
        event_favourable=event_favourable,
        rng=rng,
    )


def generate_noise_market(spec: SyntheticSpec | None = None) -> SyntheticMarket:
    """The control: geometric Brownian motion, where nothing is predictable.

    The hidden state is still generated and still observed through the same
    noisy proxies, but it no longer touches the price path. So the features look
    exactly as informative as in the signal market and are, in truth, worthless.
    That is the trap the layer has to refuse.
    """
    spec = spec or SyntheticSpec()
    rng = np.random.default_rng(spec.seed)
    state = _hidden_state(spec, rng)

    params = GbmParameters(drift=0.0, volatility=spec.bar_volatility, n_observations=spec.n_bars)
    closes = simulate_gbm(
        params, n_paths=1, n_steps=spec.n_bars - 1, seed=spec.seed, initial_price=10_000.0
    )[0]
    log_prices = np.log(closes)

    event_index: list[int] = []
    event_side: list[int] = []
    last_event = -spec.event_spacing
    for t in range(spec.momentum_window, spec.n_bars):
        if t - last_event < spec.event_spacing:
            continue
        event_index.append(t)
        event_side.append(_signal_side(log_prices, t, spec.momentum_window))
        last_event = t

    return _assemble(
        "noise",
        planted_edge=False,
        spec=spec,
        closes=closes,
        state=state,
        event_index=event_index,
        event_side=event_side,
        # Recorded for symmetry only: with no planted drift the hidden state has
        # no bearing on whether a signal pays.
        event_favourable=[bool(state[t]) for t in event_index],
        rng=rng,
    )
