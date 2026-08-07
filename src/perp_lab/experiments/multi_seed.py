"""Multi-seed, multi-asset orchestration of the walk-forward search.

One seed tells you what one run of a stochastic search found. It cannot tell you
whether that finding is a property of the market or an accident of the random
number generator. This module runs the *same* frozen experiment across a list of
seeds and assets so the two can be told apart.

Three sources of variation are kept distinct, because conflating them is the
easiest way to overstate evidence:

* **Temporal (market) uncertainty** -- there is only ONE price history. It is
  quantified by bootstrapping the concatenated out-of-sample returns, once per
  selected result. Running ten seeds does not create ten independent histories.
* **Seed variability** -- the spread of outcomes across seeds on that same
  history. This measures the search's own instability, not additional evidence.
* **Fold variability** -- the spread across walk-forward folds within a run.

Work is checkpointed per (asset, seed) unit, so an interrupted study resumes
without repeating completed units and without ever evaluating one twice.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from perp_lab.config import Paths
from perp_lab.search.config import SearchRunConfig
from perp_lab.search.runner import SearchRunResult, run_search
from perp_lab.tracking.identity import build_identity, identity_record
from perp_lab.tracking.journal import Checkpoint, Journal, atomic_write_json
from perp_lab.tracking.run import generate_run_id, git_state
from perp_lab.utils.logging import get_logger
from perp_lab.utils.seeds import SeedScheduler

ENGINES = ("random_search", "genetic_algorithm")


def unit_key(symbol: str, seed: int) -> str:
    """Stable identity of one (asset, seed) work unit."""
    return f"{symbol}|seed={seed}"


def _poolable_payload(cfg: SearchRunConfig) -> dict[str, Any]:
    """The configuration minus the dimensions the study deliberately varies."""
    payload = cfg.model_dump(mode="json")
    for varying in ("seed", "symbol", "label"):
        payload.pop(varying, None)
    return payload


def config_fingerprint(cfg: SearchRunConfig) -> str:
    """Hash of everything that must be identical for results to be poolable.

    The per-run ``seed``, ``symbol`` and ``label`` are excluded: they are exactly
    the dimensions the study varies. Everything else -- family, geometry, budget,
    costs, objective, data contract -- must match, otherwise the units are not
    measuring the same thing and must not be aggregated.
    """
    text = json.dumps(_poolable_payload(cfg), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


@dataclass
class MultiSeedPlan:
    """The full grid of work units, resolved before anything is executed."""

    symbols: tuple[str, ...]
    seeds: tuple[int, ...]
    base_config: SearchRunConfig

    def units(self) -> list[tuple[str, int]]:
        return [(symbol, seed) for symbol in self.symbols for seed in self.seeds]

    def __len__(self) -> int:
        return len(self.symbols) * len(self.seeds)


@dataclass
class MultiSeedResult:
    study_id: str
    study_dir: Path
    plan: MultiSeedPlan
    units: dict[str, dict[str, Any]] = field(default_factory=dict)
    resumed: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "study_id": self.study_id,
            "study_dir": str(self.study_dir),
            "symbols": list(self.plan.symbols),
            "seeds": list(self.plan.seeds),
            "n_units": len(self.plan),
            "n_resumed": self.resumed,
            "units": self.units,
        }


def resolve_seeds(base_seed: int, n_seeds: int) -> tuple[int, ...]:
    """Derive ``n_seeds`` reproducible run seeds from one recorded base seed.

    Consecutive integers would be a defensible choice too, but deriving them
    through the scheduler keeps a single rule for every stream in the project and
    avoids any accidental structure between neighbouring runs.
    """
    scheduler = SeedScheduler(base_seed)
    return tuple(scheduler.stream("run_seed", index=i) % 1_000_000 for i in range(n_seeds))


def _unit_summary(result: SearchRunResult) -> dict[str, Any]:
    """The per-unit facts the aggregate analysis needs, without the bulk."""
    summary = result.summary
    methods = summary.get("methods", {})
    return {
        "run_id": result.run_id,
        "run_dir": str(result.run_dir) if result.run_dir else None,
        "n_folds": summary.get("n_folds"),
        "budget_parity": summary.get("budget_parity"),
        "seed_schedule": summary.get("seed_schedule"),
        "engines": {
            name: {
                "evaluated": methods[name]["counters"]["evaluated"],
                "n_feasible": methods[name]["n_feasible"],
                "best_val_fitness": methods[name]["best_fitness"],
                "aggregate_test": methods[name]["aggregate_test"],
            }
            for name in ENGINES
            if name in methods
        },
        "fold_winners": {
            name: [
                {
                    "fold": w["fold"],
                    "winner": w.get("winner"),
                    "val_sharpe": w.get("val_sharpe"),
                    "test_metrics": w.get("test_metrics"),
                }
                for w in winners
            ]
            for name, winners in result.fold_winners.items()
        },
    }


def run_multi_seed(
    base_config: SearchRunConfig,
    *,
    symbols: tuple[str, ...],
    seeds: tuple[int, ...],
    study_dir: str | Path | None = None,
    paths: Paths | None = None,
    resume: bool = True,
    repo_root: str | Path = ".",
    contract_payload: Any | None = None,
    dataset_hashes: dict[str, str] | None = None,
    logger: logging.Logger | None = None,
) -> MultiSeedResult:
    """Execute the grid of (asset, seed) runs with checkpointing and resume."""
    log = logger or get_logger("perp_lab.multi_seed")
    paths = paths or Paths()
    plan = MultiSeedPlan(symbols=symbols, seeds=seeds, base_config=base_config)

    study_path = (
        Path(study_dir)
        if study_dir is not None
        else Path(paths.runs_dir) / generate_run_id("multiseed")
    )
    study_path.mkdir(parents=True, exist_ok=True)
    study_id = study_path.name

    journal = Journal(study_path)
    checkpoint = Checkpoint(study_path)
    gs = git_state(repo_root)
    fingerprint = config_fingerprint(base_config)

    # A commit hash does not identify a run made on a dirty worktree, and almost
    # every development run is. The identity therefore also covers uncommitted
    # changes and untracked source files, so resuming can refuse a study whose
    # code changed even though nothing was committed.
    identity = build_identity(
        config_payload=_poolable_payload(base_config),
        contract_payload=contract_payload,
        dataset_hashes=dataset_hashes,
        repo_root=repo_root,
    )
    record = identity_record(identity, repo_root=repo_root)
    if record["provisional"]:
        log.warning(
            "PROVISIONAL RUN | executing uncommitted code (diff=%s untracked=%s); "
            "results are identified exactly but reproducible only from this working tree",
            identity.components["diff_sha256"],
            identity.components["untracked_sha256"],
        )

    # Resuming into a checkpoint built under a different configuration, contract,
    # dataset or code state would silently pool incomparable results.
    checkpoint.assert_compatible(
        config_fingerprint=fingerprint,
        git_commit=gs["commit"],
        run_identity=identity.fingerprint,
    )
    checkpoint.set_meta(
        study_id=study_id,
        config_fingerprint=fingerprint,
        run_identity=identity.fingerprint,
        identity_components=identity.components,
        provisional=record["provisional"],
        git_commit=gs["commit"],
        git_dirty=gs["dirty"],
        symbols=list(symbols),
        seeds=list(seeds),
        family=base_config.family,
        budget=base_config.budget,
    )
    atomic_write_json(study_path / "run_identity.json", record)

    units = plan.units()
    total = len(units)
    already = sum(1 for s, sd in units if checkpoint.is_done(unit_key(s, sd)))
    journal.event(
        "study_started",
        study_id=study_id,
        total_units=total,
        already_complete=already,
        symbols=list(symbols),
        seeds=list(seeds),
        config_fingerprint=fingerprint,
        git_commit=gs["commit"],
        git_dirty=gs["dirty"],
    )
    journal.status(state="running", completed=already, total=total, phase="search")

    completed = already
    results: dict[str, dict[str, Any]] = checkpoint.results() if resume else {}

    for symbol, seed in units:
        key = unit_key(symbol, seed)
        if resume and checkpoint.is_done(key):
            log.info("resume | skipping completed unit %s", key)
            journal.event("unit_skipped", unit=key, reason="already in checkpoint")
            continue

        cfg = base_config.model_copy(
            update={
                "symbol": symbol,
                "seed": seed,
                "label": f"{base_config.label}_{symbol}_seed{seed}",
            }
        )
        journal.event("unit_started", unit=key, symbol=symbol, seed=seed, budget=cfg.budget)
        log.info("unit %d/%d | %s", completed + 1, total, key)
        try:
            result = run_search(cfg, paths=paths, repo_root=repo_root, logger=log)
        except Exception as exc:
            journal.event("unit_failed", unit=key, error=repr(exc))
            journal.status(
                state="failed", completed=completed, total=total, phase="search", failed_unit=key
            )
            raise

        payload = {"symbol": symbol, "seed": seed, **_unit_summary(result)}
        checkpoint.mark_done(key, payload)
        results[key] = payload
        completed += 1
        journal.event(
            "unit_finished",
            unit=key,
            run_id=result.run_id,
            evaluated={n: v["evaluated"] for n, v in payload["engines"].items()},
        )
        journal.status(state="running", completed=completed, total=total, phase="search")

    journal.status(state="completed", completed=completed, total=total, phase="done")
    journal.event("study_finished", study_id=study_id, completed=completed, total=total)

    outcome = MultiSeedResult(
        study_id=study_id, study_dir=study_path, plan=plan, units=results, resumed=already
    )
    atomic_write_json(study_path / "study_manifest.json", outcome.to_dict())
    log.info("study complete | %s | %d units | dir=%s", study_id, completed, study_path)
    return outcome
