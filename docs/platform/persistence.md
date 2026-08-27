# Persistence: the study catalogue

The evidence of this study is a directory tree. Every search wrote its own
`artifacts/runs/<run_id>/*.parquet|*.json`, every gate wrote a report under
`reports/`, and the API answers questions by re-reading those files on every
request. That works for one run and fails for the question the thesis actually
asks, which is what happened across *all* families once they are judged
together.

The catalogue is an **index** over that tree. It is not a new source of truth:
the files stay immutable and every row records the path and the SHA-256 of the
artifact it was read from, so any figure that reaches a screen can be traced back
to the bytes that produced it. Deleting the database and rebuilding it from the
artifacts must produce the same catalogue; that is the test of whether the split
is honest.

## Why three stores instead of one

| Store | Holds | Why not somewhere else |
| --- | --- | --- |
| PostgreSQL (Supabase-compatible) | The catalogue: studies, rounds, families, specs, runs, seeds, folds, results, metrics, gates, artifacts, Monte Carlo summaries, holdout audit trail | Small, highly relational, queried with filters and joins. This is what SQL is for. |
| Object storage (Supabase Storage) + Parquet | The series: OHLCV, per-bar returns, trades, equity curves, drawdowns, mass search evaluations, Monte Carlo trajectories | A thousand trajectories per family is a matrix, not a document. Stored as JSON in a column it is unqueryable, unvalidatable and makes the index heavier than the evidence. |
| DuckDB | Analytical queries over those Parquet files | Reads the files in place, pushes the aggregation down, and materialises only the answer. No server, no copy, no second copy of the data to keep in sync. |

The rule that follows from this: **never store a large series as JSON inside
PostgreSQL.** Write it as Parquet, then register its location, byte size, row
count, Arrow schema, SHA-256, git commit, code version and owning run in the
`artifacts` table.

## Running with no credentials at all

Everything works offline, with nothing configured:

```bash
uv sync --extra dev
uv run alembic upgrade head        # creates data/catalog/catalog.sqlite
uv run pytest -m "not network" -q  # the whole suite, SQLite only
```

With no `DATABASE_URL`, `perp_lab.catalog.session.database_url()` resolves to a
local SQLite file under `data/catalog/`. With no
`PERP_LAB_OBJECT_STORE_BACKEND`, `open_object_store()` returns a
`LocalObjectStore` writing under `data/object_store/`. Both directories are
git-ignored. Nothing reaches the network, and no test does either — the Supabase
backend is exercised only for its refusal to be constructed without credentials.

## Environment variables

None of these have a default that contains a secret, and none are written to any
file in this repository. `.env.example` lists the names with empty values;
`.env` itself is git-ignored.

| Variable | Required | Default | Meaning |
| --- | --- | --- | --- |
| `DATABASE_URL` | no | local SQLite under `data/catalog/` | SQLAlchemy URL of the catalogue. For Supabase, the pooled PostgreSQL connection string, e.g. `postgresql+psycopg://<user>:<password>@<host>:6543/postgres`. |
| `PERP_LAB_OBJECT_STORE_BACKEND` | no | `local` | `local` or `supabase`. Selecting `supabase` without the three variables below fails immediately rather than degrading silently. |
| `PERP_LAB_OBJECT_STORE_ROOT` | no | `data/object_store` | Root directory of the local object store. |
| `SUPABASE_URL` | only for the Supabase backend | — | Project URL, e.g. `https://<project-ref>.supabase.co`. |
| `SUPABASE_SERVICE_ROLE_KEY` | only for the Supabase backend | — | Service-role key. Server-side only; it bypasses row-level security and must never reach a browser bundle. |
| `SUPABASE_STORAGE_BUCKET` | only for the Supabase backend | — | Bucket that holds the registered Parquet objects. |

## Migrations

Alembic lives at `alembic.ini` (repository root) with the scripts in
`migrations/`. `migrations/env.py` is wired to `catalog.models.Base.metadata`
and resolves the URL through `database_url()`, so the same commands work against
SQLite and PostgreSQL. `alembic.ini` deliberately carries an empty
`sqlalchemy.url`.

```bash
uv run alembic upgrade head          # apply everything
uv run alembic downgrade base        # unapply everything
uv run alembic current               # what is applied
uv run alembic revision --autogenerate -m "describe the change"

# against a hosted database
$env:DATABASE_URL = "postgresql+psycopg://..."   # PowerShell
uv run alembic upgrade head
```

Both directions are verified on SQLite by
`tests/unit/test_catalog_migrations.py`.

Dialect differences worth knowing, also recorded in the migration's docstring:

- JSON columns are `JSONB` on PostgreSQL and plain `JSON` (text) on SQLite. Only
  PostgreSQL can index or query *inside* the payload, so no code filters on JSON
  contents.
- `status` is a `VARCHAR(32)` plus a `CHECK` constraint on both dialects, not a
  native PostgreSQL enum: adding a state stays an ordinary column migration.
- SQLite enforces foreign keys only under `PRAGMA foreign_keys=ON`, which
  `build_engine()` sets on every connection. Without it the `ondelete` clauses
  would be decorative.
- Index changes are wrapped in `batch_alter_table` because SQLite cannot `ALTER`
  in place. This is a no-op on PostgreSQL.

## Schema

Fourteen tables. `→` is a foreign key, with its `ON DELETE` behaviour in
brackets.

**Structure**

- `studies` — one investigation: assets, timeframe, holdout boundary. Natural
  key `key`. The holdout columns are *boundaries*; no observation from inside
  the frozen window is stored anywhere in this schema.
- `experiment_rounds` → `studies` [CASCADE] — a pre-registered gate (S1, S2, R2,
  R3) and the criterion it applied. Natural key `(study_id, key)`.
- `strategy_families` → `studies` [CASCADE] — one hypothesis under test. Natural
  key `(study_id, key)`.
- `strategy_specs` → `strategy_families` [CASCADE] — a concrete parameterisation,
  its parameters in JSON. Natural key `(family_id, spec_hash)`.

**Execution**

- `runs` → `studies` [CASCADE], `experiment_rounds` [SET NULL],
  `strategy_families` [SET NULL] — one executed search: family × asset × engine.
  Natural key `run_id` (the directory name under `artifacts/runs/`).
  Reorganising gates must not delete the record that a run happened, hence
  `SET NULL`.
- `run_seeds` → `runs` [CASCADE] — one seed, with its out-of-sample aggregate
  over all folds. Natural key `(run_id, seed)`.
- `folds` → `runs` [CASCADE] — a walk-forward split with its train/test windows,
  purge and embargo. Natural key `(run_id, fold_index)`. A definition, so it
  carries provenance but no status.
- `fold_results` → `folds` [CASCADE], `run_seeds` [CASCADE], `strategy_specs`
  [SET NULL] — what one seed achieved on one fold. Natural key
  `(fold_id, run_seed_id)`.
- `search_evaluations` → `runs` [CASCADE], `strategy_specs` [SET NULL] — every
  candidate scored during a search; the highest-cardinality table. Natural key
  `(run_id, seed, fold_index, evaluation_index)`.

**Measurements and verdicts**

- `metrics` → `studies` [CASCADE] — long-format home for everything that is not
  one of the twelve core columns: p-values, deflated Sharpe, PBO, per-regime
  statistics. Natural key `(study_id, scope, scope_ref, metric_key)`.
- `gate_results` → `experiment_rounds` [CASCADE], `strategy_families` [CASCADE] —
  one family judged against one criterion. Natural key
  `(round_id, family_id, symbol, criterion_key)`.

**Bulk evidence and the frozen partition**

- `artifacts` → `runs` [SET NULL], `studies` [SET NULL] — a registered object:
  URI, backend, bucket, key, kind, byte size, row count, SHA-256, Arrow schema.
  Natural keys `uri` and `(backend, bucket, object_key)`. `SET NULL` because the
  file outlives the catalogue row and its digest is the audit trail.
- `monte_carlo_runs` → `studies` [CASCADE], `strategy_families` [CASCADE],
  `artifacts` [SET NULL] — the resampling summary; the paths themselves are the
  linked Parquet. Natural key `(study_id, family_id, symbol, method, seed)`.
- `holdout_registry` → `studies` [CASCADE] — the audit trail of the frozen
  partition and nothing else. Natural key `(study_id, candidate_key)`.

### Core metrics versus JSON

Twelve figures are typed, indexed, filterable columns on `run_seeds` and
`fold_results`: `total_return`, `sharpe`, `sortino`, `max_drawdown`, `calmar`,
`profit_factor`, `win_rate`, `n_trades`, `turnover`, `exposure`, `costs`,
`funding`. They are `DOUBLE PRECISION` (`sa.Double`), not `Numeric`: these are
statistical estimates, not ledger amounts, exact decimal arithmetic would imply
a precision they do not have, and `Numeric` round-trips as `decimal.Decimal`,
which neither Polars nor DuckDB consume without a cast.

Everything variable — strategy parameters, per-family criteria detail, run
configuration, Arrow schemas — is JSON. Adding a strategy family must never
require a migration.

### Absence is a state, never a zero

Every result-bearing table carries `status`
(`perp_lab.catalog.status.ResultStatus`: `EXECUTED`, `AUDITED`, `REJECTED`,
`INVALIDATED`, `SKIPPED`, `NOT_EXECUTED`, `NOT_AVAILABLE`, `HOLDOUT_LOCKED`) and
every metric column is nullable. The repositories enforce the corresponding
rule: writing numbers under a status that measured nothing raises
`MetricsWithoutMeasurementError`, and moving a row *to* such a status clears its
metric columns to `NULL` rather than leaving figures behind that no status
vouches for.

### Provenance is not optional

Every result row carries `source_artifact`, `source_sha256`, `git_commit`,
`code_version` and `ingested_at`. A row that cannot name the artifact it came
from is not admissible.

### The holdout

`holdout_registry` records *procedural facts about* the frozen partition:
whether an explicit authorisation token existed and when, the commit that
contained the selection rule before the partition was opened, the commit that
recorded the result afterwards, the fingerprint of the frozen candidate, the
dataset SHA-256, the exact command, and whether the reading has been audited.

It stores **no observation, no return and no metric from inside the window.**
The default state is the honest one — `HOLDOUT_LOCKED`, unopened, unaudited —
and both the repository and a database `CHECK` constraint refuse an entry that
claims to be audited without recording an opening.

## Idempotency

Ingestion is re-run constantly: after a bug fix, after a gate closes, after a
machine dies halfway through. Running it twice must leave the database exactly
as one run left it. Two mechanisms, both resting on the natural-key unique
constraints listed above:

1. `repositories._upsert` looks the row up by its natural key and updates it in
   place. This keeps the ORM identity map coherent and lets callers keep using
   the returned object, which is what everything the API navigates needs.
2. `bulk_upsert_search_evaluations` uses `INSERT ... ON CONFLICT DO UPDATE` on
   PostgreSQL and SQLite. `search_evaluations` is the table with hundreds of
   thousands of rows, where a `SELECT` per row would dominate ingestion time.
   Other dialects fall back to the row-at-a-time path.

`tests/unit/test_catalog_repositories.py` asserts both: writing the same record
twice yields one row and updates it rather than duplicating.

## Analytical queries

`perp_lab.catalog.analytics` runs DuckDB over registered Parquet. Every
statement is a named constant with bound parameters; the only values interpolated
into SQL text are column names, and those are checked against the file's own
schema first. The connection is pinned to UTC, because `date_trunc` over a
timezone-aware column otherwise resolves in the local zone and a daily bucket
would depend on the machine that produced it.

Helpers: `aggregate_metrics_across_runs`, `per_fold_rollup`, `status_breakdown`,
`resample_equity`, `parquet_columns`, and `materialise`, which returns a local
path for an object — free for the local backend, cached on disk for a remote
one.

Aggregates exclude rows whose status measured nothing. A family with three
executed seeds and seven that never ran has a mean over three, and the count
column says so.

## Pointing at Supabase

Nothing in the code changes. Set the variables, run the migrations, and switch
the object-store backend:

```bash
export DATABASE_URL="postgresql+psycopg://<user>:<password>@<host>:6543/postgres"
export PERP_LAB_OBJECT_STORE_BACKEND=supabase
export SUPABASE_URL="https://<project-ref>.supabase.co"
export SUPABASE_SERVICE_ROLE_KEY="<service-role-key>"
export SUPABASE_STORAGE_BUCKET="<bucket>"

uv run alembic upgrade head
```

Row-level security policies for anything a browser can reach are **not
implemented yet**. The service role bypasses them, so it must stay server-side.

## Ingestion

`scripts/ingest_study_catalogue.py` walks the **gate-report inventory**, not the
run-directory listing, and upserts the catalogue. Original files are never
copied or rewritten: Parquet ledgers are registered in place with their SHA-256
and row count. Running the command twice updates rows in place and must not
change the counts.

The frozen holdout is written as a `HOLDOUT_LOCKED` registry row. Files whose
names announce a holdout reading are skipped. After each pass the catalogue is
compared with the source summaries; a mismatch is a reason not to point the
dashboard at the database, not a number to coerce.

```bash
uv run alembic upgrade head
uv run python scripts/ingest_study_catalogue.py
```
