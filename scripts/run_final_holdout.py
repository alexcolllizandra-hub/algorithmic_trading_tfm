"""Piece 3 of the study closure: open the frozen holdout, once.

The candidate and the selection rule are frozen in
`docs/methodology/final_holdout_evaluation.md`, committed before this runs.

Validate the machinery without opening anything:

    uv run python scripts/run_final_holdout.py --partition development

Open the frozen holdout (irreversible, once):

    uv run python scripts/run_final_holdout.py --partition holdout --confirm-open-holdout
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any

from perp_lab.config.settings import load_data_contract, load_experiment_config, load_settings
from perp_lab.experiments.final_holdout import (
    build_slices,
    buy_and_hold,
    evaluate_candidate,
    load_frozen_candidate,
    provenance,
)
from perp_lab.reporting.study_closure import PRIMARY_ENGINE, PRIMARY_SYMBOL, build_inventory

log = logging.getLogger("final_holdout")

CANDIDATE_FAMILY = "volatility_breakout"
TIMEFRAME = "1h"
REGIME_SEED = 42


def _markdown(payload: dict[str, Any]) -> str:
    prov = payload["provenance"]
    result = payload["result"]
    combined = result["combined"]
    bh = payload["buy_and_hold"]
    lines: list[str] = []
    add = lines.append

    research = prov["is_research_result"]
    add("# Final holdout evaluation — result")
    add("")
    if not research:
        add(
            "> **SMOKE TEST, NOT A RESULT.** This run evaluated the development "
            "partition, whose bars trained and selected the very parameters being "
            "replayed. It exists only to prove the machinery works. The numbers "
            "below mean nothing and must not be quoted."
        )
    else:
        add(
            "> **The frozen holdout was opened once, here.** This is the honest "
            "result of the best available candidate. It is not a promoted strategy, "
            "and no threshold is attached to it, because nothing was promoted."
        )
    add("")
    add(f"**Opened:** {prov['opened_at']} · **Commit:** `{prov['git']['commit']}`")
    add(f"**Worktree clean:** {prov['git']['worktree_clean']}")
    add(f"**Partition evaluated:** {prov['partition_evaluated']}")
    add("")

    add("## The candidate, as frozen")
    add("")
    cand = prov["candidate"]
    add(
        f"`{cand['family']}` on {cand['symbol']} {cand['timeframe']}, "
        f"{cand['engine']}, fold {cand['fold']} winner of each of "
        f"{cand['n_members']} seeds, equally weighted."
    )
    add("")
    add("| Seed | Selection fingerprint | Candidate |")
    add("|---|---|---|")
    for member in cand["members"]:
        add(
            f"| {member['seed']} | `{member['selection_fingerprint']}` | "
            f"`{member['candidate_id']}` |"
        )
    add("")

    add("## Datasets opened")
    add("")
    add("| Dataset | Rows | SHA-256 | Role |")
    add("|---|---:|---|---|")
    for name, record in prov["dataset_hashes"].items():
        sha = str(record.get("sha256") or "")
        add(
            f"| `{name}` | {record.get('rows', 0):,} | `{sha[:16]}…` | "
            f"{record.get('role', 'funding')} |"
        )
    add("")

    add("## Result")
    add("")
    add(
        f"Window: {result['window']['start']} .. {result['window']['end']} ({result['n_bars']:,} bars)"
    )
    add("")
    add("| Metric | Candidate | Buy and hold |")
    add("|---|---:|---:|")
    rows = [
        ("Total net return", "total_return", "{:+.2%}"),
        ("Annualised return", "ann_return", "{:+.2%}"),
        ("Sharpe", "sharpe", "{:+.2f}"),
        ("Sortino", "sortino", "{:+.2f}"),
        ("Maximum drawdown", "max_drawdown", "{:.2%}"),
        ("Annualised volatility", "ann_volatility", "{:.2%}"),
        ("Exposure", "exposure", "{:.1%}"),
        ("Trades", "n_trades", "{:.0f}"),
    ]
    for label, key, fmt in rows:
        left = combined.get(key)
        right = bh.get(key)
        add(
            f"| {label} | {fmt.format(left) if left is not None else '—'} | "
            f"{fmt.format(right) if right is not None else '—'} |"
        )
    add("")

    paid = result["costs_paid"]
    add(
        f"Costs actually paid over the window: {paid['fees_and_slippage']:+.2%} in fees "
        f"and slippage and {paid['funding']:+.2%} in funding, "
        f"{paid['total']:+.2%} in total, as a fraction of equity."
    )
    add("")

    add("### Per seed")
    add("")
    add("| Seed | Total return | Sharpe | Trades |")
    add("|---|---:|---:|---:|")
    for member in result["per_member"]:
        m = member["metrics"]
        add(
            f"| {member['seed']} | {m.get('total_return', 0):+.2%} | "
            f"{m.get('sharpe', 0):+.2f} | {m.get('n_trades', 0):.0f} |"
        )
    add("")

    add("## Cost model and regime, as frozen")
    add("")
    costs = prov["costs"]
    add(
        f"Fees {costs['fee_bps_per_side']} bps per side, slippage "
        f"{costs['slippage_bps_per_side']} bps per side, funding "
        f"{costs['funding_treatment']}; annualised over "
        f"{prov['annualization_days']} days. The regime model was fitted on "
        f"{prov['regime']['fit_bars']:,} development bars and applied forward; no "
        "evaluation bar informed its boundaries."
    )
    add("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path())
    parser.add_argument("--partition", choices=("development", "holdout"), default="development")
    parser.add_argument(
        "--confirm-open-holdout",
        action="store_true",
        help="Required to read the frozen holdout. Opening it is irreversible.",
    )
    parser.add_argument("--output-dir", type=Path, default=Path("reports/study_closure"))
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    root: Path = args.root.resolve()

    if args.partition == "holdout" and not args.confirm_open_holdout:
        log.error(
            "Refusing to read the frozen holdout without --confirm-open-holdout. "
            "It may be opened exactly once."
        )
        return 2

    units = [
        u
        for u in build_inventory(root)
        if u.family == CANDIDATE_FAMILY
        and u.symbol == PRIMARY_SYMBOL
        and u.engine == PRIMARY_ENGINE
    ]
    run_dirs = {u.seed: u.run_dir for u in units}
    candidate = load_frozen_candidate(
        run_dirs,
        family=CANDIDATE_FAMILY,
        symbol=PRIMARY_SYMBOL,
        timeframe=TIMEFRAME,
        engine=PRIMARY_ENGINE,
    )
    log.info(
        "Frozen candidate: %s, fold %d, %d seeds",
        candidate.family,
        candidate.fold,
        len(candidate.members),
    )

    settings = load_settings()
    exp = load_experiment_config(Path("configs/experiment.yaml"))
    contract = load_data_contract(Path("configs/data_contract.yaml"))

    if args.partition == "holdout":
        log.warning("OPENING THE FROZEN HOLDOUT. This is the single authorised read.")

    slices = build_slices(
        candidate,
        partition=args.partition,
        exp=exp,
        contract=contract,
        paths=settings.paths,
        regime_seed=REGIME_SEED,
    )
    log.info(
        "Regime fitted on %d bars; evaluating %d bars", slices.fit.height, slices.evaluate.height
    )

    result = evaluate_candidate(candidate, slices, exp=exp)
    bh = buy_and_hold(slices.evaluate, timeframe=TIMEFRAME, days_per_year=exp.annualization_days)

    payload: dict[str, Any] = {
        "report": "final_holdout_evaluation",
        "provenance": provenance(candidate, slices, root=root, partition=args.partition, exp=exp),
        "result": result,
        "buy_and_hold": bh,
    }

    out: Path = args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    suffix = "" if args.partition == "holdout" else "_smoke"
    (out / f"final_holdout{suffix}.json").write_text(
        json.dumps(payload, indent=2, default=str), encoding="utf-8"
    )
    (out / f"final_holdout{suffix}.md").write_text(_markdown(payload), encoding="utf-8")
    log.info("Wrote %s", out / f"final_holdout{suffix}.md")

    combined = result["combined"]
    print(
        f"{args.partition}: total_return={combined.get('total_return', 0):+.4%} "
        f"sharpe={combined.get('sharpe', 0):+.3f} "
        f"max_dd={combined.get('max_drawdown', 0):.2%} "
        f"trades={combined.get('n_trades', 0):.0f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
