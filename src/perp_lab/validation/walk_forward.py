"""Expanding walk-forward partitioning with purging and embargo.

Geometry per ADR 0008; the holdout boundary comes from ADR 0003. The
development period is cut into chronological folds with three disjoint,
time-ordered roles:

    TRAIN            (fit transforms / strategy behaviour)
      |-- embargo gap
    VALIDATION       (candidate selection / calibration)
      |-- purge gap
    TEST             (out-of-sample evidence)

Geometry (all day counts from ``configs/experiment.yaml -> walk_forward``):

* **Expanding (anchored)** training: every fold's training window starts at
  ``development_start`` and grows by ``step_days`` each fold.
* Fold *k* raw boundaries (offsets in days from ``development_start``):
  ``train_end = initial_train_days + k*step_days``;
  ``val = [train_end, train_end + validation_days)``;
  ``test = [val_end, val_end + test_days)``. Folds are emitted while the test
  window fits inside the development period.

Purge and embargo are **derived from the config**, never hard-coded:

* ``purge_bars   = max(label_horizon, max_holding)`` -- removed from the END of
  the validation window so validation labels/holdings cannot overlap the test
  window.
* ``embargo_bars = purge_bars + ceil(fraction_of_test * test_bars)`` -- removed
  from the END of the training window, giving the full temporal separation
  between the data used to *fit* and the evaluation block. Because
  ``embargo_bars >= purge_bars``, the training/validation boundary is separated
  by at least the label horizon as well.

Bar counts are converted to durations with the primary-timeframe step, so the
day-based windows and bar-based purge/embargo are consistent.

Folds produced here are the *outer* folds. Candidate search runs independently
inside each one and never pools fitness across them; see ADR 0012.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

import polars as pl

from perp_lab.config.experiment import ExperimentConfig
from perp_lab.utils.timeutils import timeframe_to_timedelta


@dataclass(frozen=True)
class WalkForwardFold:
    """One expanding walk-forward fold with purge/embargo already applied."""

    index: int
    train_start: datetime
    train_end: datetime  # effective (embargo already removed)
    val_start: datetime
    val_end: datetime  # effective (purge already removed)
    test_start: datetime
    test_end: datetime
    purge_bars: int
    embargo_bars: int

    def __post_init__(self) -> None:
        # Invariants that guarantee causal ordering and disjointness.
        if not (self.train_start < self.train_end <= self.val_start):
            raise ValueError(f"Fold {self.index}: train must precede validation with a gap.")
        if not (self.val_start < self.val_end <= self.test_start):
            raise ValueError(f"Fold {self.index}: validation must precede test with a gap.")
        if not (self.test_start < self.test_end):
            raise ValueError(f"Fold {self.index}: test window must be non-empty.")

    def to_dict(self) -> dict[str, object]:
        return {
            "index": self.index,
            "train_start": self.train_start.isoformat(),
            "train_end": self.train_end.isoformat(),
            "val_start": self.val_start.isoformat(),
            "val_end": self.val_end.isoformat(),
            "test_start": self.test_start.isoformat(),
            "test_end": self.test_end.isoformat(),
            "purge_bars": self.purge_bars,
            "embargo_bars": self.embargo_bars,
        }


def generate_folds(
    development_start: datetime,
    development_end_exclusive: datetime,
    *,
    initial_train_days: int,
    validation_days: int,
    test_days: int,
    step_days: int,
    purge: timedelta,
    embargo: timedelta,
    purge_bars: int = 0,
    embargo_bars: int = 0,
    max_folds: int | None = None,
) -> list[WalkForwardFold]:
    """Generate expanding walk-forward folds between two datetimes.

    ``purge`` / ``embargo`` are durations (converted from bar counts by the
    caller). ``purge_bars`` / ``embargo_bars`` are recorded on each fold for the
    artifact. Folds are emitted while ``test_end <= development_end_exclusive``.
    """
    if development_start >= development_end_exclusive:
        raise ValueError("development_start must precede development_end_exclusive.")
    if embargo < purge:
        raise ValueError("embargo must be >= purge (embargo subsumes the label-horizon purge).")

    folds: list[WalkForwardFold] = []
    k = 0
    while True:
        train_end_raw = development_start + timedelta(days=initial_train_days + k * step_days)
        val_start = train_end_raw
        val_end_raw = val_start + timedelta(days=validation_days)
        test_start = val_end_raw
        test_end = test_start + timedelta(days=test_days)
        if test_end > development_end_exclusive:
            break

        # Both guards eat into the END of their window, so the raw boundaries
        # above stay on the config's calendar grid and only the usable span
        # shrinks. That keeps fold k comparable across purge/embargo settings.
        train_end_eff = train_end_raw - embargo
        val_end_eff = val_end_raw - purge
        # Skip degenerate folds where the guard consumed the whole window.
        if train_end_eff <= development_start or val_end_eff <= val_start:
            k += 1
            # Termination guard for the degenerate case: with max_folds set, a
            # geometry whose windows are always consumed by the guards would
            # otherwise spin until test_end leaves the development period. The
            # 4x multiplier is arbitrary headroom, not a tuned value.
            if max_folds is not None and k > max_folds * 4:
                break
            continue

        folds.append(
            WalkForwardFold(
                index=len(folds),
                train_start=development_start,
                train_end=train_end_eff,
                val_start=val_start,
                val_end=val_end_eff,
                test_start=test_start,
                test_end=test_end,
                purge_bars=purge_bars,
                embargo_bars=embargo_bars,
            )
        )
        k += 1
        if max_folds is not None and len(folds) >= max_folds:
            break
    return folds


def generate_walk_forward(
    config: ExperimentConfig, *, strict: bool = False
) -> list[WalkForwardFold]:
    """Build the walk-forward folds described by an :class:`ExperimentConfig`.

    Purge/embargo bar counts come from the config's derived properties
    (``purge_bars`` / ``embargo_bars``) and are converted to durations with the
    primary-timeframe step. When ``strict`` is True, fewer folds than
    ``walk_forward.min_folds`` raises (a data-span sanity guard).
    """
    wf = config.walk_forward
    if wf.scheme != "expanding":
        raise NotImplementedError(f"walk-forward scheme {wf.scheme!r} not implemented yet.")
    step = timeframe_to_timedelta(config.timeframes.primary)
    folds = generate_folds(
        config.periods.development_start,
        config.periods.development_end_exclusive,
        initial_train_days=wf.initial_train_days,
        validation_days=wf.validation_days,
        test_days=wf.test_days,
        step_days=wf.step_days,
        purge=config.purge_bars * step,
        embargo=config.embargo_bars * step,
        purge_bars=config.purge_bars,
        embargo_bars=config.embargo_bars,
    )
    if strict and len(folds) < wf.min_folds:
        raise ValueError(
            f"Walk-forward produced {len(folds)} folds < min_folds={wf.min_folds}; "
            "the development span is too short for the configured geometry."
        )
    return folds


def split_fold(
    df: pl.DataFrame, fold: WalkForwardFold, *, time_col: str = "open_time"
) -> dict[str, pl.DataFrame]:
    """Slice ``df`` into ``train`` / ``validation`` / ``test`` frames for a fold.

    Purge and embargo are already baked into the fold boundaries, so the three
    returned frames are guaranteed to have **no overlapping timestamps**.
    """
    train = df.filter(
        (pl.col(time_col) >= fold.train_start) & (pl.col(time_col) < fold.train_end)
    ).sort(time_col)
    validation = df.filter(
        (pl.col(time_col) >= fold.val_start) & (pl.col(time_col) < fold.val_end)
    ).sort(time_col)
    test = df.filter(
        (pl.col(time_col) >= fold.test_start) & (pl.col(time_col) < fold.test_end)
    ).sort(time_col)
    return {"train": train, "validation": validation, "test": test}


def assert_folds_exclude_holdout(folds: list[WalkForwardFold], holdout_start: datetime) -> None:
    """Raise if any fold reaches into the frozen holdout (ADR 0003).

    Fails closed on purpose: a warning here would be trivial to ignore, and a
    single fold crossing the boundary silently invalidates the whole study.
    """
    for fold in folds:
        if fold.test_end > holdout_start:
            raise ValueError(
                f"Fold {fold.index} test_end {fold.test_end} enters the frozen holdout "
                f"({holdout_start}); development must never touch the holdout."
            )
