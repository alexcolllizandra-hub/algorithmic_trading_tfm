"""Market coverage and development-only OHLCV."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from perp_lab.api import models as m
from perp_lab.api import services
from perp_lab.api.deps import PageDep, SettingsDep

router = APIRouter(tags=["market"])


@router.get("/market/coverage", response_model=m.MarketCoverageResponse)
def coverage(settings: SettingsDep) -> m.MarketCoverageResponse:
    return services.market_coverage(settings)


@router.get("/market/ohlcv", response_model=m.OhlcvResponse)
def ohlcv(
    settings: SettingsDep,
    page: PageDep,
    symbol: Annotated[str, Query(min_length=3, max_length=20)],
    timeframe: Annotated[str, Query(min_length=1, max_length=8)] = "1h",
) -> m.OhlcvResponse:
    try:
        return services.ohlcv(settings, symbol, timeframe, page)
    except FileNotFoundError as exc:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail=f"no development data for {symbol} {timeframe}",
        ) from exc
