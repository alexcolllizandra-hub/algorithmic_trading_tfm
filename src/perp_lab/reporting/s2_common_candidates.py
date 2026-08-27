"""PBO for Gate S2 via a common candidate set evaluated across contiguous blocks.

Why this module exists
----------------------
The S1-B report had to record the probability of backtest overfitting as
**unavailable**. CSCV needs one performance matrix of the *same* configurations
across all time blocks, but ADR 0012 makes the search independent per outer fold,
so no configuration is shared between folds and no such matrix exists.

This module builds the missing matrix explicitly and separately from the search:

1. draw a fixed number of unique valid configurations from the frozen search
   space with a fixed seed;
2. backtest every one of them once over the **whole development partition**, with
   the frozen costs, next-bar execution and funding;
3. slice the resulting per-bar net-return series into contiguous chronological
   blocks and record each configuration's Sharpe ratio per block.

The candidate set **selects nothing and promotes nothing**. Its only purpose is
to estimate how likely the selection procedure is to crown a configuration that
lands at or below the median out of sample. The design (candidate count, seed and
block count) is frozen in ``docs/roadmap/gate_s2_batch_01.md`` section 8 before
any S2 result existed.

Regime labels and the scored window
-----------------------------------
Part of the frozen search space is an optional regime gate, so the candidates
cannot be backtested on raw klines: they need a regime label. Fitting one regime
model over the whole development partition would label every bar with thresholds
estimated from data that includes that bar's own future, which rule 3 of the
research-integrity contract forbids even for a filter.

So the model is fitted **only on the first walk-forward fold's training window**
and applied forward. Every backtest still runs over the whole development
partition (warm-up included), but block Sharpes are measured strictly **after
that fitting window**, i.e. over exactly the span the walk-forward folds
evaluate. Inside the fitting window the labels would be in-sample, so those bars
are used to warm the rolling statistics up and contribute no performance number.

Development data only; the frozen holdout is never loaded.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

import numpy as np
import polars as pl

from perp_lab.backtesting.engine import run_backtest
from perp_lab.backtesting.metrics import bars_per_year
from perp_lab.config.experiment import ExperimentConfig
from perp_lab.evaluation.multiple_testing import probability_of_backtest_overfitting
from perp_lab.features.context import FeatureContext
from perp_lab.features.registry import build_feature_frame, feature_columns, resolve_feature_set
from perp_lab.features.spec import FeatureItemLike
from perp_lab.regimes.models import ThresholdRegime
from perp_lab.search.evaluator import _regime_feature_items, _select_regime_inputs
from perp_lab.search.registry import build_search_space
from perp_lab.search.space import ParamValue, SearchSpace
from perp_lab.strategies.base import Strategy
from perp_lab.validation.walk_forward import generate_walk_forward

# Frozen in gate_s2_batch_01.md section 8. Reproduced here, never adjusted.
N_CANDIDATES = 120
N_BLOCKS = 8
CANDIDATE_SEED = 2026
# Draws are capped so an unlucky space cannot spin forever looking for validity.
MAX_DRAWS_PER_CANDIDATE = 200


class CommonCandidateError(Exception):
    """Raised when the common candidate set cannot be built as specified."""


def sample_common_candidates(
    space: SearchSpace,
    *,
    n_candidates: int = N_CANDIDATES,
    seed: int = CANDIDATE_SEED,
) -> list[dict[str, ParamValue]]:
    """Draw ``n_candidates`` unique *valid* configurations deterministically.

    Duplicates are rejected on the space's canonical hash, so two draws that
    differ only in an inactive parameter count once -- the same rule the search
    engines use, which keeps this set comparable to what they explored.
    """
    if n_candidates < 2:
        raise CommonCandidateError("PBO needs at least two configurations to rank.")
    rng = np.random.default_rng(seed)
    chosen: list[dict[str, ParamValue]] = []
    seen: set[str] = set()
    budget = n_candidates * MAX_DRAWS_PER_CANDIDATE
    for _ in range(budget):
        if len(chosen) >= n_candidates:
            break
        values = space.sample(rng)
        values = space.repair(dict(values))
        if not space.is_valid(values)[0]:
            continue
        key = space.candidate_hash(values)
        if key in seen:
            continue
        seen.add(key)
        chosen.append(values)
    if len(chosen) < n_candidates:
        raise CommonCandidateError(
            f"only {len(chosen)} unique valid candidates found for {space.family!r} in "
            f"{budget} draws; the frozen PBO design asks for {n_candidates}."
        )
    return chosen


@dataclass(frozen=True)
class PboFrame:
    """A regime-labelled development frame plus the window that may be scored."""

    frame: pl.DataFrame
    scored_from: datetime
    regime_model: str
    regime_inputs: tuple[str, ...]
    regime_fit_start: datetime
    regime_fit_end: datetime

    def scored_mask(self) -> np.ndarray:
        """Boolean mask over ``frame`` rows whose regime label is out-of-sample."""
        return (self.frame["open_time"] >= self.scored_from).to_numpy().astype(bool)

    def to_dict(self) -> dict[str, Any]:
        return {
            "regime_model": self.regime_model,
            "regime_inputs": list(self.regime_inputs),
            "regime_fit_start": self.regime_fit_start.isoformat(),
            "regime_fit_end": self.regime_fit_end.isoformat(),
            "scored_from": self.scored_from.isoformat(),
            "bars_total": int(self.frame.height),
            "bars_scored": int(self.scored_mask().sum()),
        }


def build_pbo_frame(
    bars: pl.DataFrame,
    *,
    exp: ExperimentConfig,
    family: str,
    symbol: str,
    timeframe: str,
    funding: pl.DataFrame | None,
    holdout_start: datetime,
) -> PboFrame:
    """Attach causal regime labels to the development frame for PBO backtests.

    The regime model is the deterministic threshold model the S2-B pilots use,
    fitted on the **first** walk-forward fold's training window only. Bars from
    that window onwards keep their labels for warm-up but are excluded from
    scoring, so nothing measured here was labelled with its own future.
    """
    space = build_search_space(exp, family, symbol)
    requested: list[FeatureItemLike] = [*space.feature_items, *_regime_feature_items(exp)]
    context = FeatureContext(funding=funding)
    feats, resolved = build_feature_frame(
        bars, resolve_feature_set(requested), holdout_start=holdout_start, context=context
    )
    inputs = _select_regime_inputs(feature_columns(resolved))
    if not inputs:
        raise CommonCandidateError(
            f"{family}/{symbol}: no volatility proxy available to label regimes for PBO."
        )

    folds = generate_walk_forward(exp, strict=True)
    fit_start, fit_end = folds[0].train_start, folds[0].train_end
    train = feats.filter((pl.col("open_time") >= fit_start) & (pl.col("open_time") < fit_end))
    if train.height == 0:
        raise CommonCandidateError(
            f"{family}/{symbol}: the first fold's training window holds no bars."
        )
    model = ThresholdRegime(inputs=tuple(inputs), seed=exp.random_seed)
    model.fit(train)
    labelled = model.attach(feats)
    scored = labelled.filter(pl.col("open_time") >= fit_end)
    if scored.height < N_BLOCKS * 2:
        raise CommonCandidateError(
            f"{family}/{symbol}: only {scored.height} bars after the regime fitting "
            f"window; {N_BLOCKS} blocks cannot be formed."
        )
    return PboFrame(
        frame=labelled,
        scored_from=fit_end,
        regime_model="threshold",
        regime_inputs=tuple(inputs),
        regime_fit_start=fit_start,
        regime_fit_end=fit_end,
    )


def _block_sharpes(
    net_return: np.ndarray, *, n_blocks: int, timeframe: str, days_per_year: int
) -> np.ndarray | None:
    """Annualised Sharpe per contiguous chronological block, or ``None``.

    A block whose returns never move produces a zero Sharpe rather than a
    division by zero: a configuration that was flat for a whole block genuinely
    earned nothing there, which is different from being undefined.
    """
    if net_return.size < n_blocks * 2:
        return None
    scale = float(np.sqrt(bars_per_year(timeframe, days_per_year)))
    out: list[float] = []
    for chunk in np.array_split(net_return, n_blocks):
        std = float(np.std(chunk, ddof=1)) if chunk.size > 1 else 0.0
        out.append(float(np.mean(chunk) / std * scale) if std > 0 else 0.0)
    return np.asarray(out, dtype=float)


@dataclass(frozen=True)
class CommonCandidatePbo:
    """PBO for one family on one asset, from a common candidate set."""

    family: str
    symbol: str
    n_candidates_requested: int
    n_candidates_evaluated: int
    n_blocks: int
    candidate_seed: int
    development_bars: int
    scored_bars: int
    pbo: float
    n_splits: int
    median_block_sharpe: float
    best_candidate_block_sharpe: float
    regime: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "family": self.family,
            "symbol": self.symbol,
            "n_candidates_requested": self.n_candidates_requested,
            "n_candidates_evaluated": self.n_candidates_evaluated,
            "n_blocks": self.n_blocks,
            "candidate_seed": self.candidate_seed,
            "development_bars": self.development_bars,
            "scored_bars": self.scored_bars,
            "probability_of_backtest_overfitting": self.pbo,
            "n_splits": self.n_splits,
            "median_block_sharpe": self.median_block_sharpe,
            "best_candidate_block_sharpe": self.best_candidate_block_sharpe,
            "regime": self.regime,
        }


def common_candidate_pbo(
    exp: ExperimentConfig,
    *,
    family: str,
    symbol: str,
    bars: pl.DataFrame,
    funding: pl.DataFrame | None,
    timeframe: str,
    holdout_start: datetime,
    n_candidates: int = N_CANDIDATES,
    n_blocks: int = N_BLOCKS,
    seed: int = CANDIDATE_SEED,
) -> CommonCandidatePbo:
    """Build the CSCV matrix for one family/asset and return its PBO.

    ``bars`` must already be restricted to the development partition; this
    function does not slice it and would happily backtest whatever it is given,
    so the holdout guard belongs at the call site.
    """
    space = build_search_space(exp, family, symbol)
    candidates = sample_common_candidates(space, n_candidates=n_candidates, seed=seed)
    prepared = build_pbo_frame(
        bars,
        exp=exp,
        family=family,
        symbol=symbol,
        timeframe=timeframe,
        funding=funding,
        holdout_start=holdout_start,
    )
    frame = prepared.frame
    scored_bars = 0

    fee = exp.costs.fee_bps_per_side
    slippage = exp.costs.slippage.baseline_bps
    columns: list[np.ndarray] = []
    for values in candidates:
        strategy = space.build_fn(values)
        assert isinstance(strategy, Strategy)
        result = run_backtest(
            strategy.signals(frame),
            frame,
            timeframe=timeframe,
            fee_bps_per_side=fee,
            slippage_bps_per_side=slippage,
            days_per_year=exp.annualization_days,
            asset=symbol,
            funding=funding,
            require_funding=funding is not None,
        )
        # The ledger, not the input frame, defines the scored rows: the engine
        # drops bars it cannot price (next-bar execution needs a following bar),
        # so a mask built on the frame would be off by those rows.
        ledger = result.ledger.filter(pl.col("open_time") >= prepared.scored_from)
        scored_bars = ledger.height
        net = ledger["net_return"].fill_null(0.0).to_numpy().astype(float)
        net = np.nan_to_num(net, nan=0.0, posinf=0.0, neginf=0.0)
        block = _block_sharpes(
            net,
            n_blocks=n_blocks,
            timeframe=timeframe,
            days_per_year=exp.annualization_days,
        )
        if block is not None:
            columns.append(block)

    if len(columns) < 2:
        raise CommonCandidateError(
            f"{family}/{symbol}: fewer than two configurations produced a usable "
            "block series; PBO cannot be estimated."
        )

    matrix = np.column_stack(columns)
    result_pbo = probability_of_backtest_overfitting(matrix, n_partitions=n_blocks)
    return CommonCandidatePbo(
        family=family,
        symbol=symbol,
        n_candidates_requested=n_candidates,
        n_candidates_evaluated=matrix.shape[1],
        n_blocks=n_blocks,
        candidate_seed=seed,
        development_bars=bars.height,
        scored_bars=scored_bars,
        pbo=float(result_pbo.pbo),
        n_splits=int(result_pbo.n_splits),
        median_block_sharpe=float(np.median(matrix)),
        best_candidate_block_sharpe=float(np.max(matrix.mean(axis=0))),
        regime=prepared.to_dict(),
    )
