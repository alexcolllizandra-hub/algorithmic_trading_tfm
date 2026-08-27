"""Gate S2-B development-pilot analysis, built from persisted run artifacts.

**This module produces DEVELOPMENT-ONLY evidence. It does not promote, reject or
close anything.** The frozen holdout is never read; the only inputs are the
artifacts written by the 18 completed `perp-lab search` runs plus the separately
computed common-candidate PBO.

What S2-B is allowed to decide
------------------------------
Exactly one thing: whether the frozen **partial-signal criterion** in
``docs/roadmap/gate_s2_batch_01.md`` section 9 fires, which would authorise
*preparing* (never running) an S2-C study. The criterion is stated over a
majority of seeds precisely so a single lucky seed cannot trigger it.

Everything else in the report is description.

Reporting granularity
---------------------
The pilot varies family x asset x seed and every run evaluates both engines over
every fold, so results are reported at that full granularity rather than
collapsed to a family average. Collapsing would hide exactly the dispersion the
multi-seed design exists to expose.

Multiple-testing accounting
---------------------------
* **Deflated Sharpe** per outer fold, reusing the S1-B implementation: the fold's
  own evaluations are the trials and their validation Sharpe ratios give the
  dispersion.
* **Hansen's SPA** and **White's Reality Check** across the three families'
  out-of-sample net-return series against a do-nothing benchmark, per asset.
* **Benjamini-Hochberg** over the three families' one-sided bootstrap p-values.
* **PBO** now *is* computable, unlike at S1-B, because
  :mod:`perp_lab.reporting.s2_common_candidates` evaluates a common candidate set
  across contiguous blocks. It is reported per family x asset, together with the
  window it was measured on (the part of development whose regime labels were
  fitted out of sample).

None of these corrections covers the *cumulative* burden of four development
consultations (R2, R3, S1, S2). That is recorded as the batch attempt counter and
must be read alongside them.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np

from perp_lab.evaluation.multiple_testing import (
    benjamini_hochberg,
    reality_check,
    superior_predictive_ability,
)
from perp_lab.reporting.s1_pilot import (
    BH_ALPHA,
    BLOCK_PROBABILITY,
    BOOTSTRAP_DRAWS,
    BOOTSTRAP_SEED,
    ENGINES,
    MIN_OOS_TRADES,
    PRIMARY_ENGINE,
    S1PilotError,
    _oos_returns,
    load_engine_pilot,
)

DEV_ONLY_BANNER = (
    "DEVELOPMENT-ONLY EVIDENCE. Gate S2-B is a screen, not a promotion decision. "
    "No holdout data was read."
)

# Frozen in gate_s2_batch_01.md section 9.
MIN_SEEDS_FOR_PARTIAL_SIGNAL = 2
BATCH_ATTEMPT = 1
DEVELOPMENT_CONSULTATION = 4


class S2PilotError(S1PilotError):
    """Raised when an S2-B run's artifacts are missing or internally inconsistent."""


def load_pilot_index(path: Path) -> list[dict[str, Any]]:
    """Read the (family, symbol, seed) -> run directory map written by the runner."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    entries = sorted(
        payload.values(), key=lambda e: (str(e["family"]), str(e["symbol"]), int(e["seed"]))
    )
    if not entries:
        raise S2PilotError(f"{path} lists no runs")
    return [dict(entry) for entry in entries]


def _compounded(returns: np.ndarray) -> float:
    """Compounded net return of a per-bar series, which is what a trader keeps."""
    if returns.size == 0:
        return 0.0
    return float(np.prod(1.0 + returns) - 1.0)


def _fold_rows(run_dir: Path, engine: str) -> list[dict[str, Any]]:
    """Per-fold test metrics for one engine, including folds with no winner."""
    payload = json.loads((run_dir / f"{engine}_fold_winners.json").read_text(encoding="utf-8"))
    rows: list[dict[str, Any]] = []
    for index, winner in enumerate(payload):
        metrics = winner.get("test_metrics")
        rows.append(
            {
                "fold": index + 1,
                "has_winner": metrics is not None,
                "total_return": float(metrics["total_return"]) if metrics else None,
                "sharpe": float(metrics["sharpe"]) if metrics else None,
                "n_trades": float(metrics["n_trades"]) if metrics else 0.0,
                "max_drawdown": (
                    float(metrics["max_drawdown"])
                    if metrics and "max_drawdown" in metrics
                    else None
                ),
                "params": winner.get("params") if metrics else None,
            }
        )
    return rows


def build_arm(entry: Mapping[str, Any]) -> dict[str, Any]:
    """Summarise one (family, symbol, seed) arm across both engines and all folds."""
    run_dir = Path(str(entry["run_dir"]))
    engines: dict[str, Any] = {}
    for engine in ENGINES:
        summary = load_engine_pilot(run_dir, engine).to_dict()
        oos = _oos_returns(run_dir, engine)
        net = oos["net_return"].drop_nulls().to_numpy().astype(float)
        net = net[np.isfinite(net)]
        folds = _fold_rows(run_dir, engine)
        positive = [f["fold"] for f in folds if (f["total_return"] or 0.0) > 0]
        engines[engine] = {
            **summary,
            "compounded_oos_return": _compounded(net),
            "folds": folds,
            "folds_positive": positive,
        }
    return {
        "family": str(entry["family"]),
        "symbol": str(entry["symbol"]),
        "seed": int(entry["seed"]),
        "run_dir": str(entry["run_dir"]),
        "engines": engines,
    }


def _partial_signal(arms: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Evaluate the frozen partial-signal criterion per family x asset.

    P1 positive compounded net OOS return on a majority of seeds, P2 at least
    ``MIN_OOS_TRADES`` OOS trades on every seed counted under P1, and P3 the
    positive result is not confined to a single fold. Random Search only: the GA
    is a secondary diagnostic and decides nothing.
    """
    grouped: dict[tuple[str, str], list[Mapping[str, Any]]] = {}
    for arm in arms:
        grouped.setdefault((arm["family"], arm["symbol"]), []).append(arm)

    verdicts: list[dict[str, Any]] = []
    for (family, symbol), group in sorted(grouped.items()):
        qualifying: list[int] = []
        for arm in sorted(group, key=lambda a: int(a["seed"])):
            engine = arm["engines"][PRIMARY_ENGINE]
            p1 = engine["compounded_oos_return"] > 0.0
            p2 = engine["total_test_trades"] >= MIN_OOS_TRADES
            p3 = len(engine["folds_positive"]) > 1
            if p1 and p2 and p3:
                qualifying.append(int(arm["seed"]))
        fires = len(qualifying) >= MIN_SEEDS_FOR_PARTIAL_SIGNAL
        verdicts.append(
            {
                "family": family,
                "symbol": symbol,
                "n_seeds": len(group),
                "seeds_meeting_all_conditions": qualifying,
                "seeds_required": MIN_SEEDS_FOR_PARTIAL_SIGNAL,
                "partial_signal": fires,
            }
        )
    return {
        "engine": PRIMARY_ENGINE,
        "criterion": (
            "P1 positive compounded net OOS return on a majority of seeds; "
            f"P2 at least {MIN_OOS_TRADES} OOS trades on each such seed; "
            "P3 the positive result spans more than one fold."
        ),
        "per_family_asset": verdicts,
        "any_family_fires": any(v["partial_signal"] for v in verdicts),
    }


def _family_level_snooping(
    arms: Sequence[Mapping[str, Any]], symbol: str, seed: int
) -> dict[str, Any]:
    """SPA / Reality Check across the three families, on one asset and one seed.

    The families are compared on a *common* set of out-of-sample timestamps, so
    the test asks the right question: given three strategies observed over the
    same period, is the best one better than doing nothing?
    """
    selected = {
        arm["family"]: Path(str(arm["run_dir"]))
        for arm in arms
        if arm["symbol"] == symbol and arm["seed"] == seed
    }
    families = sorted(selected)
    if len(families) < 2:
        return {"available": False, "reason": "fewer than two families for this asset and seed"}

    aligned = None
    for family in families:
        series = _oos_returns(selected[family], PRIMARY_ENGINE).rename({"net_return": family})
        aligned = series if aligned is None else aligned.join(series, on="open_time", how="inner")
    if aligned is None or aligned.height < 4:
        return {"available": False, "reason": "fewer than four aligned out-of-sample bars"}

    matrix = aligned.select(families).to_numpy().astype(float)
    matrix = matrix[np.isfinite(matrix).all(axis=1)]
    spa = superior_predictive_ability(
        matrix,
        n_bootstrap=BOOTSTRAP_DRAWS,
        block_probability=BLOCK_PROBABILITY,
        seed=BOOTSTRAP_SEED,
    )
    rc = reality_check(
        matrix,
        n_bootstrap=BOOTSTRAP_DRAWS,
        block_probability=BLOCK_PROBABILITY,
        seed=BOOTSTRAP_SEED,
    )
    return {
        "available": True,
        "symbol": symbol,
        "seed": seed,
        "engine": PRIMARY_ENGINE,
        "benchmark": "flat (no position, no costs)",
        "families": families,
        "n_aligned_observations": int(matrix.shape[0]),
        "covers": "selection across the three S2 families only",
        "does_not_cover": (
            "the evaluations spent inside each family (see the deflated Sharpe), the "
            "three seeds, the two assets, or the four cumulative development consultations"
        ),
        "hansen_spa": spa.to_dict(),
        "white_reality_check": rc.to_dict(),
    }


def build_s2_pilot_report(
    arms: Sequence[Mapping[str, Any]],
    *,
    pbo: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Assemble the DEV-ONLY S2-B report from the per-arm summaries."""
    if not arms:
        raise S2PilotError("build_s2_pilot_report needs at least one arm")

    families = sorted({str(a["family"]) for a in arms})
    symbols = sorted({str(a["symbol"]) for a in arms})
    seeds = sorted({int(a["seed"]) for a in arms})

    # BH over the three families, pooling each family's seeds on each asset via
    # the median p-value: a family is not rewarded for one lucky seed.
    bh_blocks: dict[str, Any] = {}
    for symbol in symbols:
        p_values: list[float | None] = []
        for family in families:
            values = [
                a["engines"][PRIMARY_ENGINE]["oos_bootstrap_p_value"]
                for a in arms
                if a["family"] == family and a["symbol"] == symbol
            ]
            finite = [float(v) for v in values if v is not None]
            p_values.append(float(np.median(finite)) if finite else None)
        usable = all(p is not None for p in p_values)
        rejected = (
            benjamini_hochberg([p for p in p_values if p is not None], alpha=BH_ALPHA)
            if usable
            else ()
        )
        bh_blocks[symbol] = {
            "alpha": BH_ALPHA,
            "aggregation": "median across seeds",
            "p_values": dict(zip(families, p_values, strict=True)),
            "rejected": dict(zip(families, rejected, strict=True)) if usable else {},
            "available": usable,
        }

    snooping = [_family_level_snooping(arms, symbol, seed) for symbol in symbols for seed in seeds]

    return {
        "report": "gate_s2b_development_pilot",
        "status": DEV_ONLY_BANNER,
        "holdout_accessed": False,
        "primary_engine": PRIMARY_ENGINE,
        "batch_attempt": BATCH_ATTEMPT,
        "development_partition_consultation": DEVELOPMENT_CONSULTATION,
        "families": families,
        "symbols": symbols,
        "seeds": seeds,
        "arms": list(arms),
        "partial_signal": _partial_signal(arms),
        "multiple_testing": {
            "benjamini_hochberg": bh_blocks,
            "family_level_snooping": snooping,
            "probability_of_backtest_overfitting": {
                "available": bool(pbo),
                "method": (
                    "CSCV over a common candidate set of configurations drawn from the "
                    "frozen space and evaluated across contiguous development blocks "
                    "(gate_s2_batch_01.md section 8). This is what S1-B could not do."
                ),
                "results": list(pbo),
            },
            "not_covered": (
                "the cumulative burden of four development-partition consultations "
                "(R2, R3, S1, S2); see batch_attempt and "
                "development_partition_consultation."
            ),
        },
    }


def _fmt(value: float | None, spec: str) -> str:
    if value is None or not np.isfinite(value):
        return "n/a"
    return format(value, spec)


def render_s2_pilot_markdown(report: Mapping[str, Any]) -> str:
    """Render the DEV-ONLY tables and their caveats as Markdown."""
    lines = [
        "# Gate S2-B - development pilot (DEV-ONLY)",
        "",
        f"> **{report['status']}**",
        "",
        f"Batch attempt {report['batch_attempt']}; development-partition consultation "
        f"{report['development_partition_consultation']} (R2, R3, S1, S2).",
        "",
        f"Primary engine: `{report['primary_engine']}` (confirmatory). The genetic "
        "algorithm is a secondary diagnostic and decides nothing.",
        "",
        "## Per family x asset x seed x engine",
        "",
        "| Family | Asset | Seed | Engine | Compounded OOS return | Median fold Sharpe "
        "| OOS trades | Folds with trades | Folds return > 0 | Median DSR | Viable |",
        "|---|---|---:|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for arm in report["arms"]:
        for engine in ENGINES:
            row = arm["engines"][engine]
            lines.append(
                f"| `{arm['family']}` | {arm['symbol']} | {arm['seed']} | {engine} "
                f"| {_fmt(row['compounded_oos_return'], '+.2%')} "
                f"| {_fmt(row['median_test_sharpe'], '.2f')} "
                f"| {row['total_test_trades']:.0f} "
                f"| {row['folds_with_trades']}/{row['n_folds']} "
                f"| {row['folds_positive_return']}/{row['n_folds']} "
                f"| {_fmt(row['median_deflated_sharpe'], '.3f')} "
                f"| {'yes' if row['mechanically_viable'] else 'NO'} |"
            )

    signal = report["partial_signal"]
    lines += [
        "",
        "## Partial-signal criterion (the only decision S2-B may make)",
        "",
        f"{signal['criterion']} Engine: `{signal['engine']}`.",
        "",
        "| Family | Asset | Seeds meeting all conditions | Required | Fires |",
        "|---|---|---|---:|---|",
    ]
    for verdict in signal["per_family_asset"]:
        seeds = verdict["seeds_meeting_all_conditions"]
        lines.append(
            f"| `{verdict['family']}` | {verdict['symbol']} "
            f"| {', '.join(str(s) for s in seeds) if seeds else 'none'} "
            f"| {verdict['seeds_required']} "
            f"| {'**YES**' if verdict['partial_signal'] else 'no'} |"
        )
    lines += [
        "",
        f"**Any family fires: {'YES' if signal['any_family_fires'] else 'NO'}.**",
    ]

    pbo = report["multiple_testing"]["probability_of_backtest_overfitting"]
    lines += ["", "## Probability of backtest overfitting (common candidate set)", ""]
    if pbo["available"]:
        lines += [
            pbo["method"],
            "",
            "| Family | Asset | Configurations | Blocks | PBO | Median block Sharpe |",
            "|---|---|---:|---:|---:|---:|",
        ]
        for row in pbo["results"]:
            lines.append(
                f"| `{row['family']}` | {row['symbol']} "
                f"| {row['n_candidates_evaluated']} | {row['n_blocks']} "
                f"| {row['probability_of_backtest_overfitting']:.3f} "
                f"| {row['median_block_sharpe']:+.2f} |"
            )
        first = pbo["results"][0]
        regime = first.get("regime", {})
        if regime:
            lines += [
                "",
                f"Scored window: bars from {regime['scored_from']} onward "
                f"({first['scored_bars']} of {first['development_bars']} development bars). "
                f"The frozen space includes a regime gate, so the candidates need a regime "
                f"label; the `{regime['regime_model']}` model is fitted only on the first "
                f"walk-forward training window "
                f"([{regime['regime_fit_start']}, {regime['regime_fit_end']})) and applied "
                "forward. Earlier bars would carry labels estimated from their own future, "
                "so they warm the rolling statistics up and are excluded from scoring. "
                "This narrows the frozen design's *whole development partition* to its "
                "causal part; the change is conservative and identical for all "
                "configurations.",
            ]
    else:
        lines.append("Not computed.")

    lines += ["", "## Multiple-testing accounting", ""]
    for symbol, block in report["multiple_testing"]["benjamini_hochberg"].items():
        lines += [
            f"Benjamini-Hochberg at alpha = {block['alpha']} over the three families on "
            f"**{symbol}** ({block['aggregation']} of the one-sided bootstrap p-values, "
            "null: the family earns nothing):",
            "",
            "| Family | p-value | Rejected under BH |",
            "|---|---:|---|",
        ]
        for family in report["families"]:
            p = block["p_values"].get(family)
            rejected = block["rejected"].get(family)
            lines.append(
                f"| `{family}` | {_fmt(p, '.4f')} | "
                f"{'yes' if rejected else 'no' if rejected is not None else 'n/a'} |"
            )
        lines.append("")

    available = [
        s for s in report["multiple_testing"]["family_level_snooping"] if s.get("available")
    ]
    if available:
        lines += [
            "Hansen SPA and White Reality Check across the three families "
            "(benchmark = flat), per asset and seed:",
            "",
            "| Asset | Seed | Aligned OOS bars | SPA statistic | SPA p | RC statistic | RC p |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
        for snoop in available:
            spa, rc = snoop["hansen_spa"], snoop["white_reality_check"]
            lines.append(
                f"| {snoop['symbol']} | {snoop['seed']} | {snoop['n_aligned_observations']} "
                f"| {spa['statistic']:.3f} | {spa['p_value']:.4f} "
                f"| {rc['statistic']:.3f} | {rc['p_value']:.4f} |"
            )
        lines += [
            "",
            f"These correct for {available[0]['covers']}. They do **not** correct for "
            f"{available[0]['does_not_cover']}.",
        ]

    lines += [
        "",
        f"**Not covered by any correction above:** {report['multiple_testing']['not_covered']}",
        "",
        "## What this table is not",
        "",
        "S2-B may authorise *preparing* an S2-C study and nothing else. The performance "
        "columns are descriptive: at 25 evaluations per fold they cannot evaluate the "
        "pre-registered promotion criteria C1-C6, which are defined over 10 seeds and "
        "both assets in S2-C. No family is promoted or rejected here, and no holdout "
        "data was read.",
        "",
    ]
    return "\n".join(lines)


def write_s2_pilot_report(report: Mapping[str, Any], output_dir: Path) -> dict[str, Path]:
    """Write the JSON payload and Markdown extract for the S2-B pilot."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "s2b_pilot_report.json"
    md_path = output_dir / "s2b_pilot_report.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(render_s2_pilot_markdown(report), encoding="utf-8")
    return {"json": json_path, "markdown": md_path}
