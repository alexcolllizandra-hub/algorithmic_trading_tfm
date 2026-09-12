"""Chapter 7 addendum: no signal, or signal eaten by costs?

Every seed run behind the 13-family closure is re-priced from its persisted
ledger under four cost scenarios (taker 4+1 bps as studied; maker 2 bps with
slippage and funding kept; gross of fee and slippage with funding kept; fully
gross) without re-running anything: positions, market returns and funding are
the ledger's own. Per unit and scenario: mean total return and Sharpe across
seeds, seed counts crossing the gate's return bar, the block-bootstrap interval
on the Sharpe, and buy-and-hold priced under the same scenario.

Run with: ``uv run python scripts/build_cost_decomposition.py``
"""

from __future__ import annotations

import csv
import os
import subprocess
import time
from pathlib import Path

os.environ.setdefault("SOURCE_DATE_EPOCH", "946684800")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from perp_lab.evaluation.cost_decomposition import (
    SCENARIO_ORDER,
    SCENARIOS,
    aggregate_units,
    enumerate_closure_runs,
    score_run,
    summarise_scenarios,
)
from perp_lab.evaluation.gate_control import dump_json
from perp_lab.reporting import apply_house_style

apply_house_style()

OUT = Path("reports/thesis/chapter_07")
UNITS_CSV = Path("reports/thesis/chapter_07/ch7_results_units.csv")
PILOT_REPORTS = {
    "S1": Path("reports/gate_s1b/s1b_pilot_report.json"),
    "S2": Path("reports/gate_s2b/s2b_pilot_report.json"),
}
SCENARIO_LABEL = {
    "taker_4_1": "taker 4 + 1 bps, funding (studied)",
    "maker_2_1": "maker 2 + 1 bps, funding",
    "no_fees": "no fee, no slippage, funding",
    "gross": "fully gross",
}


def _code_commit() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _write_csv(rows: list[dict], path: Path) -> None:
    keys: list[str] = []
    for r in rows:
        for k in r:
            if k not in keys:
                keys.append(k)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def _fmt(v: object) -> str:
    if isinstance(v, bool):
        return "yes" if v else "no"
    if isinstance(v, float):
        return f"{v:.3f}"
    return str(v)


def _write_md(rows: list[dict], path: Path, title: str, columns: list[str]) -> None:
    lines = [f"# {title}", "", "| " + " | ".join(columns) + " |", "|" + "---|" * len(columns)]
    for r in rows:
        lines.append("| " + " | ".join(_fmt(r.get(c, "")) for c in columns) + " |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _figure(units: list[dict], path: Path) -> None:
    labels = sorted({(u["family"], u["symbol"]) for u in units})
    by_key = {(u["family"], u["symbol"], u["scenario"]): u for u in units}
    order = sorted(labels, key=lambda k: by_key[(k[0], k[1], "taker_4_1")]["mean_sharpe"])
    y = np.arange(len(order))
    fig, ax = plt.subplots(figsize=(9.0, 0.34 * len(order) + 1.6))
    markers = {"taker_4_1": "o", "maker_2_1": "s", "no_fees": "^", "gross": "D"}
    for name in SCENARIO_ORDER:
        ax.scatter(
            [by_key[(f, s, name)]["mean_sharpe"] for f, s in order],
            y,
            marker=markers[name],
            s=28,
            label=SCENARIO_LABEL[name],
            zorder=3,
        )
    for i, (f, s) in enumerate(order):
        xs = [by_key[(f, s, name)]["mean_sharpe"] for name in SCENARIO_ORDER]
        ax.plot([min(xs), max(xs)], [i, i], color="lightgrey", lw=1.0, zorder=1)
    ax.axvline(0.0, color="grey", lw=0.8)
    ax.set_yticks(y)
    ax.set_yticklabels([f"{f} · {s[:3]}" for f, s in order], fontsize=7)
    ax.set_xlabel("mean concatenated OOS Sharpe across seeds")
    ax.set_title("Closure units re-priced under four cost scenarios")
    ax.legend(fontsize=7, loc="lower right")
    fig.tight_layout()
    fig.savefig(path.with_suffix(".png"))
    fig.savefig(path.with_suffix(".pdf"))
    plt.close(fig)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    runs = enumerate_closure_runs(UNITS_CSV, PILOT_REPORTS)
    units_found = sorted({(r.family, r.symbol) for r in runs})
    print(f"{len(runs)} seed runs over {len(units_found)} family x asset units")

    t0 = time.perf_counter()
    seed_rows: list[dict] = []
    for i, run in enumerate(runs, 1):
        seed_rows.extend(score_run(run))
        if i % 20 == 0 or i == len(runs):
            print(f"  {i}/{len(runs)} runs scored ({time.perf_counter() - t0:.0f}s)")

    units = aggregate_units(seed_rows)
    summary = summarise_scenarios(units, seed_rows)

    _write_csv(seed_rows, OUT / "ch7_cost_scenarios_seed_runs.csv")
    _write_csv(units, OUT / "ch7_cost_scenarios_units.csv")
    _write_csv(summary, OUT / "ch7_cost_scenarios_summary.csv")
    _write_md(
        units,
        OUT / "ch7_cost_scenarios_units.md",
        "Closure units under four cost scenarios (means across seeds)",
        [
            "round",
            "family",
            "symbol",
            "scenario",
            "n_seeds",
            "mean_total_return",
            "mean_sharpe",
            "n_seeds_positive",
            "n_seeds_ci_excludes_zero",
            "n_seeds_beat_bh",
            "bh_total_return",
        ],
    )
    _write_md(
        summary,
        OUT / "ch7_cost_scenarios_summary.md",
        "Cost scenarios: how many units and seed runs cross each bar",
        [
            "scenario",
            "fee_bps_per_side",
            "slippage_bps_per_side",
            "funding_charged",
            "n_units",
            "n_units_mean_return_positive",
            "n_units_majority_positive",
            "n_units_majority_beat_bh",
            "n_seed_runs",
            "n_seed_runs_positive",
            "n_seed_runs_ci_excludes_zero",
            "median_unit_sharpe",
            "best_unit_sharpe",
        ],
    )
    _figure(units, OUT / "fig_7_8_cost_scenarios")
    # Provenance sidecar: every input ledger, its size and seed, the scenario
    # algebra, and the commit. No timestamp, so a rerun is byte-identical.
    dump_json(
        {
            "script": "scripts/build_cost_decomposition.py",
            "module": "perp_lab.evaluation.cost_decomposition",
            "code_commit": _code_commit(),
            "method": (
                "net = gross_return - fee_multiplier * fee - slippage_multiplier * slippage "
                "- funding (funding only when charged); same positions, same bars; "
                "Sharpe = concatenated OOS, annualised on 24 * 365 hourly bars"
            ),
            "scenarios": SCENARIOS,
            "bootstrap": {"block_size": 168, "n_resamples": 500, "seed": 42, "statistic": "Sharpe"},
            "inputs": [
                {
                    "round": r.round,
                    "family": r.family,
                    "symbol": r.symbol,
                    "seed": r.seed,
                    "run_dir": str(r.run_dir),
                    "engine": r.method,
                }
                for r in runs
            ],
            "coverage": {
                "n_seed_runs": len(runs),
                "n_units": len(units_found),
                "units": [f"{f}|{s}" for f, s in units_found],
            },
            "outputs": [
                "ch7_cost_scenarios_seed_runs.csv",
                "ch7_cost_scenarios_units.csv",
                "ch7_cost_scenarios_units.md",
                "ch7_cost_scenarios_summary.csv",
                "ch7_cost_scenarios_summary.md",
                "fig_7_8_cost_scenarios.png",
                "fig_7_8_cost_scenarios.pdf",
            ],
            "summary": summary,
            "units": units,
        },
        OUT / "ch7_cost_scenarios_provenance.json",
    )
    print(f"wrote {OUT} in {time.perf_counter() - t0:.0f}s")
    for s in summary:
        print(
            f"  {s['scenario']:<10} units mean>0: {s['n_units_mean_return_positive']:>2}/{s['n_units']}"
            f"  majority>0: {s['n_units_majority_positive']:>2}  seed CI>0: {s['n_seed_runs_ci_excludes_zero']:>3}/{s['n_seed_runs']}"
            f"  best unit Sharpe {s['best_unit_sharpe']:.2f}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
