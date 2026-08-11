"""Bounded-holding position state machine shared by event-driven S1 families.

``evolve_positions`` in :mod:`perp_lab.strategies.base` holds a position until a
condition closes it. Event strategies need the opposite contract: an event opens
a position for a **fixed number of bars** and the clock -- not a signal -- closes
it. Keeping that loop here means the two event families cannot drift apart in
how they count bars, which is exactly the kind of silent divergence that makes
two "identical" strategies produce different trade counts.
"""

from __future__ import annotations

import numpy as np


def evolve_timed_positions(
    long_event: np.ndarray,
    short_event: np.ndarray,
    holding_bars: int,
) -> np.ndarray:
    """Open on an event and hold exactly ``holding_bars`` bars, then flatten.

    While a position is open, further events are ignored: overlapping the same
    hypothesis with itself would size the bet by how often the trigger repeats
    rather than by the risk policy. A long and a short event on the same bar
    cancel (the evidence is contradictory), leaving the position flat.

    Once the clock runs out, a fresh event on the very next bar opens a new
    position immediately. Two same-side episodes back to back therefore appear
    in the ledger as one uninterrupted position with no intervening turnover.
    That is intended -- the second episode is a new bet on new evidence -- but it
    means *contiguous run length* is not bounded by ``holding_bars``. The bound
    that does hold is that every bar carrying exposure has a triggering event
    within the preceding ``holding_bars`` bars.
    """
    if holding_bars < 1:
        raise ValueError("holding_bars must be at least one bar.")
    n = int(long_event.shape[0])
    side = np.zeros(n, dtype=np.int8)
    remaining = 0
    current = 0
    for t in range(n):
        if remaining > 0:
            side[t] = current
            remaining -= 1
            continue
        long_fires = bool(long_event[t])
        short_fires = bool(short_event[t])
        if long_fires == short_fires:
            # No event, or a long and a short firing together: the evidence is
            # absent or contradictory, so no position is opened.
            continue
        current = 1 if long_fires else -1
        side[t] = current
        remaining = holding_bars - 1
    return side
