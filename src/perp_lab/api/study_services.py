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


def study_holdout(settings: ApiSettings) -> m.StudyHoldoutResponse:
    holdout = _payload(settings).get("holdout")
    if holdout is None:
        return m.StudyHoldoutResponse(opened=False)
    return m.StudyHoldoutResponse(
        opened=True,
        provenance=holdout.get("provenance"),
        result=holdout.get("result"),
        buy_and_hold=holdout.get("buy_and_hold"),
    )
