"""Run Gate R3 studies sequentially, with resume, robustness and audit.

The order is frozen in ``make_r3_configs.FAMILIES`` and does not depend on pilot
performance. Sequential execution avoids resource contention changing wall-clock
or starving one family while preserving deterministic numerical results.

Each family is checkpointed independently. Re-running this command resumes
completed units, then regenerates analysis/robustness and re-runs the isolation
audit. A failure stops the sequence; later families never conceal an earlier
process failure.

    uv run python scripts/run_r3_full.py
    uv run python scripts/run_r3_full.py --families breakout,mean_reversion
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

from make_r3_configs import EFFECTIVE_BUDGET, FAMILIES

SYMBOLS = "BTCUSDT,ETHUSDT"


def _run(args: list[str], *, capture: bool = False) -> subprocess.CompletedProcess[str]:
    print(f"\n$ {' '.join(args)}", flush=True)
    return subprocess.run(
        args,
        check=True,
        text=True,
        capture_output=capture,
    )


def _write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("artifacts/runs/r3_full_budget100_ga21"),
        help="A new root is used because both rejected preflight attempts are retained.",
    )
    parser.add_argument("--families", default=",".join(FAMILIES))
    parser.add_argument("--base-seed", type=int, default=42)
    parser.add_argument("--n-seeds", type=int, default=10)
    parser.add_argument("--resamples", type=int, default=500)
    args = parser.parse_args(argv)

    selected = tuple(f.strip() for f in args.families.split(",") if f.strip())
    unknown = sorted(set(selected) - set(FAMILIES))
    if unknown:
        raise SystemExit(f"Unknown R3 families: {unknown}; frozen order is {FAMILIES}")
    # User selection is a subset, but execution always follows preregistered order.
    families = tuple(f for f in FAMILIES if f in selected)

    args.root.mkdir(parents=True, exist_ok=True)
    rollup_path = args.root / "r3_execution.json"
    rollup: dict[str, Any] = {
        "started_at": datetime.now(UTC).isoformat(),
        "frozen_order": list(FAMILIES),
        "selected": list(families),
        "base_seed": args.base_seed,
        "n_seeds": args.n_seeds,
        "symbols": SYMBOLS.split(","),
        "effective_budget_per_fold_and_engine": EFFECTIVE_BUDGET,
        "families": {},
    }
    _write(rollup_path, rollup)

    for family in families:
        started = time.perf_counter()
        study_dir = args.root / family
        config = Path(f"configs/search_r3_{family}.yaml")
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
            {
                "status": "completed",
                "elapsed_seconds": round(time.perf_counter() - started, 1),
            }
        )
        _write(rollup_path, rollup)

    rollup["completed_at"] = datetime.now(UTC).isoformat()
    rollup["status"] = "completed"
    _write(rollup_path, rollup)

    _run([sys.executable, "scripts/summarise_r3_rollup.py", str(args.root)])
    print(f"\nR3 execution complete: {rollup_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
