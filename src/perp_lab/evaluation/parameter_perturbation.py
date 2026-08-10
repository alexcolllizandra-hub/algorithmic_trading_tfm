"""Parameter perturbation around frozen fold winners (Gate R4).

Re-scores already-selected winners on their **test** slices under small
parameter moves. Search is never re-run and validation is never re-opened.

    uv run python -m perp_lab.cli parameter-perturbation <run_dir> --config ...
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from perp_lab.backtesting.metrics import performance_metrics
from perp_lab.search.candidate import Candidate
from perp_lab.search.evaluator import CandidateEvaluator, build_folds_data, single_fold_bundle
from perp_lab.search.registry import build_search_space
from perp_lab.search.runner import _build_folds, _load_data, _load_reference_bars
from perp_lab.search.space import CategoricalParam, FloatParam, IntParam, SearchSpace
from perp_lab.utils.seeds import SeedScheduler


def load_fold_winners(run_dir: str | Path, method: str) -> list[dict[str, Any]]:
    path = Path(run_dir) / f"{method}_fold_winners.json"
    if not path.exists():
        raise FileNotFoundError(f"Missing fold winners: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError(f"Expected a list in {path}")
    return payload


def perturb_params(
    space: SearchSpace,
    base: dict[str, object],
    *,
    pct: float,
) -> list[dict[str, object]]:
    """Deterministic +/- ``pct`` neighbours for every active numeric parameter."""
    if pct <= 0:
        raise ValueError("pct must be positive.")

    base_active = space.active_params(base)
    variants: list[dict[str, object]] = []
    for param in space.params:
        if param.name not in base_active:
            continue
        current = base[param.name]
        for sign in (-1.0, 1.0):
            mutated = dict(base)
            if isinstance(param, IntParam):
                if not isinstance(current, int):
                    continue
                delta = max(1, round(abs(current) * pct))
                mutated[param.name] = current + int(sign * delta)
            elif isinstance(param, FloatParam):
                if not isinstance(current, (int, float)):
                    continue
                current_f = float(current)
                delta = abs(current_f) * pct
                if delta == 0.0:
                    delta = (param.high - param.low) * pct
                mutated[param.name] = current_f + sign * delta
            elif isinstance(param, CategoricalParam):
                choices = list(param.choices)
                if current not in choices:
                    continue
                idx = choices.index(current)
                step = max(1, round(len(choices) * pct))
                new_idx = int(min(max(idx + int(sign * step), 0), len(choices) - 1))
                if new_idx == idx:
                    continue
                mutated[param.name] = choices[new_idx]
            else:
                continue
            repaired = space.repair(mutated)
            valid, _ = space.is_valid(repaired)
            if not valid:
                continue
            if repaired != base:
                variants.append(repaired)
    # Stable order, drop duplicates after repair collapses neighbours.
    unique: list[dict[str, object]] = []
    seen: set[str] = set()
    for values in variants:
        key = space.candidate_hash(values)
        if key in seen:
            continue
        seen.add(key)
        unique.append(values)
    return unique


def _test_metrics(result, *, timeframe: str, days_per_year: int) -> dict[str, float]:
    net = result.ledger["net_return"].cast(float).to_numpy().astype(float)
    return performance_metrics(net, timeframe=timeframe, days_per_year=days_per_year)


def analyse_parameter_perturbation(
    run_dir: str | Path,
    method: str,
    *,
    search_config: Path,
    perturbation_pcts: tuple[float, ...] = (0.05, 0.10, 0.20),
) -> dict[str, Any]:
    """Re-score each frozen fold winner under parameter perturbations on test."""
    from perp_lab.config import Paths, load_data_contract, load_experiment_config
    from perp_lab.search.config import load_search_config
    from perp_lab.search.objective import ObjectiveConfig
    from perp_lab.utils.logging import get_logger

    run_dir = Path(run_dir)
    winners = load_fold_winners(run_dir, method)
    summary_path = run_dir / "comparison_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.exists() else {}

    cfg = load_search_config(search_config)
    exp = load_experiment_config(cfg.experiment_config)
    contract = load_data_contract(cfg.data_contract)
    paths = Paths()
    log = get_logger("parameter_perturbation")
    seed = int(summary.get("seed", cfg.seed or exp.random_seed))

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

    per_fold: list[dict[str, Any]] = []
    for winner in winners:
        fold_index = int(winner["fold"])
        params = winner.get("params") or {}
        if not params:
            continue
        nominal = winner.get("test_metrics") or {}
        fold_ev = CandidateEvaluator(
            single_fold_bundle(bundle, fold_index),
            space,
            timeframe=cfg.timeframe,
            fee_bps_per_side=exp.costs.fee_bps_per_side,
            slippage_bps_per_side=exp.costs.slippage.baseline_bps,
            days_per_year=exp.annualization_days,
            require_funding=cfg.require_funding,
            objective_cfg=objective_cfg,
            reference_bars=reference_bars,
        )
        candidate = Candidate.create(space, params, seed=seed, step=0)
        candidate.fold_index = fold_index
        nominal_result = fold_ev.evaluate_on_test(candidate, fold_index)
        nominal_metrics = _test_metrics(
            nominal_result, timeframe=cfg.timeframe, days_per_year=exp.annualization_days
        )

        perturb_rows: list[dict[str, Any]] = []
        for pct in perturbation_pcts:
            for perturbed in perturb_params(space, params, pct=pct):
                pert_candidate = Candidate.create(space, perturbed, seed=seed, step=0)
                pert_candidate.fold_index = fold_index
                result = fold_ev.evaluate_on_test(pert_candidate, fold_index)
                metrics = _test_metrics(
                    result, timeframe=cfg.timeframe, days_per_year=exp.annualization_days
                )
                perturb_rows.append(
                    {
                        "pct": pct,
                        "params": perturbed,
                        "candidate_id": pert_candidate.candidate_id,
                        "test_sharpe": metrics.get("sharpe"),
                        "test_total_return": metrics.get("total_return"),
                    }
                )

        sharpe_nom = float(nominal_metrics.get("sharpe", 0.0))
        pert_sharpes = [
            float(r["test_sharpe"]) for r in perturb_rows if r.get("test_sharpe") is not None
        ]
        same_sign = (
            bool(pert_sharpes) and all(s * sharpe_nom >= 0 for s in pert_sharpes if sharpe_nom != 0)
        ) or sharpe_nom == 0
        per_fold.append(
            {
                "fold": fold_index,
                "winner": winner.get("winner"),
                "nominal_params": params,
                "nominal_test": nominal_metrics,
                "recorded_test": nominal,
                "n_perturbations": len(perturb_rows),
                "perturbations": perturb_rows,
                "survives_perturbation": same_sign
                and all(float(r.get("test_total_return", -1.0)) > 0 for r in perturb_rows)
                if sharpe_nom > 0 and perturb_rows
                else None,
            }
        )

    return {
        "run_dir": str(run_dir),
        "method": method,
        "family": summary.get("family", cfg.family),
        "symbol": summary.get("symbol", cfg.symbol),
        "perturbation_pcts": list(perturbation_pcts),
        "n_folds": len(per_fold),
        "per_fold": per_fold,
        "method_note": (
            "Each perturbation re-scores the frozen fold winner on its own test slice "
            "only. Validation and search are not re-opened."
        ),
    }
