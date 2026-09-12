"""Re-score the closure units under alternative cost assumptions.

The study charged 4 bps taker fee plus 1 bps slippage per side and the
realised funding of every bar. A negative result under those costs leaves one
question open: is there no signal, or is there a signal the costs eat? Because
each persisted ledger keeps ``gross_return``, ``fee``, ``slippage`` and
``funding`` as separate columns, the same positions can be re-priced exactly,
without re-running anything, under any cost multiplier. This module does that
for four scenarios and reports, per closure unit, the same statistics the gate
looked at: total return, annualised Sharpe, the block-bootstrap interval on the
Sharpe, and whether the unit beats the buy-and-hold priced under the same
scenario.
"""

from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import polars as pl

from perp_lab.backtesting.metrics import performance_metrics
from perp_lab.evaluation.baselines import baselines_on_ledger
from perp_lab.evaluation.robustness import block_bootstrap_ci
from perp_lab.evaluation.study_robustness import (
    BUY_AND_HOLD,
    R3_PRIMARY_ENGINE,
    load_oos_ledger,
)

# Fee and slippage multipliers relative to the study's 4 + 1 bps per side.
# ``funding`` says whether the realised funding bill is still charged.
SCENARIOS: dict[str, dict[str, Any]] = {
    # As studied: taker fee, slippage and realised funding.
    "taker_4_1": {"fee": 1.0, "slippage": 1.0, "funding": True, "fee_bps": 4.0, "slip_bps": 1.0},
    # Maker fee (2 bps) in place of taker, slippage and funding unchanged.
    "maker_2_1": {"fee": 0.5, "slippage": 1.0, "funding": True, "fee_bps": 2.0, "slip_bps": 1.0},
    # Gross of fee and slippage, funding still charged.
    "no_fees": {"fee": 0.0, "slippage": 0.0, "funding": True, "fee_bps": 0.0, "slip_bps": 0.0},
    # Fully gross: no fee, no slippage, no funding.
    "gross": {"fee": 0.0, "slippage": 0.0, "funding": False, "fee_bps": 0.0, "slip_bps": 0.0},
}
SCENARIO_ORDER = tuple(SCENARIOS)
BOOTSTRAP_BLOCK = 168
_FAMILY_RE = re.compile(r"search_(.+?)_\d{8}T\d{6}Z_[0-9a-f]+$")


def _sharpe(x: np.ndarray) -> float:
    sd = float(x.std(ddof=1)) if x.size > 1 else 0.0
    return float(x.mean() / sd) if sd > 0 else 0.0


def scenario_net(ledger: pl.DataFrame, spec: dict[str, Any]) -> np.ndarray:
    """Per-bar net return of the same positions under one cost scenario."""
    gross = ledger["gross_return"].cast(pl.Float64).to_numpy().astype(float)
    fee = ledger["fee"].cast(pl.Float64).to_numpy().astype(float)
    slippage = ledger["slippage"].cast(pl.Float64).to_numpy().astype(float)
    funding = ledger["funding"].cast(pl.Float64).to_numpy().astype(float)
    net = gross - spec["fee"] * fee - spec["slippage"] * slippage
    if spec["funding"]:
        net = net - funding
    return np.nan_to_num(net, nan=0.0, posinf=0.0, neginf=0.0)


def gross_buy_and_hold(ledger: pl.DataFrame) -> float:
    """Price-only always-long return: no fees, no slippage, no funding."""
    oo = np.nan_to_num(ledger["oo_return"].cast(pl.Float64).to_numpy().astype(float))
    return float(np.prod(1.0 + oo) - 1.0)


@dataclass(frozen=True)
class ClosureRun:
    round: str
    family: str
    symbol: str
    seed: int
    run_dir: Path
    method: str = R3_PRIMARY_ENGINE


def _run_from_dir(run_dir: Path, round_label: str, method: str) -> ClosureRun:
    match = _FAMILY_RE.search(run_dir.name)
    if not match:
        raise ValueError(f"cannot read the family from run dir name {run_dir.name!r}")
    config = json.loads((run_dir / "search_config.json").read_text(encoding="utf-8"))
    ledger = pl.read_parquet(next(run_dir.glob(f"{method}_fold*_test_equity.parquet")))
    return ClosureRun(
        round=round_label,
        family=match.group(1),
        symbol=str(ledger["asset"][0]),
        seed=int(config["seed"]),
        run_dir=run_dir,
        method=method,
    )


def enumerate_closure_runs(
    units_csv: str | Path,
    pilot_reports: dict[str, str | Path],
    *,
    method: str = R3_PRIMARY_ENGINE,
) -> list[ClosureRun]:
    """Every seed run behind the 13-family closure that has ledgers on disk.

    Full-study families come from the chapter-7 units table (their Random
    Search runs); pilot families come from the run directories the S1-B and
    S2-B gate reports cite. Runs whose ledgers are absent are skipped and the
    caller reports coverage explicitly.
    """
    runs: dict[str, ClosureRun] = {}
    with Path(units_csv).open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            if row["engine"] != method or row["round"].startswith("CRT") or row["round"] == "S3":
                continue
            run_dir = Path(row["run_dir"].replace("\\", "/"))
            if str(run_dir) in runs or not run_dir.is_dir():
                continue
            runs[str(run_dir)] = ClosureRun(
                round=row["round"],
                family=row["family"],
                symbol=row["symbol"],
                seed=int(row["seed"]),
                run_dir=run_dir,
                method=method,
            )
    for round_label, report in pilot_reports.items():
        text = Path(report).read_text(encoding="utf-8")
        for raw in sorted(set(re.findall(r"artifacts[\\/]+runs[\\/]+[A-Za-z0-9_]+", text))):
            run_dir = Path(raw.replace("\\\\", "/").replace("\\", "/"))
            if str(run_dir) in runs or not run_dir.is_dir():
                continue
            if not any(run_dir.glob(f"{method}_fold*_test_equity.parquet")):
                continue
            runs[str(run_dir)] = _run_from_dir(run_dir, round_label, method)
    return sorted(runs.values(), key=lambda r: (r.round, r.family, r.symbol, r.seed))


def score_run(
    run: ClosureRun,
    *,
    timeframe: str = "1h",
    resamples: int = 500,
    seed: int = 42,
) -> list[dict[str, Any]]:
    """The four scenarios for one seed run, with bootstrap and buy-and-hold."""
    ledger = load_oos_ledger(run.run_dir, run.method)
    positions = ledger["position"].cast(pl.Float64).to_numpy()
    turnover = (
        ledger["turnover"].cast(pl.Float64).to_numpy() if "turnover" in ledger.columns else None
    )
    rows: list[dict[str, Any]] = []
    for name in SCENARIO_ORDER:
        spec = SCENARIOS[name]
        net = scenario_net(ledger, spec)
        metrics = performance_metrics(
            net, timeframe=timeframe, positions=positions, turnover=turnover
        )
        ci = block_bootstrap_ci(
            net, _sharpe, block_size=BOOTSTRAP_BLOCK, n_resamples=resamples, seed=seed
        )
        if spec["funding"]:
            baselines = baselines_on_ledger(
                ledger,
                timeframe=timeframe,
                fee_bps_per_side=spec["fee_bps"],
                slippage_bps_per_side=spec["slip_bps"],
                seed=seed,
            )
            bh_total = float(baselines[BUY_AND_HOLD]["total_return"])
        else:
            bh_total = gross_buy_and_hold(ledger)
        rows.append(
            {
                "round": run.round,
                "family": run.family,
                "symbol": run.symbol,
                "seed": run.seed,
                "scenario": name,
                "n_bars": int(ledger.height),
                "total_return": float(metrics["total_return"]),
                "sharpe": float(metrics["sharpe"]),
                "ann_volatility": float(metrics["ann_volatility"]),
                "max_drawdown": float(metrics["max_drawdown"]),
                "ci_low": float(ci.get("ci_low", float("nan"))),
                "ci_high": float(ci.get("ci_high", float("nan"))),
                "ci_excludes_zero": bool(ci.get("ci_low", -1.0) > 0.0),
                "bh_total_return": bh_total,
                "beats_bh": bool(metrics["total_return"] > bh_total),
                "positive": bool(metrics["total_return"] > 0.0),
            }
        )
    return rows


def _majority(n_seeds: int) -> int:
    return n_seeds // 2 + 1


def aggregate_units(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Per (family, symbol, scenario): means across seeds and seed-count criteria."""
    groups: dict[tuple[str, str, str, str], list[dict[str, Any]]] = {}
    for r in rows:
        groups.setdefault((r["round"], r["family"], r["symbol"], r["scenario"]), []).append(r)
    out: list[dict[str, Any]] = []
    for key in sorted(groups, key=lambda k: (k[1], k[2], SCENARIO_ORDER.index(k[3]))):
        rs = groups[key]
        n = len(rs)
        out.append(
            {
                "round": key[0],
                "family": key[1],
                "symbol": key[2],
                "scenario": key[3],
                "n_seeds": n,
                "mean_total_return": float(np.mean([r["total_return"] for r in rs])),
                "mean_sharpe": float(np.mean([r["sharpe"] for r in rs])),
                "median_sharpe": float(np.median([r["sharpe"] for r in rs])),
                "n_seeds_positive": int(sum(r["positive"] for r in rs)),
                "n_seeds_ci_excludes_zero": int(sum(r["ci_excludes_zero"] for r in rs)),
                "n_seeds_beat_bh": int(sum(r["beats_bh"] for r in rs)),
                "majority_required": _majority(n),
                "majority_positive": bool(sum(r["positive"] for r in rs) >= _majority(n)),
                "majority_beats_bh": bool(sum(r["beats_bh"] for r in rs) >= _majority(n)),
                "bh_total_return": float(rs[0]["bh_total_return"]),
            }
        )
    return out


def summarise_scenarios(
    units: list[dict[str, Any]], seed_rows: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """One line per scenario: how many units/seed-runs cross each bar."""
    out: list[dict[str, Any]] = []
    for name in SCENARIO_ORDER:
        us = [u for u in units if u["scenario"] == name]
        ss = [s for s in seed_rows if s["scenario"] == name]
        out.append(
            {
                "scenario": name,
                "fee_bps_per_side": SCENARIOS[name]["fee_bps"],
                "slippage_bps_per_side": SCENARIOS[name]["slip_bps"],
                "funding_charged": SCENARIOS[name]["funding"],
                "n_units": len(us),
                "n_units_mean_return_positive": int(sum(u["mean_total_return"] > 0 for u in us)),
                "n_units_majority_positive": int(sum(u["majority_positive"] for u in us)),
                "n_units_majority_beat_bh": int(sum(u["majority_beats_bh"] for u in us)),
                "n_seed_runs": len(ss),
                "n_seed_runs_positive": int(sum(s["positive"] for s in ss)),
                "n_seed_runs_ci_excludes_zero": int(sum(s["ci_excludes_zero"] for s in ss)),
                "median_unit_sharpe": float(np.median([u["mean_sharpe"] for u in us]))
                if us
                else float("nan"),
                "best_unit_sharpe": float(max(u["mean_sharpe"] for u in us))
                if us
                else float("nan"),
            }
        )
    return out
