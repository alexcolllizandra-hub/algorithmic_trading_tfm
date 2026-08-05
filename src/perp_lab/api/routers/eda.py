"""EDA figure catalogue and safe media delivery."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import FileResponse

from perp_lab.api import models as m
from perp_lab.api.deps import PageDep, SettingsDep
from perp_lab.api.eda_catalogue import discover_eda_figures, resolve_figure_path
from perp_lab.api.pagination import paginate
from perp_lab.config import load_data_contract
from perp_lab.data.splits import resolve_holdout_start

router = APIRouter(tags=["eda"])


def _figure_models(settings) -> list[m.EdaFigureModel]:
    records = discover_eda_figures(settings.eda_figures_dir, settings.eda_metadata_dir)
    return [
        m.EdaFigureModel(
            figure_id=r.figure_id,
            theme=r.theme,
            theme_label_es=r.theme_label_es,
            title_es=r.title_es,
            caption_en=r.caption_en,
            research_question_es=r.research_question_es,
            finding_es=r.finding_es,
            interpretation_es=r.interpretation_es,
            implication_es=r.implication_es,
            period=r.period,
            notebook=r.notebook,
            is_key_finding=r.is_key_finding,
            has_pdf=r.pdf_path is not None,
        )
        for r in records
    ]


@router.get("/eda/summary", response_model=m.EdaSummaryResponse)
def eda_summary(settings: SettingsDep) -> m.EdaSummaryResponse:
    contract = load_data_contract(settings.data_contract)
    holdout = resolve_holdout_start(contract)
    items = _figure_models(settings)
    themes = sorted({i.theme_label_es for i in items})
    period = items[0].period if items else None
    return m.EdaSummaryResponse(
        holdout_start=holdout.isoformat(),
        development_period=period,
        n_figures=len(items),
        n_key_findings=sum(1 for i in items if i.is_key_finding),
        themes=themes,
    )


@router.get("/eda/figures", response_model=m.EdaFiguresResponse)
def eda_figures(
    settings: SettingsDep,
    page: PageDep,
    theme: Annotated[str | None, Query()] = None,
    key_only: Annotated[bool, Query()] = False,
) -> m.EdaFiguresResponse:
    items = _figure_models(settings)
    if theme:
        items = [i for i in items if i.theme == theme]
    if key_only:
        items = [i for i in items if i.is_key_finding]
    window, meta = paginate(items, page)
    return m.EdaFiguresResponse(items=window, meta=meta)


@router.get("/eda/figures/{figure_id}")
def eda_figure_image(figure_id: str, settings: SettingsDep) -> FileResponse:
    try:
        path = resolve_figure_path(settings.eda_figures_dir, figure_id)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return FileResponse(path, media_type="image/png", filename=f"{figure_id}.png")
