"""Study-closure adapters: the whole study, not one run.

Every other service in this package answers a question about a single search
run. These answer the question the thesis actually asks — what happened across
all thirteen families once they are judged together — by serving the payload
``scripts/build_study_dashboard.py`` consolidates from the gate reports, the
persisted ledgers and the three closure reports.

The payload is read once and cached: it is several megabytes and entirely
static, since it describes a study that is closed and a holdout that is spent.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from perp_lab.api import models as m
from perp_lab.api.settings import ApiSettings
from perp_lab.catalog.status import ResultStatus

HOLDOUT_PERIOD = "[2026-01-01, 2026-07-01)"


class StudyPayloadMissingError(FileNotFoundError):
    """Raised when the consolidated study artifact has not been built yet."""


@lru_cache(maxsize=4)
def _load(path_str: str, mtime: float) -> dict[str, Any]:
    """Parse the artifact, keyed by path and modification time.

    Including the mtime in the key means rebuilding the artifact invalidates the
    cache without a server restart, which matters because the build script is
    run by hand.
    """
    del mtime
    return json.loads(Path(path_str).read_text(encoding="utf-8"))


def _payload(settings: ApiSettings) -> dict[str, Any]:
    path = settings.study_dashboard_path
    if not path.exists():
        raise StudyPayloadMissingError(
            f"The consolidated study artifact is missing: {path}. "
            "Build it with: uv run python scripts/build_study_dashboard.py"
        )
    return _load(str(path), path.stat().st_mtime)


def _summary_fields(family: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in family.items() if k not in {"equity", "seeds", "monte_carlo"}}


def study_summary(settings: ApiSettings) -> m.StudySummaryResponse:
    payload = _payload(settings)
    return m.StudySummaryResponse(
        generated_at=payload["generated_at"],
        schema_version=payload["schema_version"],
        primary_symbol=payload["primary_symbol"],
        secondary_symbol=payload["secondary_symbol"],
        primary_engine=payload["primary_engine"],
        timeframe=payload["timeframe"],
        study=m.StudyCorrections(**payload["study"]),
        families=[
            m.StudyFamilySummary(**_summary_fields(f))
            for f in sorted(payload["families"], key=lambda r: -r["total_return"])
        ],
        holdout_opened=payload.get("holdout") is not None,
    )


def study_family(settings: ApiSettings, key: str) -> m.StudyFamilyDetail:
    payload = _payload(settings)
    for family in payload["families"]:
        if family["key"] == key:
            return m.StudyFamilyDetail(**family)
    raise KeyError(key)


def study_regimes(settings: ApiSettings) -> m.StudyRegimesResponse:
    regimes = _payload(settings)["regimes"]
    return m.StudyRegimesResponse(
        exploratory=True,
        cells=regimes.get("cells", []),
        correction=regimes.get("correction", {}),
        candidate=regimes.get("candidate"),
        conclusion=regimes.get("conclusion"),
    )


HOLDOUT_ISOLATION_REASON = (
    "La partición [2026-01-01, 2026-07-01) se congeló antes de cualquier EDA, "
    "selección de familias o ajuste de parámetros. Se abre una sola vez y su "
    "lectura no se publica hasta que su procedencia esté auditada: publicar un "
    "número antes de comprobar que el candidato estaba congelado convertiría la "
    "prueba confirmatoria en una prueba más del estudio."
)

HOLDOUT_AUDIT_REQUIREMENTS: tuple[str, ...] = (
    "Autorización explícita OPEN_FINAL_HOLDOUT registrada.",
    "Commit anterior a la apertura que contenga la regla de selección y el candidato.",
    "Candidato congelado con sus parámetros exactos y su huella de selección.",
    "Configuración resuelta del experimento (costes, ejecución, anualización).",
    "SHA-256 del dataset de holdout coincidente con el registrado antes de abrir.",
    "Comando ejecutado y logs de la ejecución.",
    "Artefactos generados por la lectura.",
    "Commit posterior que registre el resultado.",
    "Ausencia de modificaciones retrospectivas entre ambos commits.",
)


def study_holdout(settings: ApiSettings) -> m.StudyHoldoutResponse:
    """The holdout's publication state, locked unless the audit has been recorded.

    The gate is deliberately on the serving side rather than only in the
    consolidation script. The reading exists on disk as evidence and must keep
    existing; what is controlled here is whether it reaches a screen. Two
    independent things have to be true to publish — the payload must contain a
    reading and the environment must assert the audit passed — so neither a
    rebuilt artifact nor a forgotten flag can publish it on its own.
    """
    holdout = _payload(settings).get("holdout")
    opened = holdout is not None

    if not settings.holdout_audited:
        return m.StudyHoldoutResponse(
            status=ResultStatus.HOLDOUT_LOCKED,
            opened=opened,
            period=HOLDOUT_PERIOD,
            reason=HOLDOUT_ISOLATION_REASON,
            requirements=list(HOLDOUT_AUDIT_REQUIREMENTS),
        )

    if holdout is None:
        return m.StudyHoldoutResponse(
            status=ResultStatus.NOT_EXECUTED,
            opened=False,
            period=HOLDOUT_PERIOD,
            reason=(
                "Este artefacto no transporta ninguna lectura del holdout. La partición se "
                "abrió una vez el 2026-08-13; su lectura está retenida a la espera de "
                "auditoría de procedencia y no se sirve por esta API."
            ),
        )

    return m.StudyHoldoutResponse(
        status=ResultStatus.AUDITED,
        opened=True,
        period=HOLDOUT_PERIOD,
        provenance=holdout.get("provenance"),
        result=holdout.get("result"),
        buy_and_hold=holdout.get("buy_and_hold"),
    )
