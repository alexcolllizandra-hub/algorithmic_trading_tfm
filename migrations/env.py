"""Alembic environment for the study catalogue.

The URL is resolved by :func:`perp_lab.catalog.session.database_url`, never from
``alembic.ini``: with ``DATABASE_URL`` set the migrations run against that
database (Supabase or any PostgreSQL), and with nothing set they run against a
local SQLite file. Cloning the repository is enough to get a migrated schema.

``render_as_batch`` is on because SQLite cannot ``ALTER`` most things in place;
Alembic emulates it by rebuilding the table. It is a no-op on PostgreSQL.
"""

from __future__ import annotations

from logging.config import fileConfig
from typing import Any

from alembic import context
from sqlalchemy.dialects.postgresql import JSONB

from perp_lab.catalog.models import Base
from perp_lab.catalog.session import build_engine, database_url

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def render_item(type_: str, obj: Any, autogen_context: Any) -> str | bool:
    """Render the dual-dialect JSON column as the constant the models define.

    Left to itself Alembic emits the PostgreSQL repr of the type and drops the
    SQLite variant along with the import it needs, producing a migration that
    fails on both dialects for different reasons.
    """
    if type_ == "type" and isinstance(obj, JSONB):
        autogen_context.imports.add("from perp_lab.catalog.models import JSON_VARIANT")
        return "JSON_VARIANT"
    return False


def _url() -> str:
    configured = config.get_main_option("sqlalchemy.url", default="") or ""
    return database_url(configured.strip() or None)


def run_migrations_offline() -> None:
    """Emit SQL to stdout instead of executing it, for review or manual application."""
    context.configure(
        url=_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
        compare_type=True,
        render_item=render_item,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against a live connection."""
    connectable = build_engine(_url())
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
            compare_type=True,
            render_item=render_item,
        )
        with context.begin_transaction():
            context.run_migrations()
    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
