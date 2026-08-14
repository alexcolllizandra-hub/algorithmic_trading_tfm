"""Idempotent ingestion of the study's existing artifacts into the catalogue.

The files under ``artifacts/`` and ``reports/`` are the scientific evidence and
stay exactly where they are. This module reads them, writes an index, and
refuses to invent a number the source does not carry.

Three rules shape every write.

**The gate reports are the authority, not the run directory listing.** The
artifact store also holds earlier pilots and abandoned attempts. Counting those
would inflate the study with work that never entered the record. The inventory
comes from :func:`perp_lab.reporting.study_closure.build_inventory`.

**Originals are never copied or rewritten.** Parquet ledgers are registered in
place via :func:`describe_existing_file`. Re-running ingestion updates the index
and leaves the bytes untouched.

**The holdout is indexed as locked, never as a result.** A registry row records
that the partition exists and is withheld. No observation, return or metric from
inside the window is read or stored. Files whose names announce a holdout
reading are skipped on purpose.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from perp_lab.catalog.models import Run, RunSeed, StrategyFamily, Study
from perp_lab.catalog.repositories import (
    Provenance,
    register_artifact,
    upsert_family,
    upsert_fold,
    upsert_fold_result,
    upsert_gate_result,
    upsert_holdout_entry,
    upsert_round,
    upsert_run,
    upsert_run_seed,
    upsert_study,
)
from perp_lab.catalog.status import ResultStatus
from perp_lab.catalog.storage import describe_existing_file
from perp_lab.reporting.study_closure import (
    GATE_CRITERIA,
    PRIMARY_SYMBOL,
    SECONDARY_SYMBOL,
    TIMEFRAME,
    StudyUnit,
    build_inventory,
)
from perp_lab.utils.hashing import sha256_file

STUDY_KEY = "perp-lab-crypto"
STUDY_TITLE = "perp-lab: interpretable intraday strategies on BTC/ETH perpetuals"

ROUND_SEQUENCE: tuple[tuple[str, str], ...] = (
    ("R2", "R2 — momentum re-baseline"),
    ("R3", "R3 — five-family promotion gate"),
    ("S1", "S1 — mechanical-viability screen"),
    ("S2", "S2 — flow and cross-asset families"),
    ("CRT_INTRADAY_V1", "CRT intradía — registered, not executed"),
)

HOLDOUT_CANDIDATE = "volatility_breakout"
HOLDOUT_START = datetime(2026, 1, 1, tzinfo=UTC)
HOLDOUT_END = datetime(2026, 7, 1, tzinfo=UTC)

# Files that announce a reading of the frozen partition. Ingestion must not
# open them: the catalogue's job is to record that they exist, not to publish
# what they contain.
HOLDOUT_FILENAME_MARKERS: tuple[str, ...] = (
    "final_holdout",
    "holdout_result",
    "holdout_ledger",
)

REGISTERED_PARQUET_SUFFIXES: tuple[str, ...] = (
    "_test_equity.parquet",
    "_test_trades.parquet",
    "_candidates.parquet",
)


class IngestError(RuntimeError):
    """Raised when the source tree cannot be indexed honestly."""


@dataclass
class IngestReport:
    """What one pass wrote, so a second pass can be compared with the first."""

    study_key: str
    n_units: int
    n_rounds: int
    n_families: int
    n_runs: int
    n_seeds: int
    n_folds: int
    n_fold_results: int
    n_artifacts: int
    n_gate_results: int
    skipped_holdout_files: list[str] = field(default_factory=list)
    mismatches: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "study_key": self.study_key,
            "n_units": self.n_units,
            "n_rounds": self.n_rounds,
            "n_families": self.n_families,
            "n_runs": self.n_runs,
            "n_seeds": self.n_seeds,
            "n_folds": self.n_folds,
            "n_fold_results": self.n_fold_results,
            "n_artifacts": self.n_artifacts,
            "n_gate_results": self.n_gate_results,
            "skipped_holdout_files": list(self.skipped_holdout_files),
            "mismatches": list(self.mismatches),
        }


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _parse_dt(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _is_holdout_path(path: Path) -> bool:
    name = path.name.lower()
    return any(marker in name for marker in HOLDOUT_FILENAME_MARKERS)


def _provenance(path: Path, *, git_commit: str | None = None) -> Provenance:
    return Provenance(
        source_artifact=path.as_posix(),
        source_sha256=sha256_file(path) if path.is_file() else None,
        git_commit=git_commit,
        code_version="catalog-ingest-1",
    )


def _core_from_aggregate(aggregate: MappingLike) -> dict[str, float | int | None]:
    """Map a comparison-summary aggregate onto the twelve typed columns.

    Figures the source does not carry stay ``None``. They are not filled with
    zero: zero is a measurement, and this function is not allowed to invent one.
    """
    return {
        "total_return": _maybe_float(aggregate.get("mean_test_total_return")),
        "sharpe": _maybe_float(aggregate.get("mean_test_sharpe")),
        "max_drawdown": _maybe_float(aggregate.get("mean_test_max_drawdown")),
        "n_trades": _maybe_int(aggregate.get("mean_test_n_trades")),
    }


def _core_from_test_metrics(metrics: MappingLike) -> dict[str, float | int | None]:
    return {
        "total_return": _maybe_float(metrics.get("total_return")),
        "sharpe": _maybe_float(metrics.get("sharpe")),
        "sortino": _maybe_float(metrics.get("sortino")),
        "max_drawdown": _maybe_float(metrics.get("max_drawdown")),
        "calmar": _maybe_float(metrics.get("calmar")),
        "profit_factor": _maybe_float(metrics.get("profit_factor")),
        "win_rate": _maybe_float(metrics.get("win_rate")),
        "n_trades": _maybe_int(metrics.get("n_trades")),
        "turnover": _maybe_float(metrics.get("turnover")),
        "exposure": _maybe_float(metrics.get("exposure")),
        "costs": _maybe_float(metrics.get("costs")),
        "funding": _maybe_float(metrics.get("funding")),
    }


def _maybe_float(value: object) -> float | None:
    if value is None:
        return None
    return float(value)  # type: ignore[arg-type]


def _maybe_int(value: object) -> int | None:
    if value is None:
        return None
    return round(float(value))  # type: ignore[arg-type]


MappingLike = dict[str, Any]


def _family_display(key: str) -> str:
    return key.replace("_", " ")


def ingest_study(
    session: Session,
    root: Path,
    *,
    units: Sequence[StudyUnit] | None = None,
    git_commit: str | None = None,
    register_parquets: bool = True,
) -> IngestReport:
    """Index the study at ``root``. Safe to call twice; the second pass updates.

    ``units`` defaults to the canonical inventory. Tests pass a synthetic list
    so they do not depend on the 142 real run directories.
    """
    root = Path(root)
    resolved_units = list(units) if units is not None else build_inventory(root)
    if not resolved_units:
        raise IngestError("The inventory is empty; refusing to create a hollow catalogue.")

    study = upsert_study(
        session,
        key=STUDY_KEY,
        title=STUDY_TITLE,
        primary_symbol=PRIMARY_SYMBOL,
        secondary_symbol=SECONDARY_SYMBOL,
        timeframe=TIMEFRAME,
        holdout_start=HOLDOUT_START,
        holdout_end=HOLDOUT_END,
        description=(
            "Catalogue of the closed crypto study. The holdout window is recorded "
            "as a boundary only; its observations are not ingested."
        ),
    )

    rounds = _ensure_rounds(session, study, root, git_commit=git_commit)
    families = _ensure_families(session, study, resolved_units, root, git_commit=git_commit)
    report = IngestReport(
        study_key=STUDY_KEY,
        n_units=len(resolved_units),
        n_rounds=len(rounds),
        n_families=len(families),
        n_runs=0,
        n_seeds=0,
        n_folds=0,
        n_fold_results=0,
        n_artifacts=0,
        n_gate_results=0,
    )

    seen_runs: set[tuple[str, str]] = set()
    for unit in resolved_units:
        key = (unit.run_dir.resolve().as_posix(), unit.engine)
        if key in seen_runs:
            continue
        seen_runs.add(key)
        counts = _ingest_run(
            session,
            study=study,
            experiment_round=rounds[unit.gate],
            family=families[unit.family],
            unit=unit,
            git_commit=git_commit,
            register_parquets=register_parquets,
            skipped=report.skipped_holdout_files,
        )
        report.n_runs += 1
        report.n_seeds += counts["seeds"]
        report.n_folds += counts["folds"]
        report.n_fold_results += counts["fold_results"]
        report.n_artifacts += counts["artifacts"]

    report.n_gate_results = _ingest_gate_verdicts(
        session, root, rounds, families, git_commit=git_commit
    )
    _lock_holdout(session, study, root, git_commit=git_commit)
    report.mismatches = verify_against_sources(session, resolved_units)
    return report


def _ensure_rounds(
    session: Session, study: Study, root: Path, *, git_commit: str | None
) -> dict[str, Any]:
    rounds: dict[str, Any] = {}
    for sequence, (key, name) in enumerate(ROUND_SEQUENCE, start=1):
        executed = key != "CRT_INTRADAY_V1"
        source = root / "docs" / "methodology"
        provenance = Provenance(
            source_artifact=source.as_posix() if source.exists() else f"round:{key}",
            source_sha256=None,
            git_commit=git_commit,
            code_version="catalog-ingest-1",
        )
        rounds[key] = upsert_round(
            session,
            study=study,
            key=key,
            name=name,
            sequence=sequence,
            criterion=GATE_CRITERIA.get(key),
            status=ResultStatus.EXECUTED if executed else ResultStatus.NOT_EXECUTED,
            status_note=(
                None
                if executed
                else "Registered as a new round. No experiment has been run; no metrics exist."
            ),
            provenance=provenance,
        )
    return rounds


def _ensure_families(
    session: Session,
    study: Study,
    units: Sequence[StudyUnit],
    root: Path,
    *,
    git_commit: str | None,
) -> dict[str, StrategyFamily]:
    families: dict[str, StrategyFamily] = {}
    seen: set[str] = set()
    for unit in units:
        if unit.family in seen:
            continue
        seen.add(unit.family)
        families[unit.family] = upsert_family(
            session,
            study=study,
            key=unit.family,
            name=_family_display(unit.family),
            hypothesis=None,
            module=f"perp_lab.strategies.{unit.family}",
            status=ResultStatus.REJECTED,
            status_note=f"Closed under gate {unit.gate}; rejected at study-level correction.",
            provenance=_provenance(unit.run_dir / "comparison_summary.json", git_commit=git_commit)
            if (unit.run_dir / "comparison_summary.json").is_file()
            else Provenance(
                source_artifact=unit.run_dir.as_posix(),
                git_commit=git_commit,
                code_version="catalog-ingest-1",
            ),
        )
    # The CRT families are hypotheses. They must appear as NOT_EXECUTED so the
    # dashboard can list them without implying a result.
    for key in (
        "crt_htf_range_reversal",
        "pdl_reclaim_long",
        "pdh_reclaim_short",
        "session_liquidity_sweep",
        "session_range_rotation",
        "opening_range_breakout_retest",
        "failed_breakout_reversal",
        "double_sweep_reversal",
        "crt_three_candle_model",
    ):
        families[key] = upsert_family(
            session,
            study=study,
            key=key,
            name=_family_display(key),
            hypothesis="Mechanical CRT / session-liquidity hypothesis. Unexecuted.",
            module=f"perp_lab.crt.strategies.{key}",
            status=ResultStatus.NOT_EXECUTED,
            status_note="CRT_INTRADAY_V1 is registered; no backtest has been run.",
            provenance=Provenance(
                source_artifact="docs/methodology/crt_intraday.md",
                git_commit=git_commit,
                code_version="catalog-ingest-1",
            ),
        )
    return families


def _ingest_run(
    session: Session,
    *,
    study: Study,
    experiment_round: Any,
    family: StrategyFamily,
    unit: StudyUnit,
    git_commit: str | None,
    register_parquets: bool,
    skipped: list[str],
) -> dict[str, int]:
    summary_path = unit.run_dir / "comparison_summary.json"
    if not summary_path.is_file():
        raise IngestError(f"{unit.run_dir}: comparison_summary.json is missing.")
    if _is_holdout_path(summary_path):
        skipped.append(summary_path.as_posix())
        return {"seeds": 0, "folds": 0, "fold_results": 0, "artifacts": 0}

    summary = _read_json(summary_path)
    provenance = _provenance(summary_path, git_commit=git_commit)
    run = upsert_run(
        session,
        study=study,
        run_id=f"{unit.run_dir.name}:{unit.engine}",
        symbol=str(summary.get("symbol") or unit.symbol),
        timeframe=str(summary.get("timeframe") or TIMEFRAME),
        engine=unit.engine,
        run_dir=unit.run_dir.as_posix(),
        experiment_round=experiment_round,
        family=family,
        config={
            "seed": summary.get("seed"),
            "budget": summary.get("budget"),
            "n_folds": summary.get("n_folds"),
            "label": summary.get("label"),
        },
        status=ResultStatus.EXECUTED,
        provenance=provenance,
    )

    method = (summary.get("methods") or {}).get(unit.engine) or {}
    aggregate = method.get("aggregate_test") or {}
    seed = upsert_run_seed(
        session,
        run=run,
        seed=int(summary.get("seed") or unit.seed),
        n_folds=int(summary.get("n_folds") or 0) or None,
        metrics=_core_from_aggregate(aggregate),
        status=ResultStatus.EXECUTED,
        provenance=provenance,
    )

    n_folds, n_results = _ingest_folds(
        session, unit=unit, run=run, seed=seed, git_commit=git_commit
    )
    n_artifacts = 0
    if register_parquets:
        n_artifacts = _register_run_parquets(
            session, study=study, run=run, run_dir=unit.run_dir, skipped=skipped
        )
    return {
        "seeds": 1,
        "folds": n_folds,
        "fold_results": n_results,
        "artifacts": n_artifacts,
    }


def _ingest_folds(
    session: Session,
    *,
    unit: StudyUnit,
    run: Run,
    seed: RunSeed,
    git_commit: str | None,
) -> tuple[int, int]:
    folds_path = unit.run_dir / "folds.json"
    if not folds_path.is_file():
        return 0, 0
    payload = _read_json(folds_path)
    windows = payload.get("folds") if isinstance(payload, dict) else payload
    if not isinstance(windows, list):
        return 0, 0

    winners_path = unit.run_dir / f"{unit.engine}_fold_winners.json"
    winners_by_index: dict[int, dict[str, Any]] = {}
    if winners_path.is_file():
        winners = _read_json(winners_path)
        if isinstance(winners, list):
            winners_by_index = {int(item["fold"]): item for item in winners if "fold" in item}

    n_folds = 0
    n_results = 0
    fold_provenance = _provenance(folds_path, git_commit=git_commit)
    for window in windows:
        fold = upsert_fold(
            session,
            run=run,
            fold_index=int(window["index"]),
            train_start=_parse_dt(str(window["train_start"])),
            train_end=_parse_dt(str(window["train_end"])),
            test_start=_parse_dt(str(window["test_start"])),
            test_end=_parse_dt(str(window["test_end"])),
            purge_bars=window.get("purge_bars"),
            embargo_bars=window.get("embargo_bars"),
            provenance=fold_provenance,
        )
        n_folds += 1
        winner = winners_by_index.get(int(window["index"]))
        if winner is None:
            continue
        test_metrics = winner.get("test_metrics") or {}
        upsert_fold_result(
            session,
            fold=fold,
            run_seed=seed,
            params=winner.get("params") or {},
            metrics=_core_from_test_metrics(test_metrics),
            status=ResultStatus.EXECUTED,
            provenance=_provenance(winners_path, git_commit=git_commit),
        )
        n_results += 1
    return n_folds, n_results


def _register_run_parquets(
    session: Session,
    *,
    study: Study,
    run: Run,
    run_dir: Path,
    skipped: list[str],
) -> int:
    count = 0
    for path in sorted(run_dir.iterdir()):
        if not path.is_file():
            continue
        if _is_holdout_path(path):
            skipped.append(path.as_posix())
            continue
        if not any(path.name.endswith(suffix) for suffix in REGISTERED_PARQUET_SUFFIXES):
            continue
        kind = (
            "equity"
            if path.name.endswith("_test_equity.parquet")
            else "trades"
            if path.name.endswith("_test_trades.parquet")
            else "search_evaluations"
        )
        metadata = describe_existing_file(path, media_type="application/vnd.apache.parquet")
        register_artifact(
            session,
            metadata,
            kind=kind,
            run=run,
            study=study,
            status=ResultStatus.EXECUTED,
            provenance=Provenance(
                source_artifact=path.as_posix(),
                source_sha256=metadata.sha256,
                code_version="catalog-ingest-1",
            ),
        )
        count += 1
    return count


def _ingest_gate_verdicts(
    session: Session,
    root: Path,
    rounds: dict[str, Any],
    families: dict[str, StrategyFamily],
    *,
    git_commit: str | None,
) -> int:
    """Record the study-level rejection of every executed family.

    Per-criterion R3 bars live in the thesis report when it is present; every
    other family is recorded as rejected under its gate's pre-registered
    criterion, which is the honest summary of the closed study.
    """
    written = 0
    for family_key, family in families.items():
        if family.status is ResultStatus.NOT_EXECUTED:
            continue
        gate = _gate_for_family(family_key, rounds)
        if gate is None:
            continue
        upsert_gate_result(
            session,
            experiment_round=rounds[gate],
            family=family,
            symbol=PRIMARY_SYMBOL,
            criterion_key="study_level",
            criterion=GATE_CRITERIA.get(gate),
            verdict="REJECTED",
            status=ResultStatus.REJECTED,
            provenance=Provenance(
                source_artifact=f"gate:{gate}",
                git_commit=git_commit,
                code_version="catalog-ingest-1",
            ),
        )
        written += 1
    return written


def _gate_for_family(family_key: str, rounds: dict[str, Any]) -> str | None:
    mapping = {
        "momentum": "R2",
        "breakout": "R3",
        "mean_reversion": "R3",
        "volatility_breakout": "R3",
        "funding": "R3",
        "BTC_ETH_confirmation": "R3",
        "intraday_seasonality": "S1",
        "mtf_trend_consensus": "S1",
        "illiquidity_reversion": "S1",
        "xasset_spread_reversion": "S1",
        "taker_flow_extreme": "S2",
        "funding_reversal": "S2",
        "flow_price_divergence": "S2",
    }
    key = mapping.get(family_key)
    return key if key in rounds else None


def _lock_holdout(session: Session, study: Study, root: Path, *, git_commit: str | None) -> None:
    """Record that the partition exists and that its reading is not published."""
    upsert_holdout_entry(
        session,
        study=study,
        candidate_key=HOLDOUT_CANDIDATE,
        candidate_fingerprint="predeclared:volatility_breakout",
        status=ResultStatus.HOLDOUT_LOCKED,
        status_note=(
            "The reserved window is [2026-01-01, 2026-07-01). A reading may exist "
            "on disk; it is not ingested and must not be served until audited."
        ),
        authorization_token_present=False,
        commit_before="02b79f1",
        audited=False,
        provenance=Provenance(
            source_artifact="docs/methodology/holdout_audit_status.md",
            git_commit=git_commit,
            code_version="catalog-ingest-1",
        ),
    )


def verify_against_sources(session: Session, units: Sequence[StudyUnit]) -> list[str]:
    """Re-read the source files and compare them with what the catalogue holds.

    A mismatch is a string describing the disagreement, never a coerced number.
    The dashboard must not be pointed at the catalogue while this list is
    non-empty: the index would then be a different claim from the evidence.
    """
    mismatches: list[str] = []
    seen: set[tuple[str, str]] = set()
    for unit in units:
        key = (unit.run_dir.resolve().as_posix(), unit.engine)
        if key in seen:
            continue
        seen.add(key)
        summary_path = unit.run_dir / "comparison_summary.json"
        if not summary_path.is_file():
            mismatches.append(f"{unit.run_dir.name}: source summary missing after ingest")
            continue
        summary = _read_json(summary_path)
        run_id = f"{unit.run_dir.name}:{unit.engine}"
        run = session.scalars(select(Run).where(Run.run_id == run_id)).one_or_none()
        if run is None:
            mismatches.append(f"{run_id}: run was not ingested")
            continue
        expected = _core_from_aggregate(
            ((summary.get("methods") or {}).get(unit.engine) or {}).get("aggregate_test") or {}
        )
        seed_row = next(
            (s for s in run.seeds if s.seed == int(summary.get("seed") or unit.seed)), None
        )
        if seed_row is None:
            mismatches.append(f"{unit.run_dir.name}: seed row missing")
            continue
        for column, expected_value in expected.items():
            observed = getattr(seed_row, column)
            if expected_value is None and observed is None:
                continue
            if expected_value is None or observed is None:
                mismatches.append(
                    f"{unit.run_dir.name}.{column}: source={expected_value!r} catalogue={observed!r}"
                )
                continue
            if abs(float(observed) - float(expected_value)) > 1e-9:
                mismatches.append(
                    f"{unit.run_dir.name}.{column}: source={expected_value} catalogue={observed}"
                )
    return mismatches


def ingest_twice_is_identical(session: Session, root: Path, units: Sequence[StudyUnit]) -> bool:
    """Run ingestion twice and report whether the counts stayed put."""
    first = ingest_study(session, root, units=units, register_parquets=False)
    second = ingest_study(session, root, units=units, register_parquets=False)
    return (
        first.n_runs == second.n_runs
        and first.n_seeds == second.n_seeds
        and first.n_folds == second.n_folds
        and first.n_fold_results == second.n_fold_results
        and not second.mismatches
    )


__all__ = [
    "HOLDOUT_CANDIDATE",
    "HOLDOUT_END",
    "HOLDOUT_START",
    "STUDY_KEY",
    "IngestError",
    "IngestReport",
    "ingest_study",
    "verify_against_sources",
]
