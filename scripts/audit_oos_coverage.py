"""Diagnose whether both engines are scored over the identical out-of-sample bars.

Two engines compared on different bar sets are not comparable, and a baseline
computed over different bars is a different baseline. This script reports, per
run and per fold, how many bars each engine's persisted OOS ledger covers and
whether the timestamp sets are exactly equal.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import polars as pl

ENGINES = ("random_search", "genetic_algorithm")


def _fold(path: Path) -> int:
    match = re.search(r"fold(\d+)", path.name)
    return int(match.group(1)) if match else -1


def _ledgers(run_dir: Path, engine: str) -> dict[int, pl.DataFrame]:
    paths = sorted(run_dir.glob(f"{engine}_fold*_test_equity.parquet"), key=_fold)
    return {_fold(p): pl.read_parquet(p) for p in paths}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("study_dir", type=Path)
    parser.add_argument("--max-units", type=int, default=4)
    args = parser.parse_args()

    checkpoint = json.loads((args.study_dir / "checkpoint.json").read_text(encoding="utf-8"))
    units = checkpoint["units"]

    mismatched_units = 0
    for key in sorted(units)[: args.max_units]:
        run_dir = Path(units[key]["run_dir"])
        per_engine = {e: _ledgers(run_dir, e) for e in ENGINES}
        folds = sorted(set(per_engine[ENGINES[0]]) | set(per_engine[ENGINES[1]]))
        print(f"\n{key}  ({run_dir.name})")
        print(
            f"  folds present: rs={len(per_engine['random_search'])} "
            f"ga={len(per_engine['genetic_algorithm'])}"
        )
        differing = []
        for fold in folds:
            rs = per_engine["random_search"].get(fold)
            ga = per_engine["genetic_algorithm"].get(fold)
            if rs is None or ga is None:
                differing.append((fold, "missing", None, None))
                continue
            rs_times = set(rs["open_time"].to_list())
            ga_times = set(ga["open_time"].to_list())
            if rs_times != ga_times:
                differing.append((fold, "timestamps differ", rs.height, ga.height))
        if differing:
            mismatched_units += 1
            for fold, why, a, b in differing[:6]:
                print(f"    fold {fold:>2}: {why}  rs_bars={a} ga_bars={b}")
                if why == "timestamps differ":
                    rs = per_engine["random_search"][fold]
                    ga = per_engine["genetic_algorithm"][fold]
                    print(f"       rs {rs['open_time'].min()} .. {rs['open_time'].max()}")
                    print(f"       ga {ga['open_time'].min()} .. {ga['open_time'].max()}")
        else:
            print("    every fold covers identical timestamps")

        totals = {e: sum(d.height for d in per_engine[e].values()) for e in ENGINES}
        print(f"  concatenated bars: {totals}")

    print(f"\nUnits with a coverage mismatch: {mismatched_units}/{args.max_units}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
