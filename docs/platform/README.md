# perp-lab Research Platform V1

A professional, read-only web platform for inspecting perp-lab strategy-search
experiments. It has a strict separation of concerns:

- **Quantitative core (Python):** the existing `perp_lab` package (features,
  regimes, strategies, backtester, walk-forward search, artifacts). Unchanged as
  the source of truth.
- **Quantitative API (FastAPI):** `src/perp_lab/api/` — a versioned, read-only
  adapter that maps on-disk run artifacts to typed JSON. It imports the core
  package; it does **not** reimplement any quant logic.
- **Web platform (Next.js + TypeScript):** `apps/web/` — renders the API. No
  backtesting/search/objective logic is duplicated in TypeScript.

```
Browser ──HTTP──▶ Next.js (apps/web, :3000)
                     │  fetch /api/v1/*
                     ▼
              FastAPI (src/perp_lab/api, :8000)
                     │  reads (read-only)
                     ▼
        Artifact directory  +  data/manifests  (source of truth)
                     ▲
                     │ written by
              perp-lab CLI (search / comparison runs)
```

## Ports

| Service | Port | Status in this phase |
|---|---|---|
| Web platform (Next.js) | 3000 | Implemented |
| Quantitative API (FastAPI) | 8000 | Implemented |
| MLflow | 5000 | Reserved / documented, not deployed |
| PostgreSQL | 5432 | Reserved (internal), not deployed |
| Redis | 6379 | Reserved (internal), not deployed |
| Grafana | 3001 | Reserved, not deployed |
| Prometheus | 9090 | Reserved, not deployed |

The reserved services are intentionally **not** implemented — the run-artifact
directory remains the single source of truth. Host ports are overridable via
`WEB_PORT` / `API_PORT` (compose) to avoid clashes with other local stacks.

## Artifact contract

The API reads a per-run directory under `PERP_LAB_RUNS_DIR`
(default `artifacts/runs/<run_id>/`). Key files it understands:

- `search_config.json`, `resolved_experiment_config.yaml` — resolved config.
- `dataset_manifests.json` — dataset ids + sha256 + row counts actually used.
- `feature_manifest.json` — causal feature definitions.
- `folds.json` — walk-forward train/val/test boundaries, purge/embargo.
- `search_space.json`, `objective.json`, `algorithms.json` — search definition.
- `comparison_summary.json`, `comparison_report.md` — RS vs GA summary.
- `<method>_candidates.parquet`, `<method>_failed_candidates.json` — ledgers.
- `<method>_convergence.json`, `ga_diversity.json`, `ga_lineage.json`.
- `<method>_fold_winners.json` — selected candidate per fold.
- `<method>_fold{k}_test_{equity,trades}.parquet` — fold-winner test outputs.
- `metrics.json`, `environment.json`, `git_state.json`, `warnings.json`.

Run kind (synthetic smoke / development / holdout) is derived from the run label
and surfaced as a badge everywhere so synthetic fixtures can never be mistaken
for research results.

## API endpoints (v1, read-only)

Base path `/api/v1`. Interactive docs at `/api/v1/docs`; schema at
`/api/v1/openapi.json`.

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Liveness + artifact-root/runs availability. |
| GET | `/runs` | Paginated run summaries (filter/sort in UI). |
| GET | `/runs/{run_id}` | Resolved config + manifests + folds. |
| GET | `/runs/{run_id}/comparison` | RS vs GA fair-budget comparison. |
| GET | `/runs/{run_id}/candidates` | Paginated candidate ranking. |
| GET | `/runs/{run_id}/folds` | Walk-forward partitions, purge/embargo. |
| GET | `/runs/{run_id}/analytics` | Convergence, GA diversity, lineage. |
| GET | `/runs/{run_id}/performance` | Fold-winner test metrics. |
| GET | `/runs/{run_id}/equity` | Equity/drawdown series for a fold/method. |
| GET | `/runs/{run_id}/trades` | Paginated trades (CSV export in UI). |
| GET | `/runs/{run_id}/artifacts` | Manifests, search space, env, warnings. |
| GET | `/runs/{run_id}/validity` | Budget parity and methodological-validity checks. |
| GET | `/market/coverage` | Dataset coverage + authenticity (dev only). |
| GET | `/market/ohlcv` | Development-only OHLCV bars for charts. |
| GET | `/research/summary` | Research-phase summary and holdout status. |
| GET | `/research/timeline` | Development coverage, folds, purge, embargo and holdout boundary. |
| GET | `/eda/summary` | EDA catalogue summary and available themes. |
| GET | `/eda/figures` | Paginated EDA figure catalogue. |
| GET | `/eda/figures/{figure_id}` | A catalogue figure, constrained to the EDA root. |
| GET | `/methodology/features` | Registered causal feature definitions. |
| GET | `/methodology/strategies` | Interpretable strategy definitions. |

**Security:** run ids are validated and resolved strictly beneath the configured
runs root (path-traversal rejected); the API is read-only; CORS is a narrow
allow-list; every response carries an `X-Request-ID`; the frozen holdout is
never served (development partitions only).

## Canonical web platform: six research sections

The Next.js platform is the canonical presentation layer. The legacy Streamlit
dashboard remains an internal/legacy inspection tool; it is not the public
research narrative.

1. **Visión general** — research phases, artifact evidence and methodological
   warnings.
2. **Datos y EDA** — development-data coverage, fold timeline and the catalogue
   of descriptive figures.
3. **Metodología** — causal features, interpretable strategy families, execution
   timing and walk-forward validation.
4. **Experimentos** — run browser, candidates, convergence and the RS-vs-GA
   validity/fairness panel.
5. **Resultados** — selected-fold equity, drawdown and trades. The contextual
   bar synchronises run, method, fold and candidate through the URL.
6. **Diagnóstico** — manifests, artifacts, environment, warnings and API/system
   state.

Legacy URLs redirect to the corresponding section (`/market` → `/datos-eda`,
`/strategy-lab` → `/metodologia`, `/performance` → `/resultados`, etc.).

### Equity pagination correction

`GET /runs/{run_id}/equity` returns a paginated `points` window **and** an
`EquitySeriesSummary` calculated from the complete on-disk equity series. Cards
and fold-level performance must use `summary`, never the final point in the
current page.

This is tested against
`search_momentum_20260804T190438Z_1a68e0`, Random Search, fold 0:

- `final_equity = 0.9040595814842268`
- `n_points_total = 2159`
- period `2022-03-31` to `2022-06-28`

With `limit=500`, the API deliberately returns 500 display points but retains
the same full-series summary. This prevents a chart viewport from changing a
reported financial metric.

## Commands

### Install

```bash
# Python core + API
uv sync --extra dev --extra api
# Frontend
cd apps/web && npm ci && cd ../..
```

### Run in development

```bash
# API (terminal 1)
uv run uvicorn perp_lab.api.main:app --reload --port 8000

# Web (terminal 2)  — PowerShell
cd apps/web
$env:NEXT_PUBLIC_API_BASE="http://localhost:8000/api/v1"
npm run dev            # http://localhost:3000
```

### Docker Compose

```bash
docker compose build
docker compose up -d          # web :3000, api :8000
docker compose ps             # both should be (healthy)
docker compose down
# Override host ports if 3000/8000 are taken locally:
#   $env:WEB_PORT="3002"; $env:API_PORT="8000"; docker compose up -d
```

### Tests

```bash
# Backend (Python)
uv run pytest -m "not network"
# Frontend
cd apps/web
npm run lint && npm run format:check && npm run typecheck && npm run test
# Playwright E2E (build with the mock base first)
$env:NEXT_PUBLIC_API_BASE="/mock-api/v1"; npm run build; npx playwright test
```

### Inspect the real pilot

```bash
# Provenance/authenticity audit (REAL_HISTORICAL vs SYNTHETIC_FIXTURE)
uv run perp-lab data-audit
# Reproduce the ETH development pilot (RS vs GA, real funding, holdout-guarded)
uv run perp-lab search --config configs/search_pilot_eth.yaml
```

## Security assumptions

- Read-only platform; no mutation endpoints; no auth yet (document + add before
  any remote deployment).
- Client cannot supply arbitrary filesystem paths; only validated run ids.
- Artifacts/data/configs are mounted **read-only** into the API container.
- Containers run as non-root users with Docker health checks.
- Secrets are never committed; configuration is environment-based
  (`.env.example`).

## Extension points

- **New API endpoint:** add a Pydantic model in `api/models.py`, an adapter in
  `api/services.py`, and a route in `api/routers/`. Frontend types live in
  `apps/web/src/lib/api-types.ts` (kept aligned with the schemas).
- **New strategy family / search space:** implement in the Python core; the API
  and UI surface it automatically from the artifacts (no TS changes needed for
  read-only inspection).
- **New module/page:** add under `apps/web/src/app/<route>/page.tsx` and a nav
  entry in `apps/web/src/components/layout/nav.ts`.

## Not implemented (planned)

MLflow, PostgreSQL, Redis, Grafana, Prometheus, distributed workers,
authentication, asynchronous job execution, paper trading, live execution,
triple-barrier labeling, meta-labeling and final-holdout evaluation are **not**
implemented in this phase. They are reserved/documented only.

## Current scientific limits

- The frozen final holdout `[2026-01-01, 2026-07-01)` has not been opened by
  this platform. It is not served by the API.
- The dashboard's pilot artifacts are development evidence only; they do not
  establish robustness or final performance.
- The displayed historical pilot uses one seed and a deliberately limited
  search budget. Its effective counts are unequal: Random Search = 12 and
  Genetic Algorithm = 10. The validity panel exposes this mismatch, therefore
  no conclusion of RS or GA superiority is permitted from that run.
- LightGBM and every ML meta-filter remain unimplemented in this dashboard
  phase.
- The leakage-safe outer-fold search repetition and the definitive multi-seed
  experiment are subsequent experimental phases. Until they complete, numerical
  results must remain labelled exploratory/replaced-pending-repetition where
  applicable.
