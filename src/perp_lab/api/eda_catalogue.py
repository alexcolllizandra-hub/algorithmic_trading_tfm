"""Discover validated EDA figures and join them with on-disk metadata."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_FIGURE_ID = re.compile(r"^(f[a-z]?\d+[a-z]?|fa\d+)_[\w]+$")

# Thematic grouping for the dashboard gallery (stable figure-id prefixes).
THEME_BY_PREFIX: dict[str, str] = {
    "f01": "calidad_datos",
    "f02": "calidad_datos",
    "fa2": "calidad_datos",
    "f03": "precios_retornos",
    "f04": "precios_retornos",
    "f05": "precios_retornos",
    "f06": "precios_retornos",
    "f07": "precios_retornos",
    "f08": "volatilidad_regimenes",
    "f09": "volatilidad_regimenes",
    "f19": "volatilidad_regimenes",
    "f20": "volatilidad_regimenes",
    "f23": "volatilidad_regimenes",
    "f22": "colas_distribucion",
    "f24": "colas_distribucion",
    "f11": "volumen_actividad",
    "f12": "volumen_actividad",
    "f13": "volumen_actividad",
    "f14": "volumen_actividad",
    "f15": "funding_basis",
    "f16": "funding_basis",
    "f17": "dependencia_btc_eth",
    "f18": "dependencia_btc_eth",
    "f10": "dependencia_temporal",
    "f21": "dependencia_temporal",
}

THEME_LABELS_ES: dict[str, str] = {
    "calidad_datos": "Calidad y cobertura de datos",
    "precios_retornos": "Precios y retornos",
    "colas_distribucion": "Distribución y riesgo de cola",
    "volatilidad_regimenes": "Volatilidad y regímenes",
    "volumen_actividad": "Volumen y actividad de mercado",
    "funding_basis": "Funding y basis",
    "dependencia_btc_eth": "Dependencia BTC-ETH",
    "dependencia_temporal": "Dependencia temporal y lead-lag",
}

# Curated principal findings (artifact-backed ids; captions come from metadata).
KEY_FINDING_IDS: frozenset[str] = frozenset(
    {
        "f05_return_distribution_shape",
        "f08_volatility_dynamics",
        "f16_funding",
        "f17_cross_asset",
        "f19_regime_price_shading",
        "f23_regime_statistical_comparison",
    }
)


@dataclass(frozen=True)
class EdaFigureRecord:
    figure_id: str
    theme: str
    theme_label_es: str
    title_es: str
    caption_en: str
    research_question_es: str
    finding_es: str
    interpretation_es: str
    implication_es: str
    period: str | None
    notebook: str | None
    png_path: Path
    pdf_path: Path | None
    is_key_finding: bool
    metadata_path: Path | None


def _figure_prefix(figure_id: str) -> str:
    return figure_id.split("_", 1)[0]


def _load_meta(meta_dir: Path, figure_id: str) -> dict[str, Any] | None:
    path = meta_dir / f"{figure_id}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _title_from_caption(caption: str) -> str:
    # Use the part before the first dash/em dash as a short title.
    for sep in (" — ", " - "):
        if sep in caption:
            return caption.split(sep, 1)[0].strip()
    return caption[:120].strip()


def discover_eda_figures(
    figures_dir: Path,
    metadata_dir: Path,
    *,
    repo_root: Path | None = None,
) -> list[EdaFigureRecord]:
    """Return every indexed PNG figure under ``figures_dir`` with safe metadata."""
    if not figures_dir.is_dir():
        return []
    records: list[EdaFigureRecord] = []
    for png in sorted(figures_dir.glob("*.png")):
        figure_id = png.stem
        if not _FIGURE_ID.match(figure_id):
            continue
        prefix = _figure_prefix(figure_id)
        theme = THEME_BY_PREFIX.get(prefix, "otros")
        meta = _load_meta(metadata_dir, figure_id)
        caption = str(meta.get("caption", "")) if meta else figure_id.replace("_", " ")
        title = _title_from_caption(caption) if caption else figure_id
        pdf = png.with_suffix(".pdf")
        records.append(
            EdaFigureRecord(
                figure_id=figure_id,
                theme=theme,
                theme_label_es=THEME_LABELS_ES.get(theme, theme),
                title_es=title,
                caption_en=caption,
                research_question_es=str(meta.get("research_question_es", "")) if meta else "",
                finding_es=str(meta.get("finding_es", "")) if meta else "",
                interpretation_es=str(meta.get("interpretation_es", "")) if meta else "",
                implication_es=str(meta.get("methodological_implication_es", "")) if meta else "",
                period=str(meta.get("period")) if meta and meta.get("period") else None,
                notebook=str(meta.get("notebook")) if meta and meta.get("notebook") else None,
                png_path=png.resolve(),
                pdf_path=pdf.resolve() if pdf.exists() else None,
                is_key_finding=figure_id in KEY_FINDING_IDS,
                metadata_path=(metadata_dir / f"{figure_id}.json").resolve()
                if (metadata_dir / f"{figure_id}.json").exists()
                else None,
            )
        )
    return records


def resolve_figure_path(figures_dir: Path, figure_id: str) -> Path:
    """Resolve a figure id to an absolute PNG path; raise on traversal/unknown ids."""
    if not _FIGURE_ID.match(figure_id):
        raise ValueError(f"invalid figure id: {figure_id}")
    root = figures_dir.resolve()
    path = (root / f"{figure_id}.png").resolve()
    if not str(path).startswith(str(root)):
        raise ValueError("path traversal rejected")
    if not path.is_file():
        raise FileNotFoundError(f"figure not found: {figure_id}")
    return path
