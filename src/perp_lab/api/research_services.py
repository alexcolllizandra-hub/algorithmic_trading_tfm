"""Research narrative adapters: summary, timeline, validity."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from perp_lab.api import models as m
from perp_lab.api.settings import ApiSettings
from perp_lab.dashboard import loader


def _parse_dt(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _days_between(start: datetime | None, end: datetime | None) -> int | None:
    if start is None or end is None:
        return None
    return max(0, (end - start).days)


def research_summary(
    settings: ApiSettings, *, run_id: str | None = None
) -> m.ResearchSummaryResponse:
    from perp_lab.config import load_data_contract
    from perp_lab.data.splits import resolve_holdout_start

    runs = loader.discover_runs(settings.runs_dir)
    n_dev = sum(1 for r in runs if r.kind == loader.KIND_DEVELOPMENT)
    n_syn = sum(1 for r in runs if r.kind == loader.KIND_SYNTHETIC)
    contract = load_data_contract(settings.data_contract)
    holdout_start = resolve_holdout_start(contract)

    pilot_run_id = run_id
    if pilot_run_id is None:
        dev_runs = [r for r in runs if r.kind == loader.KIND_DEVELOPMENT]
        pilot_run_id = dev_runs[0].run_id if dev_runs else None

    pilot_symbol = None
    pilot_timeframe = None
    pilot_interval = None
    pilot_budget = None
    pilot_evaluated: dict[str, int | None] = {}
    pilot_folds = None
    pilot_seed = None
    pilot_fraction_used: float | None = None

    if pilot_run_id:
        run_dir = settings.runs_dir / pilot_run_id
        if run_dir.is_dir():
            art = loader.load_run(run_dir)
            cfg = art.config or {}
            pilot_symbol = str(cfg.get("symbol", ""))
            pilot_timeframe = str(cfg.get("timeframe", ""))
            pilot_budget = cfg.get("budget") or (art.summary or {}).get("budget")
            pilot_seed = cfg.get("seed")
            folds_raw = art.folds if isinstance(art.folds, dict) else {}
            pilot_folds = len(folds_raw.get("folds", [])) if folds_raw else None
            methods = (art.summary or {}).get("methods") or {}
            for name, body in methods.items():
                if isinstance(body, dict):
                    counters = body.get("counters") or {}
                    if isinstance(counters, dict):
                        pilot_evaluated[name] = counters.get("evaluated")
            # Pilot-used interval from fold test windows.
            fold_models = folds_raw.get("folds", []) if isinstance(folds_raw, dict) else []
            test_starts: list[datetime] = []
            test_ends: list[datetime] = []
            for f in fold_models:
                if isinstance(f, dict):
                    ts = _parse_dt(f.get("test_start"))
                    te = _parse_dt(f.get("test_end"))
                    if ts:
                        test_starts.append(ts)
                    if te:
                        test_ends.append(te)
            if test_starts and test_ends:
                pilot_interval = f"{min(test_starts).date()} .. {max(test_ends).date()}"
                pilot_days = _days_between(min(test_starts), max(test_ends))
                dev_end = holdout_start
                dev_start = _parse_dt("2020-01-01T00:00:00+00:00")
                if dev_start and pilot_days is not None:
                    total_dev_days = _days_between(dev_start, dev_end)
                    if total_dev_days and total_dev_days > 0:
                        pilot_fraction_used = round(pilot_days / total_dev_days * 100.0, 1)

    return m.ResearchSummaryResponse(
        holdout_start=holdout_start.isoformat(),
        runs_total=len(runs),
        runs_development=n_dev,
        runs_synthetic=n_syn,
        pilot_run_id=pilot_run_id,
        pilot_symbol=pilot_symbol,
        pilot_timeframe=pilot_timeframe,
        pilot_interval=pilot_interval,
        pilot_budget=pilot_budget,
        pilot_evaluated=pilot_evaluated,
        pilot_folds=pilot_folds,
        pilot_seed=pilot_seed,
        pilot_fraction_of_dev_days=pilot_fraction_used,
        artifact_root_exists=settings.artifact_root.exists(),
    )


def _maybe_iso(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    parsed = _parse_dt(value)
    return parsed.isoformat() if parsed else None


def research_timeline(settings: ApiSettings, run_id: str) -> m.TimelineResponse:
    from perp_lab.config import load_data_contract
    from perp_lab.config import load_settings as load_app_settings
    from perp_lab.data.splits import resolve_holdout_start
    from perp_lab.eda.datasets import DataLake

    run_dir = settings.runs_dir / run_id
    if not run_dir.is_dir():
        raise FileNotFoundError(run_id)
    art = loader.load_run(run_dir)
    cfg = art.config or {}
    symbol = str(cfg.get("symbol", "BTCUSDT"))
    timeframe = str(cfg.get("timeframe", "1h"))
    contract = load_data_contract(settings.data_contract)
    holdout_start = resolve_holdout_start(contract)
    lake = DataLake(contract, load_app_settings().paths)
    key = f"{symbol}:{timeframe}_development"
    dev_available = lake.available().get(key, False)
    dev_start = dev_end = dev_bars = None
    if dev_available:
        loaded = lake.load_klines(symbol, timeframe, partition="development")
        frame = loaded.frame
        if frame.height:
            dev_start = frame["open_time"].min()
            dev_end = frame["open_time"].max()
            dev_bars = frame.height

    folds_raw = art.folds if isinstance(art.folds, dict) else {}
    fold_rows: list[m.TimelineFold] = []
    pilot_test_starts: list[datetime] = []
    pilot_test_ends: list[datetime] = []
    for f in folds_raw.get("folds", []) if isinstance(folds_raw, dict) else []:
        if not isinstance(f, dict):
            continue
        fold_rows.append(
            m.TimelineFold(
                index=int(f.get("index", 0)),
                train_start=str(f.get("train_start")) if f.get("train_start") else None,
                train_end=str(f.get("train_end")) if f.get("train_end") else None,
                val_start=str(f.get("val_start")) if f.get("val_start") else None,
                val_end=str(f.get("val_end")) if f.get("val_end") else None,
                test_start=str(f.get("test_start")) if f.get("test_start") else None,
                test_end=str(f.get("test_end")) if f.get("test_end") else None,
                purge_bars=f.get("purge_bars"),
                embargo_bars=f.get("embargo_bars"),
            )
        )
        ts = _parse_dt(f.get("test_start"))
        te = _parse_dt(f.get("test_end"))
        if ts:
            pilot_test_starts.append(ts)
        if te:
            pilot_test_ends.append(te)

    pilot_start = min(pilot_test_starts).isoformat() if pilot_test_starts else None
    pilot_end = max(pilot_test_ends).isoformat() if pilot_test_ends else None
    pilot_days = _days_between(
        min(pilot_test_starts) if pilot_test_starts else None,
        max(pilot_test_ends) if pilot_test_ends else None,
    )
    dev_days = _days_between(
        dev_start if isinstance(dev_start, datetime) else _parse_dt(dev_start),
        dev_end if isinstance(dev_end, datetime) else _parse_dt(dev_end),
    )
    pct_used = None
    if pilot_days is not None and dev_days and dev_days > 0:
        pct_used = round(pilot_days / dev_days * 100.0, 1)
    pct_unused = round(100.0 - pct_used, 1) if pct_used is not None else None

    return m.TimelineResponse(
        run_id=run_id,
        symbol=symbol,
        timeframe=timeframe,
        holdout_start=holdout_start.isoformat(),
        development_start=_maybe_iso(dev_start),
        development_end=_maybe_iso(dev_end),
        development_bars=dev_bars,
        pilot_used_start=pilot_start,
        pilot_used_end=pilot_end,
        pilot_used_days=pilot_days,
        pilot_used_pct_of_dev=pct_used,
        pilot_unused_pct_of_dev=pct_unused,
        n_folds=len(fold_rows),
        folds=fold_rows,
    )


def run_validity(run_dir: Path) -> m.RunValidityResponse:
    art = loader.load_run(run_dir)
    summary = art.summary or {}
    cfg = art.config or {}
    warnings: list[m.ValidityWarning] = []
    checks: list[m.ValidityCheck] = []

    budget = summary.get("budget") or cfg.get("budget")
    methods = summary.get("methods") or {}
    rs_eval = None
    ga_eval = None
    for name, body in methods.items():
        if isinstance(body, dict):
            counters = body.get("counters") or {}
            evaluated = counters.get("evaluated") if isinstance(counters, dict) else None
            if name == "random_search":
                rs_eval = evaluated
            if name == "genetic_algorithm":
                ga_eval = evaluated

    same_budget = budget is not None and rs_eval is not None and ga_eval is not None
    equal_effective = rs_eval == ga_eval if same_budget else None
    checks.append(
        m.ValidityCheck(
            id="same_max_budget",
            label_es="Presupuesto máximo configurado",
            status="pass" if budget else "warn",
            detail_es=f"Presupuesto único de evaluaciones: {budget}" if budget else "No disponible",
        )
    )
    if rs_eval is not None and ga_eval is not None:
        st = "pass" if rs_eval == ga_eval else "warn"
        checks.append(
            m.ValidityCheck(
                id="equal_effective_evaluations",
                label_es="Evaluaciones efectivas RS vs GA",
                status=st,
                detail_es=(
                    f"Random Search: {rs_eval}; GA: {ga_eval}. "
                    + (
                        "Mismo conteo efectivo."
                        if rs_eval == ga_eval
                        else "Conteo desigual: apto para validar el pipeline, no para comparación definitiva."
                    )
                ),
            )
        )
        if rs_eval != ga_eval:
            warnings.append(
                m.ValidityWarning(
                    code="unequal_effective_budget",
                    severity="warn",
                    message_es=(
                        "Mismo presupuesto máximo, pero distinto número de evaluaciones efectivas "
                        f"({rs_eval} RS frente a {ga_eval} GA). Válido para validación del pipeline, "
                        "no para una comparación algorítmica definitiva."
                    ),
                )
            )

    if art.kind == loader.KIND_DEVELOPMENT:
        warnings.append(
            m.ValidityWarning(
                code="exploratory_development",
                severity="info",
                message_es=(
                    "Resultados sobre datos de desarrollo con validación walk-forward. "
                    "No son evidencia del holdout final congelado."
                ),
            )
        )

    if bool(cfg.get("synthetic", False)):
        warnings.append(
            m.ValidityWarning(
                code="synthetic_fixture",
                severity="error",
                message_es="Ejecución con datos sintéticos: no usar como evidencia empírica.",
            )
        )

    return m.RunValidityResponse(
        run_id=run_dir.name,
        kind=art.kind,
        checks=checks,
        warnings=warnings,
        budget=budget,
        random_search_evaluated=rs_eval,
        genetic_algorithm_evaluated=ga_eval,
        equal_effective_evaluations=equal_effective,
    )
