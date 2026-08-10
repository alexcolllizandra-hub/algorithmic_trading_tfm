"""Close Gate R3 once all five family studies have finished.

Regenerates the cross-family rollup and writes a single gate verdict JSON.
Does not modify search artifacts or touch the holdout.

    uv run python scripts/finalize_r3_gate.py artifacts/runs/r3_full_budget100_ga21
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from make_r3_configs import FAMILIES


def _load(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "root", type=Path, default=Path("artifacts/runs/r3_full_budget100_ga21"), nargs="?"
    )
    args = parser.parse_args(argv)

    execution = _load(args.root / "r3_execution.json") or {}
    families_meta = execution.get("families", {})
    incomplete = [
        family for family in FAMILIES if families_meta.get(family, {}).get("status") != "completed"
    ]
    if incomplete:
        print(f"Gate R3 not ready: incomplete families {incomplete}")
        return 1

    subprocess.run(
        [sys.executable, "scripts/summarise_r3_rollup.py", str(args.root)],
        check=True,
    )
    rollup = _load(args.root / "r3_family_rollup.json") or {}
    summary = rollup.get("summary", {})
    promoted = summary.get("promoted", [])
    rejected = summary.get("rejected", [])

    verdict = {
        "gate": "R3",
        "closed_at": datetime.now(UTC).isoformat(),
        "root": str(args.root),
        "protocol": rollup.get("protocol"),
        "effective_budget_per_fold_and_engine": rollup.get("effective_budget_per_fold_and_engine"),
        "n_families": summary.get("n_families_total", len(FAMILIES)),
        "n_promoted": len(promoted),
        "n_rejected": len(rejected),
        "promoted_families": promoted,
        "rejected_families": rejected,
        "gate_status": "PASSED_WITH_SURVIVORS" if promoted else "CLOSED_NEGATIVE",
        "r4_required": bool(promoted),
        "note": (
            "All five families were evaluated under identical budget and geometry. "
            "Rejected families are recorded with evidence and are not retuned."
        ),
    }
    out = args.root / "r3_gate_verdict.json"
    out.write_text(json.dumps(verdict, indent=2) + "\n", encoding="utf-8")

    print(f"Gate R3 status : {verdict['gate_status']}")
    print(f"Promoted       : {promoted or 'none'}")
    print(f"Rejected       : {rejected}")
    print(f"R4 required    : {verdict['r4_required']}")
    print(f"Written        : {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
