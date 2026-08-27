"""EXPLORATORY: does any rejected family work in only part of the state space?

The gates judged each family on its whole out-of-sample record. A family can be
flat overall and still be doing something in a corner of the state space -- only
when volatility is high, say, or only while the market trends. This module asks
that one question of the families the study already rejected. It adds no family,
changes no parameter, and promotes nothing.

**Everything here is a generated hypothesis, not a validated result.** Slicing a
flat record into regimes is exactly how a researcher manufactures a false
positive: with enough slices something always looks good. Two safeguards keep
that constraint. The regime labels are causal, so no slice is defined using
information the strategy could not have had; and the whole block is corrected for
multiplicity within itself, over every family-by-regime cell at once.

Two state dimensions are used, and they come from different places for a reason:

* **Volatility** reuses the ``regime``/``regime_id`` labels already carried by
  the persisted ledgers. Those come from a threshold model fitted on each fold's
  *training* slice only, so they are causal by construction.
* **Trend** is taken from ``eda.regimes.tag_trend_volatility_regimes``, but only
  its ``trend_regime`` output -- price against its own trailing moving average,
  which looks strictly backwards. That function's volatility buckets are computed
  from full-sample quantiles and are therefore **deliberately not used here**:
  they are fine for describing a market, but a slice defined with future
  information cannot be allowed to inform a candidate for the holdout.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import polars as pl

from perp_lab.backtesting.metrics import bars_per_year
from perp_lab.eda.regimes import tag_trend_volatility_regimes
from perp_lab.eda.returns import add_log_returns
from perp_lab.evaluation.multiple_testing import (
    benjamini_hochberg_correction,
    holm_bonferroni,
)
from perp_lab.reporting.study_closure import (
    ALPHA,
    BOOTSTRAP_SEED,
    PRIMARY_ENGINE,
    TIMEFRAME,
    StudyUnit,
    _bootstrap_p_value,
)

#: A cell smaller than this cannot support a claim, so it is reported and then
#: excluded from the corrected family of tests rather than quietly kept.
MIN_CELL_BARS = 500

TREND_WINDOW = 96


@dataclass(frozen=True)
class RegimeCell:
    """One family's out-of-sample record inside one market state."""

    family: str
    gate: str
    dimension: str
    regime: str
    n_bars: int
    share_of_bars: float
    mean_bar_return: float
    total_return: float
    sharpe_annualised: float
    p_value: float | None

    @property
    def testable(self) -> bool:
        return self.p_value is not None

    def to_dict(self) -> dict[str, Any]:
        return {
            "family": self.family,
            "gate": self.gate,
            "dimension": self.dimension,
            "regime": self.regime,
            "n_bars": self.n_bars,
            "share_of_bars": self.share_of_bars,
            "mean_bar_return": self.mean_bar_return,
            "total_return": self.total_return,
            "sharpe_annualised": self.sharpe_annualised,
            "p_value": self.p_value,
        }


def _unit_ledger_with_regime(run_dir: Path, engine: str) -> pl.DataFrame:
    """Per-bar out-of-sample returns with the fold's train-fitted regime label."""
    paths = sorted(run_dir.glob(f"{engine}_fold*_test_equity.parquet"))
    if not paths:
        return pl.DataFrame(
            schema={
                "open_time": pl.Datetime("ms", "UTC"),
                "net_return": pl.Float64,
                "regime": pl.String,
            }
        )
    frames: list[pl.DataFrame] = []
    for path in paths:
        frame = pl.read_parquet(path)
        if "regime" not in frame.columns:
            continue
        frames.append(
            frame.select(
                "open_time",
                pl.col("net_return").cast(pl.Float64),
                pl.col("regime").cast(pl.String),
            )
        )
    if not frames:
        return pl.DataFrame(
            schema={
                "open_time": pl.Datetime("ms", "UTC"),
                "net_return": pl.Float64,
                "regime": pl.String,
            }
        )
    return pl.concat(frames).sort("open_time")


def family_regime_series(
    units: list[StudyUnit], *, symbol: str, engine: str = PRIMARY_ENGINE
) -> dict[str, pl.DataFrame]:
    """Per family, the seed-averaged return series with its volatility regime.

    Seeds are averaged as in the study-level accounting. A bar's regime is the
    label the folds agree on; seeds share the fold geometry and the regime model
    is fitted on the fold's training slice, so the label does not depend on which
    seed the search happened to start from.
    """
    out: dict[str, pl.DataFrame] = {}
    for family in sorted({u.family for u in units}):
        selected = [
            u for u in units if u.family == family and u.symbol == symbol and u.engine == engine
        ]
        frames = [_unit_ledger_with_regime(u.run_dir, engine) for u in selected]
        frames = [f for f in frames if f.height > 0]
        if not frames:
            continue
        out[family] = (
            pl.concat(frames)
            .group_by("open_time")
            .agg(
                pl.col("net_return").mean(),
                pl.col("regime").first(),
            )
            .sort("open_time")
        )
    return out


def causal_trend_labels(bars: pl.DataFrame, *, window: int = TREND_WINDOW) -> pl.DataFrame:
    """``open_time`` -> ``trend_regime`` (up / down / flat), from past data only.

    Delegates to the EDA tagger and keeps only its trend output, which compares
    the close with its own trailing moving average. The tagger's volatility
    buckets are not returned: those use full-sample quantiles and would leak.
    """
    tagged = tag_trend_volatility_regimes(
        add_log_returns(bars.sort("open_time")),
        trend_window=window,
        vol_window=window,
    )
    return tagged.select("open_time", "trend_regime")


def _cell(
    family: str, gate: str, dimension: str, regime: str, returns: np.ndarray, total_bars: int
) -> RegimeCell:
    scale = float(np.sqrt(bars_per_year(TIMEFRAME)))
    std = float(returns.std(ddof=1)) if returns.size > 1 else 0.0
    sharpe = float(returns.mean() / std) if std > 0 else 0.0
    testable = returns.size >= MIN_CELL_BARS
    return RegimeCell(
        family=family,
        gate=gate,
        dimension=dimension,
        regime=regime,
        n_bars=int(returns.size),
        share_of_bars=float(returns.size / total_bars) if total_bars else 0.0,
        mean_bar_return=float(returns.mean()) if returns.size else 0.0,
        total_return=float(np.prod(1.0 + returns) - 1.0) if returns.size else 0.0,
        sharpe_annualised=sharpe * scale,
        p_value=_bootstrap_p_value(returns, seed=BOOTSTRAP_SEED) if testable else None,
    )


def regime_cells(
    series: dict[str, pl.DataFrame],
    gates: dict[str, str],
    *,
    trend: pl.DataFrame | None = None,
) -> list[RegimeCell]:
    """Every family-by-regime cell, on both state dimensions."""
    cells: list[RegimeCell] = []
    for family, frame in series.items():
        gate = gates.get(family, "?")
        working = frame
        if trend is not None:
            working = working.join(trend, on="open_time", how="left")
        total = working.height
        dimensions = [("volatility", "regime")]
        if trend is not None:
            dimensions.append(("trend", "trend_regime"))
        for dimension, column in dimensions:
            if column not in working.columns:
                continue
            for label in sorted(working[column].drop_nulls().unique().to_list()):
                subset = working.filter(pl.col(column) == label)
                returns = subset["net_return"].cast(pl.Float64).to_numpy().astype(float)
                returns = returns[np.isfinite(returns)]
                if returns.size == 0:
                    continue
                cells.append(_cell(family, gate, dimension, str(label), returns, total))
    return cells


def correct_within_block(cells: list[RegimeCell]) -> dict[str, Any]:
    """Correct the whole exploratory block for multiplicity, within itself.

    Conditioning multiplies the tests: thirteen families across several states is
    a far larger family of hypotheses than thirteen families alone. Correcting
    inside this block is what stops the slicing from producing the discovery it
    was designed to look for. The block is corrected on its own and is **not**
    merged with the study-level count, which answered a different question.
    """
    testable = [c for c in cells if c.testable]
    labels = [f"{c.family}|{c.dimension}|{c.regime}" for c in testable]
    p_values = [c.p_value for c in testable if c.p_value is not None]

    holm = holm_bonferroni(p_values, alpha=ALPHA)
    bh = benjamini_hochberg_correction(p_values, alpha=ALPHA)

    survivors = [labels[i] for i, flag in enumerate(bh.rejected) if flag]
    return {
        "alpha": ALPHA,
        "n_cells": len(cells),
        "n_testable_cells": len(testable),
        "n_excluded_small_cells": len(cells) - len(testable),
        "min_cell_bars": MIN_CELL_BARS,
        "holm_bonferroni": {
            "n_rejected": holm.n_rejected,
            "adjusted_p_values": dict(zip(labels, holm.adjusted_p_values, strict=True)),
        },
        "benjamini_hochberg": {
            "n_rejected": bh.n_rejected,
            "adjusted_p_values": dict(zip(labels, bh.adjusted_p_values, strict=True)),
        },
        "survivors": survivors,
    }


def best_conditional_candidate(
    cells: list[RegimeCell], correction: dict[str, Any]
) -> dict[str, Any] | None:
    """The one conditional cell, if any, that survived correction within the block.

    Returned so the holdout selection rule can consider it. If nothing survives,
    ``None`` is returned and the rule falls back to the unconditional winner --
    which is the expected outcome and must not be worked around.
    """
    survivors = correction["survivors"]
    if not survivors:
        return None
    by_label = {f"{c.family}|{c.dimension}|{c.regime}": c for c in cells}
    best = max(survivors, key=lambda label: by_label[label].sharpe_annualised)
    cell = by_label[best]
    return {
        "label": best,
        **cell.to_dict(),
        "adjusted_p_value": correction["benjamini_hochberg"]["adjusted_p_values"][best],
    }
