# Quantitative API (FastAPI)

Read-only, versioned (`/api/v1`) adapter over perp-lab run artifacts and
validated market manifests. The application code lives in the core Python
package at `src/perp_lab/api/` (so it is covered by ruff, pyright and pytest);
this directory only holds the container/deployment glue.

## Run locally (dev)

```bash
uv sync --extra dev
uv run uvicorn perp_lab.api.main:app --reload --port 8000
# docs: http://localhost:8000/api/v1/docs
```

Environment variables (see repository `.env.example`):

- `PERP_LAB_ARTIFACT_ROOT` (default `artifacts`)
- `PERP_LAB_RUNS_DIR` (default `<artifact_root>/runs`)
- `PERP_LAB_MANIFESTS_DIR` (default `data/manifests`)
- `PERP_LAB_DATA_CONTRACT` (default `configs/data_contract.yaml`)
- `PERP_LAB_CORS_ORIGINS` (default `http://localhost:3000`)

## Container

Built from the repository root (`docker compose build api`). Runs as a non-root
user; artifacts/data/configs are provided as read-only volumes.
