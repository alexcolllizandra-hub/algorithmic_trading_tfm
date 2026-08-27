"""Run the ``CRT_INTRADAY_V1`` studies sequentially, with resume, robustness and audit.

A direct analogue of ``run_r3_full.py``, pointed at the round's own configs. The
order is frozen in ``make_crt_configs.ordered_families`` and does not depend on
any pilot: the mirror pair ``pdl_reclaim_long`` / ``pdh_reclaim_short`` runs
first because one mechanism read in two directions is also the cheapest check
that the engine is not direction-biased.

Sequential execution keeps wall-clock and numerical results deterministic rather
than letting resource contention decide either. Each family is checkpointed
independently, so re-running resumes completed units, regenerates analysis and
robustness, and re-runs the isolation audit. A failure stops the sequence: a
later family must never conceal an earlier process failure.

Nothing here may promote anything. The reserved partition is consumed, so this
round produces evidence and not operational candidates -- see
``docs/methodology/crt_intraday.md`` section 6bis.

    uv run python scripts/run_crt_v1.py
    uv run python scripts/run_crt_v1.py --families pdl_reclaim_long,pdh_reclaim_short
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from make_crt_configs import EFFECTIVE_BUDGET, ordered_families

FAMILIES = ordered_families()
SYMBOLS = "BTCUSDT,ETHUSDT"


def _run(args: list[str], *, capture: bool = False) -> subprocess.CompletedProcess[str]:
    print(f"\n$ {' '.join(args)}", flush=True)
    return subprocess.run(args, check=True, text=True, capture_output=capture)


def _write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("artifacts/runs/crt_v1_budget100"))
    parser.add_argument("--families", default=",".join(FAMILIES))
    parser.add_argument("--base-seed", type=int, default=42)
    parser.add_argument("--n-seeds", type=int, default=10)
    parser.add_argument("--resamples", type=int, default=500)
    args = parser.parse_args(argv)

    selected = tuple(f.strip() for f in args.families.split(",") if f.strip())
    unknown = sorted(set(selected) - set(FAMILIES))
    if unknown:
        raise SystemExit(f"Unknown CRT families: {unknown}; frozen order is {FAMILIES}")
    # A user selection is a subset; execution always follows the preregistered order.
    families = tuple(f for f in FAMILIES if f in selected)

    args.root.mkdir(parents=True, exist_ok=True)
    rollup_path = args.root / "crt_v1_execution.json"
    rollup: dict[str, Any] = {
        "round": "CRT_INTRADAY_V1",
        "started_at": datetime.now(UTC).isoformat(),
        "frozen_order": list(FAMILIES),
        "selected": list(families),
        "base_seed": args.base_seed,
        "n_seeds": args.n_seeds,
        "symbols": SYMBOLS.split(","),
        "effective_budget_per_fold_and_engine": EFFECTIVE_BUDGET,
        "primary_engine": "random_search",
        "ga_role": "robustness cross-check only, never a discovery engine",
        "promotion_possible": False,
        "promotion_note": (
            "The reserved partition is consumed; no family in this round can be promoted. "
            "See docs/methodology/holdout_audit_status.md section 5.1."
        ),
        "families": {},
    }
    _write(rollup_path, rollup)

    for family in families:
        started = time.perf_counter()
        study_dir = args.root / family
        config = Path(f"configs/search_crt_v1_{family}.yaml")
        if not config.exists():
            raise SystemExit(f"Missing config {config}; run scripts/make_crt_configs.py first.")
        entry = rollup["families"].setdefault(family, {})
        entry.update({"status": "running", "study_dir": str(study_dir)})
        _write(rollup_path, rollup)
        try:
            _run(
                [
                    sys.executable,
                    "-m",
                    "perp_lab.cli",
                    "multi-seed",
                    "--config",
                    str(config),
                    "--symbols",
                    SYMBOLS,
                    "--n-seeds",
                    str(args.n_seeds),
                    "--base-seed",
                    str(args.base_seed),
                    "--study-dir",
                    str(study_dir),
                ]
            )
            _run(
                [
                    sys.executable,
                    "-m",
                    "perp_lab.cli",
                    "study-robustness",
                    str(study_dir),
                    "--experiment-config",
                    "configs/experiment.yaml",
                    "--resamples",
                    str(args.resamples),
                ]
            )
            _run([sys.executable, "scripts/audit_study_isolation.py", str(study_dir)])
            summary = _run(
                [sys.executable, "scripts/summarise_multiseed.py", str(study_dir)],
                capture=True,
            ).stdout
            (study_dir / "headline_summary.txt").write_text(summary, encoding="utf-8")
        except subprocess.CalledProcessError as exc:
            entry.update(
                {
                    "status": "failed",
                    "failed_command": exc.cmd,
                    "returncode": exc.returncode,
                    "elapsed_seconds": round(time.perf_counter() - started, 1),
                }
            )
            _write(rollup_path, rollup)
            raise
        entry.update(
            {"status": "completed", "elapsed_seconds": round(time.perf_counter() - started, 1)}
        )
        _write(rollup_path, rollup)

    rollup["completed_at"] = datetime.now(UTC).isoformat()
    rollup["status"] = "completed"
    _write(rollup_path, rollup)
    print(f"\nCRT_INTRADAY_V1 execution complete: {rollup_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
