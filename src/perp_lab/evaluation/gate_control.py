"""Positive control for Gate R3: known-Sharpe strategies through the unchanged gate.

The study's causality guards were validated by planting a leak on purpose. This
module does the equivalent for the promotion gate: it manufactures strategies
whose true net Sharpe is known, writes them in the exact ledger layout a real
run persists, and pushes them through ``analyse_run`` and
``evaluate_r3_promotion`` as they are. The gate code is never touched; only its
input is synthetic. The question it answers is the one a tribunal asks first:
would this gate ever let anything through, and at what Sharpe?

Design choices that keep the control honest:

* The scaffold is a real run of a real family: its bars, its positions, its
  fees, slippage, funding and trade boundaries are kept. Only the per-bar
  return is replaced, and only on bars where the strategy held a position, so
  exposure, turnover and trade counts stay exactly those of a real strategy.
* The injected series is Student-t with four degrees of freedom, scaled to the
  scaffold's own in-position volatility, so tails are fat rather than Gaussian.
* The target is the *net* annualised Sharpe over all out-of-sample bars, the
  quantity an investor sees. The drift on in-position bars is solved for
  analytically from the in-position fraction, and the realised Sharpe of each
  synthetic run is reported next to the target so the calibration can be
  audited.
* Buy-and-hold, costs, funding and fold geometry are the real ones, so the
  ``beats_buy_and_hold`` and ``survives_double_costs`` criteria bite exactly as
  they bit the real families.
"""

from __future__ import annotations

import csv
import json
import math
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import polars as pl

from perp_lab.evaluation.study_robustness import (
    PROMOTION_TESTS,
    R3_PRIMARY_ENGINE,
    analyse_run,
    evaluate_r3_promotion,
)

BARS_PER_YEAR_1H = 24 * 365
STUDENT_T_DF = 4
_FOLD_RE = re.compile(r"fold(\d+)")


def _fold_index(path: Path) -> int:
    match = _FOLD_RE.search(path.name)
    return int(match.group(1)) if match else -1


# ---------------------------------------------------------------------------
# Calibration
# ---------------------------------------------------------------------------


def expected_sharpe(mu_p: float, sigma_p: float, in_position_fraction: float) -> float:
    """Annualised Sharpe over all bars of a series that is ``mu_p + sigma_p * z`` on a
    fraction ``f`` of bars and exactly zero on the rest.

    ``E[r] = f mu_p`` and ``Var[r] = f sigma_p^2 + f (1 - f) mu_p^2``; the second
    term is the variance the on/off switching adds.
    """
    f = in_position_fraction
    if f <= 0.0 or sigma_p <= 0.0:
        return 0.0
    mean_all = f * mu_p
    var_all = f * sigma_p**2 + f * (1.0 - f) * mu_p**2
    return mean_all / math.sqrt(var_all) * math.sqrt(BARS_PER_YEAR_1H)


def calibrate_mu(target_sharpe: float, sigma_p: float, in_position_fraction: float) -> float:
    """Per-bar drift on in-position bars that yields ``target_sharpe`` over all bars.

    ``expected_sharpe`` is monotone in ``mu_p`` and bounded by
    ``sqrt(f / (1 - f)) * sqrt(bars_per_year)`` as the drift grows, which is far
    above any Sharpe worth asking about; a target beyond it is a caller error.
    """
    if target_sharpe == 0.0:
        return 0.0
    if sigma_p <= 0.0 or not 0.0 < in_position_fraction <= 1.0:
        raise ValueError("calibration needs sigma_p > 0 and 0 < in_position_fraction <= 1")
    sign = 1.0 if target_sharpe > 0 else -1.0
    target = abs(target_sharpe)
    f = in_position_fraction
    if f < 1.0:
        ceiling = math.sqrt(f / (1.0 - f)) * math.sqrt(BARS_PER_YEAR_1H)
        if target >= ceiling:
            raise ValueError(f"target Sharpe {target} exceeds the attainable ceiling {ceiling:.2f}")
    lo, hi = 0.0, sigma_p
    while expected_sharpe(hi, sigma_p, f) < target:
        hi *= 2.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if expected_sharpe(mid, sigma_p, f) < target:
            lo = mid
        else:
            hi = mid
    return sign * 0.5 * (lo + hi)


def scaled_student_t(rng: np.random.Generator, size: int, df: int = STUDENT_T_DF) -> np.ndarray:
    """Student-t draws rescaled to unit variance (needs ``df > 2``)."""
    if df <= 2:
        raise ValueError("Student-t needs df > 2 for a finite variance")
    return rng.standard_t(df, size=size) / math.sqrt(df / (df - 2))


VOL_HALFLIFE_BARS = 24


def ewma_volatility(returns: np.ndarray, halflife: int = VOL_HALFLIFE_BARS) -> np.ndarray:
    """Causal EWMA volatility of a return series, seeded at its global variance.

    Bar ``t`` uses returns up to ``t - 1`` only, so the path is the volatility a
    trader could have known; it carries the market's own clustering into the
    synthetic series.
    """
    r = np.nan_to_num(np.asarray(returns, dtype=float))
    lam = math.exp(math.log(0.5) / max(1, halflife))
    var = np.empty(r.size, dtype=float)
    level = float(np.var(r)) if r.size > 1 else 0.0
    for t in range(r.size):
        var[t] = level
        level = lam * level + (1.0 - lam) * r[t] ** 2
    return np.sqrt(var)


def lag1_autocorrelation(x: np.ndarray) -> float:
    x = np.asarray(x, dtype=float)
    if x.size < 3:
        return 0.0
    a, b = x[:-1], x[1:]
    if a.std() == 0.0 or b.std() == 0.0:
        return 0.0
    phi = float(np.corrcoef(a, b)[0, 1])
    return float(np.clip(phi, -0.9, 0.9)) if math.isfinite(phi) else 0.0


def ar1_innovations(e: np.ndarray, phi: float) -> np.ndarray:
    """AR(1) with unit stationary variance driven by unit-variance innovations."""
    if phi == 0.0 or e.size == 0:
        return e
    z = np.empty(e.size, dtype=float)
    scale = math.sqrt(1.0 - phi * phi)
    z[0] = e[0]
    for t in range(1, e.size):
        z[t] = phi * z[t - 1] + scale * e[t]
    return z


# ---------------------------------------------------------------------------
# Scaffold runs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ScaffoldRun:
    """One real run whose bars, positions, costs and trades are reused."""

    family: str
    symbol: str
    seed: int
    run_dir: Path
    method: str = R3_PRIMARY_ENGINE

    @property
    def fold_files(self) -> list[Path]:
        return sorted(
            self.run_dir.glob(f"{self.method}_fold*_test_equity.parquet"), key=_fold_index
        )

    def trades_file(self, equity_file: Path) -> Path:
        return equity_file.with_name(equity_file.name.replace("_test_equity", "_test_trades"))


def list_scaffold_runs(
    units_csv: str | Path,
    family: str,
    *,
    method: str = R3_PRIMARY_ENGINE,
) -> list[ScaffoldRun]:
    """The seed runs of one full-study family, from the chapter-7 units table."""
    seen: dict[str, ScaffoldRun] = {}
    with Path(units_csv).open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            if row["family"] != family or row["engine"] != method:
                continue
            if row["round"].startswith("CRT") or row["round"] == "S3":
                continue
            run_dir = Path(row["run_dir"].replace("\\", "/"))
            if str(run_dir) in seen:
                continue
            seen[str(run_dir)] = ScaffoldRun(
                family=family,
                symbol=row["symbol"],
                seed=int(row["seed"]),
                run_dir=run_dir,
                method=method,
            )
    runs = sorted(seen.values(), key=lambda r: (r.symbol, r.seed))
    if not runs:
        raise ValueError(f"no {method} runs for family {family!r} in {units_csv}")
    return runs


# ---------------------------------------------------------------------------
# Synthesis
# ---------------------------------------------------------------------------


def _recompute_trades(trades: pl.DataFrame, ledger: pl.DataFrame) -> pl.DataFrame:
    """Per-trade net return compounded from the ledger's per-bar returns."""
    if trades.height == 0 or "trade_id" not in ledger.columns:
        return trades
    per_trade = (
        ledger.filter(pl.col("trade_id").is_not_null())
        .group_by("trade_id")
        .agg(((pl.col("net_return") + 1.0).product() - 1.0).alias("_net"))
    )
    out = trades.join(per_trade, on="trade_id", how="left")
    return out.with_columns(
        pl.coalesce([pl.col("_net"), pl.col("net_return")]).alias("net_return")
    ).drop("_net")


def synthesize_run(
    scaffold: ScaffoldRun,
    out_dir: Path,
    *,
    target_sharpe: float,
    rng: np.random.Generator,
    df: int = STUDENT_T_DF,
) -> dict[str, Any]:
    """Write a synthetic run with the scaffold's layout and a known net Sharpe.

    Returns the calibration record: in-position fraction, in-position sigma,
    the solved drift and the Sharpe the synthetic series actually realised.
    """
    fold_files = scaffold.fold_files
    if not fold_files:
        raise FileNotFoundError(f"no {scaffold.method} fold ledgers under {scaffold.run_dir}")
    folds = [pl.read_parquet(p) for p in fold_files]

    position = np.concatenate([f["position"].cast(pl.Float64).to_numpy() for f in folds])
    real_net = np.concatenate([f["net_return"].cast(pl.Float64).to_numpy() for f in folds])
    in_position = np.abs(position) > 0
    f_in = float(in_position.mean())
    sigma_p = float(real_net[in_position].std(ddof=1)) if in_position.sum() > 1 else 0.0
    if f_in <= 0.0 or sigma_p <= 0.0:
        raise ValueError(f"scaffold {scaffold.run_dir} never holds a position; cannot inject")

    mu_p = calibrate_mu(target_sharpe, sigma_p, f_in)

    # Shape of the innovations comes from the scaffold itself: the real
    # volatility path (clustering) and the real lag-1 autocorrelation of the
    # in-position returns. The path is rescaled to mean square sigma_p^2 and the
    # AR(1) keeps unit variance, so the per-bar variance the calibration assumes
    # is unchanged and the target Sharpe still holds in expectation.
    r_in = real_net[in_position]
    phi = lag1_autocorrelation(r_in)
    vol_path = ewma_volatility(real_net)[in_position]
    rms = float(np.sqrt(np.mean(vol_path**2)))
    vol_path = vol_path / rms * sigma_p if rms > 0 else np.full(r_in.size, sigma_p)
    innovations = ar1_innovations(scaled_student_t(rng, int(in_position.sum()), df), phi)
    net = np.zeros(position.size, dtype=float)
    net[in_position] = mu_p + vol_path * innovations

    out_dir.mkdir(parents=True, exist_ok=True)
    offset = 0
    n_trades = 0
    for equity_file, fold in zip(fold_files, folds, strict=True):
        n = fold.height
        fold_net = net[offset : offset + n]
        offset += n
        gross = (
            fold_net
            + fold["fee"].cast(pl.Float64).to_numpy()
            + fold["slippage"].cast(pl.Float64).to_numpy()
            + fold["funding"].cast(pl.Float64).to_numpy()
        )
        equity = np.cumprod(1.0 + fold_net)
        drawdown = equity / np.maximum.accumulate(equity) - 1.0
        synthetic = fold.with_columns(
            pl.Series("net_return", fold_net),
            pl.Series("gross_return", gross),
            pl.Series("equity", equity),
            pl.Series("drawdown", drawdown),
        )
        synthetic.write_parquet(out_dir / equity_file.name)

        trades_file = scaffold.trades_file(equity_file)
        if trades_file.exists():
            trades = _recompute_trades(pl.read_parquet(trades_file), synthetic)
            trades.write_parquet(out_dir / trades_file.name)
            n_trades += trades.height

    sd_all = float(net.std(ddof=1))
    realised = float(net.mean() / sd_all * math.sqrt(BARS_PER_YEAR_1H)) if sd_all > 0 else 0.0
    centred = net[in_position] - net[in_position].mean()
    var_in = float(np.mean(centred**2))
    kurtosis = float(np.mean(centred**4) / var_in**2 - 3.0) if var_in > 0 else 0.0
    return {
        "n_bars": int(position.size),
        "n_folds": len(folds),
        "in_position_fraction": f_in,
        "sigma_in_position": sigma_p,
        "mu_in_position": mu_p,
        "target_sharpe": target_sharpe,
        "realised_sharpe": realised,
        "lag1_autocorrelation": phi,
        "vol_halflife_bars": VOL_HALFLIFE_BARS,
        "realised_excess_kurtosis": kurtosis,
        "n_trades": n_trades,
    }


# ---------------------------------------------------------------------------
# Monte Carlo tasks (top-level so a process pool can pickle them)
# ---------------------------------------------------------------------------


def run_control_task(task: dict[str, Any]) -> dict[str, Any]:
    """Synthesize one run, score it with the unchanged gate code, clean up."""
    scaffold = ScaffoldRun(
        family=task["family"],
        symbol=task["symbol"],
        seed=int(task["seed"]),
        run_dir=Path(task["run_dir"]),
        method=task.get("method", R3_PRIMARY_ENGINE),
    )
    rng = np.random.default_rng(
        np.random.SeedSequence(
            [
                int(task["master_seed"]),
                int(task["scaffold_index"]),
                int(task["level_index"]),
                int(task["rep"]),
                int(task["seed"]),
            ]
        )
    )
    out_dir = Path(task["out_root"]) / (
        f"s{task['scaffold_index']}_l{task['level_index']}_r{task['rep']}_"
        f"{scaffold.symbol}_{scaffold.seed}"
    )
    try:
        calibration = synthesize_run(
            scaffold, out_dir, target_sharpe=float(task["target_sharpe"]), rng=rng
        )
        scored = analyse_run(
            out_dir,
            scaffold.method,
            fee_bps_per_side=float(task["fee_bps"]),
            slippage_bps_per_side=float(task["slippage_bps"]),
        )
    finally:
        shutil.rmtree(out_dir, ignore_errors=True)
    return {
        "scaffold": scaffold.family,
        "scaffold_index": int(task["scaffold_index"]),
        "level_index": int(task["level_index"]),
        "target_sharpe": float(task["target_sharpe"]),
        "rep": int(task["rep"]),
        "symbol": scaffold.symbol,
        "seed": scaffold.seed,
        "tests": scored["tests"],
        "total_return": float(scored["strategy"]["total_return"]),
        "sharpe": float(scored["strategy"]["sharpe"]),
        "bh_total_return": float(scored["buy_and_hold"]["total_return"]),
        "n_trades": int(calibration["n_trades"]),
        "calibration": calibration,
    }


def build_tasks(
    scaffolds: list[list[ScaffoldRun]],
    levels: list[float],
    reps: int,
    *,
    out_root: Path,
    master_seed: int,
    fee_bps: float,
    slippage_bps: float,
) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    for s_idx, runs in enumerate(scaffolds):
        for l_idx, level in enumerate(levels):
            for rep in range(reps):
                for run in runs:
                    tasks.append(
                        {
                            "family": run.family,
                            "symbol": run.symbol,
                            "seed": run.seed,
                            "run_dir": str(run.run_dir),
                            "method": run.method,
                            "scaffold_index": s_idx,
                            "level_index": l_idx,
                            "target_sharpe": level,
                            "rep": rep,
                            "out_root": str(out_root),
                            "master_seed": master_seed,
                            "fee_bps": fee_bps,
                            "slippage_bps": slippage_bps,
                        }
                    )
    return tasks


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------


def gate_verdicts(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One gate decision per (scaffold, level, replication), via the real gate."""
    groups: dict[tuple[int, int, int], list[dict[str, Any]]] = {}
    for r in results:
        groups.setdefault((r["scaffold_index"], r["level_index"], r["rep"]), []).append(r)

    verdicts: list[dict[str, Any]] = []
    for key in sorted(groups):
        runs = groups[key]
        payload = {
            "per_run": {
                f"{r['symbol']}|{r['seed']}": {
                    "method": R3_PRIMARY_ENGINE,
                    "symbol": r["symbol"],
                    "tests": r["tests"],
                }
                for r in runs
            }
        }
        gate = evaluate_r3_promotion(payload)
        row: dict[str, Any] = {
            "scaffold": runs[0]["scaffold"],
            "scaffold_index": key[0],
            "level_index": key[1],
            "target_sharpe": runs[0]["target_sharpe"],
            "rep": key[2],
            "verdict": gate["verdict"],
            "promoted": gate["verdict"] == "PROMOTED",
            "n_rejections": len(gate["triggered_rejections"]),
            "triggered_rejections": ";".join(gate["triggered_rejections"]),
            "failed_promotion_criteria": ";".join(gate["failed_promotion_criteria"]),
            "mean_realised_sharpe": float(
                np.mean([r["calibration"]["realised_sharpe"] for r in runs])
            ),
            "mean_net_sharpe": float(np.mean([r["sharpe"] for r in runs])),
            "mean_total_return": float(np.mean([r["total_return"] for r in runs])),
        }
        for symbol, report in gate["by_symbol"].items():
            tag = symbol.replace("USDT", "").lower()
            for name in PROMOTION_TESTS:
                row[f"{tag}_{name}"] = bool(report["promotion"][name]["pass"])
        verdicts.append(row)
    return verdicts


def summarise_levels(verdicts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Promotion rate and criterion pass rates per (scaffold, target Sharpe)."""
    groups: dict[tuple[int, int], list[dict[str, Any]]] = {}
    for v in verdicts:
        groups.setdefault((v["scaffold_index"], v["level_index"]), []).append(v)
    rows: list[dict[str, Any]] = []
    for key in sorted(groups):
        vs = groups[key]
        n = len(vs)
        row: dict[str, Any] = {
            "scaffold": vs[0]["scaffold"],
            "target_sharpe": vs[0]["target_sharpe"],
            "n_replications": n,
            "n_promoted": int(sum(v["promoted"] for v in vs)),
            "promotion_rate": float(np.mean([v["promoted"] for v in vs])),
            "rejection_rate": float(np.mean([v["n_rejections"] > 0 for v in vs])),
            "mean_realised_sharpe": float(np.mean([v["mean_realised_sharpe"] for v in vs])),
            "mean_net_sharpe": float(np.mean([v["mean_net_sharpe"] for v in vs])),
            "mean_total_return": float(np.mean([v["mean_total_return"] for v in vs])),
        }
        criterion_keys = sorted(k for k in vs[0] if any(k.endswith(t) for t in PROMOTION_TESTS))
        for k in criterion_keys:
            row[f"majority_pass_rate_{k}"] = float(np.mean([v[k] for v in vs]))
        rows.append(row)
    return rows


def summarise_runs(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Per-run (single seed) pass rate of each criterion, by scaffold, level, symbol."""
    groups: dict[tuple[int, int, str], list[dict[str, Any]]] = {}
    for r in results:
        groups.setdefault((r["scaffold_index"], r["level_index"], r["symbol"]), []).append(r)
    rows: list[dict[str, Any]] = []
    for key in sorted(groups):
        rs = groups[key]
        row: dict[str, Any] = {
            "scaffold": rs[0]["scaffold"],
            "target_sharpe": rs[0]["target_sharpe"],
            "symbol": key[2],
            "n_runs": len(rs),
            "mean_realised_sharpe": float(
                np.mean([r["calibration"]["realised_sharpe"] for r in rs])
            ),
            "mean_total_return": float(np.mean([r["total_return"] for r in rs])),
            "bh_total_return": float(rs[0]["bh_total_return"]),
            "mean_n_trades": float(np.mean([r["n_trades"] for r in rs])),
        }
        for name in (*PROMOTION_TESTS, "min_oos_trades_met"):
            row[f"pass_rate_{name}"] = float(np.mean([r["tests"][name] for r in rs]))
        rows.append(row)
    return rows


def summarise_blocking(verdicts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Among the replications a level did NOT promote, which criterion failed
    its seed majority most often, per symbol, and which rejection fired most."""
    groups: dict[tuple[int, int], list[dict[str, Any]]] = {}
    for v in verdicts:
        groups.setdefault((v["scaffold_index"], v["level_index"]), []).append(v)
    rows: list[dict[str, Any]] = []
    for key in sorted(groups):
        blocked = [v for v in groups[key] if not v["promoted"]]
        row: dict[str, Any] = {
            "scaffold": groups[key][0]["scaffold"],
            "target_sharpe": groups[key][0]["target_sharpe"],
            "n_replications": len(groups[key]),
            "n_blocked": len(blocked),
        }
        if not blocked:
            row["most_blocking_criterion"] = ""
            row["most_blocking_share"] = 0.0
            row["most_frequent_rejection"] = ""
            rows.append(row)
            continue
        counts: dict[str, int] = {}
        for v in blocked:
            for item in v["failed_promotion_criteria"].split(";"):
                if item:
                    counts[item] = counts.get(item, 0) + 1
        rejections: dict[str, int] = {}
        for v in blocked:
            for item in v["triggered_rejections"].split(";"):
                if item:
                    rejections[item] = rejections.get(item, 0) + 1
        # Strip the "(n/required)" tally so the same criterion aggregates.
        by_name: dict[str, int] = {}
        for item, n in counts.items():
            name = item.split(" (")[0]
            by_name[name] = by_name.get(name, 0) + n
        top = max(by_name.items(), key=lambda kv: (kv[1], kv[0])) if by_name else ("", 0)
        top_rej = max(rejections.items(), key=lambda kv: (kv[1], kv[0])) if rejections else ("", 0)
        row["most_blocking_criterion"] = top[0]
        row["most_blocking_share"] = top[1] / len(blocked)
        row["most_frequent_rejection"] = top_rej[0]
        row["most_frequent_rejection_share"] = top_rej[1] / len(blocked)
        for name in sorted(by_name):
            row[f"blocked_share_{name.replace(': ', '_')}"] = by_name[name] / len(blocked)
        rows.append(row)
    return rows


def dump_json(payload: Any, path: Path) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
