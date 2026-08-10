"""Measure the wall-clock cost of the per-outer-fold protocol against the old one.

ADR 0012 originally claimed the corrected protocol costs "roughly fifteen times
the search work". That is true in *unique evaluations* and false in *compute*,
and the difference decides whether the study geometry has to shrink:

* superseded protocol: one evaluation backtests EVERY fold's validation slice, so
  a budget of B costs B x F backtests;
* current protocol: one evaluation backtests ONE fold, and the budget is spent in
  every fold, so the run costs B x F backtests as well.

The theoretical backtest count is therefore equivalent at the same per-fold
budget. Wall-clock can still differ through per-evaluator caches, strategy
construction, fold-setup overhead and the GA's own bookkeeping, so this script
measures it rather than asserting it.

Both arms share ONE pre-built bundle, so feature construction, regime fitting and
data loading are excluded from the comparison; what is timed is exactly the part
the protocol changed.

    uv run python scripts/benchmark_protocol_cost.py --config configs/search_pilot_momentum.yaml
    uv run python scripts/benchmark_protocol_cost.py --candidates 10 --synthetic
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

import numpy as np

from perp_lab.config import Paths, load_data_contract, load_experiment_config
from perp_lab.search.candidate import Candidate
from perp_lab.search.config import load_search_config
from perp_lab.search.evaluator import CandidateEvaluator, build_folds_data, single_fold_bundle
from perp_lab.search.objective import ObjectiveConfig
from perp_lab.search.registry import build_search_space
from perp_lab.search.runner import _build_folds, _load_data, _load_reference_bars
from perp_lab.utils.logging import get_logger
from perp_lab.utils.seeds import SeedScheduler


def _sample(space, n: int, seed: int) -> list[Candidate]:
    """A fixed candidate list, so both arms evaluate identical work."""
    rng = np.random.default_rng(seed)
    out: list[Candidate] = []
    seen: set[str] = set()
    for _ in range(n * 400):
        if len(out) >= n:
            break
        values = space.sample(rng)
        if not space.is_valid(values)[0]:
            continue
        cid = space.candidate_hash(values)
        if cid in seen:
            continue
        seen.add(cid)
        out.append(Candidate.create(space, values, seed=seed, step=len(out)))
    if len(out) < n:
        raise SystemExit(f"space yielded only {len(out)} of {n} unique valid candidates")
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/search_pilot_momentum.yaml", type=Path)
    parser.add_argument(
        "--candidates",
        type=int,
        default=12,
        help="candidates per fold; cost scales linearly, the ratio does not",
    )
    parser.add_argument("--out", type=Path, default=Path("reports/tables/protocol_cost.json"))
    args = parser.parse_args(argv)

    log = get_logger("benchmark")
    cfg = load_search_config(args.config)
    exp = load_experiment_config(cfg.experiment_config)
    contract = load_data_contract(cfg.data_contract)
    paths = Paths()
    seed = cfg.seed if cfg.seed is not None else exp.random_seed

    frame, funding, holdout_start, _ = _load_data(cfg, exp, contract, paths, seed=seed, log=log)
    folds = _build_folds(cfg, exp, frame, holdout_start)
    reference_bars = _load_reference_bars(cfg, exp, contract, paths, seed=seed, log=log)
    seeds = SeedScheduler(seed)

    bundle = build_folds_data(
        frame,
        folds,
        exp=exp,
        family=cfg.family,
        symbol=cfg.symbol,
        timeframe=cfg.timeframe,
        regime_model=cfg.regime_model,
        seed=seeds.stream("regime_base", symbol=cfg.symbol, timeframe=cfg.timeframe),
        funding=funding,
        holdout_start=holdout_start,
        seeds=seeds,
        reference_bars=reference_bars,
        reference_symbol=exp.strategies.families.cross_asset.reference_symbol.get(cfg.symbol),
    )
    space = build_search_space(exp, cfg.family, cfg.symbol)
    objective_cfg = ObjectiveConfig.from_experiment(exp, require_funding=cfg.require_funding)
    n_folds = len(bundle.folds)

    def evaluator(b) -> CandidateEvaluator:
        return CandidateEvaluator(
            b,
            space,
            timeframe=cfg.timeframe,
            fee_bps_per_side=exp.costs.fee_bps_per_side,
            slippage_bps_per_side=exp.costs.slippage.baseline_bps,
            days_per_year=exp.annualization_days,
            require_funding=cfg.require_funding,
            objective_cfg=objective_cfg,
            reference_bars=reference_bars,
        )

    n = args.candidates
    print(f"family={cfg.family} symbol={cfg.symbol} folds={n_folds} candidates/fold={n}")

    # Superseded protocol: n evaluations, each backtesting every fold's validation.
    started = time.perf_counter()
    old_ev = evaluator(bundle)
    for candidate in _sample(space, n, seed=1):
        old_ev.evaluate(candidate)
    old_seconds = time.perf_counter() - started
    old_backtests = n * n_folds

    # Current protocol: n evaluations INSIDE EACH fold, one backtest apiece.
    started = time.perf_counter()
    new_backtests = 0
    for fd in bundle.folds:
        fold_ev = evaluator(single_fold_bundle(bundle, fd.index))
        for candidate in _sample(space, n, seed=1):
            fold_ev.evaluate(candidate)
            new_backtests += 1
    new_seconds = time.perf_counter() - started

    payload: dict[str, Any] = {
        "config": str(args.config),
        "family": cfg.family,
        "symbol": cfg.symbol,
        "n_folds": n_folds,
        "candidates_per_fold": n,
        "superseded_protocol": {
            "name": "pooled_across_folds_contaminated",
            "unique_evaluations": n,
            "validation_backtests": old_backtests,
            "seconds": round(old_seconds, 3),
        },
        "current_protocol": {
            "name": "independent_search_per_outer_fold",
            "unique_evaluations": n * n_folds,
            "validation_backtests": new_backtests,
            "seconds": round(new_seconds, 3),
        },
        "backtest_ratio_new_over_old": round(new_backtests / old_backtests, 4),
        "wall_clock_ratio_new_over_old": round(new_seconds / old_seconds, 4),
        "note": (
            "Equal backtest counts at the same per-fold budget. Any wall-clock gap is "
            "overhead (evaluator setup, per-fold caches, strategy construction), not "
            "extra backtesting work."
        ),
    }
    print(json.dumps(payload, indent=2))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"written: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
