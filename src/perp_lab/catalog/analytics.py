"""DuckDB over the registered Parquet, for questions SQL rows cannot answer.

The catalogue tables answer "which runs exist and what did they score". They
deliberately do not hold the series: a per-bar return column for thirteen
families across ten seeds is tens of millions of values, and a relational row
per bar would make the index heavier than the evidence it indexes.

So the series stay in Parquet — written and registered through
:mod:`perp_lab.catalog.storage` — and the aggregate questions are pushed down to
DuckDB, which reads those files directly and never materialises more than the
answer. Nothing here recomputes a backtest; it only reduces what a run already
wrote.

Every statement is a named constant with bound parameters. The only values
interpolated into SQL text are column names, and those are checked against the
Parquet file's own schema first, so a caller cannot smuggle an expression in
through a column argument.

Expected shapes
---------------
* *measurement frames* — one row per (family, symbol, engine, seed, fold_index)
  with a ``status`` column and the core metric columns. Rows whose status did
  not measure anything are excluded from aggregates rather than counted as zero.
* *equity frames* — a timestamp column and a value column, named by the caller.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path

import duckdb
import polars as pl

from perp_lab.catalog.status import MEASURED_STATUSES
from perp_lab.catalog.storage import LocalObjectStore, ObjectStore

MEASURED_STATUS_VALUES: list[str] = sorted(status.value for status in MEASURED_STATUSES)
"""Statuses under which a number legitimately exists; everything else is excluded."""


class AnalyticsError(RuntimeError):
    """Raised when a query cannot be run against the given Parquet sources."""


# --------------------------------------------------------------------------- #
# SQL
# --------------------------------------------------------------------------- #

SQL_AGGREGATE_METRICS_ACROSS_RUNS = """
SELECT
    family,
    symbol,
    engine,
    count(*)                       AS n_results,
    count(DISTINCT seed)           AS n_seeds,
    avg(total_return)              AS mean_total_return,
    median(total_return)           AS median_total_return,
    avg(sharpe)                    AS mean_sharpe,
    median(sharpe)                 AS median_sharpe,
    min(max_drawdown)              AS worst_max_drawdown,
    sum(n_trades)                  AS total_trades
FROM read_parquet($files)
WHERE list_contains($measured, status)
GROUP BY family, symbol, engine
ORDER BY family, symbol, engine
"""
"""Family-level rollup over measurement frames, ignoring unmeasured rows."""

SQL_PER_FOLD_ROLLUP = """
SELECT
    family,
    symbol,
    fold_index,
    count(*)             AS n_results,
    count(DISTINCT seed) AS n_seeds,
    avg(total_return)    AS mean_total_return,
    stddev_samp(total_return) AS sd_total_return,
    avg(sharpe)          AS mean_sharpe,
    min(max_drawdown)    AS worst_max_drawdown
FROM read_parquet($files)
WHERE list_contains($measured, status)
GROUP BY family, symbol, fold_index
ORDER BY family, symbol, fold_index
"""
"""Per-fold rollup: the spread across seeds within a fold, fold by fold."""

SQL_RESAMPLE_EQUITY = """
SELECT
    date_trunc($unit, {time_column})                       AS bucket,
    last({value_column} ORDER BY {time_column})            AS value_close,
    min({value_column})                                    AS value_min,
    max({value_column})                                    AS value_max,
    count(*)                                               AS n_bars
FROM read_parquet($files)
GROUP BY bucket
ORDER BY bucket
"""
"""Decimate a series to the resolution a chart can actually show."""

SQL_STATUS_BREAKDOWN = """
SELECT status, count(*) AS n_rows
FROM read_parquet($files)
GROUP BY status
ORDER BY status
"""
"""How many rows sit under each status — the honest denominator for a coverage claim."""

SQL_DESCRIBE = "SELECT * FROM read_parquet($files) LIMIT 0"

VALID_TRUNCATION_UNITS: frozenset[str] = frozenset(
    {"minute", "hour", "day", "week", "month", "quarter", "year"}
)


# --------------------------------------------------------------------------- #
# Plumbing
# --------------------------------------------------------------------------- #


@contextmanager
def duckdb_connection() -> Iterator[duckdb.DuckDBPyConnection]:
    """An in-process, in-memory DuckDB pinned to UTC.

    The session timezone is set explicitly because ``date_trunc`` over a
    timezone-aware column resolves in the *session's* zone: left alone, the same
    query would bucket a day differently in Madrid than in UTC, and a figure in
    the thesis would depend on the laptop that produced it.
    """
    connection = duckdb.connect()
    try:
        connection.execute("SET TimeZone='UTC'")
        yield connection
    finally:
        connection.close()


def _as_file_list(sources: str | Path | Iterable[str | Path]) -> list[str]:
    if isinstance(sources, str | Path):
        candidates = [Path(sources)]
    else:
        candidates = [Path(source) for source in sources]
    if not candidates:
        raise AnalyticsError("No Parquet sources were given.")
    missing = [str(path) for path in candidates if not path.is_file()]
    if missing:
        raise AnalyticsError(f"Parquet sources do not exist: {missing}")
    return [path.as_posix() for path in candidates]


def _quote_identifier(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def parquet_columns(sources: str | Path | Iterable[str | Path]) -> list[str]:
    """Column names of the given Parquet files, read from the footer only."""
    files = _as_file_list(sources)
    with duckdb_connection() as connection:
        return [
            str(name) for name in connection.execute(SQL_DESCRIBE, {"files": files}).pl().columns
        ]


def _checked_column(name: str, available: Sequence[str], *, role: str) -> str:
    if name not in available:
        raise AnalyticsError(
            f"No {role} column {name!r} in the Parquet source; available columns: "
            f"{sorted(available)}"
        )
    return _quote_identifier(name)


# --------------------------------------------------------------------------- #
# Queries
# --------------------------------------------------------------------------- #


def aggregate_metrics_across_runs(
    sources: str | Path | Iterable[str | Path],
) -> pl.DataFrame:
    """Family-level aggregates over one or many measurement frames.

    Rows whose status did not measure anything are dropped, not averaged in as
    zero: a family with three executed seeds and seven that never ran has a mean
    over three, and the count column says so.
    """
    files = _as_file_list(sources)
    with duckdb_connection() as connection:
        return connection.execute(
            SQL_AGGREGATE_METRICS_ACROSS_RUNS,
            {"files": files, "measured": MEASURED_STATUS_VALUES},
        ).pl()


def per_fold_rollup(sources: str | Path | Iterable[str | Path]) -> pl.DataFrame:
    """Per-fold statistics across seeds, for one or many measurement frames."""
    files = _as_file_list(sources)
    with duckdb_connection() as connection:
        return connection.execute(
            SQL_PER_FOLD_ROLLUP,
            {"files": files, "measured": MEASURED_STATUS_VALUES},
        ).pl()


def status_breakdown(sources: str | Path | Iterable[str | Path]) -> pl.DataFrame:
    """Row counts per status, so coverage can be stated instead of assumed."""
    files = _as_file_list(sources)
    with duckdb_connection() as connection:
        return connection.execute(SQL_STATUS_BREAKDOWN, {"files": files}).pl()


def resample_equity(
    sources: str | Path | Iterable[str | Path],
    *,
    unit: str = "day",
    time_column: str = "ts",
    value_column: str = "equity",
) -> pl.DataFrame:
    """Reduce an equity (or drawdown) series to one row per truncated period."""
    normalised_unit = unit.strip().lower()
    if normalised_unit not in VALID_TRUNCATION_UNITS:
        raise AnalyticsError(
            f"Unsupported truncation unit {unit!r}; expected one of "
            f"{sorted(VALID_TRUNCATION_UNITS)}."
        )
    files = _as_file_list(sources)
    available = parquet_columns(files)
    statement = SQL_RESAMPLE_EQUITY.format(
        time_column=_checked_column(time_column, available, role="timestamp"),
        value_column=_checked_column(value_column, available, role="value"),
    )
    with duckdb_connection() as connection:
        return connection.execute(statement, {"files": files, "unit": normalised_unit}).pl()


# --------------------------------------------------------------------------- #
# Getting remote objects onto a local disk DuckDB can read
# --------------------------------------------------------------------------- #


def materialise(store: ObjectStore, key: str, cache_dir: str | Path) -> Path:
    """Return a local path for ``key``, downloading it only if it is remote.

    The local backend already exposes a real path, so nothing is copied in the
    offline configuration; a remote backend is cached under ``cache_dir`` and
    reused on the next call.
    """
    if isinstance(store, LocalObjectStore):
        path = store.local_path(key)
        if not path.is_file():
            raise AnalyticsError(f"No object at key {key!r} under {store.root}.")
        return path

    target = Path(cache_dir) / key
    if target.is_file():
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(store.get(key))
    return target


__all__ = [
    "MEASURED_STATUS_VALUES",
    "SQL_AGGREGATE_METRICS_ACROSS_RUNS",
    "SQL_DESCRIBE",
    "SQL_PER_FOLD_ROLLUP",
    "SQL_RESAMPLE_EQUITY",
    "SQL_STATUS_BREAKDOWN",
    "VALID_TRUNCATION_UNITS",
    "AnalyticsError",
    "aggregate_metrics_across_runs",
    "duckdb_connection",
    "materialise",
    "parquet_columns",
    "per_fold_rollup",
    "resample_equity",
    "status_breakdown",
]
