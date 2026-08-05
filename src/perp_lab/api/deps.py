"""FastAPI dependencies: settings, pagination and safe run-dir resolution."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import Depends, HTTPException, Query, status
from fastapi import Path as PathParam

from perp_lab.api.pagination import PageParams
from perp_lab.api.security import InvalidRunId, RunNotFound, resolve_run_dir
from perp_lab.api.settings import ApiSettings, get_settings

SettingsDep = Annotated[ApiSettings, Depends(get_settings)]


def page_params(
    settings: SettingsDep,
    limit: Annotated[int, Query(ge=1, le=100_000)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> PageParams:
    capped = min(limit, settings.max_page_size)
    return PageParams(limit=capped, offset=offset)


PageDep = Annotated[PageParams, Depends(page_params)]


def get_run_dir(
    settings: SettingsDep,
    run_id: Annotated[str, PathParam(min_length=1, max_length=160)],
) -> Path:
    try:
        return resolve_run_dir(run_id, settings.runs_dir)
    except InvalidRunId as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RunNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


RunDirDep = Annotated[Path, Depends(get_run_dir)]
