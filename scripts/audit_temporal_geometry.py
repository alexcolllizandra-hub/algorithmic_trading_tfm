"""Read-only audit of the walk-forward temporal geometry actually executed.

Reports, from configuration and persisted artifacts only (no re-running of any
search, no holdout access):

* the fold geometry the configuration *would* produce over the full development
  period, versus the folds a given run actually executed;
* per-fold train / validation / test boundaries with real bar counts;
* purge / embargo, candidates evaluated and the validation-selected winner;
* concatenated out-of-sample test metrics across the executed folds;
* an explicit holdout-containment check.

Usage:
    uv run python scripts/audit_temporal_geometry.py <run_id>
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import polars as pl

from perp_lab.backtesting.metrics import performance_metrics
from perp_lab.config import load_data_contract, load_experiment_config
from perp_lab.data.splits import resolve_holdout_start
from perp_lab.validation.walk_forward import generate_folds

RUNS_DIR = Path("artifacts/runs")
PROCESSED = Path("data/processed")


def _iso(value: Any) -> datetime:
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def _load_bars(symbol: str, timeframe: str) -> pl.DataFrame | None:
    """Load the DEVELOPMENT klines only; the holdout partition is not read here."""
    path = PROCESSED / symbol / f"{timeframe}_development.parquet"
    if not path.exists():
        return None
    if "holdout" in path.name:  # defensive: never read the frozen partition
        raise RuntimeError("refusing to read a holdout partition")
    return pl.read_parquet(path).sort("open_time")


def _count(bars: pl.DataFrame | None, start: datetime, end: datetime) -> int | None:
    if bars is None:
        return None
    return int(bars.filter((pl.col("open_time") >= start) & (pl.col("open_time") < end)).height)


def full_geometry(exp: Any, holdout_start: datetime) -> list[dict[str, Any]]:
    """Folds the configuration yields over the whole development period."""
    wf = exp.walk_forward
    from perp_lab.utils.timeutils import timeframe_to_timedelta

    step = timeframe_to_timedelta(exp.timeframes.primary)
    folds = generate_folds(
        exp.periods.development_start,
        exp.periods.development_end_exclusive,
        initial_train_days=wf.initial_train_days,
        validation_days=wf.validation_days,
        test_days=wf.test_days,
        step_days=wf.step_days,
        purge=exp.purge_bars * step,
        embargo=exp.embargo_bars * step,
        purge_bars=exp.purge_bars,
        embargo_bars=exp.embargo_bars,
    )
    for f in folds:
        assert f.test_end <= holdout_start, "config geometry must not touch the holdout"
    return [f.to_dict() for f in folds]


def concat_oos(run_dir: Path, method: str) -> tuple[pl.DataFrame | None, list[int]]:
    """Concatenate the persisted per-fold OOS test equity for one method."""
    found: list[tuple[int, Path]] = [
        (int(p.stem.split("fold")[1].split("_")[0]), p)
        for p in run_dir.glob(f"{method}_fold*_test_equity.parquet")
    ]
    if not found:
        return None, []
    found.sort()
    frames = [pl.read_parquet(p).with_columns(pl.lit(idx).alias("fold")) for idx, p in found]
    series = pl.concat(frames, how="diagonal_relaxed").sort(["fold", "open_time"])
    return series, [idx for idx, _ in found]


def _metrics(series: pl.DataFrame, timeframe: str) -> dict[str, float]:
    return performance_metrics(
        series["net_return"].to_numpy(),
        timeframe=timeframe,
        positions=series["position"].to_numpy() if "position" in series.columns else None,
        turnover=series["turnover"].to_numpy() if "turnover" in series.columns else None,
    )


def _trades(run_dir: Path, method: str) -> pl.DataFrame | None:
    frames = [
        pl.read_parquet(p) for p in sorted(run_dir.glob(f"{method}_fold*_test_trades.parquet"))
    ]
    return pl.concat(frames, how="diagonal_relaxed") if frames else None


def _breakdown(series: pl.DataFrame, timeframe: str, key: str, title: str) -> None:
    """Recompute metrics independently within each group of the OOS series."""
    print(f"\n    {title}")
    print(f"      {key:<8} {'bars':>6} {'total_ret':>11} {'sharpe':>8} {'max_dd':>9} {'legs':>6}")
    for value in series[key].unique().sort().to_list():
        sub = series.filter(pl.col(key) == value)
        if sub.height < 2:
            continue
        m = _metrics(sub, timeframe)
        print(
            f"      {value!s:<8} {int(m['n_bars']):>6} {m['total_return']:>10.2%} "
            f"{m['sharpe']:>8.3f} {m['max_drawdown']:>8.2%} {int(m.get('n_trades', 0)):>6}"
        )


def main(run_id: str) -> int:
    run_dir = RUNS_DIR / run_id
    if not run_dir.is_dir():
        print(f"run not found: {run_dir}")
        return 1

    summary = json.loads((run_dir / "comparison_summary.json").read_text(encoding="utf-8"))
    folds_doc = json.loads((run_dir / "folds.json").read_text(encoding="utf-8"))
    executed = folds_doc["folds"]

    contract = load_data_contract(Path("configs/data_contract.yaml"))
    holdout_start = resolve_holdout_start(contract)
    exp = load_experiment_config(Path("configs/experiment.yaml"))

    symbol = summary["symbol"]
    timeframe = summary["timeframe"]
    bars = _load_bars(symbol, timeframe)

    print("=" * 78)
    print(f"TEMPORAL AUDIT  run={run_id}")
    print(f"symbol={symbol} timeframe={timeframe} seed={summary['seed']}")
    print(f"label={summary['label']}")
    print("=" * 78)

    dev_start = exp.periods.development_start
    dev_end = exp.periods.development_end_exclusive
    dev_days = (dev_end - dev_start).days
    print(f"\nDevelopment period : {dev_start.date()} .. {dev_end.date()}  ({dev_days} days)")
    print(f"Frozen holdout     : {holdout_start.date()} .. {contract.cutoff_date}  (NOT read)")

    cfg_folds = full_geometry(exp, holdout_start)
    print(
        f"\nConfig geometry (initial_train={exp.walk_forward.initial_train_days}d, "
        f"val={exp.walk_forward.validation_days}d, test={exp.walk_forward.test_days}d, "
        f"step={exp.walk_forward.step_days}d, min_folds={exp.walk_forward.min_folds})"
    )
    print(f"  folds available over full development : {len(cfg_folds)}")
    print(f"  folds actually executed by this run   : {len(executed)}")
    if cfg_folds:
        print(
            f"  full-geometry OOS span : {cfg_folds[0]['test_start'][:10]} .. "
            f"{cfg_folds[-1]['test_end'][:10]}"
        )

    print("\n" + "-" * 78)
    print("PER-FOLD GEOMETRY (executed folds, from folds.json)")
    print("-" * 78)

    winners: dict[str, list[dict[str, Any]]] = {}
    for method in summary["methods"]:
        path = run_dir / f"{method}_fold_winners.json"
        if path.exists():
            winners[method] = json.loads(path.read_text(encoding="utf-8"))

    oos_test_days = 0
    for f in executed:
        ts, te = _iso(f["train_start"]), _iso(f["train_end"])
        vs, ve = _iso(f["val_start"]), _iso(f["val_end"])
        xs, xe = _iso(f["test_start"]), _iso(f["test_end"])
        oos_test_days += (xe - xs).days
        print(f"\nFold {f['index']}")
        print(
            f"  train      {ts.date()} .. {te.date()}  "
            f"({(te - ts).days:>4}d, bars={_count(bars, ts, te)})"
        )
        print(
            f"  validation {vs.date()} .. {ve.date()}  "
            f"({(ve - vs).days:>4}d, bars={_count(bars, vs, ve)})"
        )
        print(
            f"  test  OOS  {xs.date()} .. {xe.date()}  "
            f"({(xe - xs).days:>4}d, bars={_count(bars, xs, xe)})"
        )
        print(f"  purge={f['purge_bars']} bars   embargo={f['embargo_bars']} bars")
        print(f"  gap train_end->val_start = {(vs - te)}")
        print(f"  gap val_end  ->test_start = {(xs - ve)}")
        print(f"  test_end <= holdout_start : {xe <= holdout_start}")
        for method, rows in winners.items():
            row = next((r for r in rows if r["fold"] == f["index"]), None)
            if row is None:
                continue
            tm = row["test_metrics"]
            print(
                f"    {method:<18} winner={row['winner']}  "
                f"val_sharpe={row['val_sharpe']:.4f}  "
                f"test_sharpe={tm['sharpe']:.4f}  test_ret={tm['total_return']:.4%}  "
                f"legs={tm['n_trades']:.0f}"
            )

    print("\n" + "-" * 78)
    print("SEARCH BUDGET / FAIRNESS (from comparison_summary.json)")
    print("-" * 78)
    for method, body in summary["methods"].items():
        c = body["counters"]
        print(
            f"  {method:<18} cap={body['budget']:>4}  proposed={c['proposed']:>4}  "
            f"invalid={c['invalid']:>3}  duplicate={c['duplicate']:>3}  cached={c['cached']:>4}  "
            f"EVALUATED={c['evaluated']:>4}  seed={body['seed']}"
        )
    parity = summary.get("budget_parity")
    if parity is not None:
        print(f"\n  nominal budget          : {parity['nominal_budget']}")
        print(f"  evaluated per method    : {parity['evaluated_per_method']}")
        print(f"  EQUAL EFFECTIVE BUDGET  : {parity['equal_effective_budget']}")
    print(f"\n  shared search space version : {summary['space_version']}")
    print(f"  shared seed                 : {summary['seed']}")
    print(f"  shared folds                : {summary['n_folds']} (one FoldsBundle for both)")

    print("\n" + "-" * 78)
    print("CONCATENATED OOS TEST SERIES (per method, persisted equity artifacts)")
    print("-" * 78)
    for method in summary["methods"]:
        series, found = concat_oos(run_dir, method)
        if series is None:
            print(f"\n  {method}: NO per-fold OOS equity artifacts persisted -> cannot concatenate")
            continue
        print(f"\n  {method}: folds with equity artifacts = {found}")
        if "net_return" not in series.columns:
            print(f"    columns available: {series.columns}")
            continue
        m = _metrics(series, timeframe)
        span_start = series["open_time"].min()
        span_end = series["open_time"].max()
        days = (span_end - span_start).days  # type: ignore[operator]
        print(f"    span      : {span_start} .. {span_end}  ({days} days)")
        print(f"    bars      : {int(m['n_bars'])}")
        print(f"    total ret : {m['total_return']:.4%}")
        print(f"    CAGR      : {m['ann_return']:.4%}   (>=1y span: {days >= 365})")
        print(f"    ann vol   : {m['ann_volatility']:.4%}")
        print(f"    sharpe    : {m['sharpe']:.4f}")
        print(f"    sortino   : {m['sortino']:.4f}")
        print(f"    max DD    : {m['max_drawdown']:.4%}")
        print(f"    calmar    : {m['calmar']:.4f}")
        print(f"    turnover  : {m.get('turnover', float('nan')):.2f}")
        print(f"    exposure  : {m.get('exposure', float('nan')):.4f}")
        print(f"    legs      : {int(m.get('n_trades', 0))}   # turnover events, NOT round trips")
        print("    costs (fraction of initial capital, summed per bar):")
        for col in ("gross_return", "fee", "slippage", "cost", "funding"):
            if col in series.columns:
                print(f"      {col:<13}: {float(series[col].sum()):+.6f}")
        trades = _trades(run_dir, method)
        if trades is not None and trades.height:
            dur = trades["n_bars"].mean()
            print(f"    round-trip trades : {trades.height}")
            print(f"    mean duration     : {float(dur):.1f} bars ({float(dur):.1f} h at 1h)")
            wins = int((trades["net_return"] > 0).sum())
            print(f"    winning trades    : {wins} ({wins / trades.height:.1%})")
        else:
            print("    round-trip trades : no trade artifacts persisted")

        _breakdown(series, timeframe, "fold", "BY FOLD")
        _breakdown(
            series.with_columns(pl.col("open_time").dt.year().alias("year")),
            timeframe,
            "year",
            "BY CALENDAR YEAR",
        )
        if "regime" in series.columns:
            _breakdown(series, timeframe, "regime", "BY VOLATILITY REGIME (train-fitted)")
        else:
            print(
                "\n    BY VOLATILITY REGIME: not available in this artifact "
                "(regime label not persisted by the run that produced it)"
            )
        assets = series["asset"].unique().to_list() if "asset" in series.columns else []
        print(f"\n    BY ASSET: {assets} (single-asset run; no cross-asset aggregation)")

        assert isinstance(span_end, datetime) and span_end < holdout_start, (
            "OOS series must not enter the holdout"
        )

    print("\n" + "-" * 78)
    print("COVERAGE")
    print("-" * 78)
    print(f"  OOS test days executed : {oos_test_days} of {dev_days} development days")
    print(f"  fraction of development covered by OOS test : {oos_test_days / dev_days:.2%}")
    print(f"  folds executed / folds available : {len(executed)} / {len(cfg_folds)}")
    print("\n  HOLDOUT: not opened by this audit; only its start boundary was read")
    print("           from configs/data_contract.yaml metadata.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else ""))
