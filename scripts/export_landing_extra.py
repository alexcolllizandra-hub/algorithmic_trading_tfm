"""Export the landing's additional real-data charts to one compact JSON.

Run with: ``uv run python scripts/export_landing_extra.py``

Three blocks, one file (``apps/web/public/data/landing_extra.json``):

* ``families`` -- the seed-average BTCUSDT equity curve of every multiseed
  study, downsampled from the explorer export (which already holds exact
  decimated values), plus its median return and buy-and-hold on the same bars.
* ``null_distribution`` -- the circular-shift null of the study's best
  (rejected) family, recomputed with the exact parameters notebook 07 used
  (seed 42, 1,000 rotations per seed), binned for drawing, with the ten real
  seed returns and the central 95% band.
* ``funded`` -- the strategy-vs-coin-flip pass probabilities under the two
  mapped real prop-firm rule sets, read from the notebook 07 table.

Everything here traces to an artifact; nothing is invented for layout.
"""

from __future__ import annotations

import csv
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from perp_lab.evaluation.montecarlo import PROP_FIRM_PRESETS, null_circular_shifts
from perp_lab.evaluation.study_robustness import load_oos_ledger

STRATEGIES_DIR = Path("apps/web/public/data/strategies")
OUT = Path("apps/web/public/data/landing_extra.json")
SEED = 42  # notebook 07's seed, so the landing chart matches figure k03
CURVE_POINTS = 150


def thin(curve: list[float]) -> list[float]:
    step = max(1, len(curve) // CURVE_POINTS)
    out = curve[::step]
    if out[-1] != curve[-1]:
        out.append(curve[-1])
    return [round(v, 4) for v in out]


def families_block() -> list[dict]:
    index = json.loads((STRATEGIES_DIR / "index.json").read_text(encoding="utf-8"))
    rows = []
    for study in index["studies"]:
        family_file = json.loads(
            (STRATEGIES_DIR / f"{study['family']}.json").read_text(encoding="utf-8")
        )
        asset = family_file["per_asset"].get("BTCUSDT")
        if asset is None:
            continue
        rows.append(
            {
                "family": study["family"],
                "round": study["round"],
                "median_return": study["headline"]["BTCUSDT"]["median_total_return"],
                "buy_and_hold": asset["buy_and_hold"]["total_return"],
                "curve": thin(asset["average_curve"]),
            }
        )
    return rows


def null_block() -> dict:
    rob = json.loads(
        Path(
            "artifacts/runs/r3_full_budget100_ga21/volatility_breakout/study_robustness.json"
        ).read_text(encoding="utf-8")
    )
    units = {
        k: v
        for k, v in rob["per_run"].items()
        if "BTCUSDT" in k and "random_search" in k
    }
    pooled = []
    reals = []
    for _key, entry in sorted(units.items()):
        ledger = load_oos_ledger(entry["run_dir"], "random_search")
        out = null_circular_shifts(ledger, n_shifts=1000, seed=SEED)
        pooled.append(out["null"]["total_return"])
        reals.append(round(out["real"]["total_return"], 4))
    pooled_arr = np.concatenate(pooled)
    lo, hi = np.percentile(pooled_arr, [2.5, 97.5])
    # Bin over the central 99%: circular rotations occasionally compound into
    # a +1000% tail that would crush the readable region into the left edge.
    # The clip is for DISPLAY only, is declared in the payload, and never
    # touches the band or the percentiles.
    clip_lo, clip_hi = np.percentile(pooled_arr, [0.5, 99.5])
    clipped_share = float(((pooled_arr < clip_lo) | (pooled_arr > clip_hi)).mean())
    visible = pooled_arr[(pooled_arr >= clip_lo) & (pooled_arr <= clip_hi)]
    counts, edges = np.histogram(visible, bins=60)
    density = counts / counts.max()
    return {
        "display_clipped_share": round(clipped_share, 4),
        "family": "volatility_breakout",
        "symbol": "BTCUSDT",
        "n_rotations": int(pooled_arr.size),
        "bins": [
            {"x": round(float((edges[i] + edges[i + 1]) / 2), 4), "d": round(float(density[i]), 4)}
            for i in range(len(counts))
        ],
        "real_seeds": reals,
        "band": [round(float(lo), 4), round(float(hi), 4)],
    }


def funded_block() -> dict:
    with Path("reports/tables/montecarlo/t05_cuenta_fondeada.csv").open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    firms = []
    for firm_id, preset in PROP_FIRM_PRESETS.items():
        entry = {"id": firm_id, "source": preset["source"], "retrieved": preset["retrieved"]}
        rules = preset["rules"]
        entry["rules"] = {
            "profit_target": rules.profit_target,
            "max_total_drawdown": rules.max_total_drawdown,
            "max_daily_loss": rules.max_daily_loss,
            "max_days": rules.max_days,
        }
        for row in rows:
            if row["firm"] != firm_id:
                continue
            arm = row["arm"]
            entry[f"{arm}_phase1"] = round(float(row["pass_phase1"]), 4)
            entry[f"{arm}_both"] = round(float(row["pass_both"]), 4)
        firms.append(entry)
    return {"n_paths": 1000, "firms": firms}


def main() -> int:
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "note": (
            "Development out-of-sample evidence only; nothing promoted or promotable. "
            "Null and funded blocks reproduce notebook 07 (seed 42)."
        ),
        "families": families_block(),
        "null_distribution": null_block(),
        "funded": funded_block(),
    }
    OUT.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
    print(
        f"{OUT} -> {OUT.stat().st_size // 1024} KB | families={len(payload['families'])} "
        f"| null rotations={payload['null_distribution']['n_rotations']} "
        f"| firms={len(payload['funded']['firms'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
