"""Report for the M1/M2 meta-labeling validation on synthetic markets.

**EXPLORATORY / INFRASTRUCTURE-ONLY.** Every number in this report is computed on
generated data. Nothing here is a claim about BTC or ETH, nothing here promotes,
rejects or closes a family, and nothing here is an operational candidate. The
frozen holdout is not addressable from this module.

The report is built around one comparison and one control:

* on the **signal** market a real edge was planted, so a working layer must
  improve ``primary_only`` measurably;
* on the **noise** market nothing was planted, so a working layer must **not**
  produce out-of-sample profit — and "improved the primary" is not evidence of
  anything there, because filtering a rule that only pays costs always improves
  it. The decisive column is therefore *profitable folds*, not *improved folds*.

A verdict is emitted for the machinery, not for a strategy: it states whether the
implementation behaved correctly on data whose ground truth is known.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

from perp_lab.meta_labeling.study import MarketStudy

BANNER = "EXPLORATORY / INFRASTRUCTURE-ONLY - synthetic data, no operational candidate"

#: What the machinery must do to be considered validated. Fixed before the runs.
SIGNAL_MIN_IMPROVED_SHARE = 0.6
SIGNAL_MIN_PR_AUC_LIFT = 1.05
NOISE_MAX_PR_AUC_LIFT = 1.15


def _share(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else float("nan")


def _verdict(signal: Sequence[MarketStudy], noise: Sequence[MarketStudy]) -> dict[str, Any]:
    """Did the layer behave as it must on data whose answer is already known?

    Three checks, all pre-specified:

    1. on the planted-edge market the filter improves the primary in most folds;
    2. on that same market the probabilities carry information (PR-AUC lift
       above the base rate);
    3. on the pure-noise control the layer does **not** end up profitable out of
       sample and its probabilities carry no information.

    Check 3 is deliberately expressed on realised profit rather than on
    abstention alone. Abstention is the mechanism; not making money on noise is
    the property that matters, and a layer could satisfy the second without the
    first by acting and losing.
    """
    signal_folds = [f for s in signal for f in s.folds]
    noise_folds = [f for s in noise for f in s.folds]
    signal_lift = [
        f.test_predictive.pr_auc_lift for f in signal_folds if f.test_predictive is not None
    ]
    noise_lift = [
        f.test_predictive.pr_auc_lift for f in noise_folds if f.test_predictive is not None
    ]
    signal_improved = _share(sum(f.net_return_delta > 0 for f in signal_folds), len(signal_folds))
    noise_total = float(np.median([s.arm_total("primary_plus_meta_labeling") for s in noise]))
    median_signal_lift = float(np.median(signal_lift)) if signal_lift else float("nan")
    median_noise_lift = float(np.median(noise_lift)) if noise_lift else float("nan")

    # A control on which the layer never acted has no probabilities to score.
    # That is the ideal outcome, not a missing result: it declined every fold.
    noise_uninformative = not noise_lift or median_noise_lift <= NOISE_MAX_PR_AUC_LIFT
    checks = {
        "signal_improves_primary": bool(signal_improved >= SIGNAL_MIN_IMPROVED_SHARE),
        "signal_probabilities_informative": bool(median_signal_lift >= SIGNAL_MIN_PR_AUC_LIFT),
        "noise_not_profitable": bool(noise_total <= 0.0),
        "noise_probabilities_uninformative": bool(noise_uninformative),
    }
    acted = sum(not f.abstained for f in noise_folds)
    return {
        "checks": checks,
        "machinery_validated": all(checks.values()),
        "signal_improved_share": signal_improved,
        "signal_median_pr_auc_lift": median_signal_lift,
        "noise_median_pr_auc_lift": median_noise_lift,
        "noise_median_meta_total_return": noise_total,
        "noise_folds_acted": acted,
        "noise_folds": len(noise_folds),
        "noise_folds_profitable": sum(f.test_meta.net_return > 0.0 for f in noise_folds),
    }


def build_synthetic_validation_report(
    signal_studies: Sequence[MarketStudy],
    noise_studies: Sequence[MarketStudy],
    *,
    seeds: Sequence[int],
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    """Assemble the machine-readable report from both markets' studies."""
    if not signal_studies or not noise_studies:
        raise ValueError(
            "Both markets are required: a signal result without its noise control "
            "is not evidence that the machinery works."
        )
    return {
        "banner": BANNER,
        "generated_at": (generated_at or datetime.now(UTC)).isoformat(),
        "holdout_accessed": False,
        "data": "synthetic",
        "seeds": list(seeds),
        "verdict": _verdict(signal_studies, noise_studies),
        "signal": [s.to_dict() for s in signal_studies],
        "noise": [s.to_dict() for s in noise_studies],
    }


def _number(value: Any, spec: str = ".3f") -> str:
    if value is None:
        return "n/a"
    number = float(value)
    return "n/a" if not np.isfinite(number) else format(number, spec)


def _summaries(report: Mapping[str, Any], market: str) -> list[tuple[int, dict[str, Any]]]:
    return [
        (seed, payload["summary"])
        for seed, payload in zip(report["seeds"], report[market], strict=True)
    ]


def _arm_rows(report: Mapping[str, Any], market: str) -> list[str]:
    rows = []
    for seed, summary in _summaries(report, market):
        rows.append(
            f"| {market} | {seed} | {summary['n_folds']} | {summary['folds_acted']} | "
            f"{_number(summary['primary_only_total_return'], '+.2%')} | "
            f"{_number(summary['primary_plus_meta_total_return'], '+.2%')} | "
            f"{summary['folds_improved']}/{summary['n_folds']} | "
            f"{summary['folds_profitable']}/{summary['n_folds']} | "
            f"{_number(summary['median_net_return_delta'], '+.3f')} | "
            f"{_number(summary['delta_stability_sd'])} |"
        )
    return rows


def _predictive_rows(report: Mapping[str, Any], market: str) -> list[str]:
    rows = []
    for seed, summary in _summaries(report, market):
        rows.append(
            f"| {market} | {seed} | {_number(summary['median_pr_auc'])} | "
            f"{_number(summary['median_pr_auc_lift'])} | {_number(summary['median_roc_auc'])} | "
            f"{_number(summary['median_brier'])} | "
            f"{_number(summary['primary_plus_meta_median_sharpe'], '+.2f')} |"
        )
    return rows


def _fold_rows(report: Mapping[str, Any], market: str) -> list[str]:
    rows = []
    for seed, payload in zip(report["seeds"], report[market], strict=True):
        for fold in payload["folds"]:
            predictive = fold["test_predictive"]
            rows.append(
                f"| {market} | {seed} | {fold['fold']} | {fold['selected_model'] or '-'} | "
                f"{'yes' if fold['abstained'] else 'no'} | {fold['n_train']} | "
                f"{fold['n_test']} | {_number(fold['test_signal_rate'], '.2f')} | "
                f"{_number(fold['test_primary']['net_return'], '+.2%')} | "
                f"{_number(fold['test_meta']['net_return'], '+.2%')} | "
                f"{_number(predictive['pr_auc'] if predictive else None)} | "
                f"{_number(predictive['roc_auc'] if predictive else None)} |"
            )
    return rows


def _model_competition(report: Mapping[str, Any], market: str) -> list[str]:
    chosen: dict[str, int] = {}
    for payload in report[market]:
        for fold in payload["folds"]:
            for candidate in fold["candidates"]:
                if not candidate["available"]:
                    chosen.setdefault(f"{candidate['model']} (unavailable)", 0)
            name = fold["selected_model"]
            if name is not None:
                chosen[name] = chosen.get(name, 0) + 1
    return [f"| {market} | `{name}` | {count} |" for name, count in sorted(chosen.items())]


def render_synthetic_validation_markdown(report: Mapping[str, Any]) -> str:
    """Render the report as Markdown, verdict first."""
    verdict = report["verdict"]
    status = "MACHINERY VALIDATED" if verdict["machinery_validated"] else "MACHINERY NOT VALIDATED"
    lines = [
        "# M1/M2 meta-labeling - validation on synthetic data",
        "",
        f"> **{BANNER}**",
        "",
        f"**Verdict: {status}.** This states that the implementation behaves "
        "correctly on markets whose ground truth is known. It is not a trading "
        "result, not a candidate, and not evidence about any real asset. No S2 "
        "family fired the partial-signal criterion, so there is no eligible primary "
        "strategy; this run validates the machinery in advance of one.",
        "",
        f"Holdout accessed: **{'yes' if report['holdout_accessed'] else 'no'}**. "
        f"Data: **{report['data']}**. Seeds: "
        f"{', '.join(str(s) for s in report['seeds'])}.",
        "",
        "## Pre-specified checks",
        "",
        "| Check | Result |",
        "|---|---|",
    ]
    lines += [
        f"| `{name}` | {'PASS' if passed else 'FAIL'} |"
        for name, passed in verdict["checks"].items()
    ]
    lines += [
        "",
        f"Signal market: the filter improved the primary in "
        f"{verdict['signal_improved_share']:.0%} of folds, with a median PR-AUC lift "
        f"of {_number(verdict['signal_median_pr_auc_lift'])}. Noise control: the layer "
        f"acted in {verdict['noise_folds_acted']} of {verdict['noise_folds']} folds and "
        f"was profitable in {verdict['noise_folds_profitable']}, with a median PR-AUC "
        f"lift of {_number(verdict['noise_median_pr_auc_lift'])} and a median filtered "
        f"return of {_number(verdict['noise_median_meta_total_return'], '+.2%')}.",
        "",
        "## primary_only vs primary_plus_meta_labeling (test blocks only)",
        "",
        "Returns compound the disjoint test blocks of every fold. *Improved* counts "
        "folds where the filter beat the primary; *profitable* counts folds where the "
        "filtered arm actually made money. On the noise control the two diverge, and "
        "only the second one means anything: filtering a rule that pays nothing but "
        "costs always improves it.",
        "",
        "| Market | Seed | Folds | Acted | primary_only | primary_plus_meta | "
        "Improved | Profitable | Median delta | Delta SD |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    lines += _arm_rows(report, "signal") + _arm_rows(report, "noise")

    lines += [
        "",
        "## Predictive metrics (test blocks only)",
        "",
        "PR-AUC is the headline because the meta-label is imbalanced after costs; "
        "ROC-AUC is secondary. `pr_auc_lift` divides PR-AUC by the block's base rate, "
        "so 1.0 means the model is worth exactly nothing.",
        "",
        "| Market | Seed | PR-AUC | PR-AUC lift | ROC-AUC | Brier | Meta Sharpe |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    lines += _predictive_rows(report, "signal") + _predictive_rows(report, "noise")

    lines += [
        "",
        "## Model competition",
        "",
        "Logistic regression is the interpretable baseline and is reported whether it "
        "wins or loses. The winner is chosen on validation economics only; AUC never "
        "selects a model.",
        "",
        "| Market | Model | Folds won |",
        "|---|---|---:|",
    ]
    lines += _model_competition(report, "signal") + _model_competition(report, "noise")

    lines += [
        "",
        "## Per fold",
        "",
        "| Market | Seed | Fold | Model | Abstained | Train events | Test events | "
        "Signal rate | primary_only | primary_plus_meta | PR-AUC | ROC-AUC |",
        "|---|---:|---:|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    lines += _fold_rows(report, "signal") + _fold_rows(report, "noise")

    lines += [
        "",
        "## What this does not establish",
        "",
        "- No claim about BTC, ETH or any traded market. The data is generated.",
        "- No operational candidate. The primary rule here is a synthetic momentum"
        " rule chosen to leave room for a filter, not a strategy that passed a gate.",
        "- The planted edge is stationary and known. Real edges are neither, so the"
        " measured improvement is an upper bound on what the same machinery would"
        " achieve on real data.",
        "- The frozen holdout was not read, and no exchange endpoint was contacted.",
        "",
    ]
    return "\n".join(lines)


def write_synthetic_validation_report(
    report: Mapping[str, Any], output_dir: Path
) -> dict[str, Path]:
    """Write the JSON payload and its Markdown rendering side by side."""
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "meta_labeling_synthetic.json"
    markdown_path = output_dir / "meta_labeling_synthetic.md"
    json_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    markdown_path.write_text(render_synthetic_validation_markdown(report), encoding="utf-8")
    return {"json": json_path, "markdown": markdown_path}
