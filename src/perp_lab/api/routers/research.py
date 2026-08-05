"""Research narrative endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from perp_lab.api import methodology_services, research_services
from perp_lab.api import models as m
from perp_lab.api.deps import RunDirDep, SettingsDep

router = APIRouter(tags=["research"])


@router.get("/research/summary", response_model=m.ResearchSummaryResponse)
def get_research_summary(
    settings: SettingsDep,
    run_id: Annotated[str | None, Query()] = None,
) -> m.ResearchSummaryResponse:
    return research_services.research_summary(settings, run_id=run_id)


@router.get("/research/timeline", response_model=m.TimelineResponse)
def get_timeline(
    settings: SettingsDep,
    run_id: Annotated[str, Query(min_length=1)],
) -> m.TimelineResponse:
    try:
        return research_services.research_timeline(settings, run_id)
    except FileNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/methodology/features", response_model=m.MethodologyResponse)
def get_methodology(
    settings: SettingsDep,
    run_id: Annotated[str | None, Query()] = None,
) -> m.MethodologyResponse:
    return methodology_services.methodology(settings, run_id=run_id)


@router.get("/methodology/strategies", response_model=m.MethodologyResponse)
def get_strategies(
    settings: SettingsDep,
    run_id: Annotated[str | None, Query()] = None,
) -> m.MethodologyResponse:
    return methodology_services.methodology(settings, run_id=run_id)


@router.get("/runs/{run_id}/validity", response_model=m.RunValidityResponse)
def get_validity(run_dir: RunDirDep) -> m.RunValidityResponse:
    return research_services.run_validity(run_dir)
