"""Chapter 9 addendum: can Gate R3 promote anything? A positive control.

Synthetic strategies with a known net Sharpe are written in the exact layout of
a real run (real bars, positions, costs, funding and trade boundaries from a
scaffold family) and pushed through ``analyse_run`` and
``evaluate_r3_promotion`` unchanged. The output is the gate's own power curve:
promotion rate against true Sharpe, with the pass rate of every criterion.

Run with: ``uv run python scripts/build_gate_positive_control.py``
Options:  ``--reps 40 --levels 0 0.25 0.5 0.75 1 1.5 2 --scaffolds volatility_breakout momentum``

Deterministic: a master seed feeds a SeedSequence per task; the gate's own
bootstrap uses its fixed seed; no timestamps are written.
"""

from __future__ import annotations

import argparse
import csv
import os
import subprocess
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

os.environ.setdefault("SOURCE_DATE_EPOCH", "946684800")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from perp_lab.evaluation.gate_control import (
    build_tasks,
    dump_json,
    gate_verdicts,
    list_scaffold_runs,
    run_control_task,
    summarise_blocking,
    summarise_levels,
    summarise_runs,
)
from perp_lab.evaluation.study_robustness import PROMOTION_TESTS
from perp_lab.reporting import apply_house_style

apply_house_style()

OUT = Path("reports/thesis/chapter_09")
UNITS_CSV = Path("reports/thesis/chapter_07/ch7_results_units.csv")
MASTER_SEED = 20260912
FEE_BPS = 4.0
SLIPPAGE_BPS = 1.0
DEFAULT_LEVELS = [0.0, 0.3, 0.5, 1.0]
DEFAULT_SCAFFOLDS = ["volatility_breakout", "momentum"]

CRITERION_LABEL = {
    "positive_total_return": "positive net return",
    "bootstrap_sharpe_ci_excludes_zero": "bootstrap CI > 0",
    "survives_double_costs": "survives 2x costs",
    "beats_buy_and_hold": "beats buy-and-hold",
    "survives_drop_top_trades": "survives dropping top 5 trades",
    "not_confined_to_one_fold": "not confined to one fold",
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


def _figure(
    levels_rows: list[dict], run_rows: list[dict], scaffolds: list[str], path: Path
) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(11.0, 4.2))
    ax = axes[0]
    for name in scaffolds:
        rows = [r for r in levels_rows if r["scaffold"] == name]
        ax.plot(
            [r["target_sharpe"] for r in rows],
            [r["promotion_rate"] for r in rows],
            marker="o",
            label=f"scaffold: {name}",
        )
    ax.axhline(0.0, color="grey", lw=0.6)
    ax.set_ylim(-0.03, 1.03)
    ax.set_xlabel("true net annualised Sharpe of the injected strategy")
    ax.set_ylabel("promotion rate (share of replications)")
    ax.set_title("Gate R3 promotion rate vs true Sharpe")
    ax.legend(fontsize=8, loc="upper left")

    ax = axes[1]
    primary = scaffolds[0]
    for symbol, ls in (("BTCUSDT", "-"), ("ETHUSDT", "--")):
        rows = [r for r in run_rows if r["scaffold"] == primary and r["symbol"] == symbol]
        for name in PROMOTION_TESTS:
            ax.plot(
                [r["target_sharpe"] for r in rows],
                [r[f"pass_rate_{name}"] for r in rows],
                ls,
                marker=".",
                lw=1.0,
                label=f"{CRITERION_LABEL[name]} ({symbol[:3]})",
            )
    ax.set_ylim(-0.03, 1.03)
    ax.set_xlabel("true net annualised Sharpe")
    ax.set_ylabel("per-seed pass rate")
    ax.set_title(f"Each criterion, per seed run (scaffold: {primary})")
    ax.legend(fontsize=6, ncol=2, loc="lower right")
    fig.tight_layout()
    fig.savefig(path.with_suffix(".png"))
    fig.savefig(path.with_suffix(".pdf"))
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reps", type=int, default=50)
    parser.add_argument("--levels", type=float, nargs="+", default=DEFAULT_LEVELS)
    parser.add_argument("--scaffolds", nargs="+", default=DEFAULT_SCAFFOLDS)
    parser.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 2))
    args = parser.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    scaffolds = [list_scaffold_runs(UNITS_CSV, name) for name in args.scaffolds]
    for name, runs in zip(args.scaffolds, scaffolds, strict=True):
        symbols = sorted({r.symbol for r in runs})
        print(f"scaffold {name}: {len(runs)} seed runs over {symbols}")

    # Short, ASCII path: Windows MAX_PATH bites long scratch paths.
    out_root = Path(tempfile.gettempdir()) / "perp_gate_control"
    out_root.mkdir(parents=True, exist_ok=True)
    tasks = build_tasks(
        scaffolds,
        args.levels,
        args.reps,
        out_root=out_root,
        master_seed=MASTER_SEED,
        fee_bps=FEE_BPS,
        slippage_bps=SLIPPAGE_BPS,
    )
    print(f"{len(tasks)} synthetic runs through the unchanged gate on {args.workers} workers")

    t0 = time.perf_counter()
    results: list[dict] = []
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(run_control_task, t) for t in tasks]
        for i, fut in enumerate(as_completed(futures), 1):
            results.append(fut.result())
            if i % 200 == 0 or i == len(futures):
                print(f"  {i}/{len(futures)} done ({time.perf_counter() - t0:.0f}s)")
    results.sort(
        key=lambda r: (r["scaffold_index"], r["level_index"], r["rep"], r["symbol"], r["seed"])
    )

    verdicts = gate_verdicts(results)
    levels_rows = summarise_levels(verdicts)
    run_rows = summarise_runs(results)
    blocking_rows = summarise_blocking(verdicts)

    _write_csv(levels_rows, OUT / "t_gate_positive_control.csv")
    _write_csv(run_rows, OUT / "t_gate_positive_control_criteria.csv")
    _write_csv(blocking_rows, OUT / "t_gate_blocking_criteria.csv")
    _write_csv(verdicts, OUT / "gate_positive_control_replications.csv")
    _write_md(
        blocking_rows,
        OUT / "t_gate_blocking_criteria.md",
        "Gate R3 positive control: what blocks the replications that are not promoted",
        [
            "scaffold",
            "target_sharpe",
            "n_replications",
            "n_blocked",
            "most_blocking_criterion",
            "most_blocking_share",
            "most_frequent_rejection",
        ],
    )
    _write_md(
        levels_rows,
        OUT / "t_gate_positive_control.md",
        "Gate R3 positive control: promotion rate by true net Sharpe",
        [
            "scaffold",
            "target_sharpe",
            "n_replications",
            "n_promoted",
            "promotion_rate",
            "mean_realised_sharpe",
            "mean_total_return",
        ],
    )
    _write_md(
        run_rows,
        OUT / "t_gate_positive_control_criteria.md",
        "Gate R3 positive control: per-seed pass rate of each criterion",
        [
            "scaffold",
            "target_sharpe",
            "symbol",
            "bh_total_return",
            "mean_total_return",
            *[f"pass_rate_{n}" for n in PROMOTION_TESTS],
        ],
    )
    _figure(levels_rows, run_rows, args.scaffolds, OUT / "fig_gate_power_curve")

    dump_json(
        {
            "design": {
                "master_seed": MASTER_SEED,
                "levels": args.levels,
                "replications_per_level": args.reps,
                "scaffolds": {
                    name: [
                        {"symbol": r.symbol, "seed": r.seed, "run_dir": str(r.run_dir)}
                        for r in runs
                    ]
                    for name, runs in zip(args.scaffolds, scaffolds, strict=True)
                },
                "fee_bps_per_side": FEE_BPS,
                "slippage_bps_per_side": SLIPPAGE_BPS,
                "innovation": (
                    "Student-t (4 df) innovations, AR(1) with the scaffold's lag-1 "
                    "autocorrelation, scaled by the scaffold's causal EWMA volatility path "
                    "(half-life 24 bars); zero on bars without a position"
                ),
                "gate": "perp_lab.evaluation.study_robustness.analyse_run + evaluate_r3_promotion, unchanged",
                "n_synthetic_runs": len(tasks),
            },
            "code_commit": _code_commit(),
            "levels": levels_rows,
            "per_run": run_rows,
        },
        OUT / "gate_positive_control.json",
    )
    print(f"wrote {OUT} in {time.perf_counter() - t0:.0f}s")
    for r in levels_rows:
        print(
            f"  {r['scaffold']:<20} Sharpe {r['target_sharpe']:<5} promoted {r['n_promoted']:>3}/{r['n_replications']}"
            f"  realised {r['mean_realised_sharpe']:.2f}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
