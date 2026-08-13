"""The vocabulary the study speaks when a number is absent.

A dashboard that renders a missing result as ``0`` is not neutral: zero is a
measurement, and printing it where nothing was measured invents evidence. Every
layer between the artifacts and the screen therefore carries an explicit state
instead, and the states below are the whole permitted set.

The distinction that matters most is between *not run*, *run and rejected*, and
*run but not publishable*. Those are three different scientific claims and the
interface must never blur them.
"""

from __future__ import annotations

from enum import StrEnum


class ResultStatus(StrEnum):
    """Why a cell in the study has, or has not, a number in it."""

    EXECUTED = "EXECUTED"
    """The experiment ran and produced a result. Says nothing about its quality."""

    AUDITED = "AUDITED"
    """Executed, and its provenance has been checked against the source artifacts."""

    REJECTED = "REJECTED"
    """Executed and measured, and it failed its pre-declared acceptance criterion."""

    INVALIDATED = "INVALIDATED"
    """Executed, but the result cannot be trusted — leakage, a bug, a broken contract."""

    SKIPPED = "SKIPPED"
    """Deliberately not run, because it was inapplicable rather than unfinished."""

    NOT_EXECUTED = "NOT_EXECUTED"
    """Planned and in scope, but never run. An honest gap, not a zero."""

    NOT_AVAILABLE = "NOT_AVAILABLE"
    """Ran, but this particular figure was not persisted and cannot be recovered."""

    HOLDOUT_LOCKED = "HOLDOUT_LOCKED"
    """Withheld by the holdout protocol. The absence of a metric is the point."""


TERMINAL_STATUSES: frozenset[ResultStatus] = frozenset(
    {
        ResultStatus.REJECTED,
        ResultStatus.INVALIDATED,
        ResultStatus.SKIPPED,
    }
)
"""States that close a line of enquiry; nothing further is expected to arrive."""

MEASURED_STATUSES: frozenset[ResultStatus] = frozenset(
    {
        ResultStatus.EXECUTED,
        ResultStatus.AUDITED,
        ResultStatus.REJECTED,
    }
)
"""States in which a metric legitimately exists. Anything else must render as text."""


def has_metrics(status: ResultStatus) -> bool:
    """Whether a numeric payload may accompany this state.

    ``INVALIDATED`` is excluded on purpose: the numbers exist on disk but must
    not be shown, because showing a figure the project has declared untrustworthy
    invites it to be quoted anyway.
    """
    return status in MEASURED_STATUSES
