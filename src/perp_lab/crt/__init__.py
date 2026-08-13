"""Candle Range Theory: discretionary price-action ideas made mechanical.

CRT is normally taught as a way of *looking* at charts — a range gets swept, the
sweep gets rejected, the level gets reclaimed, price rotates to the mid. Stated
that way it cannot be tested, because every term is a judgement call and the
judgement is made after the outcome is visible.

This package turns each term into an arithmetic definition with an explicit
threshold, and each pattern into an ordered state machine, so that a setup either
occurred or did not according to rules fixed before the data was read.

Three commitments hold throughout:

- **Levels are usable only after the period that produced them has closed.**
  Every range carries ``available_from`` and consumers filter on it.
- **Order is part of the definition.** A reclaim only exists if a sweep preceded
  it within a bar budget; unordered booleans would fire on bars where the
  sequence never happened.
- **Nothing here is claimed to be profitable.** These are hypotheses, registered
  as a new experimental round and subject to the same protocol — walk-forward,
  purging, embargo, ten seeds, cost stress and multiple-testing correction — as
  every family the study has already rejected.
"""

from __future__ import annotations

from perp_lab.crt.ranges import (
    RangeConfig,
    RangeError,
    RangeKind,
    active_ranges_at,
    build_ranges,
    latest_range,
)
from perp_lab.crt.sessions import (
    DEFAULT_SESSIONS,
    SESSION_REGISTRY,
    SessionError,
    SessionSpec,
    resolve_session,
    session_windows,
    tag_sessions,
)
from perp_lab.crt.states import (
    Bar,
    InteractionConfig,
    LevelState,
    LevelTracker,
    Side,
    Transition,
    run_tracker,
)

__all__ = [
    "DEFAULT_SESSIONS",
    "SESSION_REGISTRY",
    "Bar",
    "InteractionConfig",
    "LevelState",
    "LevelTracker",
    "RangeConfig",
    "RangeError",
    "RangeKind",
    "SessionError",
    "SessionSpec",
    "Side",
    "Transition",
    "active_ranges_at",
    "build_ranges",
    "latest_range",
    "resolve_session",
    "run_tracker",
    "session_windows",
    "tag_sessions",
]
