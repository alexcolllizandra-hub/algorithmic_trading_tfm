"""Adapter services: map on-disk artifacts to versioned API models.

All artifact interpretation delegates to ``perp_lab.dashboard.loader`` and
``perp_lab.data`` — this layer only reshapes those results into the v1 response
models. No backtesting, search or objective logic is re-implemented here.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import polars as pl

from perp_lab.api import models as m
from perp_lab.api.pagination import PageParams, paginate
from perp_lab.api.settings import ApiSettings
from perp_lab.dashboard import loader

_OBJ_PREFIX = "obj_"
_FOLD_RE = re.compile(r"_fold(\d+)_test_(equity|trades)\.parquet$")


# Runs
def list_run_summaries(settings: ApiSettings) -> list[m.RunSummaryModel]:
    runs = loader.discover_runs(settings.runs_dir)
    return [
        m.RunSummaryModel(
            run_id=r.run_id,
            kind=r.kind,
            label=r.label,
            family=r.family,
            algorithm=r.algorithm,
            symbol=r.symbol,
            timeframe=r.timeframe,
            seed=r.seed,
            budget=r.budget,
            n_folds=r.n_folds,
            best_method=r.best_method,
            has_comparison=r.has_comparison,
            protocol=r.protocol,
            contaminated=r.protocol != loader.CURRENT_SEARCH_PROTOCOL,
        )
        for r in runs
    ]


def _artifact_files(run_dir: Path) -> list[str]:
    return sorted(p.name for p in run_dir.iterdir() if p.is_file())


def run_detail(run_dir: Path) -> m.RunDetailResponse:
    art = loader.load_run(run_dir)
    return m.RunDetailResponse(
        run_id=run_dir.name,
        kind=art.kind,
        summary=art.summary,
        config=art.config,
        environment=art.environment,
        git_state=loader._read_json(run_dir / "git_state.json"),
        available_methods=art.available_methods,
        artifact_files=_artifact_files(run_dir),
        warnings=list(loader.warning_messages(art)),
    )


def comparison(run_dir: Path) -> m.ComparisonResponse:
    art = loader.load_run(run_dir)
    s = art.summary or {}
    table = loader.comparison_table(art.summary)
    methods = (
        [m.MethodComparison(**row) for row in table.to_dicts()] if not table.is_empty() else []
    )
    fb = loader.fair_budget_report(art.summary)
    rows = (
        [m.FairBudgetRow(**r) for r in fb["rows"].to_dicts()] if not fb["rows"].is_empty() else []
    )
    return m.ComparisonResponse(
        run_id=run_dir.name,
        kind=art.kind,
        family=str(s.get("family", "")),
        symbol=str(s.get("symbol", "")),
        timeframe=str(s.get("timeframe", "")),
        budget=s.get("budget"),
        comparison_metric=s.get("comparison_metric"),
        best_out_of_sample_method=s.get("best_out_of_sample_method"),
        warning=s.get("warning"),
        search_protocol=art.protocol,
        contaminated=art.contaminated,
        methods=methods,
        fair_budget=m.FairBudget(
            budget=fb["budget"],
            n_folds=fb["n_folds"],
            parity_level=fb["parity_level"],
            definition=fb["definition"],
            ok=bool(fb["ok"]),
            rows=rows,
        ),
    )


# Candidates
def _parse_params(value: Any) -> dict[str, Any]:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return {}
    return {}


def candidate_models(run_dir: Path, method: str) -> list[m.CandidateModel]:
    df = loader.candidate_ranking(run_dir, method)
    if df.is_empty():
        return []
    out: list[m.CandidateModel] = []
    for row in df.to_dicts():
        objective = {
            k[len(_OBJ_PREFIX) :]: float(v)
            for k, v in row.items()
            if k.startswith(_OBJ_PREFIX) and isinstance(v, int | float) and v is not None
        }
        out.append(
            m.CandidateModel(
                candidate_id=str(row.get("candidate_id")),
                family=row.get("family"),
                fold_index=row.get("fold_index"),
                status=row.get("status"),
                fitness=row.get("fitness"),
                failure_reason=row.get("failure_reason"),
                step=row.get("step"),
                n_active_params=row.get("n_active_params"),
                mean_val_sharpe=row.get("mean_val_sharpe"),
                params=_parse_params(row.get("params_json")),
                objective_components=objective,
            )
        )
    return out


def paginate_candidates(run_dir: Path, method: str, params: PageParams) -> m.CandidatesResponse:
    items, meta = paginate(candidate_models(run_dir, method), params)
    return m.CandidatesResponse(run_id=run_dir.name, method=method, items=items, meta=meta)


# Folds
def folds(run_dir: Path) -> m.FoldsResponse:
    art = loader.load_run(run_dir)
    folds_df = loader.folds_frame(art)
    fold_models = [m.FoldModel(**r) for r in folds_df.to_dicts()] if not folds_df.is_empty() else []
    winners: dict[str, list[m.FoldWinnerModel]] = {}
    for method in loader.METHODS:
        wf = loader.fold_winners_frame(run_dir, method)
        if wf.is_empty():
            continue
        method_winners: list[m.FoldWinnerModel] = []
        for r in wf.to_dicts():
            r = dict(r)
            r["params"] = _parse_params(r.pop("params", "{}"))
            method_winners.append(m.FoldWinnerModel(**r))
        winners[method] = method_winners
    regime_inputs = []
    if isinstance(art.folds, dict):
        regime_inputs = list(art.folds.get("regime_inputs", []))
    return m.FoldsResponse(
        run_id=run_dir.name, regime_inputs=regime_inputs, folds=fold_models, winners=winners
    )


# Search analytics
def search_analytics(run_dir: Path) -> m.SearchAnalyticsResponse:
    art = loader.load_run(run_dir)
    convergence: dict[str, list[m.ConvergencePoint]] = {}
    fold_ids: set[int] = set()
    for method in loader.METHODS:
        cf = loader.convergence_frame(run_dir, method)
        if not cf.is_empty():
            convergence[method] = [m.ConvergencePoint(**r) for r in cf.to_dicts()]
            fold_ids.update(int(v) for v in cf["fold"].to_list())
    div = loader.diversity_frame(art)
    diversity = [m.GaGenerationDiversity(**r) for r in div.to_dicts()] if not div.is_empty() else []
    gb = loader.generation_best_frame(art)
    return m.SearchAnalyticsResponse(
        run_id=run_dir.name,
        search_protocol=art.protocol,
        convergence_folds=sorted(fold_ids),
        convergence=convergence,
        ga_diversity=diversity,
        ga_generation_best=gb.to_dicts() if not gb.is_empty() else [],
        ga_lineage=art.ga_lineage,
    )


# Performance / equity / trades
def _fold_winners_map(run_dir: Path) -> dict[tuple[str, int], dict[str, Any]]:
    """Map (method, fold) -> fold-winner record when artifacts exist."""
    out: dict[tuple[str, int], dict[str, Any]] = {}
    for method in loader.METHODS:
        path = run_dir / f"{method}_fold_winners.json"
        if not path.exists():
            continue
        try:
            rows = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if not isinstance(rows, list):
            continue
        for row in rows:
            if isinstance(row, dict) and row.get("fold") is not None:
                out[(method, int(row["fold"]))] = row
    return out


def _equity_summary(eq: pl.DataFrame, winner: dict[str, Any] | None) -> m.EquitySeriesSummary:
    n = eq.height
    final_equity = _to_float(eq["equity"][-1]) if n and "equity" in eq.columns else None
    max_dd = _to_float(eq["drawdown"].min()) if n and "drawdown" in eq.columns else None
    period_start = _iso(eq["open_time"][0]) if n and "open_time" in eq.columns else None
    period_end = _iso(eq["open_time"][-1]) if n and "open_time" in eq.columns else None
    candidate_id = winner.get("winner") if winner else None
    return m.EquitySeriesSummary(
        n_points_total=n,
        final_equity=final_equity,
        max_drawdown=max_dd,
        period_start=period_start,
        period_end=period_end,
        candidate_id=str(candidate_id) if candidate_id else None,
    )


def _fold_equity_files(run_dir: Path) -> list[tuple[str, int]]:
    """Return (method, fold) pairs that have a test-equity artifact on disk."""
    found: list[tuple[str, int]] = []
    for p in sorted(run_dir.glob("*_fold*_test_equity.parquet")):
        match = _FOLD_RE.search(p.name)
        if not match:
            continue
        method = p.name[: match.start()]
        found.append((method, int(match.group(1))))
    return found


def performance(run_dir: Path) -> m.PerformanceResponse:
    art = loader.load_run(run_dir)
    s = art.summary or {}
    aggregate: dict[str, dict[str, float | int]] = {}
    for name, method in (s.get("methods") or {}).items():
        agg = method.get("aggregate_test") if isinstance(method, dict) else None
        if isinstance(agg, dict):
            aggregate[name] = agg
    winners = _fold_winners_map(run_dir)
    fold_perf: list[m.PerformanceFold] = []
    for method, fold in _fold_equity_files(run_dir):
        eq = loader.equity_frame(run_dir, method, fold)
        tr = loader.trades_frame(run_dir, method, fold)
        summary = _equity_summary(eq, winners.get((method, fold)))
        fold_perf.append(
            m.PerformanceFold(
                method=method,
                fold=fold,
                n_points=summary.n_points_total,
                final_equity=summary.final_equity,
                max_drawdown=summary.max_drawdown,
                n_trades=tr.height,
                candidate_id=summary.candidate_id,
                period_start=summary.period_start,
                period_end=summary.period_end,
            )
        )
    return m.PerformanceResponse(
        run_id=run_dir.name,
        kind=art.kind,
        warning=s.get("warning"),
        aggregate=aggregate,
        folds=fold_perf,
        best_method=s.get("best_out_of_sample_method"),
    )


def _iso(value: Any) -> str:
    return value.isoformat() if isinstance(value, datetime) else str(value)


def _to_float(value: Any) -> float | None:
    if isinstance(value, int | float):
        return float(value)
    return None


def equity(run_dir: Path, method: str, fold: int, params: PageParams) -> m.EquityResponse:
    eq = loader.equity_frame(run_dir, method, fold)
    winners = _fold_winners_map(run_dir)
    summary = _equity_summary(eq, winners.get((method, fold)))
    points: list[m.EquityPoint] = []
    if not eq.is_empty() and "open_time" in eq.columns:
        for r in eq.to_dicts():
            points.append(
                m.EquityPoint(
                    open_time=_iso(r.get("open_time")),
                    equity=r.get("equity"),
                    drawdown=r.get("drawdown"),
                )
            )
    window, meta = paginate(points, params)
    return m.EquityResponse(
        run_id=run_dir.name,
        method=method,
        fold=fold,
        points=window,
        meta=meta,
        summary=summary,
    )


def trades(run_dir: Path, method: str, fold: int, params: PageParams) -> m.TradesResponse:
    tr = loader.trades_frame(run_dir, method, fold)
    items: list[m.TradeModel] = []
    if not tr.is_empty():
        for r in tr.to_dicts():
            items.append(
                m.TradeModel(
                    trade_id=r.get("trade_id"),
                    entry_time=_iso(r.get("entry_time"))
                    if r.get("entry_time") is not None
                    else None,
                    exit_time=_iso(r.get("exit_time")) if r.get("exit_time") is not None else None,
                    n_bars=r.get("n_bars"),
                    position=r.get("position"),
                    net_return=r.get("net_return"),
                    funding=r.get("funding"),
                    cost=r.get("cost"),
                    exit_reason=r.get("exit_reason"),
                )
            )
    window, meta = paginate(items, params)
    return m.TradesResponse(run_id=run_dir.name, method=method, fold=fold, items=window, meta=meta)


# Artifacts
def artifacts(run_dir: Path) -> m.ArtifactsResponse:
    art = loader.load_run(run_dir)
    failed: dict[str, list[dict[str, Any]]] = {}
    for method in loader.METHODS:
        data = loader._read_json(run_dir / f"{method}_failed_candidates.json")
        if isinstance(data, dict) and isinstance(data.get("candidates"), list):
            failed[method] = data["candidates"]
        elif isinstance(data, list):
            failed[method] = data
    return m.ArtifactsResponse(
        run_id=run_dir.name,
        dataset_manifests=art.dataset_manifests,
        feature_manifest=art.feature_manifest,
        search_space=art.search_space,
        objective=art.objective,
        environment=art.environment,
        git_state=loader._read_json(run_dir / "git_state.json"),
        warnings=list(loader.warning_messages(art)),
        failed_candidates=failed,
        files=_artifact_files(run_dir),
    )


# Market coverage (manifest-based; holdout-safe, no data read)
def market_coverage(settings: ApiSettings) -> m.MarketCoverageResponse:
    from perp_lab.config import load_data_contract
    from perp_lab.data.provenance import _classify
    from perp_lab.data.splits import resolve_holdout_start

    contract = load_data_contract(settings.data_contract)
    holdout_start = resolve_holdout_start(contract)
    datasets: list[m.DatasetCoverage] = []
    dev_ends: list[datetime] = []
    for mpath in sorted(settings.manifests_dir.glob("*.json")):
        meta = json.loads(mpath.read_text(encoding="utf-8"))
        source = str(meta.get("source", ""))
        period_end = meta.get("period_end")
        crosses = None
        if period_end is not None:
            end = datetime.fromisoformat(str(period_end).replace("Z", "+00:00"))
            crosses = end >= holdout_start
            if "development" in str(meta.get("dataset_id", "")) and not crosses:
                dev_ends.append(end)
        datasets.append(
            m.DatasetCoverage(
                dataset_id=str(meta.get("dataset_id", mpath.stem)),
                classification=_classify(source),
                provider=source or "unknown",
                symbol=meta.get("symbol"),
                timeframe=meta.get("timeframe"),
                stream=meta.get("stream"),
                row_count=meta.get("row_count"),
                min_timestamp=str(meta.get("period_start")) if meta.get("period_start") else None,
                max_timestamp=str(period_end) if period_end else None,
                crosses_holdout=crosses,
            )
        )
    dev_end_max = max(dev_ends).isoformat() if dev_ends else None
    return m.MarketCoverageResponse(
        holdout_start=holdout_start.isoformat(),
        development_end_max=dev_end_max,
        datasets=datasets,
    )


def ohlcv(
    settings: ApiSettings,
    symbol: str,
    timeframe: str,
    params: PageParams,
) -> m.OhlcvResponse:
    """Development-partition OHLCV only. Holdout observations are never exposed."""
    from perp_lab.config import load_data_contract, load_settings
    from perp_lab.eda.datasets import DataLake

    contract = load_data_contract(settings.data_contract)
    lake = DataLake(contract, load_settings().paths)
    loaded = lake.load_klines(symbol, timeframe, partition="development")
    df = loaded.frame.select(["open_time", "open", "high", "low", "close", "volume"])
    rows = df.to_dicts()
    window, meta = paginate(rows, params)
    bars = [
        m.OhlcvBar(
            open_time=_iso(r["open_time"]),
            open=float(r["open"]),
            high=float(r["high"]),
            low=float(r["low"]),
            close=float(r["close"]),
            volume=float(r["volume"]),
        )
        for r in window
    ]
    return m.OhlcvResponse(
        symbol=symbol.upper(),
        timeframe=timeframe,
        holdout_excluded=loaded.holdout_excluded,
        bars=bars,
        meta=meta,
    )
