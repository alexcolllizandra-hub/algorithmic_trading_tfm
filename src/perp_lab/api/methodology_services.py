"""Methodology documentation adapters (read-only, artifact-backed)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from perp_lab.api import models as m
from perp_lab.api.settings import ApiSettings
from perp_lab.dashboard import loader
from perp_lab.features.manifest import _FORMULAS

_STRATEGY_DOCS: dict[str, dict[str, str]] = {
    "momentum": {
        "name_es": "Momentum (cruce de medias)",
        "hypothesis_es": (
            "Los precios pueden persistir en una dirección durante intervalos "
            "suficientemente largos para que un cruce de medias móviles capture tendencia."
        ),
        "status": "implementada",
    },
    "breakout": {
        "name_es": "Ruptura (breakout)",
        "hypothesis_es": (
            "Rupturas de máximos/mínimos recientes pueden señalar continuación "
            "cuando el canal se construye solo con barras pasadas."
        ),
        "status": "implementada",
    },
    "mean_reversion": {
        "name_es": "Reversión a la media",
        "hypothesis_es": (
            "Desviaciones extremas respecto a una media móvil pueden revertir "
            "cuando el z-score supera umbrales de entrada/salida."
        ),
        "status": "implementada",
    },
}


def _feature_docs_from_manifest(manifest: dict[str, Any]) -> list[m.FeatureDocModel]:
    features = manifest.get("features") or []
    out: list[m.FeatureDocModel] = []
    for f in features:
        if not isinstance(f, dict):
            continue
        kind = str(f.get("kind", ""))
        out.append(
            m.FeatureDocModel(
                name=str(f.get("name", kind)),
                family=str(f.get("family", "other")),
                formula=_FORMULAS.get(kind, str(f.get("formula", kind))),
                inputs=[str(c) for c in (f.get("inputs") or [])],
                lag_bars=f.get("lag_bars"),
                warmup_bars=f.get("warmup"),
                interpretation_es=str(f.get("description", "")),
            )
        )
    return out


def _strategy_docs(search_space: dict[str, Any] | None) -> list[m.StrategyDocModel]:
    families = list(_STRATEGY_DOCS.keys())
    if search_space and isinstance(search_space.get("families"), list):
        families = [str(x) for x in search_space["families"]]
    out: list[m.StrategyDocModel] = []
    for fam in families:
        doc = _STRATEGY_DOCS.get(fam, {})
        params: list[str] = []
        if search_space and isinstance(search_space.get("spaces"), dict):
            space = search_space["spaces"].get(fam) or {}
            if isinstance(space, dict):
                params = sorted(str(k) for k in space)
        out.append(
            m.StrategyDocModel(
                family=fam,
                name_es=doc.get("name_es", fam),
                hypothesis_es=doc.get("hypothesis_es", ""),
                status=doc.get("status", "desconocida"),
                parameters=params,
            )
        )
    return out


def methodology(settings: ApiSettings, *, run_id: str | None = None) -> m.MethodologyResponse:
    source_run_id = run_id
    run_dir: Path | None = None
    if source_run_id:
        candidate = settings.runs_dir / source_run_id
        if candidate.is_dir():
            run_dir = candidate
    if run_dir is None:
        dev = [
            r for r in loader.discover_runs(settings.runs_dir) if r.kind == loader.KIND_DEVELOPMENT
        ]
        if dev:
            run_dir = settings.runs_dir / dev[0].run_id
            source_run_id = dev[0].run_id
    manifest: dict[str, Any] | None = None
    search_space: dict[str, Any] | None = None
    if run_dir and run_dir.is_dir():
        mf = run_dir / "feature_manifest.json"
        if mf.exists():
            try:
                manifest = json.loads(mf.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                manifest = None
        ss = run_dir / "search_space.json"
        if ss.exists():
            try:
                search_space = json.loads(ss.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                search_space = None
    features = _feature_docs_from_manifest(manifest) if manifest else []
    strategies = _strategy_docs(search_space)
    return m.MethodologyResponse(
        features=features,
        strategies=strategies,
        source_run_id=source_run_id,
    )
