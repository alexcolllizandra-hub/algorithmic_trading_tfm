"""FastAPI application factory for the perp-lab quantitative API.

Read-only, versioned (``/api/v1``) adapter over run artifacts and validated
market manifests. Adds CORS (narrowly configured), structured request logging
with a per-request id, and typed error responses. It never exposes the artifact
filesystem directly.

It serves no frozen-holdout observation. The ``/study/holdout`` endpoint returns
the *published result* of the single sanctioned reading of that partition — the
metrics and provenance recorded in Phase H — not the bars themselves, which
remain unavailable through every market and run endpoint.
"""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from perp_lab.api import API_VERSION
from perp_lab.api.routers import eda, health, market, research, runs, study
from perp_lab.api.settings import get_settings

_log = logging.getLogger("perp_lab.api")

API_PREFIX = f"/api/{API_VERSION}"

_DESCRIPTION = (
    "Read-only research API over perp-lab search-run artifacts and validated "
    "market data. Development walk-forward metrics are EXPLORATORY and are not "
    "final-holdout performance."
)


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="perp-lab Quantitative API",
        version="1.0.0",
        description=_DESCRIPTION,
        openapi_url=f"{API_PREFIX}/openapi.json",
        docs_url=f"{API_PREFIX}/docs",
        redoc_url=f"{API_PREFIX}/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=False,
        allow_methods=["GET", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

    @app.middleware("http")
    async def request_context(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
        request.state.request_id = request_id
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            _log.exception(
                "request_id=%s unhandled error %s %s", request_id, request.method, request.url.path
            )
            raise
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        response.headers["X-Request-ID"] = request_id
        _log.info(
            "request_id=%s %s %s -> %d (%.1f ms)",
            request_id,
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
        )
        return response

    app.include_router(health.router, prefix=API_PREFIX)
    app.include_router(runs.router, prefix=API_PREFIX)
    app.include_router(market.router, prefix=API_PREFIX)
    app.include_router(research.router, prefix=API_PREFIX)
    app.include_router(eda.router, prefix=API_PREFIX)
    app.include_router(study.router, prefix=API_PREFIX)

    @app.get("/", include_in_schema=False)
    def root() -> dict[str, str]:
        return {
            "service": "perp-lab-api",
            "docs": f"{API_PREFIX}/docs",
            "health": f"{API_PREFIX}/health",
        }

    return app


app = create_app()
