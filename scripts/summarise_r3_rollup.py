"""Cross-family Gate R3 rollup from persisted study artifacts.

Reads each family's ``study_robustness.json`` and ``multi_seed_analysis.json``.
Nothing is recomputed; every number traces to files under the study root.

    uv run python scripts/summarise_r3_rollup.py artifacts/runs/r3_full_budget100_ga21
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

PRIMARY_ENGINE = "random_search"


def _load(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _family_row(study_dir: Path) -> dict[str, Any] | None:
    robustness = _load(study_dir / "study_robustness.json")
    analysis = _load(study_dir / "multi_seed_analysis.json")
    if robustness is None:
        return None

    promo = robustness.get("r3_promotion", {})
    tally = robustness.get("by_symbol_and_engine", {})
    paired = (analysis or {}).get("paired_rs_vs_ga", {})
    combined = paired.get("combined", paired)

    rs_rows = {
        key.split("|", 1)[0]: row
        for key, row in tally.items()
        if key.endswith(f"|{PRIMARY_ENGINE}")
    }

    return {
        "study_dir": str(study_dir),
        "verdict": promo.get("verdict", "UNKNOWN"),
        "triggered_rejections": promo.get("triggered_rejections", []),
        "failed_promotion_criteria": promo.get("failed_promotion_criteria", []),
        "by_symbol_rs": {
            symbol: {
                "n_positive": rs_rows.get(symbol, {}).get("n_positive"),
                "n_beat_buy_and_hold": rs_rows.get(symbol, {}).get("n_beat_buy_and_hold"),
                "n_survive_double_costs": rs_rows.get(symbol, {}).get("n_survive_double_costs"),
                "n_bootstrap_ci_excludes_zero": rs_rows.get(symbol, {}).get(
                    "n_bootstrap_ci_excludes_zero"
                ),
                "n_survives_drop_top_trades": rs_rows.get(symbol, {}).get(
                    "n_survives_drop_top_trades"
                ),
                "n_not_confined_to_one_fold": rs_rows.get(symbol, {}).get(
                    "n_not_confined_to_one_fold"
                ),
                "median_total_return": rs_rows.get(symbol, {}).get("median_total_return"),
                "median_buy_and_hold_return": rs_rows.get(symbol, {}).get(
                    "median_buy_and_hold_return"
                ),
                "promotion": promo.get("by_symbol", {}).get(symbol, {}).get("promotion", {}),
            }
            for symbol in sorted(rs_rows)
        },
        "paired_ga_minus_rs": {
            "mean_difference": paired.get("mean_difference_ga_minus_rs"),
            "ci_low": combined.get("ci_low"),
            "ci_high": combined.get("ci_high"),
            "verdict": paired.get("verdict"),
        },
    }


def build_rollup(root: Path) -> dict[str, Any]:
    execution = _load(root / "r3_execution.json") or {}
    families_meta = execution.get("families", {})
    order = execution.get("frozen_order") or sorted(families_meta)

    rows: dict[str, Any] = {}
    for family in order:
        meta = families_meta.get(family, {})
        study_dir = Path(meta.get("study_dir", root / family))
        status = meta.get("status", "unknown")
        row = _family_row(study_dir) if status == "completed" else None
        rows[family] = {
            "status": status,
            "study_dir": str(study_dir),
            "elapsed_seconds": meta.get("elapsed_seconds"),
            "analysis": row,
        }

    completed = [f for f, r in rows.items() if r.get("analysis")]
    promoted = [f for f in completed if rows[f]["analysis"]["verdict"] == "PROMOTED"]
    rejected = [f for f in completed if rows[f]["analysis"]["verdict"] == "REJECTED"]

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "root": str(root),
        "protocol": "independent_search_per_outer_fold",
        "effective_budget_per_fold_and_engine": execution.get(
            "effective_budget_per_fold_and_engine"
        ),
        "n_seeds": execution.get("n_seeds"),
        "symbols": execution.get("symbols"),
        "primary_engine": PRIMARY_ENGINE,
        "families": rows,
        "summary": {
            "n_families_total": len(order),
            "n_completed": len(completed),
            "n_promoted": len(promoted),
            "n_rejected": len(rejected),
            "promoted": promoted,
            "rejected": rejected,
        },
    }


def _fmt_pct(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:+.2%}"


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Gate R3 family rollup",
        "",
        f"Generated: {payload['generated_at']}",
        f"Root: `{payload['root']}`",
        f"Protocol: `{payload['protocol']}`",
        f"Budget: {payload['effective_budget_per_fold_and_engine']} evals/fold/engine",
        f"Primary engine: `{payload['primary_engine']}`",
        "",
        "## Summary",
        "",
        f"- Completed: {payload['summary']['n_completed']}/{payload['summary']['n_families_total']}",
        f"- Promoted: {payload['summary']['n_promoted']}",
        f"- Rejected: {payload['summary']['n_rejected']}",
        "",
        "## Comparison (random_search, 10 seeds per asset)",
        "",
        "| family | verdict | BTC +seeds | ETH +seeds | BTC med ret | ETH med ret | GA-RS mean |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]

    for family, row in payload["families"].items():
        analysis = row.get("analysis")
        if not analysis:
            lines.append(f"| {family} | {row['status']} | — | — | — | — | — |")
            continue
        btc = analysis["by_symbol_rs"].get("BTCUSDT", {})
        eth = analysis["by_symbol_rs"].get("ETHUSDT", {})
        paired = analysis["paired_ga_minus_rs"]
        mean_diff = paired.get("mean_difference")
        lines.append(
            f"| {family} | {analysis['verdict']} "
            f"| {btc.get('n_positive', '—')}/10 "
            f"| {eth.get('n_positive', '—')}/10 "
            f"| {_fmt_pct(btc.get('median_total_return'))} "
            f"| {_fmt_pct(eth.get('median_total_return'))} "
            f"| {mean_diff:+.3f} |"
            if mean_diff is not None
            else f"| {family} | {analysis['verdict']} | … |"
        )

    lines.extend(["", "## Rejection detail", ""])
    for family, row in payload["families"].items():
        analysis = row.get("analysis")
        if not analysis or analysis["verdict"] != "REJECTED":
            continue
        lines.append(f"### {family}")
        if analysis["triggered_rejections"]:
            lines.append("- Rejections: " + "; ".join(analysis["triggered_rejections"]))
        if analysis["failed_promotion_criteria"]:
            lines.append(
                "- Failed promotion: " + "; ".join(analysis["failed_promotion_criteria"][:6])
            )
        lines.append("")

    lines.append("Development-period evidence only. The frozen holdout was never opened.")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "root", type=Path, default=Path("artifacts/runs/r3_full_budget100_ga21"), nargs="?"
    )
    args = parser.parse_args(argv)

    payload = build_rollup(args.root)
    json_path = args.root / "r3_family_rollup.json"
    md_path = args.root / "r3_family_rollup.md"
    json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(payload), encoding="utf-8")

    print(
        f"Completed families : {payload['summary']['n_completed']}/{payload['summary']['n_families_total']}"
    )
    print(f"Promoted           : {payload['summary']['n_promoted']}")
    print(f"Rejected           : {payload['summary']['n_rejected']}")
    print(f"Written            : {json_path}")
    print(f"Written            : {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
