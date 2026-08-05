"""Health endpoint."""

from __future__ import annotations

from fastapi import APIRouter

from perp_lab.api import API_VERSION
from perp_lab.api.deps import SettingsDep
from perp_lab.api.models import HealthResponse
from perp_lab.dashboard import loader

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health(settings: SettingsDep) -> HealthResponse:
    runs = loader.discover_runs(settings.runs_dir)
    return HealthResponse(
        api_version=API_VERSION,
        environment=settings.environment,
        artifact_root_exists=settings.artifact_root.exists(),
        runs_available=len(runs),
    )
