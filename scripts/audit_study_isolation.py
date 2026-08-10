"""Audit every completed run in a multi-seed study against ADR 0012.

This is the study-level companion to ``audit_fold_isolation.py``. It proves that
full seed coverage is not hiding one unit produced under a different protocol or
with unequal per-fold budgets.

    uv run python scripts/audit_study_isolation.py artifacts/runs/<study>
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from audit_fold_isolation import audit


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("study_dir", type=Path)
    args = parser.parse_args(argv)

    checkpoint = json.loads((args.study_dir / "checkpoint.json").read_text(encoding="utf-8"))
    units = checkpoint.get("units", {})
    expected = len(checkpoint.get("meta", {}).get("symbols", [])) * len(
        checkpoint.get("meta", {}).get("seeds", [])
    )
    if len(units) != expected:
        print(f"FAILED: checkpoint contains {len(units)} of {expected} planned units")
        return 1

    failures: dict[str, list[str]] = {}
    for key, unit in sorted(units.items()):
        run_dir = Path(unit["run_dir"])
        print(f"\n[{key}]")
        problems = audit(run_dir)
        if problems:
            failures[key] = problems

    print(f"\nAudited {len(units)} runs; failures: {len(failures)}")
    if failures:
        for key, problems in failures.items():
            print(f"  {key}: {'; '.join(problems)}")
        return 1
    print("study fold-isolation audit: PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
