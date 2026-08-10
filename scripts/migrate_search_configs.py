"""Rewrite search configs to the fixed effective-budget contract.

The GA is now budget-driven rather than generation-driven, so `ga.generations`
becomes `ga.max_generations` (a safety cap) and the shared target moves to a
top-level `effective_budget`. The previous unique-evaluation formula is used to
choose a budget that the old configuration could actually reach, so the migrated
configs run at a comparable cost to the ones they replace.
"""

from __future__ import annotations

import re
from pathlib import Path

# path -> (effective_budget, max_generations)
TARGETS = {
    "configs/search.yaml": (2000, 60),
    "configs/search_development_btc.yaml": (300, 40),
    "configs/search_development_eth.yaml": (300, 40),
    "configs/search_pilot.yaml": (12, 20),
    "configs/search_pilot_eth.yaml": (12, 20),
    "configs/search_smoke.yaml": (16, 20),
}


def migrate(path: Path, budget: int, max_generations: int) -> bool:
    text = path.read_text(encoding="utf-8")
    if "max_generations" in text:
        return False
    text = re.sub(
        r"^(\s*)generations:\s*\d+", rf"\1max_generations: {max_generations}", text, flags=re.M
    )
    if "effective_budget:" not in text:
        text = re.sub(
            r"^ga:",
            f"# Unique, valid, non-cached objective evaluations EVERY engine must spend.\n"
            f"effective_budget: {budget}\n\nga:",
            text,
            count=1,
            flags=re.M,
        )
    path.write_text(text, encoding="utf-8")
    return True


def main() -> int:
    for name, (budget, max_generations) in TARGETS.items():
        path = Path(name)
        if not path.exists():
            print(f"skip (missing): {name}")
            continue
        changed = migrate(path, budget, max_generations)
        print(f"{'migrated' if changed else 'already migrated'}: {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
