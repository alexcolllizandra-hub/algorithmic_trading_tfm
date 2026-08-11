"""Gate S1-B development-pilot analysis, built from persisted run artifacts.

**This module produces DEVELOPMENT-ONLY evidence. It does not promote, reject or
close anything.** The frozen holdout is never read; the only inputs are the
artifacts a completed `perp-lab search` run wrote under ``artifacts/runs/``.

What S1-B is allowed to decide
------------------------------
The frozen pre-specification (``docs/roadmap/gate_s1_batch_01.md`` section 3)
states that S1-B exists to surface implementation faults and families that
*cannot trade at all*, and that a family is dropped "only for a mechanical
reason -- no valid candidates, no trades, or a failed invariant -- never for weak
performance". :func:`build_s1_pilot_report` therefore reports exactly one
gating verdict, ``mechanically_viable``, and reports every performance number
next to it as description.

What the multiple-testing block does and does not cover
------------------------------------------------------
Three of the four corrections in ``evaluation/multiple_testing`` can be computed
from S1-B artifacts, and one cannot:

* **Deflated Sharpe** is computed *per outer fold*, where the fold's own 25
  evaluations are the trials and their validation Sharpe ratios give the
  dispersion. Sharpe ratios are de-annualised first, because the deflation
  formula is expressed per observation.
* **Hansen's SPA** and **White's Reality Check** are computed across the four
  families' out-of-sample net-return series against a do-nothing benchmark. They
  correct for having tried *four families*; they do not correct for the 375
  evaluations spent inside each family, which is what the deflated Sharpe covers.
* **Benjamini-Hochberg** is applied to the four families' one-sided bootstrap
  p-values.
* **PBO (CSCV) is not computable here.** CSCV needs one performance matrix of the
  same configurations across all time blocks, but ADR 0012 makes the search
  independent per outer fold, so no configuration is shared between folds. The
  report records this as unavailable rather than substituting a different
  statistic under the same name. Producing it requires evaluating a common
  candidate set across every fold, which is an S1-C task.

Skewness and kurtosis are left at their Gaussian defaults in the deflated Sharpe,
which *flatters* the result: real crypto returns are fat tailed, and accounting
for that would only lower the deflated Sharpe. An optimistic assumption cannot
manufacture a negative finding.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import polars as pl

from perp_lab.backtesting.metrics import bars_per_year
from perp_lab.evaluation.multiple_testing import (
    benjamini_hochberg,
    deflated_sharpe_ratio,
    reality_check,
    stationary_bootstrap_indices,
    superior_predictive_ability,
)
from perp_lab.utils.timeutils import timeframe_to_timedelta

ENGINES: tuple[str, ...] = ("random_search", "genetic_algorithm")
# Random Search is confirmatory; the GA is a secondary diagnostic and never
# decides anything (gate_s1_batch_01.md section 3).
PRIMARY_ENGINE = "random_search"

# Frozen in gate_s1_batch_01.md section 4. Reproduced, never adjusted here.
DEFLATED_SHARPE_THRESHOLD = 0.95
MIN_OOS_TRADES = 5
BH_ALPHA = 0.05

# Stationary-bootstrap settings for the family-level tests. A mean block length
# of 24 bars keeps a full day of hourly autocorrelation inside a block.
BOOTSTRAP_DRAWS = 2000
BLOCK_PROBABILITY = 1.0 / 24.0
BOOTSTRAP_SEED = 42

DEV_ONLY_BANNER = (
    "DEVELOPMENT-ONLY EVIDENCE. Gate S1-B is a mechanical viability screen, not a "
    "promotion decision. No holdout data was read."
)


class S1PilotError(Exception):
    """Raised when a pilot run's artifacts are missing or internally inconsistent."""


def _read_json(path: Path) -> Any:
    if not path.exists():
        raise S1PilotError(f"missing required artifact: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _median(values: list[float]) -> float | None:
    finite = [v for v in values if np.isfinite(v)]
    return float(np.median(finite)) if finite else None


def _validation_bars(run_dir: Path, timeframe: str) -> int:
    """Bars in one fold's validation window, from the persisted fold geometry."""
    payload = _read_json(run_dir / "folds.json")
    folds = payload["folds"] if isinstance(payload, dict) else payload
    if not folds:
        raise S1PilotError(f"{run_dir.name}: folds.json records no folds")
    first = folds[0]
    start = datetime.fromisoformat(str(first["val_start"]))
    end = datetime.fromisoformat(str(first["val_end"]))
    step = timeframe_to_timedelta(timeframe)
    return int((end - start) / step)


def _oos_returns(run_dir: Path, engine: str) -> pl.DataFrame:
    """Concatenated per-bar out-of-sample net returns across every outer fold.

    Test windows do not overlap under the pre-registered geometry, so the
    concatenation is a genuine contiguous out-of-sample series. That is asserted
    rather than assumed: a duplicated timestamp would mean a bar was counted
    twice.
    """
    frames = [
        pl.read_parquet(path).select("open_time", "net_return")
        for path in sorted(run_dir.glob(f"{engine}_fold*_test_equity.parquet"))
    ]
    if not frames:
        return pl.DataFrame({"open_time": [], "net_return": []})
    joined = pl.concat(frames).sort("open_time")
    if joined["open_time"].n_unique() != joined.height:
        raise S1PilotError(
            f"{run_dir.name}/{engine}: out-of-sample folds overlap in time; "
            "concatenating them would count bars twice."
        )
    return joined


def _bootstrap_p_value(returns: np.ndarray, *, seed: int) -> float | None:
    """One-sided stationary-bootstrap p-value for a positive mean bar return."""
    if returns.size < 2:
        return None
    rng = np.random.default_rng(seed)
    indices = stationary_bootstrap_indices(
        returns.size, BOOTSTRAP_DRAWS, block_probability=BLOCK_PROBABILITY, rng=rng
    )
    observed = float(returns.mean())
    # Recentred at zero: the null is "this family earns nothing".
    boot = returns[indices].mean(axis=1) - observed
    return float(np.mean(boot >= observed))


def _fold_deflated_sharpes(
    run_dir: Path, engine: str, *, timeframe: str, validation_bars: int
) -> list[dict[str, float]]:
    """Deflated Sharpe per outer fold, using that fold's own trials.

    Each fold ran its own independent search, so the trial count and the
    cross-trial Sharpe dispersion are per-fold quantities. Validation Sharpe
    ratios are annualised by the backtester and are de-annualised here, because
    the deflation formula is stated per observation.
    """
    path = run_dir / f"{engine}_candidates.parquet"
    if not path.exists():
        raise S1PilotError(f"missing required artifact: {path}")
    ledger = pl.read_parquet(path)
    scale = float(np.sqrt(bars_per_year(timeframe)))
    results: list[dict[str, float]] = []
    for (fold,), group in ledger.group_by("fold_index", maintain_order=True):
        sharpes = group["mean_val_sharpe"].drop_nulls().to_numpy().astype(float)
        sharpes = sharpes[np.isfinite(sharpes)] / scale
        if sharpes.size < 2:
            continue
        std = float(np.std(sharpes, ddof=1))
        if std <= 0:
            continue
        deflated = deflated_sharpe_ratio(
            float(sharpes.max()),
            n_trials=int(sharpes.size),
            n_observations=validation_bars,
            sharpe_std=std,
        )
        results.append({"fold": float(fold), **deflated.to_dict()})  # type: ignore[dict-item]
    return results


@dataclass(frozen=True)
class EnginePilot:
    """One family evaluated by one engine in the S1-B development pilot."""

    family: str
    engine: str
    run_id: str
    run_dir: str
    n_folds: int
    budget_per_fold: int
    n_unique_evaluations: int
    n_feasible: int
    folds_without_winner: int
    median_test_total_return: float | None
    median_test_sharpe: float | None
    total_test_trades: float
    folds_with_trades: int
    folds_positive_return: int
    oos_bars: int
    oos_mean_net_return: float | None
    oos_bootstrap_p_value: float | None
    median_deflated_sharpe: float | None
    folds_deflated_sharpe_above_threshold: int
    n_deflated_sharpe_folds: int
    mechanically_viable: bool
    viability_failures: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "family": self.family,
            "engine": self.engine,
            "run_id": self.run_id,
            "run_dir": self.run_dir,
            "n_folds": self.n_folds,
            "budget_per_fold": self.budget_per_fold,
            "n_unique_evaluations": self.n_unique_evaluations,
            "n_feasible": self.n_feasible,
            "folds_without_winner": self.folds_without_winner,
            "median_test_total_return": self.median_test_total_return,
            "median_test_sharpe": self.median_test_sharpe,
            "total_test_trades": self.total_test_trades,
            "folds_with_trades": self.folds_with_trades,
            "folds_positive_return": self.folds_positive_return,
            "oos_bars": self.oos_bars,
            "oos_mean_net_return": self.oos_mean_net_return,
            "oos_bootstrap_p_value": self.oos_bootstrap_p_value,
            "median_deflated_sharpe": self.median_deflated_sharpe,
            "folds_deflated_sharpe_above_threshold": (self.folds_deflated_sharpe_above_threshold),
            "n_deflated_sharpe_folds": self.n_deflated_sharpe_folds,
            "mechanically_viable": self.mechanically_viable,
            "viability_failures": list(self.viability_failures),
        }


def load_engine_pilot(run_dir: Path, engine: str) -> EnginePilot:
    """Summarise one engine's S1-B pilot from its persisted artifacts."""
    run_dir = Path(run_dir)
    summary = _read_json(run_dir / "comparison_summary.json")
    if engine not in summary.get("methods", {}):
        raise S1PilotError(f"{run_dir.name}: no results for engine {engine!r}")
    method = summary["methods"][engine]
    timeframe = str(summary["timeframe"])
    all_folds = _read_json(run_dir / f"{engine}_fold_winners.json")
    # A fold in which no candidate was feasible has no winner and no test slice.
    # It is a real outcome, recorded rather than dropped, but it contributes no
    # performance numbers and no freezing invariant to check.
    winners = [w for w in all_folds if "test_metrics" in w]
    folds_without_winner = len(all_folds) - len(winners)

    returns = [float(w["test_metrics"]["total_return"]) for w in winners]
    sharpes = [float(w["test_metrics"]["sharpe"]) for w in winners]
    trades = [float(w["test_metrics"]["n_trades"]) for w in winners]

    failures: list[str] = []
    if int(method["n_feasible"]) == 0:
        failures.append("no feasible candidate in any fold")
    if not winners:
        failures.append("no outer fold produced a winner")
    if sum(trades) < MIN_OOS_TRADES:
        failures.append(f"fewer than {MIN_OOS_TRADES} out-of-sample trades in total")
    if not all(bool(w.get("frozen_before_test")) for w in winners):
        failures.append("a fold winner was not frozen before its test slice")
    if any(w.get("selection_basis") != "validation_only" for w in all_folds):
        failures.append("a fold winner was selected on something other than validation")
    if not summary.get("budget_parity", {}).get("equal_effective_budget", True):
        failures.append("the engines did not spend an equal effective budget")

    oos = _oos_returns(run_dir, engine)
    net = oos["net_return"].drop_nulls().to_numpy().astype(float)
    net = net[np.isfinite(net)]
    deflated = _fold_deflated_sharpes(
        run_dir,
        engine,
        timeframe=timeframe,
        validation_bars=_validation_bars(run_dir, timeframe),
    )
    deflated_values = [d["deflated_sharpe"] for d in deflated]

    return EnginePilot(
        family=str(summary["family"]),
        engine=engine,
        run_id=str(summary.get("run_id", run_dir.name)),
        run_dir=f"artifacts/runs/{run_dir.name}",
        n_folds=int(summary["n_folds"]),
        budget_per_fold=int(summary["budget"]),
        n_unique_evaluations=int(method["n_unique_candidates"]),
        n_feasible=int(method["n_feasible"]),
        folds_without_winner=folds_without_winner,
        median_test_total_return=_median(returns),
        median_test_sharpe=_median(sharpes),
        total_test_trades=float(sum(trades)),
        folds_with_trades=int(sum(1 for t in trades if t > 0)),
        folds_positive_return=int(sum(1 for r in returns if r > 0)),
        oos_bars=int(net.size),
        oos_mean_net_return=float(net.mean()) if net.size else None,
        oos_bootstrap_p_value=_bootstrap_p_value(net, seed=BOOTSTRAP_SEED),
        median_deflated_sharpe=_median(deflated_values),
        folds_deflated_sharpe_above_threshold=int(
            sum(1 for v in deflated_values if v > DEFLATED_SHARPE_THRESHOLD)
        ),
        n_deflated_sharpe_folds=len(deflated),
        mechanically_viable=not failures,
        viability_failures=tuple(failures),
    )


def _family_level_snooping_tests(run_dirs: Mapping[str, Path]) -> dict[str, Any]:
    """SPA / Reality Check across the four families' out-of-sample series."""
    families = sorted(run_dirs)
    aligned: pl.DataFrame | None = None
    for family in families:
        series = _oos_returns(Path(run_dirs[family]), PRIMARY_ENGINE).rename({"net_return": family})
        aligned = series if aligned is None else aligned.join(series, on="open_time", how="inner")
    if aligned is None or aligned.height < 4:
        return {
            "available": False,
            "reason": "fewer than four aligned out-of-sample observations",
        }
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
        "engine": PRIMARY_ENGINE,
        "benchmark": "flat (no position, no costs)",
        "families": families,
        "n_aligned_observations": int(matrix.shape[0]),
        "covers": "selection across the four families only",
        "does_not_cover": (
            "the evaluations spent inside each family; see the deflated Sharpe ratio"
        ),
        "hansen_spa": spa.to_dict(),
        "white_reality_check": rc.to_dict(),
    }


def build_s1_pilot_report(run_dirs: Mapping[str, Path]) -> dict[str, Any]:
    """Assemble the DEV-ONLY S1-B report from one run directory per family."""
    if not run_dirs:
        raise S1PilotError("build_s1_pilot_report needs at least one family run directory")

    per_family: dict[str, Any] = {}
    for family in sorted(run_dirs):
        run_dir = Path(run_dirs[family])
        engines = {engine: load_engine_pilot(run_dir, engine).to_dict() for engine in ENGINES}
        recorded = {payload["family"] for payload in engines.values()}
        if recorded != {family}:
            raise S1PilotError(
                f"run directory {run_dir.name} records family {recorded} but was "
                f"supplied as {family!r}"
            )
        per_family[family] = {
            "engines": engines,
            # Viability is a property of the family, so a fault in either engine
            # is a fault to investigate, not something the other engine excuses.
            "mechanically_viable": all(p["mechanically_viable"] for p in engines.values()),
        }

    families = sorted(per_family)
    p_values = [per_family[f]["engines"][PRIMARY_ENGINE]["oos_bootstrap_p_value"] for f in families]
    usable = all(p is not None for p in p_values)
    bh = (
        benjamini_hochberg([p for p in p_values if p is not None], alpha=BH_ALPHA) if usable else ()
    )

    return {
        "report": "gate_s1b_development_pilot",
        "status": DEV_ONLY_BANNER,
        "holdout_accessed": False,
        "primary_engine": PRIMARY_ENGINE,
        "gating_rule": (
            "S1-B drops a family only for a mechanical reason (no valid candidates, "
            "no trades, or a failed invariant), never for weak performance "
            "(gate_s1_batch_01.md section 3)."
        ),
        "families": families,
        "per_family": per_family,
        "mechanically_viable_families": [
            f for f in families if per_family[f]["mechanically_viable"]
        ],
        "multiple_testing": {
            "deflated_sharpe_threshold": DEFLATED_SHARPE_THRESHOLD,
            "benjamini_hochberg": {
                "alpha": BH_ALPHA,
                "p_values": dict(zip(families, p_values, strict=True)),
                "rejected": dict(zip(families, bh, strict=True)) if usable else {},
                "available": usable,
            },
            "family_level_snooping": _family_level_snooping_tests(run_dirs),
            "probability_of_backtest_overfitting": {
                "available": False,
                "reason": (
                    "CSCV needs one performance matrix of the same configurations across "
                    "all time blocks. Under ADR 0012 the search is independent per outer "
                    "fold, so no configuration is shared between folds. Computing it "
                    "requires evaluating a common candidate set across every fold, which "
                    "is an S1-C task."
                ),
            },
        },
    }


def _fmt(value: float | None, spec: str) -> str:
    if value is None or not np.isfinite(value):
        return "n/a"
    return format(value, spec)


def render_s1_pilot_markdown(report: Mapping[str, Any]) -> str:
    """Render the DEV-ONLY summary table and its caveats as Markdown."""
    lines = [
        "# Gate S1-B — development pilot (DEV-ONLY)",
        "",
        f"> **{report['status']}**",
        "",
        f"Primary engine: `{report['primary_engine']}` (confirmatory). "
        "The genetic algorithm is a secondary diagnostic and decides nothing.",
        "",
        "## Per family x engine",
        "",
        "| Family | Engine | Median OOS return | Median OOS Sharpe | OOS trades "
        "| Folds w/ trades | Folds return > 0 | Feasible | Median DSR | Mechanically viable |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for family in report["families"]:
        for engine in ENGINES:
            row = report["per_family"][family]["engines"][engine]
            verdict = "yes" if row["mechanically_viable"] else "NO"
            lines.append(
                f"| `{family}` | {engine} "
                f"| {_fmt(row['median_test_total_return'], '+.2%')} "
                f"| {_fmt(row['median_test_sharpe'], '.2f')} "
                f"| {row['total_test_trades']:.0f} "
                f"| {row['folds_with_trades']}/{row['n_folds']} "
                f"| {row['folds_positive_return']}/{row['n_folds']} "
                f"| {row['n_feasible']}/{row['n_unique_evaluations']} "
                f"| {_fmt(row['median_deflated_sharpe'], '.3f')} "
                f"| {verdict} |"
            )

    bh = report["multiple_testing"]["benjamini_hochberg"]
    lines += [
        "",
        "## Multiple-testing accounting",
        "",
        f"Benjamini-Hochberg at alpha = {bh['alpha']} over the four families' one-sided "
        f"bootstrap p-values (`{report['primary_engine']}`, null: the family earns nothing):",
        "",
        "| Family | Bootstrap p-value | Rejected under BH |",
        "|---|---:|---|",
    ]
    for family in report["families"]:
        p = bh["p_values"].get(family)
        rejected = bh["rejected"].get(family)
        lines.append(
            f"| `{family}` | {_fmt(p, '.4f')} | "
            f"{'yes' if rejected else 'no' if rejected is not None else 'n/a'} |"
        )

    snoop = report["multiple_testing"]["family_level_snooping"]
    lines.append("")
    if snoop.get("available"):
        spa = snoop["hansen_spa"]
        rc = snoop["white_reality_check"]
        lines += [
            f"Across the four families ({snoop['n_aligned_observations']} aligned "
            "out-of-sample bars, benchmark = flat):",
            "",
            f"* Hansen SPA: statistic {spa['statistic']:.3f}, p = {spa['p_value']:.4f}",
            f"* White Reality Check: statistic {rc['statistic']:.3f}, p = {rc['p_value']:.4f}",
            "",
            f"These correct for {snoop['covers']}. They do **not** correct for "
            f"{snoop['does_not_cover']}.",
        ]
    else:
        lines.append(f"Family-level SPA / Reality Check unavailable: {snoop.get('reason')}")

    pbo = report["multiple_testing"]["probability_of_backtest_overfitting"]
    lines += [
        "",
        f"**PBO (CSCV) not computed.** {pbo['reason']}",
        "",
        "## What this table is not",
        "",
        f"{report['gating_rule']} The performance columns above are descriptive: at one "
        "seed, one asset and 25 evaluations per fold they cannot evaluate the "
        "pre-registered promotion criteria C1-C6, which are defined over 10 seeds and "
        "both assets in S1-C. No family is promoted or rejected here.",
        "",
    ]
    return "\n".join(lines)


def write_s1_pilot_report(run_dirs: Mapping[str, Path], output_dir: Path) -> dict[str, Path]:
    """Write the JSON payload and Markdown extract for the S1-B pilot."""
    report = build_s1_pilot_report(run_dirs)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "s1b_pilot_report.json"
    md_path = output_dir / "s1b_pilot_report.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(render_s1_pilot_markdown(report), encoding="utf-8")
    return {"json": json_path, "markdown": md_path}
