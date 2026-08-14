"""Ingestion must index the evidence without rewriting it or inventing numbers."""

from __future__ import annotations

import json
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import polars as pl
import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from perp_lab.catalog.ingest import (
    HOLDOUT_CANDIDATE,
    STUDY_KEY,
    ingest_study,
    verify_against_sources,
)
from perp_lab.catalog.models import (
    Artifact,
    ExperimentRound,
    FoldResult,
    HoldoutRegistryEntry,
    Run,
    RunSeed,
    StrategyFamily,
)
from perp_lab.catalog.session import build_engine, build_session_factory, create_all
from perp_lab.catalog.status import ResultStatus
from perp_lab.reporting.study_closure import StudyUnit


@pytest.fixture
def session(tmp_path: Path) -> Iterator[Session]:
    engine = build_engine(f"sqlite+pysqlite:///{(tmp_path / 'catalog.sqlite').as_posix()}")
    create_all(engine)
    factory = build_session_factory(engine)
    with factory() as active:
        yield active
    engine.dispose()


def _write_run(root: Path, *, name: str = "search_momentum_test") -> Path:
    run_dir = root / "artifacts" / "runs" / name
    run_dir.mkdir(parents=True)
    summary = {
        "family": "momentum",
        "symbol": "BTCUSDT",
        "timeframe": "1h",
        "seed": 42,
        "budget": 10,
        "n_folds": 2,
        "label": "synthetic",
        "methods": {
            "random_search": {
                "aggregate_test": {
                    "mean_test_sharpe": -0.25,
                    "mean_test_total_return": -0.12,
                    "mean_test_max_drawdown": -0.4,
                    "mean_test_n_trades": 8.0,
                }
            }
        },
    }
    (run_dir / "comparison_summary.json").write_text(json.dumps(summary), encoding="utf-8")
    folds = {
        "folds": [
            {
                "index": 0,
                "train_start": "2020-01-01T00:00:00+00:00",
                "train_end": "2021-01-01T00:00:00+00:00",
                "test_start": "2021-02-01T00:00:00+00:00",
                "test_end": "2021-05-01T00:00:00+00:00",
                "purge_bars": 24,
                "embargo_bars": 12,
            },
            {
                "index": 1,
                "train_start": "2020-01-01T00:00:00+00:00",
                "train_end": "2021-05-01T00:00:00+00:00",
                "test_start": "2021-06-01T00:00:00+00:00",
                "test_end": "2021-09-01T00:00:00+00:00",
                "purge_bars": 24,
                "embargo_bars": 12,
            },
        ]
    }
    (run_dir / "folds.json").write_text(json.dumps(folds), encoding="utf-8")
    winners = [
        {
            "fold": 0,
            "params": {"fast": 12, "slow": 48},
            "test_metrics": {
                "sharpe": -0.1,
                "total_return": -0.05,
                "max_drawdown": -0.2,
                "n_trades": 3,
            },
        },
        {
            "fold": 1,
            "params": {"fast": 24, "slow": 96},
            "test_metrics": {
                "sharpe": -0.4,
                "total_return": -0.19,
                "max_drawdown": -0.6,
                "n_trades": 5,
            },
        },
    ]
    (run_dir / "random_search_fold_winners.json").write_text(json.dumps(winners), encoding="utf-8")
    equity = pl.DataFrame(
        {
            "open_time": [datetime(2021, 2, 1, tzinfo=UTC), datetime(2021, 2, 2, tzinfo=UTC)],
            "net_return": [-0.01, 0.002],
        }
    )
    equity.write_parquet(run_dir / "random_search_fold0_test_equity.parquet")
    # A file whose name announces a holdout reading must be skipped, not indexed.
    (run_dir / "final_holdout_ledger.parquet").write_bytes(b"not-a-real-ledger")
    return run_dir


def _unit(run_dir: Path) -> StudyUnit:
    return StudyUnit(
        gate="R2",
        family="momentum",
        symbol="BTCUSDT",
        seed=42,
        engine="random_search",
        run_dir=run_dir,
    )


class TestIngestWritesAnIndexNotACopy:
    def test_the_original_files_are_left_byte_for_byte(
        self, session: Session, tmp_path: Path
    ) -> None:
        run_dir = _write_run(tmp_path)
        before = (run_dir / "comparison_summary.json").read_bytes()
        ingest_study(session, tmp_path, units=[_unit(run_dir)])
        assert (run_dir / "comparison_summary.json").read_bytes() == before

    def test_a_holdout_named_file_is_skipped_not_registered(
        self, session: Session, tmp_path: Path
    ) -> None:
        run_dir = _write_run(tmp_path)
        report = ingest_study(session, tmp_path, units=[_unit(run_dir)])

        assert any("final_holdout" in path for path in report.skipped_holdout_files)
        uris = session.scalars(select(Artifact.uri)).all()
        assert all("final_holdout" not in uri for uri in uris)

    def test_equity_parquet_is_registered_in_place(self, session: Session, tmp_path: Path) -> None:
        run_dir = _write_run(tmp_path)
        ingest_study(session, tmp_path, units=[_unit(run_dir)])

        artifact = session.scalars(select(Artifact).where(Artifact.kind == "equity")).one()
        assert artifact.row_count == 2
        assert artifact.content_sha256
        assert Path(artifact.object_key).exists()


class TestEnginesDoNotOverwriteEachOther:
    def test_two_engines_in_one_directory_become_two_runs(
        self, session: Session, tmp_path: Path
    ) -> None:
        """A search comparison writes both engines into the same folder.

        Using the folder name as the run identity would let the second engine
        overwrite the first engine's metrics, and the catalogue would then
        disagree with both sources.
        """
        run_dir = _write_run(tmp_path)
        payload = json.loads((run_dir / "comparison_summary.json").read_text(encoding="utf-8"))
        payload["methods"]["genetic_algorithm"] = {
            "aggregate_test": {
                "mean_test_sharpe": 0.5,
                "mean_test_total_return": 0.08,
                "mean_test_max_drawdown": -0.15,
                "mean_test_n_trades": 11.0,
            }
        }
        (run_dir / "comparison_summary.json").write_text(json.dumps(payload), encoding="utf-8")
        (run_dir / "genetic_algorithm_fold_winners.json").write_text(
            (run_dir / "random_search_fold_winners.json").read_text(encoding="utf-8"),
            encoding="utf-8",
        )

        units = [
            _unit(run_dir),
            StudyUnit(
                gate="R2",
                family="momentum",
                symbol="BTCUSDT",
                seed=42,
                engine="genetic_algorithm",
                run_dir=run_dir,
            ),
        ]
        report = ingest_study(session, tmp_path, units=units)

        assert report.n_runs == 2
        assert report.mismatches == []
        sharpes = {run.engine: run.seeds[0].sharpe for run in session.scalars(select(Run)).all()}
        assert sharpes["random_search"] == pytest.approx(-0.25)
        assert sharpes["genetic_algorithm"] == pytest.approx(0.5)


class TestIngestIsIdempotent:
    def test_running_twice_does_not_duplicate_rows(self, session: Session, tmp_path: Path) -> None:
        run_dir = _write_run(tmp_path)
        units = [_unit(run_dir)]
        first = ingest_study(session, tmp_path, units=units)
        second = ingest_study(session, tmp_path, units=units)

        assert first.n_runs == second.n_runs == 1
        assert session.scalar(select(func.count()).select_from(Run)) == 1
        assert session.scalar(select(func.count()).select_from(RunSeed)) == 1
        assert session.scalar(select(func.count()).select_from(FoldResult)) == 2
        assert (
            session.scalar(
                select(func.count())
                .select_from(StrategyFamily)
                .where(StrategyFamily.key == "momentum")
            )
            == 1
        )

    def test_a_changed_source_metric_updates_the_row_in_place(
        self, session: Session, tmp_path: Path
    ) -> None:
        run_dir = _write_run(tmp_path)
        units = [_unit(run_dir)]
        ingest_study(session, tmp_path, units=units)

        summary_path = run_dir / "comparison_summary.json"
        payload = json.loads(summary_path.read_text(encoding="utf-8"))
        payload["methods"]["random_search"]["aggregate_test"]["mean_test_sharpe"] = -0.99
        summary_path.write_text(json.dumps(payload), encoding="utf-8")

        ingest_study(session, tmp_path, units=units)
        seed = session.scalars(select(RunSeed)).one()
        assert seed.sharpe == pytest.approx(-0.99)
        assert session.scalar(select(func.count()).select_from(RunSeed)) == 1


class TestAbsenceIsAState:
    def test_metrics_the_source_does_not_carry_stay_null(
        self, session: Session, tmp_path: Path
    ) -> None:
        run_dir = _write_run(tmp_path)
        ingest_study(session, tmp_path, units=[_unit(run_dir)])
        seed = session.scalars(select(RunSeed)).one()

        assert seed.total_return == pytest.approx(-0.12)
        assert seed.sharpe == pytest.approx(-0.25)
        # The source never published these. Zero would be a lie.
        assert seed.sortino is None
        assert seed.calmar is None
        assert seed.profit_factor is None
        assert seed.win_rate is None
        assert seed.costs is None
        assert seed.funding is None

    def test_unexecuted_crt_families_carry_no_metrics(
        self, session: Session, tmp_path: Path
    ) -> None:
        run_dir = _write_run(tmp_path)
        ingest_study(session, tmp_path, units=[_unit(run_dir)])

        crt = session.scalars(
            select(StrategyFamily).where(StrategyFamily.key == "pdl_reclaim_long")
        ).one()
        assert crt.status is ResultStatus.NOT_EXECUTED

        crt_round = session.scalars(
            select(ExperimentRound).where(ExperimentRound.key == "CRT_INTRADAY_V1")
        ).one()
        assert crt_round.status is ResultStatus.NOT_EXECUTED

    def test_the_holdout_row_is_locked_and_carries_no_reading(
        self, session: Session, tmp_path: Path
    ) -> None:
        run_dir = _write_run(tmp_path)
        ingest_study(session, tmp_path, units=[_unit(run_dir)])

        entry = session.scalars(select(HoldoutRegistryEntry)).one()
        assert entry.candidate_key == HOLDOUT_CANDIDATE
        assert entry.status is ResultStatus.HOLDOUT_LOCKED
        assert entry.audited is False
        assert entry.opened_at is None


class TestVerification:
    def test_the_catalogue_agrees_with_the_source_after_ingest(
        self, session: Session, tmp_path: Path
    ) -> None:
        run_dir = _write_run(tmp_path)
        units = [_unit(run_dir)]
        report = ingest_study(session, tmp_path, units=units)

        assert report.mismatches == []
        assert verify_against_sources(session, units) == []
        assert report.study_key == STUDY_KEY

    def test_an_empty_inventory_is_refused(self, session: Session, tmp_path: Path) -> None:
        from perp_lab.catalog.ingest import IngestError

        with pytest.raises(IngestError, match="empty"):
            ingest_study(session, tmp_path, units=[])
