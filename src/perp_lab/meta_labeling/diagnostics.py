"""Explanation, drift and economic diagnostics for the meta-label layer.

Three questions are kept apart on purpose, because passing one says nothing
about the others:

1. **What is the model using?** — permutation importance and SHAP. Both are
   descriptive. A feature can dominate the explanation and still add no money.
2. **Is the model still looking at the same world?** — drift. A meta-label is
   fitted on one period and applied to a later one; if the feature distribution
   has moved, the calibrated probabilities are no longer the probabilities that
   were calibrated.
3. **Does it pay?** — the economic comparison. This is the only one that may
   justify keeping a meta-label. The frozen contract in ADR 0016 forbids
   selecting a model on AUC alone: a filter that improves discrimination while
   destroying net return is rejected.

Every function here reads validation data at most. None takes a test or holdout
argument.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

import numpy as np
import polars as pl
from sklearn.inspection import permutation_importance

# The meta-label may scale a position but never reverse it. These are the frozen
# outer bounds; a configuration may narrow them, never widen them.
MIN_POSITION_SCALE = 0.0
MAX_POSITION_SCALE = 1.5


def permutation_importance_scores(
    model: Any,
    features: np.ndarray,
    labels: np.ndarray,
    feature_names: tuple[str, ...],
    *,
    seed: int,
    n_repeats: int = 20,
    scoring: str = "roc_auc",
) -> pl.DataFrame:
    """Drop in ``scoring`` when each feature is shuffled, on validation data.

    Permutation importance is model agnostic and measures what the *fitted*
    model actually relies on, which is what we want to audit. It is computed on
    validation rather than train, where an overfitted model would report
    importance for noise it merely memorised.

    Correlated features share credit and each will look weak alone; a low score
    is therefore not evidence that a feature is useless.
    """
    x = np.asarray(features, dtype=float)
    y = np.asarray(labels).astype(int).ravel()
    if x.shape[0] != y.size:
        raise ValueError("features and labels disagree on the number of events.")
    if x.shape[1] != len(feature_names):
        raise ValueError(
            f"{x.shape[1]} feature columns but {len(feature_names)} names were supplied."
        )
    if n_repeats < 1:
        raise ValueError("n_repeats must be at least 1.")

    # A single scoring name yields one Bunch; the dict return type only applies
    # when several are requested, which this signature does not allow.
    result = cast(
        Any,
        permutation_importance(
            model, x, y, scoring=scoring, n_repeats=n_repeats, random_state=seed, n_jobs=1
        ),
    )
    return (
        pl.DataFrame(
            {
                "feature": list(feature_names),
                "importance_mean": np.asarray(result.importances_mean, dtype=float),
                "importance_std": np.asarray(result.importances_std, dtype=float),
            }
        )
        .sort("importance_mean", descending=True)
        .with_columns(pl.lit(scoring).alias("scoring"), pl.lit(n_repeats).alias("n_repeats"))
    )


def population_stability_index(
    reference: np.ndarray, current: np.ndarray, *, n_bins: int = 10
) -> float:
    """PSI of ``current`` against ``reference``, using reference quantile bins.

    Bin edges come from the reference sample only, so the statistic answers
    "where did the later data fall, relative to what the model was fitted on".
    Empty bins are floored rather than dropped, because an emptied bin is
    precisely the kind of drift worth reporting and dropping it would hide it.

    Convention: below 0.1 is stable, 0.1 to 0.25 is moderate drift, above 0.25
    is severe. These are industry rules of thumb, not test statistics.
    """
    ref = np.asarray(reference, dtype=float).ravel()
    cur = np.asarray(current, dtype=float).ravel()
    if ref.size == 0 or cur.size == 0:
        raise ValueError("population_stability_index needs non-empty samples.")
    if n_bins < 2:
        raise ValueError("n_bins must be at least 2.")

    quantiles = np.linspace(0.0, 1.0, n_bins + 1)[1:-1]
    edges = np.unique(np.quantile(ref, quantiles))
    if edges.size == 0:
        # A constant reference cannot be binned; drift is then all-or-nothing.
        return 0.0 if np.all(cur == ref[0]) else float("inf")

    ref_counts = np.bincount(np.searchsorted(edges, ref, side="right"), minlength=edges.size + 1)
    cur_counts = np.bincount(np.searchsorted(edges, cur, side="right"), minlength=edges.size + 1)
    floor = 1e-6
    ref_share = np.maximum(ref_counts / ref.size, floor)
    cur_share = np.maximum(cur_counts / cur.size, floor)
    return float(np.sum((cur_share - ref_share) * np.log(cur_share / ref_share)))


def feature_drift(
    reference: np.ndarray,
    current: np.ndarray,
    feature_names: tuple[str, ...],
    *,
    n_bins: int = 10,
) -> pl.DataFrame:
    """Per-feature PSI and mean shift between two chronological blocks.

    ``reference`` is the earlier block (what the model learnt) and ``current``
    the later one (where it will be applied). The mean shift is expressed in
    reference standard deviations so features on different scales compare.
    """
    ref = np.asarray(reference, dtype=float)
    cur = np.asarray(current, dtype=float)
    if ref.ndim != 2 or cur.ndim != 2:
        raise ValueError("reference and current must both be two-dimensional.")
    if ref.shape[1] != cur.shape[1]:
        raise ValueError("reference and current must share the same feature columns.")
    if ref.shape[1] != len(feature_names):
        raise ValueError(
            f"{ref.shape[1]} feature columns but {len(feature_names)} names were supplied."
        )

    psi = [
        population_stability_index(ref[:, j], cur[:, j], n_bins=n_bins) for j in range(ref.shape[1])
    ]
    ref_std = ref.std(axis=0)
    safe_std = np.where(ref_std > 0, ref_std, 1.0)
    shift = (cur.mean(axis=0) - ref.mean(axis=0)) / safe_std
    return pl.DataFrame(
        {
            "feature": list(feature_names),
            "psi": np.asarray(psi, dtype=float),
            "mean_shift_in_reference_sd": shift.astype(float),
            "severe_drift": np.asarray(psi, dtype=float) > 0.25,
        }
    ).sort("psi", descending=True)


def meta_position_scale(
    probability: np.ndarray,
    *,
    threshold: float,
    min_scale: float = 0.5,
    max_scale: float = 1.0,
) -> np.ndarray:
    """Map meta-label probabilities to a non-negative position multiplier.

    Below ``threshold`` the trade is refused and the multiplier is exactly zero.
    Above it, confidence is mapped linearly onto ``[min_scale, max_scale]``.

    The multiplier is never negative, so the meta-label can veto or resize a
    trade but can never reverse the primary strategy's direction. That is the
    contract: direction comes from an interpretable rule, and the model only
    decides how much to believe it.
    """
    if not 0.0 < threshold < 1.0:
        raise ValueError("threshold must lie strictly inside (0, 1).")
    if not MIN_POSITION_SCALE <= min_scale <= max_scale <= MAX_POSITION_SCALE:
        raise ValueError(
            f"scales must satisfy {MIN_POSITION_SCALE} <= min_scale <= max_scale "
            f"<= {MAX_POSITION_SCALE}; got min={min_scale}, max={max_scale}."
        )
    p = np.asarray(probability, dtype=float).ravel()
    if np.any((p < 0.0) | (p > 1.0)):
        raise ValueError("probabilities must lie in [0, 1].")

    span = 1.0 - threshold
    confidence = np.clip((p - threshold) / span, 0.0, 1.0) if span > 0 else np.zeros_like(p)
    scale = min_scale + confidence * (max_scale - min_scale)
    return np.where(p >= threshold, scale, 0.0)


@dataclass(frozen=True)
class EconomicComparison:
    """Net economics of the primary rule alone versus the rule plus its filter."""

    primary_net_return: float
    filtered_net_return: float
    primary_trades: int
    filtered_trades: int
    primary_hit_rate: float
    filtered_hit_rate: float
    return_delta: float
    trades_removed: int
    cost_saved: float
    meta_adds_value: bool

    def to_dict(self) -> dict[str, float | int | bool]:
        return {
            "primary_net_return": self.primary_net_return,
            "filtered_net_return": self.filtered_net_return,
            "primary_trades": self.primary_trades,
            "filtered_trades": self.filtered_trades,
            "primary_hit_rate": self.primary_hit_rate,
            "filtered_hit_rate": self.filtered_hit_rate,
            "return_delta": self.return_delta,
            "trades_removed": self.trades_removed,
            "cost_saved": self.cost_saved,
            "meta_adds_value": self.meta_adds_value,
        }


def compare_primary_and_meta(
    trade_returns: np.ndarray,
    probability: np.ndarray,
    *,
    threshold: float,
    cost_per_trade: float = 0.0,
    min_scale: float = 1.0,
    max_scale: float = 1.0,
) -> EconomicComparison:
    """Compare ``primary_only`` against ``primary_plus_meta_labeling``.

    ``trade_returns`` are the net returns the primary strategy would have earned
    on each of its own signals, before the filter. The filtered arm scales each
    by :func:`meta_position_scale` and saves ``cost_per_trade`` on every trade it
    declines to take.

    ``meta_adds_value`` is the gate the frozen contract cares about: it is true
    only when the filter raises **net return**. A filter that improves AUC, hit
    rate or Sharpe while lowering net return does not qualify, which is why the
    flag is not derived from any classification metric.
    """
    r = np.asarray(trade_returns, dtype=float).ravel()
    p = np.asarray(probability, dtype=float).ravel()
    if r.size != p.size:
        raise ValueError("trade_returns and probability disagree on the number of trades.")
    if r.size == 0:
        raise ValueError("compare_primary_and_meta needs at least one trade.")
    if cost_per_trade < 0.0:
        raise ValueError("cost_per_trade must be non-negative.")

    scale = meta_position_scale(p, threshold=threshold, min_scale=min_scale, max_scale=max_scale)
    taken = scale > 0.0

    primary_total = float(r.sum())
    filtered_total = float(np.sum(r * scale))
    removed = int((~taken).sum())
    cost_saved = float(removed * cost_per_trade)

    primary_hits = float((r > 0).mean())
    filtered_hits = float((r[taken] > 0).mean()) if taken.any() else 0.0

    return EconomicComparison(
        primary_net_return=primary_total,
        filtered_net_return=filtered_total + cost_saved,
        primary_trades=int(r.size),
        filtered_trades=int(taken.sum()),
        primary_hit_rate=primary_hits,
        filtered_hit_rate=filtered_hits,
        return_delta=filtered_total + cost_saved - primary_total,
        trades_removed=removed,
        cost_saved=cost_saved,
        meta_adds_value=bool(filtered_total + cost_saved > primary_total),
    )
