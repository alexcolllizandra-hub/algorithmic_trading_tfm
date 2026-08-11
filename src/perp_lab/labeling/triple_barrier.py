"""Triple-barrier labeling with purging, embargo and concurrency weights.

An event signalled at bar ``t`` is entered at the **open of bar t+1**, exactly as
the backtester executes it (:mod:`perp_lab.backtesting.engine`). From that entry
the label watches three barriers:

* a profit barrier at ``entry * (1 + side * upper_atr * vol_t)``;
* a loss barrier at ``entry * (1 - side * lower_atr * vol_t)``;
* a vertical (time) barrier ``vertical_bars`` bars after entry.

Whichever is touched first ends the event. The horizontal barriers are scanned
against the high/low of each bar in the holding window, so a barrier is
registered on the bar that actually reached it rather than at the closing price.

Costs
-----
The question a meta-label has to answer is not "did price move in the signalled
direction" but **"would acting on this signal have been profitable after
costs"**. A label computed on gross returns answers the first question and
systematically over-states how often the primary rule was right, because it
hands the model a set of marginal winners that a real account would have paid
away in fees, slippage and funding.

:class:`LabelCosts` therefore charges the same three components the backtester
charges (:mod:`perp_lab.backtesting.engine`): a round trip of fee plus slippage
on entry and exit, and the funding rates settling inside the holding interval,
signed by the position. ``ret`` is the **net** return and the label is its sign
against ``min_return_bps``. With :data:`FREE_LABELS` the two coincide, which is
only appropriate for mechanical tests.

Causality
---------
``volatility_col`` must already be causal: its value on the event bar may only
use information available at that bar. The barrier widths are read on the event
bar, before the entry bar exists, so no future price influences the barrier
placement. :func:`triple_barrier_labels` is truncation invariant — labeling a
truncated history yields exactly the labels of the events whose full holding
window fits inside the truncation.

Because a label at ``t`` reads prices up to its exit, training samples overlap in
time. Two consequences are handled here rather than left to the caller:

* **Purging and embargo** (:func:`purged_embargoed_mask`) remove training events
  whose label span overlaps an evaluation block, plus a trailing embargo.
* **Sample weights** (:func:`average_uniqueness`,
  :func:`return_attributed_weights`) downweight events whose window is shared
  with many others, so a crowded period does not count many times over.

Reference: Lopez de Prado, M. (2018). *Advances in Financial Machine Learning*,
chapters 3 and 4.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
import polars as pl

EVENT_TIME_COL = "event_time"
SIDE_COL = "side"

_TOUCH_UPPER = "upper"
_TOUCH_LOWER = "lower"
_TOUCH_VERTICAL = "vertical"


ExitFill = Literal["barrier", "next_open"]


@dataclass(frozen=True)
class TripleBarrierSpec:
    """The barrier geometry, mirroring ``experiment.yaml``'s ``labeling`` block.

    ``exit_fill`` decides what price a barrier touch is credited at, and the two
    options describe genuinely different execution mechanisms:

    * ``barrier`` — the classical convention (Lopez de Prado): the touch fills at
      the barrier level, which assumes resting stop and take-profit orders in the
      market.
    * ``next_open`` — the touch is only *observed* at the end of the bar and is
      filled at the next open, which is what
      :mod:`perp_lab.backtesting.engine` can actually execute under this
      project's ``next_bar_open``, no-same-bar-fill contract.

    Use ``next_open`` whenever the label has to line up with a backtest of the
    same events; ``barrier`` labels are optimistic by exactly the move between
    the touch and the following open.
    """

    upper_barrier_atr: float
    lower_barrier_atr: float
    vertical_barrier_bars: int
    min_return_bps: float = 0.0
    exit_fill: ExitFill = "barrier"

    def __post_init__(self) -> None:
        if self.upper_barrier_atr <= 0 or self.lower_barrier_atr <= 0:
            raise ValueError("Barrier multiples must be strictly positive.")
        if self.vertical_barrier_bars < 1:
            raise ValueError("vertical_barrier_bars must be at least 1.")
        if self.min_return_bps < 0:
            raise ValueError("min_return_bps must be non-negative.")
        if self.exit_fill not in ("barrier", "next_open"):
            raise ValueError("exit_fill must be 'barrier' or 'next_open'.")

    def to_dict(self) -> dict[str, float | int | str]:
        return {
            "upper_barrier_atr": self.upper_barrier_atr,
            "lower_barrier_atr": self.lower_barrier_atr,
            "vertical_barrier_bars": self.vertical_barrier_bars,
            "min_return_bps": self.min_return_bps,
            "exit_fill": self.exit_fill,
        }


@dataclass(frozen=True)
class LabelCosts:
    """What acting on a signal costs, in the backtester's own cost model.

    ``fee_bps_per_side`` and ``slippage_bps_per_side`` are charged twice — once
    on the entry fill and once on the exit — because a label describes a
    completed round trip. ``funding_rate_col`` names a per-bar column holding
    the funding rate settling inside that bar (the ledger's
    ``funding_rate_in_bar``); it is charged with the sign of the position, so a
    long pays when the rate is positive.
    """

    fee_bps_per_side: float = 0.0
    slippage_bps_per_side: float = 0.0
    funding_rate_col: str | None = None

    def __post_init__(self) -> None:
        if self.fee_bps_per_side < 0 or self.slippage_bps_per_side < 0:
            raise ValueError("Fees and slippage must be non-negative.")

    @property
    def round_trip_cost(self) -> float:
        """Fee plus slippage on both fills, as a fraction of notional."""
        return 2.0 * (self.fee_bps_per_side + self.slippage_bps_per_side) / 1e4

    def to_dict(self) -> dict[str, float | str | None]:
        return {
            "fee_bps_per_side": self.fee_bps_per_side,
            "slippage_bps_per_side": self.slippage_bps_per_side,
            "funding_rate_col": self.funding_rate_col,
            "round_trip_cost": self.round_trip_cost,
        }


#: Costless labels. Mechanically valid, economically wrong: use only in tests
#: that isolate the barrier geometry from the cost model.
FREE_LABELS = LabelCosts()


@dataclass(frozen=True)
class LabelSpans:
    """The half-open bar interval ``[start, end)`` each label was computed from."""

    start: np.ndarray
    end: np.ndarray

    def __post_init__(self) -> None:
        if self.start.shape != self.end.shape:
            raise ValueError("start and end must have the same shape.")
        if self.start.ndim != 1:
            raise ValueError("label spans must be one-dimensional.")
        if np.any(self.end <= self.start):
            raise ValueError("every label span must cover at least one bar.")

    def __len__(self) -> int:
        return int(self.start.size)


def _require_columns(frame: pl.DataFrame, columns: tuple[str, ...], *, what: str) -> None:
    missing = [c for c in columns if c not in frame.columns]
    if missing:
        raise ValueError(f"{what} is missing required column(s): {sorted(missing)}")


def triple_barrier_labels(
    bars: pl.DataFrame,
    events: pl.DataFrame,
    spec: TripleBarrierSpec,
    *,
    volatility_col: str,
    costs: LabelCosts = FREE_LABELS,
    time_col: str = "open_time",
) -> pl.DataFrame:
    """Label each event by the first barrier its holding window touches.

    Parameters
    ----------
    bars:
        Ascending OHLC frame with ``time_col``, ``open``, ``high``, ``low`` and
        ``volatility_col``. ``volatility_col`` holds the barrier half-width as a
        *fraction of price* (for example ATR divided by close) and must be
        causal at the bar it sits on.
    events:
        Frame with ``event_time`` (a timestamp present in ``bars``) and ``side``
        in ``{-1, +1}``: the direction the primary strategy wants to take.
    spec:
        Barrier geometry.
    costs:
        Fees, slippage and funding charged to the round trip. The default is
        costless and should not be used for research labels.

    Returns
    -------
    One row per labelable event with the entry/exit bars, the gross and net
    realised return in the event's own direction, the cost breakdown, the
    barrier that was touched, the three-state ``label`` and the binary
    ``meta_label``. ``ret`` is net of costs and is what the labels are cut on.
    Events whose vertical barrier would fall outside the available history are
    dropped: labeling them would require prices that do not exist yet.
    """
    _require_columns(bars, (time_col, "open", "high", "low", volatility_col), what="bars")
    _require_columns(events, (EVENT_TIME_COL, SIDE_COL), what="events")
    if costs.funding_rate_col is not None:
        _require_columns(bars, (costs.funding_rate_col,), what="bars")

    times = bars[time_col]
    if bars.height >= 2 and not times.is_sorted():
        raise ValueError("bars must be sorted ascending by time.")

    opens = bars["open"].to_numpy().astype(float)
    highs = bars["high"].to_numpy().astype(float)
    lows = bars["low"].to_numpy().astype(float)
    vols = bars[volatility_col].to_numpy().astype(float)
    n_bars = opens.size
    if costs.funding_rate_col is None:
        funding_rates = np.zeros(n_bars, dtype=float)
    else:
        funding_rates = np.nan_to_num(
            bars[costs.funding_rate_col].to_numpy().astype(float), nan=0.0
        )
    # Cumulative funding so a holding interval costs one subtraction.
    funding_cumulative = np.concatenate([[0.0], np.cumsum(funding_rates)])
    round_trip = costs.round_trip_cost

    position_of = {t: i for i, t in enumerate(times.to_list())}
    horizon = spec.vertical_barrier_bars
    threshold = spec.min_return_bps / 1e4

    rows: list[dict[str, object]] = []
    for event_time, raw_side in zip(
        events[EVENT_TIME_COL].to_list(), events[SIDE_COL].to_list(), strict=True
    ):
        side = int(raw_side)
        if side not in (-1, 1):
            raise ValueError(f"side must be -1 or +1, got {side!r}.")
        if event_time not in position_of:
            raise ValueError(f"event_time {event_time!r} is not a bar in the price frame.")
        signal_index = position_of[event_time]
        entry_index = signal_index + 1
        # The vertical barrier exits at the open of entry_index + horizon, so
        # that bar must exist for the event to be labelable at all.
        last_needed = entry_index + horizon
        if last_needed >= n_bars:
            continue
        width = vols[signal_index]
        if not np.isfinite(width) or width <= 0:
            continue

        entry = opens[entry_index]
        upper = entry * (1.0 + spec.upper_barrier_atr * width)
        lower = entry * (1.0 - spec.lower_barrier_atr * width)

        window = slice(entry_index, entry_index + horizon)
        touched_upper = np.flatnonzero(highs[window] >= upper)
        touched_lower = np.flatnonzero(lows[window] <= lower)
        first_upper = int(touched_upper[0]) if touched_upper.size else None
        first_lower = int(touched_lower[0]) if touched_lower.size else None

        if first_upper is None and first_lower is None:
            touch = _TOUCH_VERTICAL
            exit_index = entry_index + horizon
            exit_price = opens[exit_index]
        else:
            up = first_upper if first_upper is not None else n_bars
            down = first_lower if first_lower is not None else n_bars
            if up < down:
                touch, offset, exit_price = _TOUCH_UPPER, up, upper
            elif down < up:
                touch, offset, exit_price = _TOUCH_LOWER, down, lower
            else:
                # Both barriers are inside the same bar's range. Intrabar order is
                # unknowable from OHLC, so the pessimistic branch is taken rather
                # than a coin flip that would flatter the label.
                touch = _TOUCH_UPPER if side < 0 else _TOUCH_LOWER
                offset = up
                exit_price = upper if side < 0 else lower
            exit_index = entry_index + offset
            if spec.exit_fill == "next_open":
                # The touch is observed at the end of its bar, so the first
                # executable price is the following open.
                exit_index += 1
                exit_price = opens[exit_index]

        raw_return = float(exit_price / entry - 1.0)
        gross_return = side * raw_return
        # Funding settles on the bars the position is actually held, exactly the
        # bars the engine charges it on: [entry_index, exit_index).
        funding_paid = side * float(
            funding_cumulative[exit_index] - funding_cumulative[entry_index]
        )
        net_return = gross_return - round_trip - funding_paid
        if net_return > threshold:
            label = 1
        elif net_return < -threshold:
            label = -1
        else:
            label = 0

        rows.append(
            {
                EVENT_TIME_COL: event_time,
                SIDE_COL: side,
                "entry_index": entry_index,
                "entry_time": times[entry_index],
                "entry_price": entry,
                "upper_barrier": upper,
                "lower_barrier": lower,
                "exit_index": exit_index,
                "exit_time": times[exit_index],
                "exit_price": float(exit_price),
                "holding_bars": exit_index - entry_index,
                "barrier_touched": touch,
                "gross_ret": gross_return,
                "cost": round_trip,
                "funding": funding_paid,
                "ret": net_return,
                "label": label,
                "meta_label": int(label > 0),
            }
        )

    schema = {
        EVENT_TIME_COL: events.schema[EVENT_TIME_COL],
        SIDE_COL: pl.Int64,
        "entry_index": pl.Int64,
        "entry_time": bars.schema[time_col],
        "entry_price": pl.Float64,
        "upper_barrier": pl.Float64,
        "lower_barrier": pl.Float64,
        "exit_index": pl.Int64,
        "exit_time": bars.schema[time_col],
        "exit_price": pl.Float64,
        "holding_bars": pl.Int64,
        "barrier_touched": pl.String,
        "gross_ret": pl.Float64,
        "cost": pl.Float64,
        "funding": pl.Float64,
        "ret": pl.Float64,
        "label": pl.Int64,
        "meta_label": pl.Int64,
    }
    return pl.DataFrame(rows, schema=schema)


def label_spans(labels: pl.DataFrame) -> LabelSpans:
    """The ``[entry_index, exit_index + 1)`` bar interval each label observed."""
    _require_columns(labels, ("entry_index", "exit_index"), what="labels")
    start = labels["entry_index"].to_numpy().astype(np.int64)
    end = labels["exit_index"].to_numpy().astype(np.int64) + 1
    return LabelSpans(start=start, end=end)


def purged_embargoed_mask(
    spans: LabelSpans,
    *,
    evaluation_start: int,
    evaluation_end: int,
    embargo_bars: int,
) -> np.ndarray:
    """Which training events survive purging and embargo around an eval block.

    ``[evaluation_start, evaluation_end)`` is the bar interval being evaluated.
    An event is dropped when its label span overlaps that interval (purging: the
    label was partly computed from prices the evaluation will also use) or when
    it starts within ``embargo_bars`` after the interval ends (embargo: serial
    correlation would otherwise leak evaluation information back into training).

    Returns a boolean keep-mask aligned with ``spans``.
    """
    if evaluation_end <= evaluation_start:
        raise ValueError("evaluation_end must be strictly after evaluation_start.")
    if embargo_bars < 0:
        raise ValueError("embargo_bars must be non-negative.")
    overlaps = (spans.start < evaluation_end) & (spans.end > evaluation_start)
    embargoed = (spans.start >= evaluation_end) & (spans.start < evaluation_end + embargo_bars)
    return ~(overlaps | embargoed)


def concurrency(spans: LabelSpans, n_bars: int) -> np.ndarray:
    """Number of label spans covering each bar (``length n_bars``)."""
    if n_bars < 1:
        raise ValueError("n_bars must be at least 1.")
    counts = np.zeros(n_bars + 1, dtype=np.int64)
    start = np.clip(spans.start, 0, n_bars)
    end = np.clip(spans.end, 0, n_bars)
    np.add.at(counts, start, 1)
    np.add.at(counts, end, -1)
    return np.cumsum(counts)[:n_bars]


def average_uniqueness(spans: LabelSpans, n_bars: int) -> np.ndarray:
    """Average uniqueness of each label: the mean of ``1 / concurrency`` over it.

    An event that holds the market to itself scores 1. An event whose window is
    shared with nine others throughout scores 0.1. Using these as sample weights
    stops a dense cluster of overlapping events from dominating the fit.
    """
    counts = concurrency(spans, n_bars)
    safe = np.where(counts > 0, counts, 1)
    inverse = 1.0 / safe
    cumulative = np.concatenate([[0.0], np.cumsum(inverse)])
    start = np.clip(spans.start, 0, n_bars)
    end = np.clip(spans.end, 0, n_bars)
    lengths = np.maximum(end - start, 1)
    return (cumulative[end] - cumulative[start]) / lengths


def return_attributed_weights(
    spans: LabelSpans,
    bar_returns: np.ndarray,
    *,
    normalise: bool = True,
) -> np.ndarray:
    """Sample weights combining uniqueness with the magnitude of the move.

    Each bar return is divided by the number of concurrent labels before being
    attributed to an event, so overlapping events split the return between them
    instead of each claiming all of it. Weights are absolute values; the sign
    lives in the label, not in the weight.
    """
    returns = np.asarray(bar_returns, dtype=float)
    if returns.ndim != 1:
        raise ValueError("bar_returns must be one-dimensional.")
    n_bars = returns.size
    counts = concurrency(spans, n_bars)
    safe = np.where(counts > 0, counts, 1)
    attributed = np.concatenate([[0.0], np.cumsum(returns / safe)])
    start = np.clip(spans.start, 0, n_bars)
    end = np.clip(spans.end, 0, n_bars)
    weights = np.abs(attributed[end] - attributed[start])
    if normalise and weights.sum() > 0:
        weights = weights * (weights.size / weights.sum())
    return weights
