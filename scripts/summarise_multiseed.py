"""Print the headline multi-seed table: OOS coverage, bootstrap intervals, tallies.

Reads only the study's own artifacts, so every number here is traceable to a file
under the study directory. Nothing is recomputed or estimated.
"""

from __future__ import annotations

import argparse
import json
import statistics as st
from pathlib import Path

BLOCK = "block_168"  # one week of hourly bars


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("study_dir", type=Path)
    args = parser.parse_args()

    robustness = json.loads((args.study_dir / "study_robustness.json").read_text("utf-8"))
    analysis = json.loads((args.study_dir / "multi_seed_analysis.json").read_text("utf-8"))
    manifest = json.loads((args.study_dir / "study_manifest.json").read_text("utf-8"))

    runs = list(robustness["per_run"].values())
    print(f"Study        : {manifest['study_id']}")
    print(
        f"Units        : {manifest['n_units']}  ({len(manifest['symbols'])} assets "
        f"x {len(manifest['seeds'])} seeds)"
    )
    print(f"Base seeds   : {manifest['seeds']}")
    if runs:
        print(
            f"OOS window   : {runs[0]['oos_start'][:10]} .. {runs[0]['oos_end'][:10]}  "
            f"({runs[0]['n_bars']} bars per run, identical for every seed)"
        )

    print("\nPer asset and engine (10 seeds each)")
    header = (
        f"{'symbol / engine':<34}{'positive':>9}{'>B&H':>7}{'2x cost':>9}{'CI>0':>6}"
        f"{'median ret':>12}{'B&H ret':>10}{'median bootstrap Sharpe CI':>30}"
    )
    print(header)
    print("-" * len(header))
    for symbol in sorted({r["symbol"] for r in runs}):
        for engine in ("random_search", "genetic_algorithm"):
            sub = [r for r in runs if r["symbol"] == symbol and r["method"] == engine]
            if not sub:
                continue
            tally = robustness["by_symbol_and_engine"][f"{symbol}|{engine}"]
            lo = st.median(r["bootstrap_sharpe"][BLOCK]["ci_low"] for r in sub)
            hi = st.median(r["bootstrap_sharpe"][BLOCK]["ci_high"] for r in sub)
            print(
                f"{symbol + ' / ' + engine:<34}"
                f"{tally['n_positive']:>9}{tally['n_beat_buy_and_hold']:>7}"
                f"{tally['n_survive_double_costs']:>9}{tally['n_bootstrap_ci_excludes_zero']:>6}"
                f"{tally['median_total_return']:>12.4f}"
                f"{tally['median_buy_and_hold_return']:>10.4f}"
                f"{f'[{lo:+.3f}, {hi:+.3f}]':>30}"
            )

    paired = analysis["paired_rs_vs_ga"]
    # Current analyses nest the correctly collapsed calendar-fold inference in
    # ``combined``. Superseded pre-ADR-0012 studies stored the same headline
    # fields at the top level; retaining that read path lets this script compare
    # old and new evidence without rewriting historical artifacts.
    combined = paired.get("combined", paired)
    print("\nPaired GA - RS (seeds averaged within each symbol x fold cell)")
    print(f"  cells                : {paired['n_cells_symbol_seed_fold']}")
    print(f"  units of inference   : {paired['n_independent_units_used']}")
    print(f"  mean difference      : {paired['mean_difference_ga_minus_rs']:+.4f}")
    print(f"  95% CI               : [{combined['ci_low']:+.4f}, {combined['ci_high']:+.4f}]")
    print(f"  effect size (dz)     : {combined['effect_size_cohens_dz']:+.3f}")
    print(f"  verdict              : {paired['verdict']}")

    vd = analysis["variance_decomposition"]
    print("\nWhere the variation comes from")
    for engine in ("random_search", "genetic_algorithm"):
        payload = vd[engine]
        print(
            f"  {engine:<20} seed sd (same data) {payload['seed_variability']['mean_sd_within_symbol_fold']:.4f}"
            f"   fold sd (market) {payload['fold_level_mean']['sd']:.4f}"
            f"   ratio {vd['seed_to_fold_sd_ratio']['values'][engine]:.3f}"
        )

    promo = robustness.get("r3_promotion", {})
    if promo:
        print(
            f"\nGate R3 promotion ({promo.get('engine', 'random_search')}): {promo.get('verdict')}"
        )
        for symbol, report in sorted(promo.get("by_symbol", {}).items()):
            passed = sum(1 for row in report["promotion"].values() if row["pass"])
            print(
                f"  {symbol}: {passed}/{len(report['promotion'])} criteria pass "
                f"(need {report['majority_required']}/{report['n_seeds']})"
            )
        if promo.get("triggered_rejections"):
            print("  rejections:", "; ".join(promo["triggered_rejections"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
