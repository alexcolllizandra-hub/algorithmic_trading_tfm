"""Study-level multiple-testing accounting across every family the thesis tested.

Each research gate corrected for multiplicity *inside itself*: R3 across its five
families, S1 across its four, S2 across its three. Nobody ever corrected across
the gates. But the decision that matters for the thesis -- "of everything we
tried, did anything work?" -- selects the best family out of all of them, so the
denominator is the whole study, not one batch.

This module rebuilds that denominator from the persisted artifacts and applies
the correction once, over every family at once. It recomputes nothing: it reads
the out-of-sample ledgers the gates already wrote, so the numbers here are the
same numbers, only judged against a larger family of tests.

Conventions are inherited rather than invented. The bootstrap, its block length
and its seed match ``reporting/s1_pilot.py``; the primary engine is Random Search
as in every gate; Sharpe ratios are de-annualised before deflation because the
deflation formula is stated per observation.

The analysis is run on BTCUSDT because it is the only asset every one of the
thirteen families was tested on; ETHUSDT is reported separately, over the subset
that has it, as a consistency check rather than as extra tests.

This module never reads market data and never touches the frozen holdout.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import polars as pl

from perp_lab.backtesting.metrics import bars_per_year
from perp_lab.evaluation.multiple_testing import (
    MultipleTestCorrection,
    benjamini_hochberg_correction,
    deflated_sharpe_ratio,
    holm_bonferroni,
    probability_of_backtest_overfitting,
    stationary_bootstrap_indices,
)

PRIMARY_ENGINE = "random_search"
PRIMARY_SYMBOL = "BTCUSDT"
SECONDARY_SYMBOL = "ETHUSDT"
TIMEFRAME = "1h"

ALPHA = 0.05
BOOTSTRAP_DRAWS = 2000
BOOTSTRAP_BATCH = 100
BLOCK_PROBABILITY = 1.0 / 24.0
BOOTSTRAP_SEED = 42
PBO_PARTITIONS = 8

R2_STUDY = Path("artifacts/runs/multiseed_momentum_r2_clean_v2/study_robustness.json")
R3_ROOT = Path("artifacts/runs/r3_full_budget100_ga21")
S1_REPORT = Path("reports/gate_s1b/s1b_pilot_report.json")
S2_REPORT = Path("reports/gate_s2b/s2b_pilot_report.json")

R3_FAMILIES = (
    "breakout",
    "mean_reversion",
    "volatility_breakout",
    "funding",
    "BTC_ETH_confirmation",
)

#: The acceptance criterion each gate pre-registered, quoted so the inventory
#: records what every family was actually judged against at the time.
GATE_CRITERIA: dict[str, str] = {
    "R2": (
        "Six robustness criteria on Random Search, both assets, majority of 10 seeds "
        "(ADR 0013). Momentum re-baselined after the outer-fold leakage fix."
    ),
    "R3": (
        "All six promotion criteria (positive net OOS return, bootstrap Sharpe CI "
        "excluding zero, survives doubled costs, beats buy-and-hold, survives dropping "
        "the top five trades, not confined to one fold) on Random Search, on both "
        "assets, on at least 6 of 10 seeds; plus a veto below 5 OOS trades (ADR 0015)."
    ),
    "S1": (
        "S1-B screened for mechanical viability only and could not reject on "
        "performance; the S1-C promotion criterion (same six, 6/10 seeds, both assets, "
        "plus deflated Sharpe > 0.95, PBO < 0.5 and BH at 0.05) was never executed "
        "(ADR 0016)."
    ),
    "S2": (
        "S2-B partial-signal trigger: positive compounded net OOS return on at least "
        "2 of 3 seeds, at least 5 OOS trades on each such seed, and not confined to a "
        "single fold. It did not fire, so S2-C promotion was never authorised."
    ),
}


class StudyClosureError(RuntimeError):
    """Raised when the persisted evidence cannot support the accounting."""


@dataclass(frozen=True)
class StudyUnit:
    """One (family, asset, seed, engine) search that was actually executed."""

    gate: str
    family: str
    symbol: str
    seed: int
    engine: str
    run_dir: Path


@dataclass(frozen=True)
class FamilyResult:
    """Study-level statistics for one family on one asset."""

    gate: str
    family: str
    symbol: str
    n_seeds: int
    n_bars: int
    mean_bar_return: float
    total_return: float
    sharpe_per_observation: float
    sharpe_annualised: float
    p_value: float
    skewness: float
    kurtosis: float
    seeds: tuple[int, ...] = field(default=())

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "gate": self.gate,
            "family": self.family,
            "symbol": self.symbol,
            "n_seeds": self.n_seeds,
            "n_bars": self.n_bars,
            "mean_bar_return": self.mean_bar_return,
            "total_return": self.total_return,
            "sharpe_per_observation": self.sharpe_per_observation,
            "sharpe_annualised": self.sharpe_annualised,
            "p_value": self.p_value,
            "skewness": self.skewness,
            "kurtosis": self.kurtosis,
            "seeds": list(self.seeds),
        }
        return payload


# --------------------------------------------------------------------------- #
# Inventory: which searches were actually run, according to the gate reports
# --------------------------------------------------------------------------- #


def _read_json(path: Path) -> Any:
    if not path.exists():
        raise StudyClosureError(f"Required evidence file is missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _run_dir(root: Path, raw: str) -> Path:
    """Resolve a recorded run directory, tolerating the separator it was written with."""
    name = raw.replace("\\", "/").rstrip("/").rsplit("/", 1)[-1]
    return root / "artifacts" / "runs" / name


def _units_from_study_robustness(root: Path, path: Path, gate: str, family: str) -> list[StudyUnit]:
    """Units recorded by a multi-seed study, keyed ``SYMBOL|seed=N|engine``."""
    payload = _read_json(root / path)
    units: list[StudyUnit] = []
    for key, record in payload.get("per_run", {}).items():
        symbol, seed_part, engine = key.split("|")
        units.append(
            StudyUnit(
                gate=gate,
                family=family,
                symbol=symbol,
                seed=int(seed_part.removeprefix("seed=")),
                engine=engine,
                run_dir=_run_dir(root, str(record["run_dir"])),
            )
        )
    return units


def build_inventory(root: Path) -> list[StudyUnit]:
    """Every search unit behind gates R2, R3, S1 and S2, from the gate reports.

    The gate reports are the authority, not the run directory listing: the
    artifact store also holds earlier pilots and abandoned attempts, and counting
    those would inflate the denominator with work that never entered the record.
    """
    units: list[StudyUnit] = []
    units.extend(_units_from_study_robustness(root, R2_STUDY, "R2", "momentum"))

    for family in R3_FAMILIES:
        units.extend(
            _units_from_study_robustness(
                root, R3_ROOT / family / "study_robustness.json", "R3", family
            )
        )

    s1 = _read_json(root / S1_REPORT)
    for family, payload in s1["per_family"].items():
        for engine, record in payload["engines"].items():
            units.append(
                StudyUnit(
                    gate="S1",
                    family=family,
                    symbol=PRIMARY_SYMBOL,
                    seed=42,
                    engine=engine,
                    run_dir=_run_dir(root, str(record["run_dir"])),
                )
            )

    s2 = _read_json(root / S2_REPORT)
    for arm in s2["arms"]:
        for engine in arm["engines"]:
            units.append(
                StudyUnit(
                    gate="S2",
                    family=str(arm["family"]),
                    symbol=str(arm["symbol"]),
                    seed=int(arm["seed"]),
                    engine=engine,
                    run_dir=_run_dir(root, str(arm["run_dir"])),
                )
            )
    return units


# --------------------------------------------------------------------------- #
# Out-of-sample series
# --------------------------------------------------------------------------- #


def _unit_oos_returns(run_dir: Path, engine: str) -> pl.DataFrame:
    """Per-bar out-of-sample net returns, concatenated across that unit's folds.

    Folds whose search found no admissible candidate wrote no ledger; they are
    absent rather than zero, because "the family could not act" is not the same
    claim as "the family acted and earned nothing".
    """
    paths = sorted(run_dir.glob(f"{engine}_fold*_test_equity.parquet"))
    if not paths:
        return pl.DataFrame(
            {"open_time": [], "net_return": []},
            schema={"open_time": pl.Datetime("ms", "UTC"), "net_return": pl.Float64},
        )
    frame = pl.concat([pl.read_parquet(p).select("open_time", "net_return") for p in paths]).sort(
        "open_time"
    )
    if frame["open_time"].n_unique() != frame.height:
        raise StudyClosureError(
            f"{run_dir.name}/{engine}: out-of-sample folds overlap in time; "
            "concatenating them would count the same bar twice."
        )
    return frame


def family_oos_series(
    units: list[StudyUnit], *, symbol: str, engine: str
) -> dict[str, pl.DataFrame]:
    """One out-of-sample return series per family, averaged over its seeds.

    Averaging across seeds is the right summary here because the protocol treats
    seeds as replicates of the same hypothesis, not as separate hypotheses: a
    family is one idea, and its performance is what that idea delivered on
    average once the arbitrary starting point of the search is integrated out.
    """
    series: dict[str, pl.DataFrame] = {}
    for family in sorted({u.family for u in units}):
        selected = [
            u for u in units if u.family == family and u.symbol == symbol and u.engine == engine
        ]
        frames = [_unit_oos_returns(u.run_dir, engine) for u in selected]
        frames = [f for f in frames if f.height > 0]
        if not frames:
            continue
        series[family] = (
            pl.concat(frames)
            .group_by("open_time")
            .agg(pl.col("net_return").mean())
            .sort("open_time")
        )
    return series


def _bootstrap_p_value(returns: np.ndarray, *, seed: int) -> float:
    """One-sided stationary-bootstrap p-value for a positive mean bar return.

    Drawn in batches: the index matrix for a full study-length series is hundreds
    of megabytes in one piece, and nothing is gained by holding it all at once.
    The seed still fixes the result exactly.
    """
    rng = np.random.default_rng(seed)
    observed = float(returns.mean())
    exceedances = 0
    drawn = 0
    while drawn < BOOTSTRAP_DRAWS:
        batch = min(BOOTSTRAP_BATCH, BOOTSTRAP_DRAWS - drawn)
        indices = stationary_bootstrap_indices(
            returns.size, batch, block_probability=BLOCK_PROBABILITY, rng=rng
        )
        # Recentred at zero: the null is that the family earns nothing.
        centred = returns[indices].mean(axis=1) - observed
        exceedances += int(np.count_nonzero(centred >= observed))
        drawn += batch
    return exceedances / BOOTSTRAP_DRAWS


def _moments(returns: np.ndarray) -> tuple[float, float]:
    """Sample skewness and raw (non-excess) kurtosis of the return series."""
    centred = returns - returns.mean()
    variance = float(np.mean(centred**2))
    if variance <= 0:
        return 0.0, 3.0
    skew = float(np.mean(centred**3) / variance**1.5)
    kurt = float(np.mean(centred**4) / variance**2)
    return skew, kurt


def family_results(
    units: list[StudyUnit], series: dict[str, pl.DataFrame], *, symbol: str
) -> list[FamilyResult]:
    """Per-family study-level statistics, ordered from most to least promising."""
    gate_of = {u.family: u.gate for u in units}
    results: list[FamilyResult] = []
    scale = float(np.sqrt(bars_per_year(TIMEFRAME)))
    for family, frame in series.items():
        returns = frame["net_return"].cast(pl.Float64).to_numpy().astype(float)
        returns = returns[np.isfinite(returns)]
        if returns.size < 2:
            continue
        std = float(returns.std(ddof=1))
        sharpe = float(returns.mean() / std) if std > 0 else 0.0
        skew, kurt = _moments(returns)
        seeds = tuple(
            sorted(
                {
                    u.seed
                    for u in units
                    if u.family == family and u.symbol == symbol and u.engine == PRIMARY_ENGINE
                }
            )
        )
        results.append(
            FamilyResult(
                gate=gate_of[family],
                family=family,
                symbol=symbol,
                n_seeds=len(seeds),
                n_bars=int(returns.size),
                mean_bar_return=float(returns.mean()),
                total_return=float(np.prod(1.0 + returns) - 1.0),
                sharpe_per_observation=sharpe,
                sharpe_annualised=sharpe * scale,
                p_value=_bootstrap_p_value(returns, seed=BOOTSTRAP_SEED),
                skewness=skew,
                kurtosis=kurt,
                seeds=seeds,
            )
        )
    return sorted(results, key=lambda r: r.p_value)


# --------------------------------------------------------------------------- #
# Study-level corrections
# --------------------------------------------------------------------------- #


def aligned_matrix(series: dict[str, pl.DataFrame]) -> tuple[list[str], np.ndarray]:
    """Families as columns on their common bars, for CSCV.

    An inner join is deliberate: the overfitting question compares configurations
    against each other, which is only meaningful where they were all live.
    """
    families = sorted(series)
    if len(families) < 2:
        return families, np.empty((0, len(families)))
    joined = series[families[0]].rename({"net_return": families[0]})
    for family in families[1:]:
        joined = joined.join(
            series[family].rename({"net_return": family}), on="open_time", how="inner"
        )
    matrix = joined.select(families).to_numpy().astype(float)
    return families, matrix[np.isfinite(matrix).all(axis=1)]


def evaluations_examined(units: list[StudyUnit]) -> int:
    """Total strategy configurations actually scored anywhere in the study.

    Answers "how many configurations were tried": every candidate
    the searches evaluated, across both engines, all folds, all seeds, both
    assets. It is far larger than the family count and is the denominator the
    deflated Sharpe ratio deserves.
    """
    total = 0
    for run_dir in sorted({u.run_dir for u in units}):
        for engine in ("random_search", "genetic_algorithm"):
            path = run_dir / f"{engine}_candidates.parquet"
            if path.exists():
                total += pl.read_parquet(path, columns=["fold_index"]).height
    return total


def study_level_corrections(
    results: list[FamilyResult], matrix: np.ndarray, *, n_evaluations: int
) -> dict[str, Any]:
    """Holm, Benjamini-Hochberg, PBO and a deflated Sharpe over the whole study."""
    p_values = [r.p_value for r in results]
    holm = holm_bonferroni(p_values, alpha=ALPHA)
    bh = benjamini_hochberg_correction(p_values, alpha=ALPHA)

    best = max(results, key=lambda r: r.sharpe_per_observation)
    sharpes = np.array([r.sharpe_per_observation for r in results], dtype=float)
    sharpe_std = float(sharpes.std(ddof=1)) if sharpes.size > 1 else 0.0

    deflated = {}
    for label, n_trials in (
        ("family_selection", len(results)),
        ("all_configurations_evaluated", max(n_evaluations, len(results))),
    ):
        dsr = deflated_sharpe_ratio(
            best.sharpe_per_observation,
            n_trials=n_trials,
            n_observations=best.n_bars,
            sharpe_std=sharpe_std,
            skewness=best.skewness,
            kurtosis=best.kurtosis,
        )
        deflated[label] = {
            "n_trials": n_trials,
            "observed_sharpe_per_observation": dsr.observed_sharpe,
            "benchmark_sharpe_per_observation": dsr.benchmark_sharpe,
            "deflated_sharpe": dsr.deflated_sharpe,
            "probability_best_is_spurious": 1.0 - dsr.deflated_sharpe,
        }

    pbo: dict[str, Any]
    if matrix.shape[0] >= PBO_PARTITIONS and matrix.shape[1] >= 2:
        result = probability_of_backtest_overfitting(matrix, n_partitions=PBO_PARTITIONS)
        pbo = {
            "available": True,
            "pbo": result.pbo,
            "n_splits": result.n_splits,
            "n_partitions": PBO_PARTITIONS,
            "n_observations": int(matrix.shape[0]),
            "n_configurations": int(matrix.shape[1]),
        }
    else:
        pbo = {"available": False, "reason": "not enough aligned bars or configurations"}

    return {
        "alpha": ALPHA,
        "n_tests": len(results),
        "best_family": best.family,
        "holm_bonferroni": _correction_payload(holm, results),
        "benjamini_hochberg": _correction_payload(bh, results),
        "deflated_sharpe": deflated,
        "probability_of_backtest_overfitting": pbo,
        "n_configurations_evaluated": n_evaluations,
    }


def _correction_payload(
    correction: MultipleTestCorrection, results: list[FamilyResult]
) -> dict[str, Any]:
    families = [r.family for r in results]
    return {
        "method": correction.method,
        "alpha": correction.alpha,
        "n_tests": correction.n_tests,
        "n_rejected": correction.n_rejected,
        "adjusted_p_values": dict(zip(families, correction.adjusted_p_values, strict=True)),
        "rejected": dict(zip(families, correction.rejected, strict=True)),
    }


def sensitivity_to_the_count(results: list[FamilyResult], counts: dict[str, int]) -> dict[str, Any]:
    """Does the verdict depend on how the tests were counted?

    The study never pre-registered a single study-level N, so the choice is made
    here rather than inherited. Reporting the verdict under several defensible
    counts is what keeps that choice from mattering: if nothing survives under
    the most generous count, nothing survives, full stop.
    """
    smallest = min(r.p_value for r in results)
    out: dict[str, Any] = {}
    for label, n in counts.items():
        out[label] = {
            "n_tests": n,
            "bonferroni_threshold": ALPHA / n,
            "smallest_raw_p_value": smallest,
            "any_survive": bool(smallest <= ALPHA / n),
        }
    return out
