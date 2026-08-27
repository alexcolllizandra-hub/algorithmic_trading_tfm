"""Export every multiseed study to static JSON for the web strategy explorer.

Run with: ``uv run python scripts/export_strategy_explorer.py``

One index plus one file per family under ``apps/web/public/data/strategies/``.
Everything the explorer shows comes from here, and everything here comes from
the study artifacts: per-seed out-of-sample equity curves (decimated for
drawing; every kept point is the exact equity at that bar), the full metric
set the robustness battery computed, buy-and-hold on the same bars, and the
closure verdict where one exists. Nothing is invented and nothing is promoted:
the CRT round is post-closure and not promotable (the reserved partition is
consumed), and the file says so per study.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from perp_lab.evaluation.montecarlo import (
    bar_net_returns,
    path_metrics,
    percentile_of,
    stationary_bar_bootstrap,
)
from perp_lab.evaluation.study_robustness import load_oos_ledger
from perp_lab.tracking.identity import worktree_state

OUT = Path("apps/web/public/data/strategies")
ENGINE = "random_search"  # the study's primary engine; GA lives in /experimentos
CURVE_POINTS = 400
MC_PATHS = 500
MC_BLOCK_BARS = 168  # the C2 gate's decision block
MC_SEED = 42

STUDIES: dict[str, tuple[str, str]] = {
    # family -> (study_dir, round tag)
    "momentum": ("artifacts/runs/multiseed_momentum_r2_clean_v2", "R2"),
    "breakout": ("artifacts/runs/r3_full_budget100_ga21/breakout", "R3"),
    "mean_reversion": ("artifacts/runs/r3_full_budget100_ga21/mean_reversion", "R3"),
    "volatility_breakout": ("artifacts/runs/r3_full_budget100_ga21/volatility_breakout", "R3"),
    "funding": ("artifacts/runs/r3_full_budget100_ga21/funding", "R3"),
    "BTC_ETH_confirmation": ("artifacts/runs/r3_full_budget100_ga21/BTC_ETH_confirmation", "R3"),
    "pdl_reclaim_long": ("artifacts/runs/crt_v1_budget100/pdl_reclaim_long", "CRT_V1"),
    "pdh_reclaim_short": ("artifacts/runs/crt_v1_budget100/pdh_reclaim_short", "CRT_V1"),
    "crt_htf_range_reversal": (
        "artifacts/runs/crt_v1_budget100/crt_htf_range_reversal",
        "CRT_V1",
    ),
    "session_liquidity_sweep": (
        "artifacts/runs/crt_v1_budget100/session_liquidity_sweep",
        "CRT_V1",
    ),
    "session_range_rotation": (
        "artifacts/runs/crt_v1_budget100/session_range_rotation",
        "CRT_V1",
    ),
    "opening_range_breakout_retest": (
        "artifacts/runs/crt_v1_budget100/opening_range_breakout_retest",
        "CRT_V1",
    ),
    "failed_breakout_reversal": (
        "artifacts/runs/crt_v1_budget100/failed_breakout_reversal",
        "CRT_V1",
    ),
    "double_sweep_reversal": (
        "artifacts/runs/crt_v1_budget100/double_sweep_reversal",
        "CRT_V1",
    ),
    "crt_three_candle_model": (
        "artifacts/runs/crt_v1_budget100/crt_three_candle_model",
        "CRT_V1",
    ),
}

# The CRT round cannot promote anything: the reserved partition is consumed
# (holdout_audit_status.md section 5.1, crt_v1_execution.json).
CRT_VERDICT = "EVALUATED_POST_CLOSURE_NOT_PROMOTABLE"

METRIC_KEYS = (
    "total_return",
    "ann_return",
    "ann_volatility",
    "sharpe",
    "sortino",
    "calmar",
    "max_drawdown",
    "time_in_drawdown",
    "hit_rate",
    "n_trades",
    "exposure",
    "turnover",
    "var_95",
    "expected_shortfall_95",
    "skewness",
    "excess_kurtosis",
)


def decimate_indices(n: int) -> list[int]:
    step = max(1, n // CURVE_POINTS)
    idx = list(range(0, n, step))
    if idx[-1] != n - 1:
        idx.append(n - 1)
    return idx


def decimate(equity: np.ndarray) -> list[float]:
    """Every k-th exact equity value plus the last one, rounded for transport."""
    return [round(float(equity[i]), 5) for i in decimate_indices(equity.size)]


def fold_winners(run_dir: str) -> list[dict[str, Any]]:
    """The frozen winner of each fold: params and its one test evaluation."""
    path = Path(run_dir) / f"{ENGINE}_fold_winners.json"
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for w in json.loads(path.read_text(encoding="utf-8")):
        test = w.get("test_metrics") or {}
        rows.append(
            {
                "fold": w.get("fold"),
                "params": w.get("params") or {},
                "val_sharpe": w.get("val_sharpe"),
                "test_sharpe": test.get("sharpe"),
                "test_return": test.get("total_return"),
                "n_trades": test.get("n_trades"),
            }
        )
    return rows


def monte_carlo_block(net: np.ndarray, source_seed: int) -> dict[str, Any]:
    """Terminal-return dispersion of the median seed under the study's bootstrap.

    Same machinery as notebook 07 (stationary bar bootstrap, 168-bar expected
    block); it measures dispersion under resampling and validates nothing.
    """
    table = stationary_bar_bootstrap(
        net, block_length=MC_BLOCK_BARS, n_resamples=MC_PATHS, seed=MC_SEED
    )
    terminal = np.asarray(table["total_return"], dtype=float)
    observed = float(np.prod(1.0 + net) - 1.0)
    qs = {f"p{p:02d}": round(float(np.percentile(terminal, p)), 5) for p in (5, 25, 50, 75, 95)}
    return {
        "method": "stationary_bar_bootstrap",
        "block_bars": MC_BLOCK_BARS,
        "n_paths": MC_PATHS,
        "seed": MC_SEED,
        "source_seed": source_seed,
        "observed_total_return": round(observed, 5),
        "observed_percentile": round(percentile_of(observed, terminal), 4),
        "probability_positive": round(float((terminal > 0).mean()), 4),
        "terminal_quantiles": qs,
    }


def closure_metadata() -> dict[str, dict[str, Any]]:
    path = Path("reports/study_closure/study_dashboard.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    out: dict[str, dict[str, Any]] = {}
    for fam in data["families"]:
        out.setdefault(fam["family"], {})[fam["symbol"]] = {
            "thesis": fam.get("thesis"),
            "verdict": fam.get("verdict"),
            "p_value": fam.get("p_value"),
            "holm_adjusted_p": fam.get("holm_adjusted_p"),
        }
    return out


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    closure = closure_metadata()
    state = worktree_state(".")

    index: dict[str, Any] = {
        "generated_at": datetime.now(UTC).isoformat(),
        "code_commit": state.get("commit"),
        "engine": ENGINE,
        "note": (
            "Development walk-forward out-of-sample only. No study figure is final "
            "holdout performance; nothing here is promoted or promotable."
        ),
        "studies": [],
    }

    for family, (study_dir, round_tag) in STUDIES.items():
        rob = json.loads((Path(study_dir) / "study_robustness.json").read_text(encoding="utf-8"))
        per_asset: dict[str, Any] = {}
        for key, entry in sorted(rob["per_run"].items()):
            symbol, seed_part, engine = key.split("|")
            if engine != ENGINE:
                continue
            seed = int(seed_part.split("=")[1])
            ledger = load_oos_ledger(entry["run_dir"], ENGINE)
            net = bar_net_returns(ledger)
            equity = np.cumprod(1.0 + net)

            asset = per_asset.setdefault(
                symbol,
                {
                    "oos_start": entry["oos_start"],
                    "oos_end": entry["oos_end"],
                    "n_bars": entry["n_bars"],
                    "buy_and_hold": {
                        k: entry["buy_and_hold"].get(k)
                        for k in ("total_return", "sharpe", "max_drawdown")
                    },
                    # Real bar timestamps at the decimated points (day precision)
                    # and the benchmark equity on exactly the same bars.
                    "curve_times": [
                        str(ledger["open_time"][i])[:10] for i in decimate_indices(net.size)
                    ],
                    "seeds": [],
                    "_net_sum": np.zeros(net.size),
                    "_nets": {},
                },
            )
            if "curve" not in asset["buy_and_hold"]:
                bh_equity = np.cumprod(1.0 + ledger["oo_return"].to_numpy())
                asset["buy_and_hold"]["curve"] = decimate(bh_equity)
            asset["_net_sum"] = asset["_net_sum"] + net
            asset["_nets"][seed] = net
            asset["seeds"].append(
                {
                    "seed": seed,
                    "metrics": {k: entry["strategy"].get(k) for k in METRIC_KEYS},
                    "curve": decimate(equity),
                    "fold_winners": fold_winners(entry["run_dir"]),
                }
            )

        for symbol, asset in per_asset.items():
            mean_net = asset.pop("_net_sum") / max(len(asset["seeds"]), 1)
            nets = asset.pop("_nets")
            asset["average_curve"] = decimate(np.cumprod(1.0 + mean_net))
            asset["average_metrics"] = {k: round(v, 6) for k, v in path_metrics(mean_net).items()}
            # Monte Carlo on the median seed by total return: no seed cherry-pick.
            by_ret = sorted(
                asset["seeds"], key=lambda s: s["metrics"].get("total_return") or 0.0
            )
            median_seed = by_ret[len(by_ret) // 2]["seed"]
            asset["monte_carlo"] = monte_carlo_block(nets[median_seed], median_seed)
            meta = closure.get(family, {}).get(symbol, {})
            asset["closure"] = meta or None

        verdict = (
            closure.get(family, {}).get("BTCUSDT", {}).get("verdict")
            if family in closure
            else CRT_VERDICT
        )
        thesis = closure.get(family, {}).get("BTCUSDT", {}).get("thesis")

        file_name = f"{family}.json"
        (OUT / file_name).write_text(
            json.dumps(
                {"family": family, "round": round_tag, "per_asset": per_asset},
                separators=(",", ":"),
            ),
            encoding="utf-8",
        )

        def _median(symbol_key: str, metric: str, per_asset: dict = per_asset) -> float | None:
            rows = per_asset.get(symbol_key, {}).get("seeds", [])
            vals = [s["metrics"].get(metric) for s in rows]
            vals = [v for v in vals if v is not None]
            return round(float(np.median(vals)), 6) if vals else None

        index["studies"].append(
            {
                "family": family,
                "round": round_tag,
                "verdict": verdict,
                "thesis": thesis,
                "file": f"/data/strategies/{file_name}",
                "assets": sorted(per_asset),
                "n_seeds": max((len(a["seeds"]) for a in per_asset.values()), default=0),
                "headline": {
                    sym: {
                        "median_total_return": _median(sym, "total_return"),
                        "median_sharpe": _median(sym, "sharpe"),
                        "median_max_drawdown": _median(sym, "max_drawdown"),
                        "buy_and_hold_return": per_asset[sym]["buy_and_hold"]["total_return"],
                    }
                    for sym in sorted(per_asset)
                },
            }
        )
        sizes = (OUT / file_name).stat().st_size // 1024
        print(f"{family:32} {round_tag:7} assets={sorted(per_asset)} {sizes} KB")

    (OUT / "index.json").write_text(json.dumps(index, indent=1), encoding="utf-8")
    print(f"\nindex: {len(index['studies'])} studies -> {OUT / 'index.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
