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
| GET | `/market/coverage` | Dataset coverage + authenticity (dev only). |
| GET | `/market/ohlcv` | Development-only OHLCV bars for charts. |

**Security:** run ids are validated and resolved strictly beneath the configured
runs root (path-traversal rejected); the API is read-only; CORS is a narrow
allow-list; every response carries an `X-Request-ID`; the frozen holdout is
never served (development partitions only).

## Web modules

1. Executive Overview — runs, run-type counts, data authenticity/health, best
   OOS metric, prominent exploratory warning.
2. Market Overview — symbol/timeframe selector, candlesticks, coverage &
   missing-data indicators (development data only).
3. Strategy Lab — strategy families + parameter-space definitions, read-only
   config viewer (no execution buttons).
4. Experiments — run browser (filter/sort), RS vs GA comparison, fair-budget
   verification, candidate ranking, fold winners, validation vs test, runtime/
   failure analysis.
5. Search Analytics — convergence curves, GA diversity by generation, lineage,
   fitness-component decomposition.
6. Performance — equity & drawdown with fold boundaries, risk metrics, paginated
   trades with CSV export, cost/slippage/funding contribution.
7. Artifact Inspector — dataset & feature manifests, partitions, search space,
   objective, environment/git state, warnings, failed candidates, missing/
   corrupt diagnostics.
8. Architecture / System Status — implemented components, data flow, service
   health, implemented vs planned vs unavailable.

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
