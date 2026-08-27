"""Engine and session construction, offline by default.

The catalogue must be usable by anyone who clones the repository, with no
account, no container and no secret. ``DATABASE_URL`` is therefore optional: with
nothing set, the engine points at a local SQLite file under ``data/catalog/``,
which is enough to run every migration, every repository and the whole test
suite. Pointing the same code at Supabase (or any PostgreSQL) is a matter of
exporting one variable.

Two dialect details are handled here rather than being left to the caller:

* SQLite ignores foreign keys unless ``PRAGMA foreign_keys=ON`` is issued on each
  connection. Without it the constraint tests would pass vacuously and a
  development database would happily accumulate orphans that PostgreSQL would
  have refused.
* SQLite's default isolation handling in the DBAPI suppresses ``BEGIN`` for DDL,
  which breaks Alembic's transactional migrations on some platforms; using the
  SQLAlchemy 2 ``future`` engine with explicit transactions avoids it.
"""

from __future__ import annotations

import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from perp_lab.catalog.models import Base

DATABASE_URL_ENV = "DATABASE_URL"

DEFAULT_SQLITE_PATH = Path("data/catalog/catalog.sqlite")
"""Where the offline catalogue lives when no ``DATABASE_URL`` is configured."""


def default_sqlite_url(path: str | Path = DEFAULT_SQLITE_PATH) -> str:
    """A SQLAlchemy URL for a local SQLite file, creating its directory."""
    resolved = Path(path).expanduser()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite+pysqlite:///{resolved.as_posix()}"


def database_url(explicit: str | None = None) -> str:
    """Resolve the database URL: argument, then ``DATABASE_URL``, then SQLite.

    Never returns a URL containing credentials this function invented. If a
    hosted database is wanted, its URL — including its password — comes from the
    environment and from nowhere else.
    """
    if explicit:
        return explicit
    from_env = os.environ.get(DATABASE_URL_ENV, "").strip()
    return from_env or default_sqlite_url()


def _enable_sqlite_foreign_keys(dbapi_connection: Any, _record: Any) -> None:
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def build_engine(url: str | None = None, *, echo: bool = False) -> Engine:
    """Create an engine for ``url`` (default: resolved from the environment)."""
    resolved = database_url(url)
    engine = create_engine(resolved, echo=echo, future=True)
    if engine.dialect.name == "sqlite":
        event.listen(engine, "connect", _enable_sqlite_foreign_keys)
    return engine


def build_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Session factory that keeps objects usable after ``commit()``."""
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)


def create_all(engine: Engine) -> None:
    """Create every table directly, bypassing Alembic.

    For tests and throwaway local databases only. Alembic is the authority on
    the schema of anything whose contents are meant to survive; ``create_all``
    cannot express a downgrade and leaves no version stamp.
    """
    Base.metadata.create_all(engine)


def drop_all(engine: Engine) -> None:
    """Drop every catalogue table. Test helper; never call this on a real database."""
    Base.metadata.drop_all(engine)


@contextmanager
def session_scope(
    engine_or_factory: Engine | sessionmaker[Session] | None = None,
) -> Iterator[Session]:
    """Transactional scope: commit on success, roll back on any exception.

    Accepts an engine, a session factory, or nothing at all (in which case an
    engine is built from the environment).
    """
    if engine_or_factory is None:
        factory = build_session_factory(build_engine())
    elif isinstance(engine_or_factory, Engine):
        factory = build_session_factory(engine_or_factory)
    else:
        factory = engine_or_factory

    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


__all__ = [
    "DATABASE_URL_ENV",
    "DEFAULT_SQLITE_PATH",
    "build_engine",
    "build_session_factory",
    "create_all",
    "database_url",
    "default_sqlite_url",
    "drop_all",
    "session_scope",
]
