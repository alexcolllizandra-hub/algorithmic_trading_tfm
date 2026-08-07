"""Print the search space of every registered strategy family.

Used to check that a newly registered family is actually reachable from the
validated configuration, and to see the size of the space it opens before
spending a search budget on it.
"""

from __future__ import annotations

from perp_lab.config import load_experiment_config
from perp_lab.search.registry import FAMILIES, build_search_space


def main() -> int:
    exp = load_experiment_config("configs/experiment.yaml")
    print(f"{'family':<26}{'params':>7}{'grid':>10}  features")
    print("-" * 70)
    for family in FAMILIES:
        space = build_search_space(exp, family, "ETHUSDT")
        grid = 1
        for param in space.params:
            grid *= max(1, len(getattr(param, "choices", (True, False))))
        features = [getattr(item, "kind", str(item)) for item in space.feature_items]
        shown = ", ".join(sorted(set(features))[:4]) or "-"
        print(f"{family:<26}{len(space.params):>7}{grid:>10}  {shown}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
