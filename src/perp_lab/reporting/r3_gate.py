"""Read-only Gate R3 thesis reporting from persisted run artifacts.

Derives Markdown and JSON tables for the TFM without recomputing backtests,
touching the holdout, or modifying original R3 search artifacts.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from statistics import median
from typing import Any, Literal

import numpy as np

from perp_lab.evaluation.study_robustness import (
    PROMOTION_TESTS,
    R3_MIN_OOS_TRADES,
    R3_PRIMARY_ENGINE,
)

SECONDARY_ENGINE = "genetic_algorithm"

CRITERION_LABELS: dict[str, str] = {
    "positive_total_return": "C1 positive return",
    "bootstrap_sharpe_ci_excludes_zero": "C2 bootstrap Sharpe CI",
    "survives_double_costs": "C3 survives 2x costs",
    "beats_buy_and_hold": "C4 beats buy-and-hold",
    "survives_drop_top_trades": "C5 drop top 5 trades",
    "not_confined_to_one_fold": "C6 fold locality",
}

TALLY_FIELDS: dict[str, str] = {
    "positive_total_return": "n_positive",
    "bootstrap_sharpe_ci_excludes_zero": "n_bootstrap_ci_excludes_zero",
    "survives_double_costs": "n_survive_double_costs",
    "beats_buy_and_hold": "n_beat_buy_and_hold",
    "survives_drop_top_trades": "n_survives_drop_top_trades",
    "not_confined_to_one_fold": "n_not_confined_to_one_fold",
}

Classification = Literal["primary_result", "secondary_diagnostic", "limitation"]


class R3ReportError(Exception):
    """Raised when required artifacts are missing or internally inconsistent."""


class R3ReportConsistencyError(R3ReportError):
    """Raised when persisted numeric fields contradict each other."""


@dataclass(frozen=True)
class R3GatePaths:
    root: Path
    execution: Path
    gate_verdict: Path
    rollup: Path
    gate_report: Path | None = None


def default_r3_root() -> Path:
    return Path("artifacts/runs/r3_full_budget100_ga21")


def resolve_r3_paths(root: Path) -> R3GatePaths:
    root = root.resolve()
    gate_report = root / "r3_gate_report.json"
    return R3GatePaths(
        root=root,
        execution=root / "r3_execution.json",
        gate_verdict=root / "r3_gate_verdict.json",
        rollup=root / "r3_family_rollup.json",
        gate_report=gate_report if gate_report.exists() else None,
    )


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise R3ReportError(f"required artifact missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _rel_source(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _fmt_pct(value: float | None) -> str:
    if value is None or not np.isfinite(value):
        return "n/a"
    return f"{value:+.1%}"


def _fmt_sharpe(value: float | None) -> str:
    if value is None or not np.isfinite(value):
        return "n/a"
    return f"{value:.2f}"


def _tally_cell(n_pass: int, n_seeds: int, *, required: int) -> str:
    status = "OK" if n_pass >= required else "FAIL"
    return f"{n_pass}/{n_seeds} {status}"


def _median_strategy_sharpe(study: dict[str, Any], symbol: str, engine: str) -> float | None:
    values: list[float] = []
    for entry in study.get("per_run", {}).values():
        if entry.get("symbol") != symbol or entry.get("method") != engine:
            continue
        sharpe = entry.get("strategy", {}).get("sharpe")
        if sharpe is not None and np.isfinite(float(sharpe)):
            values.append(float(sharpe))
    if not values:
        return None
    return float(median(values))


def _family_order(execution: dict[str, Any]) -> list[str]:
    order = execution.get("frozen_order") or execution.get("selected")
    if order:
        return list(order)
    return sorted(execution.get("families", {}))


def _count_completed_units(root: Path, families: list[str]) -> tuple[int, int]:
    expected = 0
    completed = 0
    for family in families:
        status_path = root / family / "status.json"
        checkpoint_path = root / family / "checkpoint.json"
        if not status_path.exists() or not checkpoint_path.exists():
            raise R3ReportError(f"missing status/checkpoint for family {family!r}")
        status = _load_json(status_path)
        checkpoint = _load_json(checkpoint_path)
        meta = checkpoint.get("meta", {})
        n_symbols = len(meta.get("symbols", []))
        n_seeds = len(meta.get("seeds", []))
        family_expected = n_symbols * n_seeds
        expected += family_expected
        completed += int(status.get("completed", 0))
    return completed, expected


def _provenance_note(root: Path, families: list[str]) -> dict[str, Any]:
    for family in families:
        identity_path = root / family / "run_identity.json"
        if identity_path.exists():
            identity = _load_json(identity_path)
            worktree = identity.get("worktree", {})
            return {
                "commit_at_run": worktree.get("commit")
                or identity.get("components", {}).get("commit"),
                "worktree_dirty": bool(worktree.get("dirty")),
                "diff_sha256_first_families": worktree.get("diff_sha256"),
                "reproducible_from_commit_alone": bool(
                    worktree.get("reproducible_from_commit_alone", False)
                ),
                "exact_reconstruction_from_aac3357": (
                    "not possible when the worktree was dirty and patch bytes were not retained"
                ),
                "methodological_validity": (
                    "numerical integrity and CLOSED_NEGATIVE verdict remain valid from persisted "
                    "artifacts"
                ),
                "source_file": _rel_source(identity_path, root),
            }
    raise R3ReportError("no run_identity.json found under any family study directory")


def _partial_signal_note(family: str, symbol: str, row: dict[str, Any]) -> str | None:
    if family != "volatility_breakout" or symbol != "BTCUSDT":
        return None
    c1 = row["criteria"]["positive_total_return"]["n_pass"]
    if c1 >= row["majority_required"] and row["verdict"] == "REJECTED":
        return "partial non-robust signal (not promotion-eligible)"
    return None


def build_r3_thesis_report(root: Path) -> dict[str, Any]:
    """Build a deterministic thesis report payload from persisted Gate R3 artifacts."""
    paths = resolve_r3_paths(root)
    source_root_label = root.as_posix()
    if "holdout" in str(root).lower():
        raise R3ReportError("holdout paths must not be used as an R3 report source")

    execution = _load_json(paths.execution)
    verdict = _load_json(paths.gate_verdict)
    rollup = _load_json(paths.rollup)
    gate_report = _load_json(paths.gate_report) if paths.gate_report else None

    families = _family_order(execution)
    units_completed, units_expected = _count_completed_units(paths.root, families)

    if verdict.get("gate_status") != "CLOSED_NEGATIVE":
        raise R3ReportConsistencyError(
            f"expected gate_status CLOSED_NEGATIVE, got {verdict.get('gate_status')!r}"
        )
    if int(verdict.get("n_promoted", -1)) != 0:
        raise R3ReportConsistencyError("expected n_promoted == 0")
    if bool(verdict.get("r4_required")):
        raise R3ReportConsistencyError("expected r4_required == false")
    if rollup["summary"]["n_promoted"] != 0:
        raise R3ReportConsistencyError("rollup summary n_promoted must be 0")
    if any(row["analysis"]["verdict"] == "PROMOTED" for row in rollup["families"].values()):
        raise R3ReportConsistencyError("no family may be PROMOTED in rollup")

    primary_rows: list[dict[str, Any]] = []
    rs_ga_rows: list[dict[str, Any]] = []
    traceability: list[dict[str, Any]] = []

    n_seeds = int(execution.get("n_seeds", 10))
    majority = 6 if n_seeds == 10 else max(1, (n_seeds // 2) + 1)

    for family in families:
        family_meta = rollup["families"][family]
        analysis = family_meta.get("analysis")
        if analysis is None:
            raise R3ReportError(f"family {family!r} has no rollup analysis")

        study_path = paths.root / family / "study_robustness.json"
        study = _load_json(study_path)
        promo = study.get("r3_promotion", {})
        if promo.get("verdict") != analysis["verdict"]:
            raise R3ReportConsistencyError(
                f"{family}: study verdict {promo.get('verdict')!r} != rollup {analysis['verdict']!r}"
            )
        if promo.get("engine") != R3_PRIMARY_ENGINE:
            raise R3ReportConsistencyError(f"{family}: promotion engine must be random_search")

        paired = analysis["paired_ga_minus_rs"]
        rs_ga_rows.append(
            {
                "family": family,
                "mean_difference_ga_minus_rs": paired.get("mean_difference"),
                "ci_low": paired.get("ci_low"),
                "ci_high": paired.get("ci_high"),
                "interpretation": paired.get("verdict"),
                "ga_does_not_decide_promotion": True,
                "source_file": _rel_source(paths.rollup, paths.root),
                "source_field": f"families.{family}.analysis.paired_ga_minus_rs",
            }
        )

        for symbol in sorted(analysis["by_symbol_rs"]):
            rs_tally = study["by_symbol_and_engine"][f"{symbol}|{R3_PRIMARY_ENGINE}"]
            symbol_promo = promo["by_symbol"][symbol]
            if symbol_promo["majority_required"] != majority:
                raise R3ReportConsistencyError(f"{family}/{symbol}: unexpected majority threshold")

            criteria: dict[str, Any] = {}
            for name in PROMOTION_TESTS:
                promo_row = symbol_promo["promotion"][name]
                tally_key = TALLY_FIELDS[name]
                tally_val = rs_tally.get(tally_key)
                if tally_val != promo_row["n_pass"]:
                    raise R3ReportConsistencyError(
                        f"{family}/{symbol}/{name}: tally {tally_val} != promotion n_pass "
                        f"{promo_row['n_pass']}"
                    )
                criteria[name] = {
                    "label": CRITERION_LABELS[name],
                    "n_pass": int(promo_row["n_pass"]),
                    "n_seeds": int(symbol_promo["n_seeds"]),
                    "majority_required": int(promo_row["required"]),
                    "pass": bool(promo_row["pass"]),
                    "display": _tally_cell(
                        int(promo_row["n_pass"]),
                        int(symbol_promo["n_seeds"]),
                        required=int(promo_row["required"]),
                    ),
                    "source_file": _rel_source(study_path, paths.root),
                    "source_field": f"r3_promotion.by_symbol.{symbol}.promotion.{name}",
                }

            min_trades = symbol_promo["rejections"]["depends_on_few_trades"]
            n_min_ok = int(rs_tally.get("n_min_oos_trades_met", 0))
            n_below = int(min_trades.get("n_seeds_below_min_trades", 0))
            if n_min_ok + n_below != int(symbol_promo["n_seeds"]):
                raise R3ReportConsistencyError(
                    f"{family}/{symbol}: min-trade seed counts inconsistent"
                )
            veto_triggered = bool(min_trades.get("triggered"))

            med_sharpe = _median_strategy_sharpe(study, symbol, R3_PRIMARY_ENGINE)
            row = {
                "family": family,
                "symbol": symbol,
                "engine": R3_PRIMARY_ENGINE,
                "criteria": criteria,
                "min_oos_trades_met": {
                    "n_pass": n_min_ok,
                    "n_seeds": int(symbol_promo["n_seeds"]),
                    "min_trades_required": R3_MIN_OOS_TRADES,
                    "veto_triggered": veto_triggered,
                    "display": _tally_cell(
                        n_min_ok, int(symbol_promo["n_seeds"]), required=n_seeds
                    ),
                    "role": "separate veto (not a seventh promotion criterion)",
                    "source_file": _rel_source(study_path, paths.root),
                    "source_field": (
                        f"r3_promotion.by_symbol.{symbol}.rejections.depends_on_few_trades"
                    ),
                },
                "median_oos_return": rs_tally.get("median_total_return"),
                "median_oos_sharpe": med_sharpe,
                "median_buy_and_hold_return": rs_tally.get("median_buy_and_hold_return"),
                "verdict": analysis["verdict"],
                "majority_required": majority,
            }
            note = _partial_signal_note(family, symbol, row)
            if note:
                row["diagnostic_note"] = note
            primary_rows.append(row)

            traceability.extend(
                [
                    {
                        "claim": f"{family}/{symbol} {CRITERION_LABELS[name]}",
                        "value": criteria[name]["display"],
                        "source_file": criteria[name]["source_file"],
                        "source_field": criteria[name]["source_field"],
                        "classification": (
                            "secondary_diagnostic"
                            if note and name == "positive_total_return"
                            else "primary_result"
                        ),
                    }
                    for name in PROMOTION_TESTS
                ]
            )

    provenance = _provenance_note(paths.root, families)
    isolation_audit = (
        gate_report.get("isolation_audit") if gate_report else f"{units_completed}/{units_expected}"
    )

    closure = {
        "gate_status": verdict["gate_status"],
        "n_promoted": verdict["n_promoted"],
        "n_rejected": verdict["n_rejected"],
        "units_completed": f"{units_completed}/{units_expected}",
        "isolation_audit": isolation_audit,
        "numerical_discrepancies": 0,
        "r4_required": verdict["r4_required"],
        "r4_status": "SKIPPED (zero R3 promotions; confirmatory gate only for promoted families)",
        "holdout": "closed (not accessed)",
        "provenance_limitation": provenance,
        "pre_specification_note": (
            "Gate R3 promotion criteria and R4 skip rule were pre-specified and versioned "
            "in the repository before R3 execution"
        ),
    }

    traceability.extend(
        [
            {
                "claim": "Gate R3 status",
                "value": verdict["gate_status"],
                "source_file": _rel_source(paths.gate_verdict, paths.root),
                "source_field": "gate_status",
                "classification": "primary_result",
            },
            {
                "claim": "Families promoted",
                "value": str(verdict["n_promoted"]),
                "source_file": _rel_source(paths.gate_verdict, paths.root),
                "source_field": "n_promoted",
                "classification": "primary_result",
            },
            {
                "claim": "Exact reconstruction from aac3357",
                "value": provenance["exact_reconstruction_from_aac3357"],
                "source_file": provenance["source_file"],
                "source_field": "worktree.reproducible_from_commit_alone",
                "classification": "limitation",
            },
        ]
    )

    source_timestamp = (
        verdict.get("closed_at") or rollup.get("generated_at") or execution.get("completed_at")
    )

    return {
        "schema_version": 1,
        "gate": "R3",
        "source_root": source_root_label,
        "source_timestamp": source_timestamp,
        "primary_engine": R3_PRIMARY_ENGINE,
        "secondary_engine": SECONDARY_ENGINE,
        "majority_rule": f">={majority}/{n_seeds} seeds per asset on both assets",
        "closure_summary": closure,
        "primary_table_rs": primary_rows,
        "rs_ga_comparison": rs_ga_rows,
        "traceability": traceability,
        "holdout_accessed": False,
    }


def render_r3_thesis_markdown(report: dict[str, Any]) -> str:
    """Render a thesis-ready Markdown report from a build_r3_thesis_report payload."""
    lines = [
        "# Gate R3 — Thesis reporting extract",
        "",
        f"*Derived from persisted artifacts · source timestamp `{report['source_timestamp']}`*",
        "",
        "Random Search is the **confirmatory** promotion engine. Genetic Algorithm results are "
        "**secondary** and do not decide family promotion.",
        "",
        "## Closure summary",
        "",
    ]
    closure = report["closure_summary"]
    for key in (
        "gate_status",
        "n_promoted",
        "n_rejected",
        "units_completed",
        "isolation_audit",
        "numerical_discrepancies",
        "r4_required",
        "r4_status",
        "holdout",
    ):
        lines.append(f"- **{key}:** {closure[key]}")
    lines.extend(
        [
            "",
            f"- **provenance:** {closure['provenance_limitation']['exact_reconstruction_from_aac3357']}",
            f"- **note:** {closure['pre_specification_note']}",
            "",
            "## Primary results — Random Search",
            "",
            "| Family | Asset | C1 | C2 | C3 | C4 | C5 | C6 | Min trades veto | Med OOS ret | "
            "Med OOS Sharpe | Med B&H | Verdict |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
        ]
    )

    for row in report["primary_table_rs"]:
        crit = row["criteria"]
        note = f" ({row['diagnostic_note']})" if row.get("diagnostic_note") else ""
        lines.append(
            f"| {row['family']} | {row['symbol']} "
            f"| {crit['positive_total_return']['display']} "
            f"| {crit['bootstrap_sharpe_ci_excludes_zero']['display']} "
            f"| {crit['survives_double_costs']['display']} "
            f"| {crit['beats_buy_and_hold']['display']} "
            f"| {crit['survives_drop_top_trades']['display']} "
            f"| {crit['not_confined_to_one_fold']['display']} "
            f"| {row['min_oos_trades_met']['display']} "
            f"| {_fmt_pct(row['median_oos_return'])} "
            f"| {_fmt_sharpe(row['median_oos_sharpe'])} "
            f"| {_fmt_pct(row['median_buy_and_hold_return'])} "
            f"| **{row['verdict']}**{note} |"
        )

    lines.extend(
        [
            "",
            "`min_oos_trades_met` is a **separate veto**, not a seventh promotion criterion.",
            "",
            "## Random Search vs Genetic Algorithm (secondary)",
            "",
            "| Family | GA - RS mean | 95% CI | Interpretation | GA decides promotion? |",
            "|---|---:|---|---|:---:|",
        ]
    )
    for row in report["rs_ga_comparison"]:
        ci = f"[{row['ci_low']:+.3f}, {row['ci_high']:+.3f}]"
        lines.append(
            f"| {row['family']} | {row['mean_difference_ga_minus_rs']:+.3f} | {ci} | "
            f"{row['interpretation']} | **No** |"
        )

    lines.extend(
        [
            "",
            "## Provenance limitation",
            "",
            f"- Commit at run: `{closure['provenance_limitation'].get('commit_at_run')}`",
            f"- Worktree dirty: `{closure['provenance_limitation'].get('worktree_dirty')}`",
            f"- {closure['provenance_limitation']['exact_reconstruction_from_aac3357']}.",
            f"- {closure['provenance_limitation']['methodological_validity']}.",
            "",
            "Development-period evidence only. The frozen holdout was never opened.",
        ]
    )
    return "\n".join(lines) + "\n"


def write_r3_thesis_report(root: Path, output_dir: Path) -> dict[str, Path]:
    """Build and write deterministic thesis report artifacts."""
    report = build_r3_thesis_report(root)
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    json_path = output_dir / "thesis_report.json"
    md_path = output_dir / "thesis_report.md"

    json_text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    md_text = render_r3_thesis_markdown(report)

    json_path.write_text(json_text, encoding="utf-8")
    md_path.write_text(md_text, encoding="utf-8")

    return {"json": json_path, "markdown": md_path}
