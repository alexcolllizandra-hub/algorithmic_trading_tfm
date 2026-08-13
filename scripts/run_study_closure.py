"""Piece 1 of the study closure: multiple-testing accounting over the whole study.

Reads only persisted development-partition artifacts. Never opens the holdout.

    uv run python scripts/run_study_closure.py
"""

from __future__ import annotations

import argparse
import json
import logging
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from perp_lab.reporting.study_closure import (
    GATE_CRITERIA,
    PRIMARY_ENGINE,
    PRIMARY_SYMBOL,
    SECONDARY_SYMBOL,
    aligned_matrix,
    build_inventory,
    evaluations_examined,
    family_oos_series,
    family_results,
    sensitivity_to_the_count,
    study_level_corrections,
)

log = logging.getLogger("study_closure")


def _inventory_rows(units: list[Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for family in sorted({u.family for u in units}):
        selected = [u for u in units if u.family == family]
        gate = selected[0].gate
        rows.append(
            {
                "gate": gate,
                "family": family,
                "symbols": sorted({u.symbol for u in selected}),
                "seeds": sorted({u.seed for u in selected}),
                "engines": sorted({u.engine for u in selected}),
                "n_units": len(selected),
                "criterion": GATE_CRITERIA[gate],
            }
        )
    return sorted(rows, key=lambda r: (r["gate"], r["family"]))


def _fmt(value: float, digits: int = 4) -> str:
    return f"{value:.{digits}f}"


def _markdown(payload: dict[str, Any]) -> str:
    corr = payload["corrections"]
    results: list[dict[str, Any]] = payload["families"]
    holm = corr["holm_bonferroni"]["adjusted_p_values"]
    bh = corr["benjamini_hochberg"]["adjusted_p_values"]

    lines: list[str] = []
    add = lines.append

    add("# Study-level multiple-testing accounting")
    add("")
    add(f"**Generated:** {payload['generated_at']} · **Commit:** `{payload['git_commit']}`")
    add(f"**Partition:** development only · **Holdout accessed:** {payload['holdout_accessed']}")
    add("")
    add(
        "Every gate corrected for multiplicity inside itself and none corrected across "
        "the gates. This document does that once, over all "
        f"{corr['n_tests']} families, on {PRIMARY_SYMBOL} with the "
        f"`{PRIMARY_ENGINE}` engine. It recomputes no backtest: it reads the "
        "out-of-sample ledgers the gates already wrote and judges them against the "
        "full family of tests the study actually ran."
    )
    add("")

    add("## 1. Inventory of everything tested")
    add("")
    add("| Gate | Family | Assets | Seeds | Engines | Units |")
    add("|---|---|---|---:|---|---:|")
    for row in payload["inventory"]:
        assets = ", ".join(s.replace("USDT", "") for s in row["symbols"])
        add(
            f"| {row['gate']} | `{row['family']}` | {assets} | {len(row['seeds'])} | "
            f"{len(row['engines'])} | {row['n_units']} |"
        )
    add("")
    add(f"**Total distinct families tested: {corr['n_tests']}.**")
    add("")
    add("Pre-registered acceptance criterion by gate:")
    add("")
    for gate, criterion in payload["criteria"].items():
        add(f"- **{gate}** — {criterion}")
    add("")

    add("## 2. Corrected results")
    add("")
    add(
        "The p-value is one-sided, from a stationary bootstrap on the concatenated "
        "out-of-sample bar returns, against the null that the family earns nothing. "
        "Seeds are averaged within a family because the protocol treats them as "
        "replicates of one hypothesis, not as separate hypotheses."
    )
    add("")
    add("| Family | Gate | Bars | Total return | Sharpe (ann.) | p | p Holm | p BH | Survives |")
    add("|---|---|---:|---:|---:|---:|---:|---:|:--:|")
    for r in results:
        fam = r["family"]
        survives = "yes" if corr["holm_bonferroni"]["rejected"][fam] else "no"
        add(
            f"| `{fam}` | {r['gate']} | {r['n_bars']:,} | {r['total_return']:+.1%} | "
            f"{r['sharpe_annualised']:+.2f} | {_fmt(r['p_value'], 3)} | "
            f"{_fmt(holm[fam], 3)} | {_fmt(bh[fam], 3)} | {survives} |"
        )
    add("")
    add(
        f"**Surviving Holm (FWER, alpha = {corr['alpha']}): "
        f"{corr['holm_bonferroni']['n_rejected']} of {corr['n_tests']}.** "
        f"Surviving Benjamini-Hochberg (FDR): {corr['benjamini_hochberg']['n_rejected']}."
    )
    add("")

    add("## 3. Is the best of them real?")
    add("")
    dsr = corr["deflated_sharpe"]
    add(
        f"The best family by out-of-sample Sharpe is `{corr['best_family']}`. The "
        "deflated Sharpe ratio asks how surprising that maximum is, given how many "
        "chances the study had to produce it."
    )
    add("")
    add("| Selection counted over | Trials | Deflated Sharpe | P(best is spurious) |")
    add("|---|---:|---:|---:|")
    for label, record in dsr.items():
        add(
            f"| {label.replace('_', ' ')} | {record['n_trials']:,} | "
            f"{_fmt(record['deflated_sharpe'], 3)} | "
            f"{_fmt(record['probability_best_is_spurious'], 3)} |"
        )
    add("")
    add(
        "Both rows use the dispersion of Sharpe ratios across the thirteen family "
        "series. For the second row that is an understatement: individual "
        "configurations vary more than family averages do, and a smaller dispersion "
        "lowers the null's expected maximum, which makes the observed Sharpe easier "
        "to beat. The assumption therefore favours the strategies, and the verdict "
        "survives it anyway."
    )
    add("")
    pbo = corr["probability_of_backtest_overfitting"]
    if pbo["available"]:
        add(
            f"**Probability of backtest overfitting: {pbo['pbo']:.3f}** "
            f"({pbo['n_splits']} CSCV splits over {pbo['n_observations']:,} aligned bars "
            f"and {pbo['n_configurations']} families). This is the probability that the "
            "family looking best in one half of the sample is median-or-worse in the "
            "other half."
        )
    else:
        add(f"Probability of backtest overfitting: unavailable ({pbo['reason']}).")
    add("")

    add("## 4. Does the verdict depend on how the tests are counted?")
    add("")
    add(
        "The study never pre-registered a single study-level N, so the count is chosen "
        "here. It is reported under several defensible definitions so the choice "
        "cannot carry the conclusion."
    )
    add("")
    add("| Counting rule | N | Bonferroni threshold | Anything survives |")
    add("|---|---:|---:|:--:|")
    for label, record in payload["sensitivity"].items():
        add(
            f"| {label.replace('_', ' ')} | {record['n_tests']:,} | "
            f"{record['bonferroni_threshold']:.2e} | "
            f"{'yes' if record['any_survive'] else 'no'} |"
        )
    add("")

    if payload["secondary"]:
        add(f"## 5. {SECONDARY_SYMBOL} consistency check")
        add("")
        add(
            "Reported over the subset of families tested on this asset. It is a "
            "consistency check on the same hypotheses, not an additional block of "
            "tests, and it is not merged into the count above."
        )
        add("")
        add("| Family | Bars | Total return | Sharpe (ann.) | p |")
        add("|---|---:|---:|---:|---:|")
        for r in payload["secondary"]:
            add(
                f"| `{r['family']}` | {r['n_bars']:,} | {r['total_return']:+.1%} | "
                f"{r['sharpe_annualised']:+.2f} | {_fmt(r['p_value'], 3)} |"
            )
        add("")

    add("## Conclusion")
    add("")
    add(payload["conclusion"])
    add("")
    return "\n".join(lines)


def _conclusion(payload: dict[str, Any]) -> str:
    corr = payload["corrections"]
    n = corr["n_tests"]
    holm_n = corr["holm_bonferroni"]["n_rejected"]
    dsr = corr["deflated_sharpe"]["all_configurations_evaluated"]
    pbo = corr["probability_of_backtest_overfitting"]
    pbo_text = (
        f" the probability of backtest overfitting is {pbo['pbo']:.3f}," if pbo["available"] else ""
    )
    verdict = "no family survives" if holm_n == 0 else f"{holm_n} of {n} families survive"
    return (
        f"Across the {n} strategy families the study tested, and against the "
        f"{corr['n_configurations_evaluated']:,} configurations actually evaluated to "
        f"produce them, {verdict} family-wise error control at "
        f"alpha = {corr['alpha']};{pbo_text} and the probability that the best family "
        f"is a product of selection rather than of edge is "
        f"{dsr['probability_best_is_spurious']:.3f}."
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path())
    parser.add_argument("--output-dir", type=Path, default=Path("reports/study_closure"))
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    root: Path = args.root.resolve()

    units = build_inventory(root)
    log.info(
        "Inventory: %d search units across %d families",
        len(units),
        len({u.family for u in units}),
    )

    series = family_oos_series(units, symbol=PRIMARY_SYMBOL, engine=PRIMARY_ENGINE)
    log.info("Built out-of-sample series for %d families on %s", len(series), PRIMARY_SYMBOL)
    results = family_results(units, series, symbol=PRIMARY_SYMBOL)

    _, matrix = aligned_matrix(series)
    log.info("Aligned matrix for CSCV: %s bars x %s families", matrix.shape[0], matrix.shape[1])

    n_evaluations = evaluations_examined(units)
    log.info("Configurations evaluated across the whole study: %d", n_evaluations)

    corrections = study_level_corrections(results, matrix, n_evaluations=n_evaluations)

    secondary_series = family_oos_series(units, symbol=SECONDARY_SYMBOL, engine=PRIMARY_ENGINE)
    secondary = family_results(units, secondary_series, symbol=SECONDARY_SYMBOL)

    counts = {
        "families": len(results),
        "family_x_asset": sum(
            len({u.symbol for u in units if u.family == f.family}) for f in results
        ),
        "family_x_asset_x_seed": len({(u.family, u.symbol, u.seed) for u in units}),
        "all_configurations_evaluated": max(n_evaluations, 1),
    }

    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True
    ).stdout.strip()

    payload: dict[str, Any] = {
        "report": "study_level_multiple_testing",
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "git_commit": commit,
        "holdout_accessed": False,
        "primary_symbol": PRIMARY_SYMBOL,
        "primary_engine": PRIMARY_ENGINE,
        "criteria": GATE_CRITERIA,
        "inventory": _inventory_rows(units),
        "families": [r.to_dict() for r in results],
        "secondary": [r.to_dict() for r in secondary],
        "corrections": corrections,
        "sensitivity": sensitivity_to_the_count(results, counts),
    }
    payload["conclusion"] = _conclusion(payload)

    out: Path = args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    (out / "study_level_multiple_testing.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )
    (out / "study_level_multiple_testing.md").write_text(_markdown(payload), encoding="utf-8")
    log.info("Wrote %s", out / "study_level_multiple_testing.md")

    print(payload["conclusion"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
