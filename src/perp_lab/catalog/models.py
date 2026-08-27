"""The catalogue schema: the study expressed as rows instead of a directory tree.

The files under ``artifacts/`` and ``reports/`` remain the scientific evidence.
Every table here is an *index* over those files, which is why provenance is a
first-class column set rather than an afterthought: a row that cannot name the
artifact and the SHA-256 it was read from is not admissible.

Three deliberate boundaries shape the schema.

**Small and queryable lives in SQL; bulk lives in Parquet.** Equity curves, per
bar returns, trade blotters and Monte Carlo trajectories are registered in
:class:`Artifact` — location, byte size, row count, schema, digest, owning run —
and read through DuckDB. Nothing large is inlined as JSON into a column.

**Core metrics are typed columns, variable parameters are JSON.** The twelve
figures the API filters and sorts by are real columns
(:class:`CoreMetricsMixin`); anything strategy-specific, and anything that only
some rounds produce, goes into a JSON payload or the long-format
:class:`Metric` table. Adding a strategy family must not require a migration.

**Absence is a state, never a zero.** Every metric column is nullable and every
result row carries a :class:`~perp_lab.catalog.status.ResultStatus`. A row whose
status is ``NOT_EXECUTED`` has ``NULL`` metrics, and the repositories refuse to
write numbers under a status that says nothing was measured.

Dialect notes
-------------
* JSON columns are ``JSONB`` on PostgreSQL and plain ``JSON`` on SQLite via
  ``with_variant``. Only PostgreSQL can index inside the payload; SQLite stores
  it as text. Do not write queries that filter on JSON contents.
* :data:`STATUS` is a non-native enum: a ``VARCHAR`` plus a ``CHECK``
  constraint, identical on both dialects. A native PostgreSQL ``ENUM`` would
  make adding a status a type migration, and SQLite has no equivalent at all.
* SQLite only enforces foreign keys when ``PRAGMA foreign_keys=ON``; the engine
  factory in :mod:`perp_lab.catalog.session` sets it on every connection.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Double,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from perp_lab.catalog.status import ResultStatus

# JSONB where it is worth having (PostgreSQL), plain JSON where it is all there
# is (SQLite, used for offline development and the test suite).
JSON_VARIANT = JSONB().with_variant(JSON(), "sqlite")

# Stored as text plus a CHECK constraint rather than a native PostgreSQL enum,
# so the vocabulary in `status.py` stays the single source of truth and adding a
# state is an ordinary column migration.
STATUS = SAEnum(
    ResultStatus,
    name="result_status",
    native_enum=False,
    length=32,
    validate_strings=True,
)

# Every metric in this schema is a statistical estimate, not a ledger amount, so
# all of them are IEEE doubles rather than `Numeric`. Exact decimal arithmetic
# would imply a precision these numbers do not have, and `Numeric` round-trips
# as `decimal.Decimal`, which neither Polars nor DuckDB consume without a cast.
Metric64 = Double


def utcnow() -> datetime:
    """Timezone-aware present. Naive datetimes are not allowed in this schema."""
    return datetime.now(UTC)


class Base(DeclarativeBase):
    """Declarative base carrying the shared type mapping."""

    type_annotation_map = {  # noqa: RUF012 - SQLAlchemy declarative API
        dict[str, Any]: JSON_VARIANT,
        datetime: DateTime(timezone=True),
    }


class ProvenanceMixin:
    """Where a row came from. Mandatory on anything that reports a result.

    ``source_artifact`` is a repository-relative path (or an object-store URI)
    and ``source_sha256`` is the digest of that exact file, so a figure on a
    screen can always be traced to the bytes that produced it. ``git_commit``
    and ``code_version`` record the code that wrote the artifact, not the code
    that ingested it.
    """

    source_artifact: Mapped[str] = mapped_column(Text, nullable=False)
    source_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    git_commit: Mapped[str | None] = mapped_column(String(40), nullable=True)
    code_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )


class StatusMixin:
    """Why this row has, or has not, numbers in it."""

    status: Mapped[ResultStatus] = mapped_column(
        STATUS, nullable=False, default=ResultStatus.EXECUTED, index=True
    )
    status_note: Mapped[str | None] = mapped_column(Text, nullable=True)


class CoreMetricsMixin:
    """The twelve figures the API filters, sorts and compares on.

    All nullable on purpose: a fold that was skipped, a seed that was never run
    and a family locked behind the holdout all legitimately have no numbers, and
    a ``NOT NULL DEFAULT 0`` would turn each of those into a false measurement.
    """

    total_return: Mapped[float | None] = mapped_column(Metric64, nullable=True)
    sharpe: Mapped[float | None] = mapped_column(Metric64, nullable=True)
    sortino: Mapped[float | None] = mapped_column(Metric64, nullable=True)
    max_drawdown: Mapped[float | None] = mapped_column(Metric64, nullable=True)
    calmar: Mapped[float | None] = mapped_column(Metric64, nullable=True)
    profit_factor: Mapped[float | None] = mapped_column(Metric64, nullable=True)
    win_rate: Mapped[float | None] = mapped_column(Metric64, nullable=True)
    n_trades: Mapped[int | None] = mapped_column(Integer, nullable=True)
    turnover: Mapped[float | None] = mapped_column(Metric64, nullable=True)
    exposure: Mapped[float | None] = mapped_column(Metric64, nullable=True)
    costs: Mapped[float | None] = mapped_column(Metric64, nullable=True)
    funding: Mapped[float | None] = mapped_column(Metric64, nullable=True)


CORE_METRIC_COLUMNS: tuple[str, ...] = (
    "total_return",
    "sharpe",
    "sortino",
    "max_drawdown",
    "calmar",
    "profit_factor",
    "win_rate",
    "n_trades",
    "turnover",
    "exposure",
    "costs",
    "funding",
)
"""Names of the typed metric columns, for validation and bulk assignment."""


# --------------------------------------------------------------------------- #
# Study structure
# --------------------------------------------------------------------------- #


class Study(Base):
    """One thesis-scale investigation: assets, timeframe and holdout boundary.

    The holdout columns record *where the frozen partition starts and ends*,
    which is metadata about the protocol. No observation from inside that window
    is stored anywhere in this schema.
    """

    __tablename__ = "studies"
    __table_args__ = (UniqueConstraint("key", name="uq_studies_key"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    primary_symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    secondary_symbol: Mapped[str | None] = mapped_column(String(32), nullable=True)
    timeframe: Mapped[str] = mapped_column(String(8), nullable=False)
    holdout_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    holdout_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )

    rounds: Mapped[list[ExperimentRound]] = relationship(
        back_populates="study", cascade="all, delete-orphan"
    )
    families: Mapped[list[StrategyFamily]] = relationship(
        back_populates="study", cascade="all, delete-orphan"
    )


class ExperimentRound(Base, StatusMixin, ProvenanceMixin):
    """A pre-registered gate (S1, S2, R2, R3 ...) and the criterion it applied."""

    __tablename__ = "experiment_rounds"
    __table_args__ = (
        UniqueConstraint("study_id", "key", name="uq_experiment_rounds_study_key"),
        Index("ix_experiment_rounds_key", "key"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    study_id: Mapped[int] = mapped_column(
        ForeignKey("studies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    key: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    criterion: Mapped[str | None] = mapped_column(Text, nullable=True)
    opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    study: Mapped[Study] = relationship(back_populates="rounds")


class StrategyFamily(Base, StatusMixin, ProvenanceMixin):
    """One hypothesis under test, independent of any particular parameterisation."""

    __tablename__ = "strategy_families"
    __table_args__ = (
        UniqueConstraint("study_id", "key", name="uq_strategy_families_study_key"),
        Index("ix_strategy_families_key", "key"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    study_id: Mapped[int] = mapped_column(
        ForeignKey("studies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    key: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    hypothesis: Mapped[str | None] = mapped_column(Text, nullable=True)
    module: Mapped[str | None] = mapped_column(Text, nullable=True)

    study: Mapped[Study] = relationship(back_populates="families")
    specs: Mapped[list[StrategySpec]] = relationship(
        back_populates="family", cascade="all, delete-orphan"
    )


class StrategySpec(Base, ProvenanceMixin):
    """A concrete parameterisation of a family, identified by a hash of its params.

    The parameters themselves are JSON: every family has a different parameter
    vocabulary, and promoting any of them to columns would mean a migration each
    time a family is added.
    """

    __tablename__ = "strategy_specs"
    __table_args__ = (
        UniqueConstraint("family_id", "spec_hash", name="uq_strategy_specs_family_hash"),
        Index("ix_strategy_specs_symbol_timeframe", "symbol", "timeframe"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    family_id: Mapped[int] = mapped_column(
        ForeignKey("strategy_families.id", ondelete="CASCADE"), nullable=False, index=True
    )
    spec_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    symbol: Mapped[str | None] = mapped_column(String(32), nullable=True)
    timeframe: Mapped[str | None] = mapped_column(String(8), nullable=True)
    params: Mapped[dict[str, Any]] = mapped_column(JSON_VARIANT, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )

    family: Mapped[StrategyFamily] = relationship(back_populates="specs")


# --------------------------------------------------------------------------- #
# Execution
# --------------------------------------------------------------------------- #


class Run(Base, StatusMixin, ProvenanceMixin):
    """One executed search: a family on one asset with one engine.

    ``round_id`` and ``family_id`` are ``SET NULL`` rather than ``CASCADE``:
    reorganising the gate structure must not silently delete the record that a
    run happened. ``run_id`` is the directory name under ``artifacts/runs/`` and
    is the natural key ingestion keys on.
    """

    __tablename__ = "runs"
    __table_args__ = (
        UniqueConstraint("run_id", name="uq_runs_run_id"),
        Index("ix_runs_family_symbol_engine", "family_id", "symbol", "engine"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[str] = mapped_column(String(128), nullable=False)
    study_id: Mapped[int] = mapped_column(
        ForeignKey("studies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    round_id: Mapped[int | None] = mapped_column(
        ForeignKey("experiment_rounds.id", ondelete="SET NULL"), nullable=True, index=True
    )
    family_id: Mapped[int | None] = mapped_column(
        ForeignKey("strategy_families.id", ondelete="SET NULL"), nullable=True, index=True
    )
    symbol: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    timeframe: Mapped[str] = mapped_column(String(8), nullable=False, index=True)
    engine: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    run_dir: Mapped[str] = mapped_column(Text, nullable=False)
    identity_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    config: Mapped[dict[str, Any]] = mapped_column(JSON_VARIANT, nullable=False, default=dict)

    seeds: Mapped[list[RunSeed]] = relationship(back_populates="run", cascade="all, delete-orphan")
    folds: Mapped[list[Fold]] = relationship(back_populates="run", cascade="all, delete-orphan")


class RunSeed(Base, StatusMixin, CoreMetricsMixin, ProvenanceMixin):
    """One seed of one run, with its out-of-sample aggregate over all folds.

    The seed is an arbitrary starting point that has to be integrated out, so the
    unit of comparison is the family; this row exists to show the spread across
    seeds, which is the most direct evidence of whether a search fitted noise.
    """

    __tablename__ = "run_seeds"
    __table_args__ = (UniqueConstraint("run_id", "seed", name="uq_run_seeds_run_seed"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(
        ForeignKey("runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    seed: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    n_folds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    n_bars: Mapped[int | None] = mapped_column(Integer, nullable=True)

    run: Mapped[Run] = relationship(back_populates="seeds")
    fold_results: Mapped[list[FoldResult]] = relationship(
        back_populates="run_seed", cascade="all, delete-orphan"
    )


class Fold(Base, ProvenanceMixin):
    """A walk-forward split: its train and test windows and the gap between them.

    A definition rather than a result, so it carries provenance but no status:
    the fold either exists in the split plan or it does not.
    """

    __tablename__ = "folds"
    __table_args__ = (
        UniqueConstraint("run_id", "fold_index", name="uq_folds_run_index"),
        Index("ix_folds_fold_index", "fold_index"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(
        ForeignKey("runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    fold_index: Mapped[int] = mapped_column(Integer, nullable=False)
    train_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    train_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    test_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    test_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    purge_bars: Mapped[int | None] = mapped_column(Integer, nullable=True)
    embargo_bars: Mapped[int | None] = mapped_column(Integer, nullable=True)
    n_train_bars: Mapped[int | None] = mapped_column(Integer, nullable=True)
    n_test_bars: Mapped[int | None] = mapped_column(Integer, nullable=True)

    run: Mapped[Run] = relationship(back_populates="folds")
    results: Mapped[list[FoldResult]] = relationship(
        back_populates="fold", cascade="all, delete-orphan"
    )


class FoldResult(Base, StatusMixin, CoreMetricsMixin, ProvenanceMixin):
    """What one seed achieved out-of-sample on one fold, with the spec it selected."""

    __tablename__ = "fold_results"
    __table_args__ = (UniqueConstraint("fold_id", "run_seed_id", name="uq_fold_results_fold_seed"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    fold_id: Mapped[int] = mapped_column(
        ForeignKey("folds.id", ondelete="CASCADE"), nullable=False, index=True
    )
    run_seed_id: Mapped[int] = mapped_column(
        ForeignKey("run_seeds.id", ondelete="CASCADE"), nullable=False, index=True
    )
    spec_id: Mapped[int | None] = mapped_column(
        ForeignKey("strategy_specs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    is_train: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    params: Mapped[dict[str, Any]] = mapped_column(JSON_VARIANT, nullable=False, default=dict)

    fold: Mapped[Fold] = relationship(back_populates="results")
    run_seed: Mapped[RunSeed] = relationship(back_populates="fold_results")


class SearchEvaluation(Base, StatusMixin, ProvenanceMixin):
    """One candidate scored during a search — the mass of the experiment.

    This is the highest-cardinality table in the catalogue, so it stores the
    objective and the parameters only; the full per-candidate series stay in
    Parquet. ``seed`` and ``fold_index`` are duplicated here as plain integers
    because they form the natural key and a natural key must not contain a
    nullable foreign key: PostgreSQL and SQLite both treat ``NULL`` as distinct,
    which would silently defeat the uniqueness that makes ingestion idempotent.
    """

    __tablename__ = "search_evaluations"
    __table_args__ = (
        UniqueConstraint(
            "run_id",
            "seed",
            "fold_index",
            "evaluation_index",
            name="uq_search_evaluations_natural_key",
        ),
        Index("ix_search_evaluations_run_seed_fold", "run_id", "seed", "fold_index"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(
        ForeignKey("runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    seed: Mapped[int] = mapped_column(Integer, nullable=False)
    fold_index: Mapped[int] = mapped_column(Integer, nullable=False)
    evaluation_index: Mapped[int] = mapped_column(Integer, nullable=False)
    generation: Mapped[int | None] = mapped_column(Integer, nullable=True)
    spec_id: Mapped[int | None] = mapped_column(
        ForeignKey("strategy_specs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    objective: Mapped[float | None] = mapped_column(Metric64, nullable=True)
    objective_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    feasible: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    params: Mapped[dict[str, Any]] = mapped_column(JSON_VARIANT, nullable=False, default=dict)


class Metric(Base, StatusMixin, ProvenanceMixin):
    """Long-format home for every figure that is not one of the core columns.

    p-values, deflated Sharpe ratios, PBO, per-regime statistics: quantities that
    exist for some scopes and not others, and whose set grows as the analysis
    does. ``value`` is nullable so that a metric can be recorded as
    ``NOT_AVAILABLE`` without inventing a number for it.
    """

    __tablename__ = "metrics"
    __table_args__ = (
        UniqueConstraint(
            "study_id", "scope", "scope_ref", "metric_key", name="uq_metrics_natural_key"
        ),
        Index("ix_metrics_key", "metric_key"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    study_id: Mapped[int] = mapped_column(
        ForeignKey("studies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    scope: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    scope_ref: Mapped[str] = mapped_column(String(191), nullable=False, index=True)
    metric_key: Mapped[str] = mapped_column(String(96), nullable=False)
    value: Mapped[float | None] = mapped_column(Metric64, nullable=True)
    unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    context: Mapped[dict[str, Any]] = mapped_column(JSON_VARIANT, nullable=False, default=dict)


class GateResult(Base, StatusMixin, ProvenanceMixin):
    """One family judged against one pre-registered criterion of one round."""

    __tablename__ = "gate_results"
    __table_args__ = (
        UniqueConstraint(
            "round_id", "family_id", "symbol", "criterion_key", name="uq_gate_results_natural_key"
        ),
        Index("ix_gate_results_verdict", "verdict"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    round_id: Mapped[int] = mapped_column(
        ForeignKey("experiment_rounds.id", ondelete="CASCADE"), nullable=False, index=True
    )
    family_id: Mapped[int] = mapped_column(
        ForeignKey("strategy_families.id", ondelete="CASCADE"), nullable=False, index=True
    )
    symbol: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    criterion_key: Mapped[str] = mapped_column(String(96), nullable=False)
    criterion: Mapped[str | None] = mapped_column(Text, nullable=True)
    verdict: Mapped[str] = mapped_column(String(24), nullable=False)
    observed: Mapped[float | None] = mapped_column(Metric64, nullable=True)
    threshold: Mapped[float | None] = mapped_column(Metric64, nullable=True)
    n_seeds_passed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    n_seeds_total: Mapped[int | None] = mapped_column(Integer, nullable=True)
    detail: Mapped[dict[str, Any]] = mapped_column(JSON_VARIANT, nullable=False, default=dict)


# --------------------------------------------------------------------------- #
# Bulk evidence and the frozen partition
# --------------------------------------------------------------------------- #


class Artifact(Base, StatusMixin, ProvenanceMixin):
    """A registered Parquet/JSON object: where it is and how to prove it is intact.

    ``run_id`` is ``SET NULL`` because the file outlives the catalogue row. If a
    run is re-ingested or removed from the index, the record of the bytes, their
    digest and their schema must survive; that record is the audit trail.
    """

    __tablename__ = "artifacts"
    __table_args__ = (
        UniqueConstraint("uri", name="uq_artifacts_uri"),
        UniqueConstraint("backend", "bucket", "object_key", name="uq_artifacts_location"),
        Index("ix_artifacts_kind", "kind"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    uri: Mapped[str] = mapped_column(Text, nullable=False)
    backend: Mapped[str] = mapped_column(String(32), nullable=False)
    bucket: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    object_key: Mapped[str] = mapped_column(Text, nullable=False)
    kind: Mapped[str] = mapped_column(String(48), nullable=False)
    media_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    byte_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    row_count: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    arrow_schema: Mapped[dict[str, Any]] = mapped_column(JSON_VARIANT, nullable=False, default=dict)
    run_id: Mapped[int | None] = mapped_column(
        ForeignKey("runs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    study_id: Mapped[int | None] = mapped_column(
        ForeignKey("studies.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )


class MonteCarloRun(Base, StatusMixin, ProvenanceMixin):
    """The summary of a resampling experiment; the paths themselves are Parquet.

    A thousand trajectories per family is a matrix, not a document. Only the
    quantiles that get read live here; ``artifact_id`` points at the file holding
    every path, so the fan chart is rebuilt from the evidence rather than from a
    JSON blob nobody can validate.
    """

    __tablename__ = "monte_carlo_runs"
    __table_args__ = (
        UniqueConstraint(
            "study_id", "family_id", "symbol", "method", "seed", name="uq_monte_carlo_natural_key"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    study_id: Mapped[int] = mapped_column(
        ForeignKey("studies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    family_id: Mapped[int] = mapped_column(
        ForeignKey("strategy_families.id", ondelete="CASCADE"), nullable=False, index=True
    )
    symbol: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    method: Mapped[str] = mapped_column(String(48), nullable=False)
    seed: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    n_paths: Mapped[int] = mapped_column(Integer, nullable=False)
    horizon_bars: Mapped[int | None] = mapped_column(Integer, nullable=True)
    block_probability: Mapped[float | None] = mapped_column(Metric64, nullable=True)
    terminal_p05: Mapped[float | None] = mapped_column(Metric64, nullable=True)
    terminal_p25: Mapped[float | None] = mapped_column(Metric64, nullable=True)
    terminal_median: Mapped[float | None] = mapped_column(Metric64, nullable=True)
    terminal_p75: Mapped[float | None] = mapped_column(Metric64, nullable=True)
    terminal_p95: Mapped[float | None] = mapped_column(Metric64, nullable=True)
    prob_positive: Mapped[float | None] = mapped_column(Metric64, nullable=True)
    mean_max_drawdown: Mapped[float | None] = mapped_column(Metric64, nullable=True)
    artifact_id: Mapped[int | None] = mapped_column(
        ForeignKey("artifacts.id", ondelete="SET NULL"), nullable=True, index=True
    )


class HoldoutRegistryEntry(Base, StatusMixin, ProvenanceMixin):
    """The audit trail of the frozen partition — never its contents.

    This table stores the procedural facts that make a holdout reading
    admissible: that an explicit authorisation existed, which commit contained
    the selection rule *before* the partition was opened, which commit recorded
    the result afterwards, the fingerprint of the frozen candidate, the digest of
    the dataset and the exact command. It stores no observation, no return and no
    metric from inside the window.

    Defaults to ``HOLDOUT_LOCKED`` and ``audited =
    False``. A ``CHECK`` constraint refuses the incoherent claim of an audited
    entry that was never opened.
    """

    __tablename__ = "holdout_registry"
    __table_args__ = (
        UniqueConstraint("study_id", "candidate_key", name="uq_holdout_registry_natural_key"),
        # Written as portable SQL rather than a SQLAlchemy expression so the
        # migration renders one statement that both dialects accept: SQLite
        # understands the `false` keyword since 3.23 and stores it as 0.
        CheckConstraint(
            "audited = false OR opened_at IS NOT NULL",
            name="ck_holdout_registry_audited_implies_opened",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    study_id: Mapped[int] = mapped_column(
        ForeignKey("studies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    candidate_key: Mapped[str] = mapped_column(String(191), nullable=False)
    candidate_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    authorization_token_present: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    authorization_recorded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    commit_before: Mapped[str | None] = mapped_column(String(40), nullable=True)
    commit_after: Mapped[str | None] = mapped_column(String(40), nullable=True)
    dataset_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    command: Mapped[str | None] = mapped_column(Text, nullable=True)
    opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    audited: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    audited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    auditor: Mapped[str | None] = mapped_column(String(128), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


__all__ = [
    "CORE_METRIC_COLUMNS",
    "JSON_VARIANT",
    "STATUS",
    "Artifact",
    "Base",
    "CoreMetricsMixin",
    "ExperimentRound",
    "Fold",
    "FoldResult",
    "GateResult",
    "HoldoutRegistryEntry",
    "Metric",
    "MonteCarloRun",
    "ProvenanceMixin",
    "Run",
    "RunSeed",
    "SearchEvaluation",
    "StatusMixin",
    "StrategyFamily",
    "StrategySpec",
    "Study",
    "utcnow",
]
