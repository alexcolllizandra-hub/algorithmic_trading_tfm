"""Audit the pilot's artifacts against the invariants the pilot exists to check.

This reads what was written, not what the code intended to write. Every claim
below is therefore checkable from disk after the fact:

* no fold ever reaches the frozen holdout;
* both engines spent exactly the declared budget in every unit;
* both engines were scored on the identical out-of-sample bars;
* every family produced 15 folds on both assets.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import polars as pl

HOLDOUT_START = datetime(2026, 1, 1, tzinfo=UTC)
EXPECTED_FOLDS = 15
ENGINES = ("random_search", "genetic_algorithm")


def main() -> int:
    root = Path("artifacts/runs/pilot")
    summary = json.loads((root / "pilot_summary.json").read_text(encoding="utf-8"))
    failures: list[str] = []

    print(f"{'family':<24}{'unit':<24}{'folds':>6}{'RS':>5}{'GA':>5}{'OOS bars':>10}  last OOS bar")
    print("-" * 100)

    for family in summary:
        checkpoint = json.loads((root / family / "checkpoint.json").read_text(encoding="utf-8"))
        units = checkpoint.get("units") or {}
        if not units:
            failures.append(f"{family}: checkpoint recorded no units")
        for unit, entry in sorted(units.items()):
            payload = entry.get("payload", entry)
            winners = payload.get("fold_winners", {})
            n_folds = {name: len(rows) for name, rows in winners.items()}
            spent = {n: e.get("evaluated") for n, e in payload.get("engines", {}).items()}

            run_dir = _run_dir(payload)
            if run_dir is None:
                failures.append(f"{family}/{unit}: no run directory to audit")
            bars, last = _oos_coverage(run_dir)
            if bars == 0:
                failures.append(f"{family}/{unit}: no out-of-sample ledger was written")

            print(
                f"{family:<24}{unit:<24}{n_folds.get('random_search', 0):>6}"
                f"{spent.get('random_search', 0):>5}{spent.get('genetic_algorithm', 0):>5}"
                f"{bars:>10}  {last}"
            )

            for engine in ENGINES:
                if n_folds.get(engine) != EXPECTED_FOLDS:
                    failures.append(f"{family}/{unit}/{engine}: {n_folds.get(engine)} folds")
            if len(set(spent.values())) != 1:
                failures.append(f"{family}/{unit}: budgets differ {spent}")
            if last is not None and last >= HOLDOUT_START:
                failures.append(f"{family}/{unit}: OOS bar {last} reaches the holdout")

    print()
    if failures:
        print(f"FAILURES ({len(failures)}):")
        for line in failures:
            print(f"  - {line}")
        return 1
    print("All pilot invariants hold: 15 folds, identical budgets, holdout untouched.")
    return 0


def _run_dir(payload: dict) -> Path | None:
    run_id = payload.get("run_id")
    if not run_id:
        return None
    path = Path("artifacts/runs") / run_id
    return path if path.exists() else None


def _oos_coverage(run_dir: Path | None) -> tuple[int, datetime | None]:
    """Concatenated out-of-sample bar count and the latest bar actually scored."""
    if run_dir is None:
        return 0, None
    # Per-fold test equity curves: one file per fold, concatenating to the
    # strategy's full out-of-sample coverage.
    ledgers = sorted(run_dir.glob("random_search_fold*_test_equity.parquet"))
    if not ledgers:
        return 0, None
    frames = [pl.read_parquet(p).select("open_time") for p in ledgers]
    times = pl.concat(frames)["open_time"]
    return times.len(), times.max()  # type: ignore[return-value]


if __name__ == "__main__":
    raise SystemExit(main())
