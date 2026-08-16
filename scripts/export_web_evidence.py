"""Export the study's evidence to the public site as a single JSON file.

Nothing here is computed: every number is read from an artifact that a notebook
or a study run already produced, so the landing page and the thesis cannot
disagree. The holdout reading is never read or exported.

Run with: ``uv run python scripts/export_web_evidence.py``
"""

from __future__ import annotations

import csv
import json
import random
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

CLOSURE = Path("reports/study_closure")
TABLES = Path("reports/tables")
STUDY_ROOT = Path("artifacts/runs/r3_full_budget100_ga21")
OUT = Path("apps/web/public/data/evidence.json")

# The scatter only needs enough points to show its shape; the full 3,000 would
# bloat the payload without changing what a reader sees.
SCATTER_POINTS = 700
SCATTER_SEED = 42


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def num(value: str | None) -> float | None:
    if value is None or value == "":
        return None
    try:
        result = float(value)
    except ValueError:
        return None
    return result if result == result else None  # drop NaN


def load_study() -> dict[str, Any]:
    dash = json.loads((CLOSURE / "study_dashboard.json").read_text(encoding="utf-8"))
    mt = json.loads((CLOSURE / "study_level_multiple_testing.json").read_text(encoding="utf-8"))
    reg = json.loads((CLOSURE / "regime_conditioned.json").read_text(encoding="utf-8"))

    if dash.get("holdout") is not None:
        raise SystemExit(
            "REFUSING TO EXPORT: study_dashboard.json contains a holdout payload. "
            "Regenerate it without --include-holdout before exporting to the public site."
        )

    study = dash["study"]
    corr = mt["corrections"]
    ds = corr["deflated_sharpe"]

    families = [
        {
            "family": f["family"],
            "symbol": f["symbol"],
            "gate": f["gate"],
            "thesis": f.get("thesis") or "",
            "total_return": f["total_return"],
            "sharpe": f["sharpe"],
            "max_drawdown": f["max_drawdown"],
            "p_value": f["p_value"],
            "holm_p": f["holm_adjusted_p"],
            "survives": bool(f["survives_correction"]),
        }
        for f in dash["families"]
    ]

    return {
        "n_families": study["n_families"],
        "n_units": study["n_units"],
        "n_configurations": study["n_configurations_evaluated"],
        "alpha": study["alpha"],
        "best_family": study["best_family"],
        "holm_rejected": study["holm"]["n_rejected"],
        "bh_rejected": study["benjamini_hochberg"]["n_rejected"],
        "smallest_raw_p": min(f["p_value"] for f in dash["families"]),
        "pbo": study["pbo"]["pbo"],
        "pbo_splits": study["pbo"]["n_splits"],
        "prob_best_spurious_families": ds["family_selection"]["probability_best_is_spurious"],
        "prob_best_spurious_all": ds["all_configurations_evaluated"][
            "probability_best_is_spurious"
        ],
        "regime_cells": reg["correction"]["n_cells"],
        "regime_survivors": len(reg["correction"]["survivors"]),
        "source_commit": study["source_commit"],
        "sensitivity": [
            {
                "definition": k,
                "n_tests": v["n_tests"],
                "threshold": v["bonferroni_threshold"],
                "any_survive": v["any_survive"],
            }
            for k, v in mt["sensitivity"].items()
        ],
        "families": families,
    }


def load_optimism() -> dict[str, Any]:
    """Validation-versus-test pairs for every fold winner in the R3 study."""
    points: list[tuple[float, float]] = []
    for family_dir in sorted(p for p in STUDY_ROOT.iterdir() if p.is_dir()):
        manifest_path = family_dir / "study_manifest.json"
        if not manifest_path.exists():
            continue
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for unit in manifest["units"].values():
            run_dir = Path(str(unit["run_dir"]).replace("\\", "/"))
            for engine in ("random_search", "genetic_algorithm"):
                path = run_dir / f"{engine}_fold_winners.json"
                if not path.exists():
                    continue
                for w in json.loads(path.read_text(encoding="utf-8")):
                    test = (w.get("test_metrics") or {}).get("sharpe")
                    val = w.get("val_sharpe")
                    if test is None or val is None:
                        continue
                    if val != val or test != test:  # NaN
                        continue
                    points.append((round(float(val), 3), round(float(test), 3)))

    n = len(points)
    if n == 0:
        return {"n": 0, "points": []}

    mean_val = sum(p[0] for p in points) / n
    mean_test = sum(p[1] for p in points) / n
    gaps = [p[0] - p[1] for p in points]
    mean_gap = sum(gaps) / n
    share_worse = sum(1 for g in gaps if g > 0) / n

    # Least-squares slope of test on validation.
    sxx = sum((p[0] - mean_val) ** 2 for p in points)
    sxy = sum((p[0] - mean_val) * (p[1] - mean_test) for p in points)
    slope = sxy / sxx if sxx else 0.0

    sample = points
    if n > SCATTER_POINTS:
        sample = random.Random(SCATTER_SEED).sample(points, SCATTER_POINTS)

    return {
        "n": n,
        "mean_val": round(mean_val, 4),
        "mean_test": round(mean_test, 4),
        "mean_gap": round(mean_gap, 4),
        "share_underperforming": round(share_worse, 4),
        "slope": round(slope, 4),
        "points": [list(p) for p in sample],
    }


def load_leakage() -> list[dict[str, Any]]:
    rows = read_csv(TABLES / "features" / "t05_leakage_counterexample.csv")
    return [
        {
            "variant": r["variant"],
            "sharpe": num(r.get("sharpe")),
            "final_equity": num(r.get("final_equity")),
        }
        for r in rows
    ]


def load_turnover() -> dict[str, Any]:
    rows = read_csv(TABLES / "backtest" / "t03_turnover_vs_edge.csv")
    grid = [
        {
            "fast": int(float(r["fast"])),
            "slow": int(float(r["slow"])),
            "turnover": num(r["turnover_units"]),
            "gross": num(r["sharpe_gross"]),
            "net": num(r["sharpe_net"]),
        }
        for r in rows
    ]
    baselines = read_csv(TABLES / "backtest" / "t07_baselines.csv")
    bh = next((num(r["sharpe"]) for r in baselines if r["baseline"] == "always_long"), None)
    return {"grid": grid, "buy_and_hold_sharpe": bh}


def load_costs() -> list[dict[str, Any]]:
    rows = read_csv(TABLES / "backtest" / "t02_cost_sensitivity.csv")
    return [{"round_trip_bps": num(r["round_trip_bps"]), "sharpe": num(r["sharpe"])} for r in rows]


def main() -> None:
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "holdout_published": False,
        "holdout_state": "HOLDOUT_LOCKED",
        "study": load_study(),
        "optimism": load_optimism(),
        "leakage": load_leakage(),
        "turnover": load_turnover(),
        "cost_sensitivity": load_costs(),
    }

    blob = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    if "holdout" in blob and "HOLDOUT_LOCKED" not in blob:
        raise SystemExit("REFUSING TO EXPORT: unexpected holdout content in the payload.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(blob, encoding="utf-8")
    size_kb = OUT.stat().st_size / 1024
    print(f"Wrote {OUT} ({size_kb:.1f} KB)")
    print(f"  families        : {len(payload['study']['families'])}")
    print(
        f"  optimism points : {payload['optimism']['n']:,} "
        f"({len(payload['optimism']['points'])} sampled)"
    )
    print(f"  turnover grid   : {len(payload['turnover']['grid'])}")
    print(f"  holdout         : {payload['holdout_state']} (no metric exported)")


if __name__ == "__main__":
    main()
