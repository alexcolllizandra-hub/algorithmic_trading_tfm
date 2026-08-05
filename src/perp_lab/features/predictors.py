"""Predictor-row snapshots for future meta-labeling (Chapter 5.6, prepared only).

Meta-labeling will later learn whether a *primary* strategy signal is worth
taking. Its predictor row must be the snapshot of causal features available **at
the moment the signal is generated** -- i.e. at the close of the signal bar --
and its (future) target will come from a triple-barrier outcome that is **not**
implemented in this phase.

This module builds that predictor snapshot while keeping four distinct time
stamps explicitly separated so no later step can confuse them:

* ``feature_time``   -- close of the bar whose features are used (== signal bar).
* ``signal_time``    -- when the primary signal is decided (== ``feature_time``).
* ``execution_time`` -- when the position is actually taken: the open of the
  next bar (next-bar execution).
* ``label_time``     -- when a triple-barrier label would resolve. **Left null**
  here on purpose; produced only once labeling is implemented.

No triple-barrier logic, no model training, no future information: this is a
pure, causal reshaping of already-built feature and signal frames.
"""

from __future__ import annotations

from collections.abc import Sequence

import polars as pl

from perp_lab.strategies.base import SIDE_COL

FEATURE_TIME = "feature_time"
SIGNAL_TIME = "signal_time"
EXECUTION_TIME = "execution_time"
LABEL_TIME = "label_time"


def build_predictor_rows(
    features: pl.DataFrame,
    signals: pl.DataFrame,
    *,
    feature_columns: Sequence[str],
    time_col: str = "open_time",
    events_only: bool = False,
) -> pl.DataFrame:
    """Assemble causal predictor rows aligned to primary signals.

    Parameters
    ----------
    features:
        Causal feature frame containing ``time_col`` and ``feature_columns``.
    signals:
        Strategy output containing ``time_col`` and :data:`SIDE_COL` (the target
        position decided at each bar's close).
    feature_columns:
        Feature columns to snapshot into the predictor row.
    events_only:
        When ``True``, keep only bars where a *new* position is initiated or the
        side changes (the natural meta-labeling events); otherwise keep every
        bar. A flat-to-flat bar is never an event.

    Returns
    -------
    A frame with the four timestamp roles, the target ``side``, an ``is_event``
    flag and the snapshot feature columns. ``label_time`` is null (labeling is
    not implemented in this phase).
    """
    missing = [c for c in feature_columns if c not in features.columns]
    if missing:
        raise ValueError(f"features frame is missing columns {missing}.")
    if SIDE_COL not in signals.columns:
        raise ValueError(f"signals frame must contain a {SIDE_COL!r} column.")

    feat = features.sort(time_col).select(time_col, *feature_columns)
    sig = signals.sort(time_col).select(time_col, SIDE_COL)
    joined = feat.join(sig, on=time_col, how="inner").sort(time_col)

    prev_side = pl.col(SIDE_COL).shift(1).fill_null(0)
    is_event = ((pl.col(SIDE_COL) != prev_side) & (pl.col(SIDE_COL) != 0)).alias("is_event")

    out = joined.with_columns(
        pl.col(time_col).alias(FEATURE_TIME),
        pl.col(time_col).alias(SIGNAL_TIME),
        pl.col(time_col).shift(-1).alias(EXECUTION_TIME),
        pl.lit(None, dtype=pl.Datetime(time_unit="ms", time_zone="UTC")).alias(LABEL_TIME),
        is_event,
    )
    ordered = out.select(
        FEATURE_TIME,
        SIGNAL_TIME,
        EXECUTION_TIME,
        LABEL_TIME,
        SIDE_COL,
        "is_event",
        *feature_columns,
    )
    if events_only:
        ordered = ordered.filter(pl.col("is_event"))
    return ordered
