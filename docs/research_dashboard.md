# Research Dashboard v0 (read-only)

A lightweight, **read-only** Streamlit viewer over the artifacts written by the
strategy-search engine (`perp_lab.search`). It never re-runs a backtest or a
search: it only loads and visualises the JSON/Parquet artifacts already on disk.

> **Exploratory results warning.** Everything shown for synthetic-smoke and
> development-data runs comes from walk-forward **validation/test** folds on the
> development period only. These are **not** final-holdout performance and must
> not be reported as the thesis's out-of-sample result. The dashboard prints
> this warning prominently on every non-holdout run.

## Launch

Port **8501** (default):

```bash
# install the optional dashboard dependency (Streamlit)
uv sync --extra dev --extra dashboard

# launch (binds http://localhost:8501)
uv run perp-lab dashboard
```

Options:

```bash
uv run perp-lab dashboard --port 8501 --runs-dir artifacts/runs --headless
```

Equivalent direct invocation (used internally):

```bash
uv run streamlit run src/perp_lab/dashboard/app.py --server.port 8501
```

## Architecture

The dashboard is split so that data logic is testable without a UI and stays
decoupled from the search engine:

| Module                              | Responsibility                                                        |
| ----------------------------------- | --------------------------------------------------------------------- |
| `perp_lab/dashboard/loader.py`      | Streamlit-free artifact loading + data transformations (unit tested). |
| `perp_lab/dashboard/app.py`         | Streamlit UI; imports only `loader`, never `perp_lab.search`.         |
| `perp_lab/cli.py` (`dashboard` cmd) | Launches Streamlit on port 8501.                                      |

`loader.py` tolerates missing/incomplete artifacts: absent files yield `None` or
empty frames instead of raising, so an interrupted run can still be browsed.

## Screens / modules

The UI is organised into a sidebar (run browser + filters) and six tabs:

- **Sidebar** — run browser with filters for **run kind**, **strategy family**
  and **run**; each run is tagged `SYNTHETIC SMOKE`, `DEVELOPMENT DATA` or
  `FINAL HOLDOUT`. An **algorithm** filter (Random Search / Genetic Algorithm)
  is applied inside the tabs.
- **Overview** — run metadata; Random Search vs Genetic Algorithm comparison
  table; fair-budget verification (per-method proposed/invalid/duplicate/cached/
  evaluated counts and a pass/fail check); the human-readable comparison report.
- **Configuration** — resolved search configuration, objective definition and
  constraints, search space, and environment.
- **Data & Features** — dataset manifests (id, sha256, row count), feature
  manifest, and the walk-forward temporal partitions (train/val/test, purge,
  embargo).
- **Convergence & Diversity** — best-fitness-per-evaluation convergence curves
  for both methods; GA per-generation diversity and best-per-generation; GA
  parent/offspring lineage.
- **Candidates** — candidate ranking by fitness with parameter inspection;
  failed/rejected candidate ledger.
- **Folds & Test** — per-fold winners with validation and test metrics; test
  equity and drawdown curves per fold; the trade table.

## Run-kind labelling

`loader.classify_run_kind` decides the badge:

1. `synthetic: true` in the search config → **synthetic-smoke**.
2. Otherwise the run label/kind is inspected. `"holdout"` (but not
   `"not_holdout"`) → **final-holdout**; `"synthetic"`/`"smoke"` →
   **synthetic-smoke**; `"development"`/`"dev"` → **development**.
3. A real summary with no synthetic flag defaults to **development**.

## Tests

`tests/unit/test_dashboard_loader.py` builds a minimal artifact directory that
mirrors the real search schema and verifies run discovery, kind classification,
the comparison table, fair-budget verification (including a violation case),
convergence/diversity frames, fold winners, folds, candidate ranking, equity/
trade frames, dataset manifests, and graceful handling of missing artifacts.

## Future service architecture (documented, NOT implemented)

The current dashboard is intentionally a single read-only Streamlit process. A
later phase may split it into services. The proposed target topology and ports
are recorded here **for design only** — none of it is implemented now:

| Service                     | Proposed port | Status          |
| --------------------------- | ------------- | --------------- |
| Streamlit research UI       | 8501          | **implemented** |
| FastAPI results/API gateway | 8000          | future          |
| PostgreSQL (run/metrics DB) | 5432          | future          |
| MinIO (artifact object store, S3 API) | 9000 (API) / 9001 (console) | future |
| Prometheus (metrics scrape) | 9090          | future          |
| Grafana (ops dashboards)    | 3000          | future          |
| Distributed workers / queue | n/a           | future          |
| Paper-trading engine        | n/a           | future          |

Explicitly **out of scope** for this phase: FastAPI, PostgreSQL, MinIO, Grafana,
Prometheus, distributed workers, paper trading, triple-barrier labeling,
meta-labeling, robustness experiments and final-holdout evaluation.
