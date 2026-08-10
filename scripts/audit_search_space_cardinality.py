"""Enumerate each finite strategy search space after repair and conditions.

Raw Cartesian products over-count candidates because family repair can map
several raw tuples to one valid strategy and inactive conditional parameters do
not contribute to candidate identity. This audit applies the real
``repair``/``is_valid``/``candidate_hash`` pipeline and reports the exact number
of unique candidates an engine can possibly evaluate.

The output is a prerequisite for declaring an equal cross-family budget: that
budget cannot exceed the smallest family's finite cardinality.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from perp_lab.config import load_experiment_config
from perp_lab.search.registry import FAMILIES, build_search_space
from perp_lab.search.space import BoolParam, CategoricalParam, FloatParam, IntParam, Param


def _values(param: Param) -> tuple[object, ...] | None:
    if isinstance(param, BoolParam):
        return (False, True)
    if isinstance(param, CategoricalParam):
        return param.choices
    if isinstance(param, IntParam):
        return tuple(range(param.low, param.high + 1, param.step))
    if isinstance(param, FloatParam):
        return None
    raise TypeError(f"Unsupported parameter type: {type(param).__name__}")


def cardinality(family: str, *, config: Path, symbol: str) -> dict[str, Any]:
    exp = load_experiment_config(config)
    space = build_search_space(exp, family, symbol)
    grids = [_values(param) for param in space.params]
    if any(grid is None for grid in grids):
        return {
            "family": family,
            "finite": False,
            "cardinality": None,
            "reason": "contains a continuous FloatParam",
        }

    concrete = [grid for grid in grids if grid is not None]
    raw_size = 1
    for grid in concrete:
        raw_size *= len(grid)
    exact = space.finite_cardinality()
    return {
        "family": family,
        "finite": True,
        "raw_cartesian_size": raw_size,
        "cardinality": exact,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("configs/experiment.yaml"))
    parser.add_argument("--symbol", default="BTCUSDT")
    parser.add_argument(
        "--out", type=Path, default=Path("reports/tables/search_space_cardinality.json")
    )
    args = parser.parse_args(argv)

    rows = [cardinality(family, config=args.config, symbol=args.symbol) for family in FAMILIES]
    finite = [int(row["cardinality"]) for row in rows if row["cardinality"] is not None]
    payload = {
        "experiment_config": str(args.config),
        "symbol": args.symbol,
        "spaces": rows,
        "smallest_finite_cardinality": min(finite) if finite else None,
    }
    print(json.dumps(payload, indent=2))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
