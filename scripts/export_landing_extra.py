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


ROB_PATH = Path(
    "artifacts/runs/r3_full_budget100_ga21/volatility_breakout/study_robustness.json"
)
R3_ROOT = Path("artifacts/runs/r3_full_budget100_ga21")
R3_FAMILIES = (
    "breakout",
    "BTC_ETH_confirmation",
    "funding",
    "mean_reversion",
    "volatility_breakout",
)


def _vb_btc_run_dirs() -> list[str]:
    """The ten BTCUSDT random-search run dirs of the study's best family."""
    rob = json.loads(ROB_PATH.read_text(encoding="utf-8"))
    units = {
        k: v
        for k, v in rob["per_run"].items()
        if "BTCUSDT" in k and "random_search" in k
    }
    return [entry["run_dir"] for _key, entry in sorted(units.items())]


def mountain_block() -> dict:
    """Pooled validation Sharpe of every random-search evaluation (10 seeds)."""
    import polars as pl

    values = []
    n_failed = 0
    n_total = 0
    for run_dir in _vb_btc_run_dirs():
        cand = pl.read_parquet(Path(run_dir) / "random_search_candidates.parquet")
        n_total += cand.height
        n_failed += cand.filter(pl.col("status") != "evaluated").height
        ok = cand.filter(pl.col("status") == "evaluated")["mean_val_sharpe"]
        values.extend(ok.to_list())
    arr = np.asarray(values, dtype=float)
    arr = arr[np.isfinite(arr)]
    counts, edges = np.histogram(arr, bins=60)
    density = counts / counts.max()
    return {
        "family": "volatility_breakout",
        "symbol": "BTCUSDT",
        "n_evaluations": int(arr.size),
        "n_total": int(n_total),
        "share_failed": round(n_failed / n_total, 4),
        "share_positive": round(float((arr > 0).mean()), 4),
        "best": round(float(arr.max()), 4),
        "median": round(float(np.median(arr)), 4),
        "bins": [
            {"x": round(float((edges[i] + edges[i + 1]) / 2), 4), "d": round(float(density[i]), 4)}
            for i in range(len(counts))
        ],
    }


def folds_block() -> dict:
    """Per-fold out-of-sample test return of the best family, across 10 seeds."""
    import polars as pl

    run_dirs = _vb_btc_run_dirs()
    fold_meta = json.loads((Path(run_dirs[0]) / "folds.json").read_text(encoding="utf-8"))
    n_folds = len(fold_meta["folds"])
    rows = []
    for k in range(n_folds):
        returns = []
        for run_dir in run_dirs:
            eq = pl.read_parquet(Path(run_dir) / f"random_search_fold{k}_test_equity.parquet")
            returns.append(float(eq["equity"][-1]) - 1.0)
        arr = np.asarray(returns)
        rows.append(
            {
                "fold": k,
                "test_start": fold_meta["folds"][k]["test_start"][:10],
                "mean": round(float(arr.mean()), 4),
                "min": round(float(arr.min()), 4),
                "max": round(float(arr.max()), 4),
            }
        )
    positive = [r for r in rows if r["mean"] > 0]
    total_positive_mean = sum(r["mean"] for r in positive)
    total_mean = sum(abs(r["mean"]) for r in rows) or 1.0
    top2 = sorted((r["mean"] for r in rows), reverse=True)[:2]
    return {
        "family": "volatility_breakout",
        "symbol": "BTCUSDT",
        "n_seeds": len(run_dirs),
        "folds": rows,
        "n_positive": len(positive),
        "top2_share_of_gains": round(
            sum(top2) / total_positive_mean, 4
        ) if total_positive_mean > 0 else None,
    }


def rs_ga_block() -> dict:
    """Random search vs genetic algorithm, same budget, per R3 family (BTC)."""
    rows = []
    for family in R3_FAMILIES:
        rob = json.loads(
            (R3_ROOT / family / "study_robustness.json").read_text(encoding="utf-8")
        )
        rs_vals = []
        ga_vals = []
        for key, entry in sorted(rob["per_run"].items()):
            if "BTCUSDT" not in key or "random_search" not in key:
                continue
            comp = json.loads(
                (Path(entry["run_dir"]) / "comparison_summary.json").read_text(encoding="utf-8")
            )
            methods = comp["methods"]
            rs_vals.append(methods["random_search"]["aggregate_test"]["mean_test_sharpe"])
            ga_vals.append(methods["genetic_algorithm"]["aggregate_test"]["mean_test_sharpe"])
        if not rs_vals:
            continue
        rows.append(
            {
                "family": family,
                "n_seeds": len(rs_vals),
                "rs": round(float(np.mean(rs_vals)), 3),
                "ga": round(float(np.mean(ga_vals)), 3),
            }
        )
    return {"metric": "mean test Sharpe of per-fold winners", "families": rows}


def meta_block() -> dict:
    """Headline numbers of the real-data meta-labeling study (RQ3)."""
    m = json.loads(
        Path("reports/meta_labeling_real/meta_labeling_real.json").read_text(encoding="utf-8")
    )
    s = m["study"]["summary"]
    return {
        "family": m["family"],
        "symbol": m["symbol"],
        "n_events": m["n_events"],
        "primary_total_return": round(s["primary_only_total_return"], 4),
        "meta_total_return": round(s["primary_plus_meta_total_return"], 4),
        "median_roc_auc": round(s["median_roc_auc"], 4),
        "abstention_rate": round(s["abstention_rate"], 4),
        "folds_improved": s["folds_improved"],
        "folds_profitable": s["folds_profitable"],
        "n_folds": s["n_folds"],
        "selected_models": s["selected_models"],
    }


def market_structure_block() -> dict:
    """Funding series, buy-and-hold underwater curve and hour×weekday
    volatility seasonality — all from the validated/processed BTC datasets."""
    import polars as pl

    bars = pl.read_parquet("data/processed/BTCUSDT/1h_development.parquet").sort("open_time")
    close = bars["close"].to_numpy()
    times = (bars["open_time"].dt.epoch("ms") // 1000).to_numpy()

    # Underwater curve of buy and hold (close vs running maximum).
    peak = np.maximum.accumulate(close)
    dd = close / peak - 1.0
    step = max(1, dd.size // 700)
    underwater = [
        {"t": int(times[i]), "dd": round(float(dd[i]), 4)} for i in range(0, dd.size, step)
    ]
    under = dd < 0
    longest = current = 0
    for flag in under:
        current = current + 1 if flag else 0
        longest = max(longest, current)

    # Hour-of-day × weekday mean absolute 1h return, in basis points.
    rets = np.diff(close) / close[:-1]
    frame = pl.DataFrame(
        {
            "hour": bars["open_time"].dt.hour().to_numpy()[1:],
            "weekday": bars["open_time"].dt.weekday().to_numpy()[1:],  # 1=Mon..7=Sun
            "absret": np.abs(rets),
        }
    )
    cells = (
        frame.group_by(["weekday", "hour"], maintain_order=False)
        .agg(pl.col("absret").mean())
        .sort(["weekday", "hour"])
    )
    seasonality = [
        {
            "w": int(row["weekday"]),
            "h": int(row["hour"]),
            "v": round(float(row["absret"]) * 1e4, 1),
        }
        for row in cells.to_dicts()
    ]

    # Weekly mean funding rate (8h events -> weekly average, annualised note).
    funding = pl.read_parquet("data/validated/BTCUSDT/fundingRate.parquet").sort("funding_time")
    funding = funding.filter(pl.col("funding_time") < pl.datetime(2026, 1, 1, time_zone="UTC"))
    weekly = (
        funding.group_by_dynamic("funding_time", every="1w")
        .agg(pl.col("funding_rate").mean())
        .sort("funding_time")
    )
    rate = funding["funding_rate"].to_numpy()
    funding_series = [
        {
            "t": int(row["funding_time"].timestamp()),
            "r": round(float(row["funding_rate"]), 6),
        }
        for row in weekly.to_dicts()
    ]
    return {
        "symbol": "BTCUSDT",
        "underwater": underwater,
        "underwater_stats": {
            "share_below_peak": round(float(under.mean()), 4),
            "max_drawdown": round(float(dd.min()), 4),
            "longest_underwater_days": int(longest / 24),
        },
        "seasonality": seasonality,
        "funding": funding_series,
        "funding_stats": {
            "n_events": int(rate.size),
            "mean_rate": round(float(rate.mean()), 6),
            "annualised_mean": round(float(rate.mean()) * 3 * 365, 4),
            "share_positive": round(float((rate > 0).mean()), 4),
        },
    }


def cost_sweep_block() -> dict:
    """Monte Carlo cost-multiplier sweep of notebook 07 (median-seed unit)."""
    with Path("reports/tables/montecarlo/t04_barrido_costes.csv").open(encoding="utf-8") as fh:
        rows = [
            {"m": float(r["multiplier"]), "ret": round(float(r["total_return"]), 4)}
            for r in csv.DictReader(fh)
        ]
    breakeven = None
    for a, b in zip(rows, rows[1:]):
        if a["ret"] >= 0 > b["ret"]:
            breakeven = a["m"] + (b["m"] - a["m"]) * a["ret"] / (a["ret"] - b["ret"])
            break
    return {
        "family": "volatility_breakout",
        "symbol": "BTCUSDT",
        "rows": rows,
        "breakeven_multiplier": round(breakeven, 2) if breakeven is not None else None,
    }


def totals_block() -> dict:
    """Study-wide counters, each derived from an on-disk artifact."""
    import polars as pl

    runs_total = sum(1 for p in Path("artifacts/runs").iterdir() if p.is_dir())
    bars_total = sum(
        pl.scan_parquet(f"data/processed/{sym}/1h_development.parquet")
        .select(pl.len())
        .collect()
        .item()
        for sym in ("BTCUSDT", "ETHUSDT")
    )
    from perp_lab.search.registry import FAMILIES

    return {
        "runs_total": runs_total,
        "bars_total": int(bars_total),
        "families_registered": len(FAMILIES),
    }


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
        "mountain": mountain_block(),
        "folds": folds_block(),
        "rs_ga": rs_ga_block(),
        "meta": meta_block(),
        "market_structure": market_structure_block(),
        "cost_sweep": cost_sweep_block(),
        "totals": totals_block(),
    }
    OUT.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
    print(
        f"{OUT} -> {OUT.stat().st_size // 1024} KB | families={len(payload['families'])} "
        f"| null rotations={payload['null_distribution']['n_rotations']} "
        f"| firms={len(payload['funded']['firms'])} "
        f"| mountain n={payload['mountain']['n_evaluations']} "
        f"| folds={len(payload['folds']['folds'])} "
        f"| rs_ga families={len(payload['rs_ga']['families'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
