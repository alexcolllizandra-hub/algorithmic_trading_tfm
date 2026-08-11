"""Build the Gate S1-B development-pilot report from the persisted search runs.

Discovers the most recent `search_<family>_*` run directory for each S1 family
and writes the DEV-ONLY report to `reports/gate_s1b/`. Reads artifacts only; it
never loads market data and therefore never touches the frozen holdout.

    uv run python scripts/analyse_s1_pilot.py
"""

from __future__ import annotations

import json
from pathlib import Path

from perp_lab.reporting.s1_pilot import write_s1_pilot_report
from perp_lab.search.registry import S1_FAMILIES

RUNS_ROOT = Path("artifacts/runs")
OUTPUT_DIR = Path("reports/gate_s1b")
PILOT_LABEL_PREFIX = "s1b_pilot_"


def _latest_pilot_run(family: str) -> Path:
    """The newest S1-B pilot run for ``family``, identified by its config label.

    Matching on the label rather than on the directory name keeps an unrelated
    run of the same family -- a smoke test, or a later full study -- from being
    picked up as pilot evidence.
    """
    candidates: list[Path] = []
    for run_dir in sorted(RUNS_ROOT.glob(f"search_{family}_*")):
        summary = run_dir / "comparison_summary.json"
        if not summary.exists():
            continue
        label = json.loads(summary.read_text(encoding="utf-8")).get("label", "")
        if str(label).startswith(PILOT_LABEL_PREFIX):
            candidates.append(run_dir)
    if not candidates:
        raise SystemExit(
            f"No S1-B pilot run found for family {family!r}. Run:\n"
            f"  uv run perp-lab search --config configs/search_s1_pilot_{family}.yaml"
        )
    return candidates[-1]


def main() -> int:
    run_dirs = {family: _latest_pilot_run(family) for family in S1_FAMILIES}
    for family, run_dir in run_dirs.items():
        print(f"{family:26s} <- {run_dir}")
    written = write_s1_pilot_report(run_dirs, OUTPUT_DIR)
    for kind, path in written.items():
        print(f"wrote {kind}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
