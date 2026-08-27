"""Study-closure endpoints: the thirteen families judged together."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, status

from perp_lab.api import models as m
from perp_lab.api import study_services
from perp_lab.api.deps import SettingsDep

router = APIRouter(tags=["study"])


def _missing(exc: study_services.StudyPayloadMissingError) -> HTTPException:
    return HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))


@router.get("/study/summary", response_model=m.StudySummaryResponse)
def get_study_summary(settings: SettingsDep) -> m.StudySummaryResponse:
    try:
        return study_services.study_summary(settings)
    except study_services.StudyPayloadMissingError as exc:
        raise _missing(exc) from exc


@router.get("/study/families/{key}", response_model=m.StudyFamilyDetail)
def get_study_family(
    settings: SettingsDep,
    key: Annotated[str, Path(min_length=1, description="family|SYMBOL")],
) -> m.StudyFamilyDetail:
    try:
        return study_services.study_family(settings, key)
    except study_services.StudyPayloadMissingError as exc:
        raise _missing(exc) from exc
    except KeyError as exc:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, detail=f"Unknown study family: {key}"
        ) from exc


@router.get("/study/regimes", response_model=m.StudyRegimesResponse)
def get_study_regimes(settings: SettingsDep) -> m.StudyRegimesResponse:
    try:
        return study_services.study_regimes(settings)
    except study_services.StudyPayloadMissingError as exc:
        raise _missing(exc) from exc


@router.get("/study/holdout", response_model=m.StudyHoldoutResponse)
def get_study_holdout(settings: SettingsDep) -> m.StudyHoldoutResponse:
    try:
        return study_services.study_holdout(settings)
    except study_services.StudyPayloadMissingError as exc:
        raise _missing(exc) from exc
