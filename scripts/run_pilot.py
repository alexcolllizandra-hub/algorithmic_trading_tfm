"""Run the pilot: every preregistered family, both assets, the full geometry.

The pilot answers one question -- does the whole pipeline run correctly for every
family? -- and deliberately does not answer whether any family is profitable. The
budget is far too small for that, and reading the pilot's winners as findings is
exactly the selection-on-the-pilot the protocol forbids.

Each family becomes one study directory with its own checkpoint, so an
interrupted pilot resumes per family without repeating completed units.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from perp_lab.config import Paths
from perp_lab.evaluation.multi_seed import analyse_study
from perp_lab.experiments.multi_seed import resolve_seeds, run_multi_seed
from perp_lab.search.config import load_search_config
from perp_lab.tracking.journal import atomic_write_json
from perp_lab.utils.logging import get_logger

FAMILIES = ("momentum", "volatility_breakout", "funding", "BTC_ETH_confirmation")
SYMBOLS = ("BTCUSDT", "ETHUSDT")

log = get_logger("perp_lab.pilot")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="artifacts/runs/pilot", type=Path)
    parser.add_argument("--n-seeds", default=1, type=int, help="Pilot may reduce seeds, not folds.")
    parser.add_argument("--base-seed", default=42, type=int)
    parser.add_argument("--families", default=",".join(FAMILIES))
    args = parser.parse_args()

    families = tuple(f.strip() for f in args.families.split(",") if f.strip())
    seeds = resolve_seeds(args.base_seed, args.n_seeds)
    root = Path(args.out)
    root.mkdir(parents=True, exist_ok=True)

    # Merge into any existing summary. Starting from an empty dict would erase
    # the families completed by an earlier invocation, and a pilot that reports
    # only its last run is not an audit of the pilot.
    summary_path = root / "pilot_summary.json"
    summary: dict[str, dict] = (
        json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.exists() else {}
    )
    for family in families:
        cfg = load_search_config(f"configs/search_pilot_{family}.yaml")
        started = time.time()
        log.info(
            "PILOT | family=%s | symbols=%s | seeds=%s | budget=%d",
            family,
            list(SYMBOLS),
            list(seeds),
            cfg.budget,
        )
        try:
            result = run_multi_seed(
                cfg,
                symbols=SYMBOLS,
                seeds=seeds,
                study_dir=root / family,
                paths=Paths(),
                logger=log,
            )
        except Exception as exc:
            log.exception("PILOT FAILED | family=%s", family)
            summary[family] = {"status": "failed", "error": repr(exc)}
            atomic_write_json(summary_path, summary)
            continue

        analysis = analyse_study(result.units)
        atomic_write_json(root / family / "multi_seed_analysis.json", analysis)
        budgets = {
            unit: {name: e.get("evaluated") for name, e in payload.get("engines", {}).items()}
            for unit, payload in result.units.items()
        }
        summary[family] = {
            "status": "completed",
            "study_id": result.study_id,
            "units": len(result.units),
            "budget_target": cfg.budget,
            "budget_spent": budgets,
            "elapsed_s": round(time.time() - started, 1),
        }
        atomic_write_json(summary_path, summary)
        log.info("PILOT OK | family=%s | %.1fs", family, time.time() - started)

    print(json.dumps(summary, indent=2)[:4000])
    failed = [f for f, p in summary.items() if p["status"] != "completed"]
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
