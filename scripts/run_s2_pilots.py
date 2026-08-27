"""Execute every Gate S2-B development pilot and record where each run landed.

Runs the 18 frozen configurations (3 families x 2 assets x 3 seeds) through the
same `perp-lab search` entry point the earlier gates used, and writes an index
mapping each (family, symbol, seed) to its run directory so the report builder
never has to guess which artifact belongs to which arm.

DEVELOPMENT DATA ONLY. The frozen holdout is never loaded.

Run with `uv run python scripts/run_s2_pilots.py`.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from perp_lab.search.config import load_search_config
from perp_lab.search.registry import S2_FAMILIES
from perp_lab.search.runner import run_search

SYMBOLS = ("BTCUSDT", "ETHUSDT")
SEEDS = (42, 43, 44)
INDEX_PATH = Path("artifacts/runs/s2b_pilot_index.json")


def main() -> int:
    index: dict[str, dict[str, object]] = {}
    total = len(S2_FAMILIES) * len(SYMBOLS) * len(SEEDS)
    done = 0
    started = time.time()

    for family in S2_FAMILIES:
        for symbol in SYMBOLS:
            for seed in SEEDS:
                config_path = Path(f"configs/search_s2_pilot_{family}_{symbol}_seed{seed}.yaml")
                config = load_search_config(config_path)
                result = run_search(config)
                if result.run_dir is None:
                    raise RuntimeError(f"{config_path} produced no run directory")
                run_dir = Path(result.run_dir)
                key = f"{family}|{symbol}|{seed}"
                index[key] = {
                    "family": family,
                    "symbol": symbol,
                    "seed": seed,
                    "config": str(config_path).replace("\\", "/"),
                    "run_dir": str(run_dir).replace("\\", "/"),
                }
                done += 1
                print(
                    f"[{done:>2}/{total}] {family:<22} {symbol} seed={seed}  -> {run_dir.name}",
                    flush=True,
                )

    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    INDEX_PATH.write_text(json.dumps(index, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"\nwrote {INDEX_PATH} ({done} runs in {time.time() - started:.0f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
