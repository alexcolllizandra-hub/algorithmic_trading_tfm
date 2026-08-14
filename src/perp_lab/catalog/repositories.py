"""Typed reads and idempotent writes over the catalogue.

Ingestion re-reads the same artifacts many times: after a bug fix, after a new
gate closes, after a machine that died halfway through. Every write here is
therefore keyed on a *natural key* — the identifier the evidence itself carries,
such as ``(run_id, seed)`` or ``(fold_id, run_seed_id)`` — and updates in place
when that key already exists. Running the whole ingestion twice must leave the
database exactly as one run left it.

Two mechanisms enforce that, and both rely on the same unique constraints:

* :func:`_upsert` looks the row up by its natural key and updates it, which
  keeps the ORM identity map coherent and lets the caller keep using the
  returned object. This is the path for everything the API navigates.
* :func:`bulk_upsert_search_evaluations` uses ``INSERT ... ON CONFLICT DO
  UPDATE`` on PostgreSQL and SQLite, because the search-evaluation table is the
  one with hundreds of thousands of rows and a per-row ``SELECT`` would dominate
  ingestion time. Other dialects fall back to the row-at-a-time path.

The second rule this module enforces is that a status which says nothing was
measured cannot carry numbers. Writing metrics under ``NOT_EXECUTED``,
``SKIPPED`` or ``HOLDOUT_LOCKED`` raises rather than being quietly stored, and
switching a row to such a status clears the metric columns to ``NULL`` instead
of leaving figures behind that no status vouches for.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from perp_lab.catalog.models import (
    CORE_METRIC_COLUMNS,
    Artifact,
    Base,
    ExperimentRound,
    Fold,
    FoldResult,
    GateResult,
    HoldoutRegistryEntry,
    Metric,
    MonteCarloRun,
    Run,
    RunSeed,
    SearchEvaluation,
    StrategyFamily,
    StrategySpec,
    Study,
    utcnow,
)
from perp_lab.catalog.status import ResultStatus, has_metrics
from perp_lab.catalog.storage import ObjectMetadata

MetricValues = Mapping[str, float | int | None]


class CatalogIntegrityError(ValueError):
    """A write that the catalogue refuses because it would misstate the evidence."""


class MetricsWithoutMeasurementError(CatalogIntegrityError):
    """Raised when numbers are supplied under a status that measured nothing."""


@dataclass(frozen=True)
class Provenance:
    """Where a row's numbers came from. Required on every result write."""

    source_artifact: str
    source_sha256: str | None = None
    git_commit: str | None = None
    code_version: str | None = None
    ingested_at: datetime | None = None

    def as_values(self) -> dict[str, Any]:
        return {
            "source_artifact": self.source_artifact,
            "source_sha256": self.source_sha256,
            "git_commit": self.git_commit,
            "code_version": self.code_version,
            "ingested_at": self.ingested_at or utcnow(),
        }


@dataclass(frozen=True)
class SearchEvaluationRecord:
    """One scored candidate, in the shape the bulk writer consumes."""

    seed: int
    fold_index: int
    evaluation_index: int
    status: ResultStatus = ResultStatus.EXECUTED
    objective: float | None = None
    objective_name: str | None = None
    generation: int | None = None
    feasible: bool | None = None
    spec_id: int | None = None
    params: dict[str, Any] = field(default_factory=dict)


# --------------------------------------------------------------------------- #
# Internals
# --------------------------------------------------------------------------- #


def _upsert[M: Base](
    session: Session,
    model: type[M],
    natural_key: Mapping[str, Any],
    values: Mapping[str, Any],
) -> M:
    """Insert or update the single row identified by ``natural_key``."""
    instance = session.scalars(select(model).filter_by(**natural_key)).one_or_none()
    if instance is None:
        instance = model(**{**natural_key, **values})
        session.add(instance)
    else:
        for name, value in values.items():
            if getattr(instance, name) != value:
                setattr(instance, name, value)
    session.flush()
    return instance


def metric_values(status: ResultStatus, metrics: MetricValues | None) -> dict[str, Any]:
    """Validate metrics against ``status`` and expand them to the full column set.

    Every core column is returned, missing ones as ``None``, so that re-ingesting
    a row whose status regressed to ``NOT_EXECUTED`` erases the old figures
    rather than leaving them stranded under a status that denies them.
    """
    supplied = dict(metrics or {})
    unknown = set(supplied) - set(CORE_METRIC_COLUMNS)
    if unknown:
        raise CatalogIntegrityError(
            f"Not core metric columns: {sorted(unknown)}. "
            "Strategy-specific or one-off figures belong in the `metrics` table."
        )
    present = {name: value for name, value in supplied.items() if value is not None}
    if present and not has_metrics(status):
        raise MetricsWithoutMeasurementError(
            f"Status {status.value} states that no publishable measurement exists, "
            f"but these metrics were supplied: {sorted(present)}. "
            "Record the absence as a status; do not store a number for it."
        )
    return {name: supplied.get(name) for name in CORE_METRIC_COLUMNS}


# --------------------------------------------------------------------------- #
# Study structure
# --------------------------------------------------------------------------- #


def upsert_study(
    session: Session,
    *,
    key: str,
    title: str,
    primary_symbol: str,
    timeframe: str,
    description: str | None = None,
    secondary_symbol: str | None = None,
    holdout_start: datetime | None = None,
    holdout_end: datetime | None = None,
) -> Study:
    """Insert or update a study. ``holdout_*`` are boundaries, never contents."""
    return _upsert(
        session,
        Study,
        {"key": key},
        {
            "title": title,
            "description": description,
            "primary_symbol": primary_symbol,
            "secondary_symbol": secondary_symbol,
            "timeframe": timeframe,
            "holdout_start": holdout_start,
            "holdout_end": holdout_end,
        },
    )


def upsert_round(
    session: Session,
    *,
    study: Study,
    key: str,
    name: str,
    provenance: Provenance,
    sequence: int = 0,
    criterion: str | None = None,
    opened_at: datetime | None = None,
    closed_at: datetime | None = None,
    status: ResultStatus = ResultStatus.EXECUTED,
    status_note: str | None = None,
) -> ExperimentRound:
    return _upsert(
        session,
        ExperimentRound,
        {"study_id": study.id, "key": key},
        {
            "name": name,
            "sequence": sequence,
            "criterion": criterion,
            "opened_at": opened_at,
            "closed_at": closed_at,
            "status": status,
            "status_note": status_note,
            **provenance.as_values(),
        },
    )


def upsert_family(
    session: Session,
    *,
    study: Study,
    key: str,
    name: str,
    provenance: Provenance,
    hypothesis: str | None = None,
    module: str | None = None,
    status: ResultStatus = ResultStatus.EXECUTED,
    status_note: str | None = None,
) -> StrategyFamily:
    return _upsert(
        session,
        StrategyFamily,
        {"study_id": study.id, "key": key},
        {
            "name": name,
            "hypothesis": hypothesis,
            "module": module,
            "status": status,
            "status_note": status_note,
            **provenance.as_values(),
        },
    )


def upsert_spec(
    session: Session,
    *,
    family: StrategyFamily,
    spec_hash: str,
    params: Mapping[str, Any],
    provenance: Provenance,
    symbol: str | None = None,
    timeframe: str | None = None,
) -> StrategySpec:
    """Register a parameterisation. Parameters stay JSON: each family differs."""
    return _upsert(
        session,
        StrategySpec,
        {"family_id": family.id, "spec_hash": spec_hash},
        {
            "params": dict(params),
            "symbol": symbol,
            "timeframe": timeframe,
            **provenance.as_values(),
        },
    )


# --------------------------------------------------------------------------- #
# Execution
# --------------------------------------------------------------------------- #


def upsert_run(
    session: Session,
    *,
    study: Study,
    run_id: str,
    symbol: str,
    timeframe: str,
    engine: str,
    run_dir: str,
    provenance: Provenance,
    experiment_round: ExperimentRound | None = None,
    family: StrategyFamily | None = None,
    identity_fingerprint: str | None = None,
    started_at: datetime | None = None,
    finished_at: datetime | None = None,
    config: Mapping[str, Any] | None = None,
    status: ResultStatus = ResultStatus.EXECUTED,
    status_note: str | None = None,
) -> Run:
    return _upsert(
        session,
        Run,
        {"run_id": run_id},
        {
            "study_id": study.id,
            "round_id": experiment_round.id if experiment_round else None,
            "family_id": family.id if family else None,
            "symbol": symbol,
            "timeframe": timeframe,
            "engine": engine,
            "run_dir": run_dir,
            "identity_fingerprint": identity_fingerprint,
            "started_at": started_at,
            "finished_at": finished_at,
            "config": dict(config or {}),
            "status": status,
            "status_note": status_note,
            **provenance.as_values(),
        },
    )


def upsert_run_seed(
    session: Session,
    *,
    run: Run,
    seed: int,
    provenance: Provenance,
    status: ResultStatus = ResultStatus.EXECUTED,
    status_note: str | None = None,
    metrics: MetricValues | None = None,
    n_folds: int | None = None,
    n_bars: int | None = None,
) -> RunSeed:
    return _upsert(
        session,
        RunSeed,
        {"run_id": run.id, "seed": seed},
        {
            "n_folds": n_folds,
            "n_bars": n_bars,
            "status": status,
            "status_note": status_note,
            **metric_values(status, metrics),
            **provenance.as_values(),
        },
    )


def upsert_fold(
    session: Session,
    *,
    run: Run,
    fold_index: int,
    train_start: datetime,
    train_end: datetime,
    test_start: datetime,
    test_end: datetime,
    provenance: Provenance,
    purge_bars: int | None = None,
    embargo_bars: int | None = None,
    n_train_bars: int | None = None,
    n_test_bars: int | None = None,
) -> Fold:
    """Register a walk-forward split. Windows must be tz-aware and chronological."""
    if train_end > test_start:
        raise CatalogIntegrityError(
            f"Fold {fold_index} of run {run.run_id!r} has a train window ending after its "
            "test window begins; a chronological split cannot overlap."
        )
    return _upsert(
        session,
        Fold,
        {"run_id": run.id, "fold_index": fold_index},
        {
            "train_start": train_start,
            "train_end": train_end,
            "test_start": test_start,
            "test_end": test_end,
            "purge_bars": purge_bars,
            "embargo_bars": embargo_bars,
            "n_train_bars": n_train_bars,
            "n_test_bars": n_test_bars,
            **provenance.as_values(),
        },
    )


def upsert_fold_result(
    session: Session,
    *,
    fold: Fold,
    run_seed: RunSeed,
    provenance: Provenance,
    status: ResultStatus = ResultStatus.EXECUTED,
    status_note: str | None = None,
    metrics: MetricValues | None = None,
    spec: StrategySpec | None = None,
    is_train: bool = False,
    params: Mapping[str, Any] | None = None,
) -> FoldResult:
    return _upsert(
        session,
        FoldResult,
        {"fold_id": fold.id, "run_seed_id": run_seed.id},
        {
            "spec_id": spec.id if spec else None,
            "is_train": is_train,
            "params": dict(params or {}),
            "status": status,
            "status_note": status_note,
            **metric_values(status, metrics),
            **provenance.as_values(),
        },
    )


def upsert_search_evaluation(
    session: Session,
    *,
    run: Run,
    seed: int,
    fold_index: int,
    evaluation_index: int,
    provenance: Provenance,
    status: ResultStatus = ResultStatus.EXECUTED,
    status_note: str | None = None,
    objective: float | None = None,
    objective_name: str | None = None,
    generation: int | None = None,
    feasible: bool | None = None,
    spec: StrategySpec | None = None,
    params: Mapping[str, Any] | None = None,
) -> SearchEvaluation:
    if objective is not None and not has_metrics(status):
        raise MetricsWithoutMeasurementError(
            f"Status {status.value} carries no publishable objective, "
            f"but one was supplied for evaluation {evaluation_index}."
        )
    return _upsert(
        session,
        SearchEvaluation,
        {
            "run_id": run.id,
            "seed": seed,
            "fold_index": fold_index,
            "evaluation_index": evaluation_index,
        },
        {
            "generation": generation,
            "spec_id": spec.id if spec else None,
            "objective": objective,
            "objective_name": objective_name,
            "feasible": feasible,
            "params": dict(params or {}),
            "status": status,
            "status_note": status_note,
            **provenance.as_values(),
        },
    )


_SEARCH_EVALUATION_UPDATE_COLUMNS: tuple[str, ...] = (
    "generation",
    "spec_id",
    "objective",
    "objective_name",
    "feasible",
    "params",
    "status",
    "status_note",
    "source_artifact",
    "source_sha256",
    "git_commit",
    "code_version",
    "ingested_at",
)


def bulk_upsert_search_evaluations(
    session: Session,
    *,
    run: Run,
    records: Sequence[SearchEvaluationRecord],
    provenance: Provenance,
) -> int:
    """Write many scored candidates at once, idempotently.

    Uses ``ON CONFLICT DO UPDATE`` against the natural key on PostgreSQL and
    SQLite; anywhere else it degrades to the row-at-a-time upsert, which is
    correct but slower. Returns the number of records written.
    """
    if not records:
        return 0

    shared = provenance.as_values()
    rows: list[dict[str, Any]] = []
    for record in records:
        if record.objective is not None and not has_metrics(record.status):
            raise MetricsWithoutMeasurementError(
                f"Status {record.status.value} carries no publishable objective, but one "
                f"was supplied for evaluation {record.evaluation_index} (seed {record.seed})."
            )
        rows.append(
            {
                "run_id": run.id,
                "seed": record.seed,
                "fold_index": record.fold_index,
                "evaluation_index": record.evaluation_index,
                "generation": record.generation,
                "spec_id": record.spec_id,
                "objective": record.objective,
                "objective_name": record.objective_name,
                "feasible": record.feasible,
                "params": dict(record.params),
                "status": record.status,
                "status_note": None,
                **shared,
            }
        )

    index_elements = ["run_id", "seed", "fold_index", "evaluation_index"]
    dialect = session.get_bind().dialect.name
    if dialect == "postgresql":
        pg_stmt = pg_insert(SearchEvaluation).values(rows)
        session.execute(
            pg_stmt.on_conflict_do_update(
                index_elements=index_elements,
                set_={name: pg_stmt.excluded[name] for name in _SEARCH_EVALUATION_UPDATE_COLUMNS},
            )
        )
    elif dialect == "sqlite":
        sqlite_stmt = sqlite_insert(SearchEvaluation).values(rows)
        session.execute(
            sqlite_stmt.on_conflict_do_update(
                index_elements=index_elements,
                set_={
                    name: sqlite_stmt.excluded[name] for name in _SEARCH_EVALUATION_UPDATE_COLUMNS
                },
            )
        )
    else:  # pragma: no cover - only reached on dialects without upsert support
        for record in records:
            upsert_search_evaluation(
                session,
                run=run,
                seed=record.seed,
                fold_index=record.fold_index,
                evaluation_index=record.evaluation_index,
                provenance=provenance,
                status=record.status,
                objective=record.objective,
                objective_name=record.objective_name,
                generation=record.generation,
                feasible=record.feasible,
                params=record.params,
            )
    session.flush()
    return len(rows)


# --------------------------------------------------------------------------- #
# Measurements and verdicts
# --------------------------------------------------------------------------- #


def upsert_metric(
    session: Session,
    *,
    study: Study,
    scope: str,
    scope_ref: str,
    metric_key: str,
    provenance: Provenance,
    status: ResultStatus = ResultStatus.EXECUTED,
    status_note: str | None = None,
    value: float | None = None,
    unit: str | None = None,
    context: Mapping[str, Any] | None = None,
) -> Metric:
    """Record a long-format figure. ``value`` stays ``NULL`` when nothing was measured."""
    if value is not None and not has_metrics(status):
        raise MetricsWithoutMeasurementError(
            f"Status {status.value} states that {metric_key!r} has no publishable value "
            f"for {scope}:{scope_ref}, but {value!r} was supplied."
        )
    return _upsert(
        session,
        Metric,
        {
            "study_id": study.id,
            "scope": scope,
            "scope_ref": scope_ref,
            "metric_key": metric_key,
        },
        {
            "value": value,
            "unit": unit,
            "context": dict(context or {}),
            "status": status,
            "status_note": status_note,
            **provenance.as_values(),
        },
    )


def upsert_gate_result(
    session: Session,
    *,
    experiment_round: ExperimentRound,
    family: StrategyFamily,
    symbol: str,
    criterion_key: str,
    verdict: str,
    provenance: Provenance,
    status: ResultStatus = ResultStatus.EXECUTED,
    status_note: str | None = None,
    criterion: str | None = None,
    observed: float | None = None,
    threshold: float | None = None,
    n_seeds_passed: int | None = None,
    n_seeds_total: int | None = None,
    detail: Mapping[str, Any] | None = None,
) -> GateResult:
    if observed is not None and not has_metrics(status):
        raise MetricsWithoutMeasurementError(
            f"Status {status.value} carries no publishable observation for criterion "
            f"{criterion_key!r}, but {observed!r} was supplied."
        )
    return _upsert(
        session,
        GateResult,
        {
            "round_id": experiment_round.id,
            "family_id": family.id,
            "symbol": symbol,
            "criterion_key": criterion_key,
        },
        {
            "criterion": criterion,
            "verdict": verdict,
            "observed": observed,
            "threshold": threshold,
            "n_seeds_passed": n_seeds_passed,
            "n_seeds_total": n_seeds_total,
            "detail": dict(detail or {}),
            "status": status,
            "status_note": status_note,
            **provenance.as_values(),
        },
    )


# --------------------------------------------------------------------------- #
# Bulk evidence and the frozen partition
# --------------------------------------------------------------------------- #


def register_artifact(
    session: Session,
    metadata: ObjectMetadata,
    *,
    kind: str,
    provenance: Provenance,
    run: Run | None = None,
    study: Study | None = None,
    status: ResultStatus = ResultStatus.EXECUTED,
    status_note: str | None = None,
) -> Artifact:
    """Index a stored object, keyed on its URI so re-uploads update in place."""
    return _upsert(
        session,
        Artifact,
        {"uri": metadata.uri},
        {
            "backend": metadata.backend,
            "bucket": metadata.bucket,
            "object_key": metadata.key,
            "kind": kind,
            "media_type": metadata.media_type,
            "byte_size": metadata.byte_size,
            "row_count": metadata.row_count,
            "content_sha256": metadata.sha256,
            "arrow_schema": dict(metadata.arrow_schema or {}),
            "run_id": run.id if run else None,
            "study_id": study.id if study else None,
            "status": status,
            "status_note": status_note,
            **provenance.as_values(),
        },
    )


def upsert_monte_carlo_run(
    session: Session,
    *,
    study: Study,
    family: StrategyFamily,
    symbol: str,
    method: str,
    seed: int,
    n_paths: int,
    provenance: Provenance,
    status: ResultStatus = ResultStatus.EXECUTED,
    status_note: str | None = None,
    horizon_bars: int | None = None,
    block_probability: float | None = None,
    terminal_p05: float | None = None,
    terminal_p25: float | None = None,
    terminal_median: float | None = None,
    terminal_p75: float | None = None,
    terminal_p95: float | None = None,
    prob_positive: float | None = None,
    mean_max_drawdown: float | None = None,
    artifact: Artifact | None = None,
) -> MonteCarloRun:
    """Record a resampling summary; the trajectories live in ``artifact``."""
    return _upsert(
        session,
        MonteCarloRun,
        {
            "study_id": study.id,
            "family_id": family.id,
            "symbol": symbol,
            "method": method,
            "seed": seed,
        },
        {
            "n_paths": n_paths,
            "horizon_bars": horizon_bars,
            "block_probability": block_probability,
            "terminal_p05": terminal_p05,
            "terminal_p25": terminal_p25,
            "terminal_median": terminal_median,
            "terminal_p75": terminal_p75,
            "terminal_p95": terminal_p95,
            "prob_positive": prob_positive,
            "mean_max_drawdown": mean_max_drawdown,
            "artifact_id": artifact.id if artifact else None,
            "status": status,
            "status_note": status_note,
            **provenance.as_values(),
        },
    )


def upsert_holdout_entry(
    session: Session,
    *,
    study: Study,
    candidate_key: str,
    candidate_fingerprint: str,
    provenance: Provenance,
    status: ResultStatus = ResultStatus.HOLDOUT_LOCKED,
    status_note: str | None = None,
    authorization_token_present: bool = False,
    authorization_recorded_at: datetime | None = None,
    commit_before: str | None = None,
    commit_after: str | None = None,
    dataset_sha256: str | None = None,
    command: str | None = None,
    opened_at: datetime | None = None,
    audited: bool = False,
    audited_at: datetime | None = None,
    auditor: str | None = None,
    notes: str | None = None,
) -> HoldoutRegistryEntry:
    """Record the audit trail of the frozen partition — never its observations.

    The default is the state the study is actually in until the very end:
    ``HOLDOUT_LOCKED``, unopened and unaudited. Claiming an audit for a partition
    that was never opened is refused here as well as by a database constraint.
    """
    if audited and opened_at is None:
        raise CatalogIntegrityError(
            f"Holdout entry {candidate_key!r} claims to be audited but records no opening; "
            "an audit is of an event that happened."
        )
    return _upsert(
        session,
        HoldoutRegistryEntry,
        {"study_id": study.id, "candidate_key": candidate_key},
        {
            "candidate_fingerprint": candidate_fingerprint,
            "authorization_token_present": authorization_token_present,
            "authorization_recorded_at": authorization_recorded_at,
            "commit_before": commit_before,
            "commit_after": commit_after,
            "dataset_sha256": dataset_sha256,
            "command": command,
            "opened_at": opened_at,
            "audited": audited,
            "audited_at": audited_at,
            "auditor": auditor,
            "notes": notes,
            "status": status,
            "status_note": status_note,
            **provenance.as_values(),
        },
    )


# --------------------------------------------------------------------------- #
# Queries
# --------------------------------------------------------------------------- #


def get_study(session: Session, key: str) -> Study | None:
    return session.scalars(select(Study).where(Study.key == key)).one_or_none()


def get_family(session: Session, *, study: Study, key: str) -> StrategyFamily | None:
    return session.scalars(
        select(StrategyFamily).where(StrategyFamily.study_id == study.id, StrategyFamily.key == key)
    ).one_or_none()


def get_run(session: Session, run_id: str) -> Run | None:
    return session.scalars(select(Run).where(Run.run_id == run_id)).one_or_none()


def list_runs(
    session: Session,
    *,
    study_key: str | None = None,
    family_key: str | None = None,
    round_key: str | None = None,
    symbol: str | None = None,
    timeframe: str | None = None,
    engine: str | None = None,
    status: ResultStatus | None = None,
) -> Sequence[Run]:
    """Runs matching the filters the API exposes, newest identifier last."""
    stmt: Select[tuple[Run]] = select(Run)
    if study_key is not None:
        stmt = stmt.join(Study, Run.study_id == Study.id).where(Study.key == study_key)
    if family_key is not None:
        stmt = stmt.join(StrategyFamily, Run.family_id == StrategyFamily.id).where(
            StrategyFamily.key == family_key
        )
    if round_key is not None:
        stmt = stmt.join(ExperimentRound, Run.round_id == ExperimentRound.id).where(
            ExperimentRound.key == round_key
        )
    if symbol is not None:
        stmt = stmt.where(Run.symbol == symbol)
    if timeframe is not None:
        stmt = stmt.where(Run.timeframe == timeframe)
    if engine is not None:
        stmt = stmt.where(Run.engine == engine)
    if status is not None:
        stmt = stmt.where(Run.status == status)
    return session.scalars(stmt.order_by(Run.run_id)).all()


def list_run_seeds(session: Session, *, run: Run) -> Sequence[RunSeed]:
    return session.scalars(
        select(RunSeed).where(RunSeed.run_id == run.id).order_by(RunSeed.seed)
    ).all()


def list_fold_results(
    session: Session,
    *,
    run: Run | None = None,
    seed: int | None = None,
    fold_index: int | None = None,
    status: ResultStatus | None = None,
) -> Sequence[FoldResult]:
    stmt: Select[tuple[FoldResult]] = select(FoldResult).join(Fold, FoldResult.fold_id == Fold.id)
    if run is not None:
        stmt = stmt.where(Fold.run_id == run.id)
    if fold_index is not None:
        stmt = stmt.where(Fold.fold_index == fold_index)
    if seed is not None:
        stmt = stmt.join(RunSeed, FoldResult.run_seed_id == RunSeed.id).where(RunSeed.seed == seed)
    if status is not None:
        stmt = stmt.where(FoldResult.status == status)
    return session.scalars(stmt.order_by(Fold.fold_index, FoldResult.id)).all()


def list_gate_results(
    session: Session,
    *,
    round_key: str | None = None,
    family_key: str | None = None,
    symbol: str | None = None,
    verdict: str | None = None,
) -> Sequence[GateResult]:
    stmt: Select[tuple[GateResult]] = select(GateResult)
    if round_key is not None:
        stmt = stmt.join(ExperimentRound, GateResult.round_id == ExperimentRound.id).where(
            ExperimentRound.key == round_key
        )
    if family_key is not None:
        stmt = stmt.join(StrategyFamily, GateResult.family_id == StrategyFamily.id).where(
            StrategyFamily.key == family_key
        )
    if symbol is not None:
        stmt = stmt.where(GateResult.symbol == symbol)
    if verdict is not None:
        stmt = stmt.where(GateResult.verdict == verdict)
    return session.scalars(stmt.order_by(GateResult.id)).all()


def get_metric(
    session: Session, *, study: Study, scope: str, scope_ref: str, metric_key: str
) -> Metric | None:
    return session.scalars(
        select(Metric).where(
            Metric.study_id == study.id,
            Metric.scope == scope,
            Metric.scope_ref == scope_ref,
            Metric.metric_key == metric_key,
        )
    ).one_or_none()


def list_artifacts(
    session: Session, *, run: Run | None = None, kind: str | None = None
) -> Sequence[Artifact]:
    stmt: Select[tuple[Artifact]] = select(Artifact)
    if run is not None:
        stmt = stmt.where(Artifact.run_id == run.id)
    if kind is not None:
        stmt = stmt.where(Artifact.kind == kind)
    return session.scalars(stmt.order_by(Artifact.uri)).all()


def list_holdout_entries(session: Session, *, study: Study) -> Sequence[HoldoutRegistryEntry]:
    return session.scalars(
        select(HoldoutRegistryEntry)
        .where(HoldoutRegistryEntry.study_id == study.id)
        .order_by(HoldoutRegistryEntry.candidate_key)
    ).all()


def count_search_evaluations(session: Session, *, run: Run) -> int:
    total = session.scalar(
        select(func.count()).select_from(SearchEvaluation).where(SearchEvaluation.run_id == run.id)
    )
    return int(total or 0)


__all__ = [
    "CatalogIntegrityError",
    "MetricValues",
    "MetricsWithoutMeasurementError",
    "Provenance",
    "SearchEvaluationRecord",
    "bulk_upsert_search_evaluations",
    "count_search_evaluations",
    "get_family",
    "get_metric",
    "get_run",
    "get_study",
    "list_artifacts",
    "list_fold_results",
    "list_gate_results",
    "list_holdout_entries",
    "list_run_seeds",
    "list_runs",
    "metric_values",
    "register_artifact",
    "upsert_family",
    "upsert_fold",
    "upsert_fold_result",
    "upsert_gate_result",
    "upsert_holdout_entry",
    "upsert_metric",
    "upsert_monte_carlo_run",
    "upsert_round",
    "upsert_run",
    "upsert_run_seed",
    "upsert_search_evaluation",
    "upsert_spec",
    "upsert_study",
]
