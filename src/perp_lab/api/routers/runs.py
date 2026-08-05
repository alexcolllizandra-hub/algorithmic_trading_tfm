"""Run browsing, comparison, candidates, folds, analytics, performance."""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query, status

from perp_lab.api import models as m
from perp_lab.api import services
from perp_lab.api.deps import PageDep, RunDirDep, SettingsDep
from perp_lab.api.pagination import paginate
from perp_lab.dashboard import loader

router = APIRouter(tags=["runs"])

MethodParam = Literal["random_search", "genetic_algorithm"]


@router.get("/runs", response_model=m.RunListResponse)
def list_runs(
    settings: SettingsDep,
    page: PageDep,
    kind: Annotated[str | None, Query()] = None,
    family: Annotated[str | None, Query()] = None,
    algorithm: Annotated[str | None, Query()] = None,
    symbol: Annotated[str | None, Query()] = None,
    sort: Annotated[Literal["run_id", "family", "kind"], Query()] = "run_id",
    order: Annotated[Literal["asc", "desc"], Query()] = "desc",
) -> m.RunListResponse:
    items = services.list_run_summaries(settings)
    if kind:
        items = [r for r in items if r.kind == kind]
    if family:
        items = [r for r in items if r.family == family]
    if algorithm:
        items = [r for r in items if r.algorithm == algorithm]
    if symbol:
        items = [r for r in items if r.symbol.upper() == symbol.upper()]
    items.sort(key=lambda r: getattr(r, sort) or "", reverse=(order == "desc"))
    window, meta = paginate(items, page)
    return m.RunListResponse(items=window, meta=meta)


@router.get("/runs/{run_id}", response_model=m.RunDetailResponse)
def get_run(run_dir: RunDirDep) -> m.RunDetailResponse:
    return services.run_detail(run_dir)


@router.get("/runs/{run_id}/comparison", response_model=m.ComparisonResponse)
def get_comparison(run_dir: RunDirDep) -> m.ComparisonResponse:
    return services.comparison(run_dir)


@router.get("/runs/{run_id}/candidates", response_model=m.CandidatesResponse)
def get_candidates(
    run_dir: RunDirDep,
    page: PageDep,
    method: Annotated[MethodParam, Query()] = "random_search",
) -> m.CandidatesResponse:
    if method not in loader.METHODS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=f"unknown method {method}")
    return services.paginate_candidates(run_dir, method, page)


@router.get("/runs/{run_id}/folds", response_model=m.FoldsResponse)
def get_folds(run_dir: RunDirDep) -> m.FoldsResponse:
    return services.folds(run_dir)


@router.get("/runs/{run_id}/analytics", response_model=m.SearchAnalyticsResponse)
def get_analytics(run_dir: RunDirDep) -> m.SearchAnalyticsResponse:
    return services.search_analytics(run_dir)


@router.get("/runs/{run_id}/performance", response_model=m.PerformanceResponse)
def get_performance(run_dir: RunDirDep) -> m.PerformanceResponse:
    return services.performance(run_dir)


@router.get("/runs/{run_id}/equity", response_model=m.EquityResponse)
def get_equity(
    run_dir: RunDirDep,
    page: PageDep,
    method: Annotated[MethodParam, Query()] = "random_search",
    fold: Annotated[int, Query(ge=0)] = 0,
) -> m.EquityResponse:
    return services.equity(run_dir, method, fold, page)


@router.get("/runs/{run_id}/trades", response_model=m.TradesResponse)
def get_trades(
    run_dir: RunDirDep,
    page: PageDep,
    method: Annotated[MethodParam, Query()] = "random_search",
    fold: Annotated[int, Query(ge=0)] = 0,
) -> m.TradesResponse:
    return services.trades(run_dir, method, fold, page)


@router.get("/runs/{run_id}/artifacts", response_model=m.ArtifactsResponse)
def get_artifacts(run_dir: RunDirDep) -> m.ArtifactsResponse:
    return services.artifacts(run_dir)
