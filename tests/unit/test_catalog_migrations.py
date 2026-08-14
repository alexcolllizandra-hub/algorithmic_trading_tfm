"""Tests that the Alembic migration actually builds — and unbuilds — the schema."""

from __future__ import annotations

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

from perp_lab.catalog.models import Base
from perp_lab.catalog.session import build_engine

REPO_ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_INI = REPO_ROOT / "alembic.ini"


@pytest.fixture
def alembic_config(tmp_path: Path) -> tuple[Config, str]:
    """An Alembic config pointed at a throwaway SQLite file."""
    url = f"sqlite+pysqlite:///{(tmp_path / 'catalog.sqlite').as_posix()}"
    config = Config(str(ALEMBIC_INI))
    config.set_main_option("script_location", str(REPO_ROOT / "migrations"))
    config.set_main_option("sqlalchemy.url", url)
    return config, url


def test_alembic_ini_carries_no_credentials() -> None:
    text = ALEMBIC_INI.read_text(encoding="utf-8")
    assert "sqlalchemy.url =\n" in text or "sqlalchemy.url =" in text
    assert "user:pass" not in text
    assert "postgres://" not in text


def test_upgrade_head_creates_every_model_table(alembic_config: tuple[Config, str]) -> None:
    config, url = alembic_config
    command.upgrade(config, "head")

    engine = build_engine(url)
    tables = set(inspect(engine).get_table_names())
    engine.dispose()

    assert set(Base.metadata.tables).issubset(tables)
    assert "alembic_version" in tables


def test_upgrade_creates_the_natural_key_and_query_indexes(
    alembic_config: tuple[Config, str],
) -> None:
    config, url = alembic_config
    command.upgrade(config, "head")

    engine = build_engine(url)
    inspector = inspect(engine)
    run_constraints = {c["name"] for c in inspector.get_unique_constraints("runs")}
    seed_constraints = {c["name"] for c in inspector.get_unique_constraints("run_seeds")}
    run_indexes = {i["name"] for i in inspector.get_indexes("runs")}
    engine.dispose()

    assert "uq_runs_run_id" in run_constraints
    assert "uq_run_seeds_run_seed" in seed_constraints
    assert "ix_runs_family_symbol_engine" in run_indexes


def test_downgrade_base_removes_every_catalogue_table(
    alembic_config: tuple[Config, str],
) -> None:
    config, url = alembic_config
    command.upgrade(config, "head")
    command.downgrade(config, "base")

    engine = build_engine(url)
    tables = set(inspect(engine).get_table_names())
    engine.dispose()

    assert set(Base.metadata.tables) & tables == set()


def test_upgrade_downgrade_upgrade_is_repeatable(alembic_config: tuple[Config, str]) -> None:
    config, url = alembic_config
    command.upgrade(config, "head")
    command.downgrade(config, "base")
    command.upgrade(config, "head")

    engine = build_engine(url)
    tables = set(inspect(engine).get_table_names())
    engine.dispose()

    assert set(Base.metadata.tables).issubset(tables)
