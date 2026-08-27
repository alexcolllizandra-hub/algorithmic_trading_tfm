"""Tests for idempotent ingestion, real constraints and honest absent metrics."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from perp_lab.catalog import repositories as repo
from perp_lab.catalog.models import Artifact, Run, RunSeed, SearchEvaluation, Study
from perp_lab.catalog.repositories import (
    MetricsWithoutMeasurementError,
    Provenance,
    SearchEvaluationRecord,
)
from perp_lab.catalog.session import build_engine, build_session_factory, create_all
from perp_lab.catalog.status import ResultStatus
from perp_lab.catalog.storage import ObjectMetadata

PROVENANCE = Provenance(
    source_artifact="artifacts/runs/r2_momentum/study_robustness.json",
    source_sha256="a" * 64,
    git_commit="b" * 40,
    code_version="0.1.0",
)


@pytest.fixture
def session(tmp_path: Path) -> Iterator[Session]:
    engine = build_engine(f"sqlite+pysqlite:///{(tmp_path / 'catalog.sqlite').as_posix()}")
    create_all(engine)
    factory = build_session_factory(engine)
    with factory() as active:
        yield active
    engine.dispose()


def _study(session: Session) -> Study:
    return repo.upsert_study(
        session,
        key="tfm",
        title="Interpretable intraday strategies on BTC/ETH perpetuals",
        primary_symbol="BTCUSDT",
        secondary_symbol="ETHUSDT",
        timeframe="1h",
        holdout_start=datetime(2026, 1, 1, tzinfo=UTC),
        holdout_end=datetime(2026, 7, 1, tzinfo=UTC),
    )


def _run(session: Session, study: Study, *, run_id: str = "r2_momentum") -> Run:
    family = repo.upsert_family(
        session,
        study=study,
        key="momentum",
        name="Momentum",
        provenance=PROVENANCE,
    )
    return repo.upsert_run(
        session,
        study=study,
        run_id=run_id,
        symbol="BTCUSDT",
        timeframe="1h",
        engine="random_search",
        run_dir=f"artifacts/runs/{run_id}",
        family=family,
        provenance=PROVENANCE,
    )


# --------------------------------------------------------------------------- #
# Idempotency
# --------------------------------------------------------------------------- #


def test_ingesting_the_same_study_twice_yields_exactly_one_row(session: Session) -> None:
    first = _study(session)
    second = repo.upsert_study(
        session,
        key="tfm",
        title="Interpretable intraday strategies on BTC/ETH perpetuals",
        primary_symbol="BTCUSDT",
        timeframe="1h",
    )
    session.commit()

    assert first.id == second.id
    assert session.query(Study).count() == 1


def test_re_ingesting_a_seed_updates_its_metrics_instead_of_duplicating(
    session: Session,
) -> None:
    study = _study(session)
    run = _run(session, study)

    repo.upsert_run_seed(
        session,
        run=run,
        seed=42,
        provenance=PROVENANCE,
        metrics={"total_return": 0.11, "sharpe": 0.8, "n_trades": 120},
    )
    updated = repo.upsert_run_seed(
        session,
        run=run,
        seed=42,
        provenance=PROVENANCE,
        metrics={"total_return": 0.13, "sharpe": 0.9, "n_trades": 121},
    )
    session.commit()

    assert session.query(RunSeed).count() == 1
    assert updated.total_return == pytest.approx(0.13)
    assert updated.n_trades == 121


def test_bulk_search_evaluations_are_written_once_however_often_ingested(
    session: Session,
) -> None:
    study = _study(session)
    run = _run(session, study)
    records = [
        SearchEvaluationRecord(
            seed=42, fold_index=0, evaluation_index=index, objective=float(index) / 100
        )
        for index in range(25)
    ]

    repo.bulk_upsert_search_evaluations(session, run=run, records=records, provenance=PROVENANCE)
    repo.bulk_upsert_search_evaluations(session, run=run, records=records, provenance=PROVENANCE)
    session.commit()

    assert repo.count_search_evaluations(session, run=run) == 25


def test_bulk_search_evaluations_update_the_objective_on_re_ingestion(
    session: Session,
) -> None:
    study = _study(session)
    run = _run(session, study)

    repo.bulk_upsert_search_evaluations(
        session,
        run=run,
        records=[SearchEvaluationRecord(seed=7, fold_index=1, evaluation_index=0, objective=0.1)],
        provenance=PROVENANCE,
    )
    repo.bulk_upsert_search_evaluations(
        session,
        run=run,
        records=[SearchEvaluationRecord(seed=7, fold_index=1, evaluation_index=0, objective=0.5)],
        provenance=PROVENANCE,
    )
    session.commit()

    assert repo.count_search_evaluations(session, run=run) == 1
    stored = session.query(SearchEvaluation).one()
    assert stored.objective == pytest.approx(0.5)


# --------------------------------------------------------------------------- #
# Constraints
# --------------------------------------------------------------------------- #


def test_a_duplicate_natural_key_is_rejected_by_the_database(session: Session) -> None:
    _study(session)
    session.commit()

    session.add(
        Study(
            key="tfm",
            title="A second study wearing the same key",
            primary_symbol="BTCUSDT",
            timeframe="1h",
        )
    )
    with pytest.raises(IntegrityError):
        session.flush()
    session.rollback()


def test_a_run_pointing_at_a_missing_study_is_rejected(session: Session) -> None:
    session.add(
        Run(
            run_id="orphan",
            study_id=9999,
            symbol="BTCUSDT",
            timeframe="1h",
            engine="random_search",
            run_dir="artifacts/runs/orphan",
            status=ResultStatus.EXECUTED,
            source_artifact="artifacts/runs/orphan/status.json",
        )
    )
    with pytest.raises(IntegrityError):
        session.flush()
    session.rollback()


def test_a_fold_whose_train_window_overlaps_its_test_window_is_refused(
    session: Session,
) -> None:
    study = _study(session)
    run = _run(session, study)

    with pytest.raises(repo.CatalogIntegrityError):
        repo.upsert_fold(
            session,
            run=run,
            fold_index=0,
            train_start=datetime(2024, 1, 1, tzinfo=UTC),
            train_end=datetime(2024, 3, 1, tzinfo=UTC),
            test_start=datetime(2024, 2, 1, tzinfo=UTC),
            test_end=datetime(2024, 4, 1, tzinfo=UTC),
            provenance=PROVENANCE,
        )


def test_deleting_a_run_removes_its_seeds_but_keeps_the_artifact_record(
    session: Session,
) -> None:
    study = _study(session)
    run = _run(session, study)
    repo.upsert_run_seed(session, run=run, seed=42, provenance=PROVENANCE)
    repo.register_artifact(
        session,
        ObjectMetadata(
            key="runs/r2_momentum/equity.parquet",
            uri="file:///tmp/runs/r2_momentum/equity.parquet",
            backend="local",
            bucket="",
            byte_size=512,
            sha256="c" * 64,
            row_count=100,
        ),
        kind="equity_curve",
        run=run,
        provenance=PROVENANCE,
    )
    session.commit()

    session.delete(run)
    session.commit()
    session.expire_all()

    assert session.query(RunSeed).count() == 0
    artifacts = session.query(Artifact).all()
    assert len(artifacts) == 1
    assert artifacts[0].run_id is None
    assert artifacts[0].content_sha256 == "c" * 64


# --------------------------------------------------------------------------- #
# Absence is a state, not a zero
# --------------------------------------------------------------------------- #


def test_a_not_executed_seed_carries_no_metrics(session: Session) -> None:
    study = _study(session)
    run = _run(session, study)

    seed = repo.upsert_run_seed(
        session,
        run=run,
        seed=99,
        provenance=PROVENANCE,
        status=ResultStatus.NOT_EXECUTED,
    )
    session.commit()

    assert seed.status is ResultStatus.NOT_EXECUTED
    assert seed.total_return is None
    assert seed.sharpe is None
    assert seed.n_trades is None


def test_writing_metrics_under_a_status_that_measured_nothing_raises(
    session: Session,
) -> None:
    study = _study(session)
    run = _run(session, study)

    with pytest.raises(MetricsWithoutMeasurementError):
        repo.upsert_run_seed(
            session,
            run=run,
            seed=99,
            provenance=PROVENANCE,
            status=ResultStatus.NOT_EXECUTED,
            metrics={"total_return": 0.0},
        )


def test_a_holdout_locked_metric_stores_null_rather_than_zero(session: Session) -> None:
    study = _study(session)

    metric = repo.upsert_metric(
        session,
        study=study,
        scope="family",
        scope_ref="momentum:BTCUSDT",
        metric_key="holdout_total_return",
        status=ResultStatus.HOLDOUT_LOCKED,
        provenance=PROVENANCE,
    )
    session.commit()

    assert metric.value is None
    assert metric.status is ResultStatus.HOLDOUT_LOCKED


def test_regressing_a_status_erases_the_figures_it_no_longer_vouches_for(
    session: Session,
) -> None:
    study = _study(session)
    run = _run(session, study)

    repo.upsert_run_seed(
        session,
        run=run,
        seed=1,
        provenance=PROVENANCE,
        metrics={"total_return": 0.42, "sharpe": 1.1},
    )
    invalidated = repo.upsert_run_seed(
        session,
        run=run,
        seed=1,
        provenance=PROVENANCE,
        status=ResultStatus.INVALIDATED,
        status_note="outer-fold leakage",
    )
    session.commit()

    assert invalidated.total_return is None
    assert invalidated.sharpe is None
    assert invalidated.status_note == "outer-fold leakage"


def test_an_unknown_metric_name_is_refused_rather_than_silently_dropped(
    session: Session,
) -> None:
    study = _study(session)
    run = _run(session, study)

    with pytest.raises(repo.CatalogIntegrityError):
        repo.upsert_run_seed(
            session,
            run=run,
            seed=1,
            provenance=PROVENANCE,
            metrics={"deflated_sharpe": 0.3},
        )


# --------------------------------------------------------------------------- #
# Provenance
# --------------------------------------------------------------------------- #


def test_every_result_row_round_trips_its_source_path_sha_and_commit(
    session: Session,
) -> None:
    study = _study(session)
    run = _run(session, study)
    seed = repo.upsert_run_seed(session, run=run, seed=42, provenance=PROVENANCE)
    fold = repo.upsert_fold(
        session,
        run=run,
        fold_index=0,
        train_start=datetime(2024, 1, 1, tzinfo=UTC),
        train_end=datetime(2024, 3, 1, tzinfo=UTC),
        test_start=datetime(2024, 3, 8, tzinfo=UTC),
        test_end=datetime(2024, 4, 1, tzinfo=UTC),
        provenance=PROVENANCE,
    )
    fold_result = repo.upsert_fold_result(
        session,
        fold=fold,
        run_seed=seed,
        provenance=PROVENANCE,
        metrics={"total_return": 0.05},
    )
    session.commit()

    for row in (run, seed, fold, fold_result):
        assert row.source_artifact == PROVENANCE.source_artifact
        assert row.source_sha256 == PROVENANCE.source_sha256
        assert row.git_commit == PROVENANCE.git_commit
        assert row.code_version == "0.1.0"
        assert row.ingested_at is not None


def test_registering_an_artifact_records_its_size_digest_and_row_count(
    session: Session,
) -> None:
    study = _study(session)
    metadata = ObjectMetadata(
        key="study/mc/momentum.parquet",
        uri="file:///store/study/mc/momentum.parquet",
        backend="local",
        bucket="",
        byte_size=2048,
        sha256="d" * 64,
        row_count=1000,
        arrow_schema={"path": "int64", "terminal_return": "double"},
    )

    artifact = repo.register_artifact(
        session, metadata, kind="monte_carlo_paths", study=study, provenance=PROVENANCE
    )
    again = repo.register_artifact(
        session, metadata, kind="monte_carlo_paths", study=study, provenance=PROVENANCE
    )
    session.commit()

    assert artifact.id == again.id
    assert artifact.byte_size == 2048
    assert artifact.row_count == 1000
    assert artifact.arrow_schema["terminal_return"] == "double"


# --------------------------------------------------------------------------- #
# The frozen partition
# --------------------------------------------------------------------------- #


def test_a_holdout_entry_defaults_to_locked_and_unaudited(session: Session) -> None:
    study = _study(session)

    entry = repo.upsert_holdout_entry(
        session,
        study=study,
        candidate_key="momentum:BTCUSDT",
        candidate_fingerprint="e" * 16,
        provenance=PROVENANCE,
    )
    session.commit()

    assert entry.status is ResultStatus.HOLDOUT_LOCKED
    assert entry.audited is False
    assert entry.opened_at is None
    assert entry.authorization_token_present is False


def test_claiming_an_audit_of_a_partition_never_opened_is_refused(session: Session) -> None:
    study = _study(session)

    with pytest.raises(repo.CatalogIntegrityError):
        repo.upsert_holdout_entry(
            session,
            study=study,
            candidate_key="momentum:BTCUSDT",
            candidate_fingerprint="e" * 16,
            provenance=PROVENANCE,
            audited=True,
        )


def test_an_opened_and_audited_holdout_entry_keeps_both_commits(session: Session) -> None:
    study = _study(session)

    entry = repo.upsert_holdout_entry(
        session,
        study=study,
        candidate_key="momentum:BTCUSDT",
        candidate_fingerprint="e" * 16,
        provenance=PROVENANCE,
        status=ResultStatus.AUDITED,
        authorization_token_present=True,
        commit_before="1" * 40,
        commit_after="2" * 40,
        dataset_sha256="f" * 64,
        command="uv run perp-lab open-holdout --candidate momentum",
        opened_at=datetime(2026, 7, 2, tzinfo=UTC),
        audited=True,
        audited_at=datetime(2026, 7, 3, tzinfo=UTC),
    )
    session.commit()

    assert entry.commit_before == "1" * 40
    assert entry.commit_after == "2" * 40
    assert entry.audited is True


# --------------------------------------------------------------------------- #
# Queries
# --------------------------------------------------------------------------- #


def test_runs_can_be_filtered_by_family_symbol_and_engine(session: Session) -> None:
    study = _study(session)
    _run(session, study, run_id="r2_momentum")
    breakout = repo.upsert_family(
        session, study=study, key="breakout", name="Breakout", provenance=PROVENANCE
    )
    repo.upsert_run(
        session,
        study=study,
        run_id="r3_breakout",
        symbol="ETHUSDT",
        timeframe="1h",
        engine="genetic_algorithm",
        run_dir="artifacts/runs/r3_breakout",
        family=breakout,
        provenance=PROVENANCE,
    )
    session.commit()

    assert [r.run_id for r in repo.list_runs(session, family_key="breakout")] == ["r3_breakout"]
    assert [r.run_id for r in repo.list_runs(session, symbol="BTCUSDT")] == ["r2_momentum"]
    assert [r.run_id for r in repo.list_runs(session, engine="genetic_algorithm")] == [
        "r3_breakout"
    ]
    assert len(repo.list_runs(session, study_key="tfm")) == 2


def test_gate_results_can_be_filtered_by_verdict(session: Session) -> None:
    study = _study(session)
    experiment_round = repo.upsert_round(
        session, study=study, key="R2", name="Robustness", provenance=PROVENANCE
    )
    family = repo.upsert_family(
        session, study=study, key="momentum", name="Momentum", provenance=PROVENANCE
    )
    repo.upsert_gate_result(
        session,
        experiment_round=experiment_round,
        family=family,
        symbol="BTCUSDT",
        criterion_key="positive_oos_return",
        verdict="FAIL",
        observed=-0.02,
        threshold=0.0,
        status=ResultStatus.REJECTED,
        provenance=PROVENANCE,
    )
    session.commit()

    failures = repo.list_gate_results(session, verdict="FAIL")
    assert len(failures) == 1
    assert failures[0].criterion_key == "positive_oos_return"
    assert repo.list_gate_results(session, verdict="PASS") == []
