"""Environment-based API configuration (no secrets, safe defaults)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


@dataclass(frozen=True)
class ApiSettings:
    """Runtime configuration resolved from environment variables.

    All paths are resolved to absolute form so downstream path-traversal checks
    can compare against a stable root.
    """

    artifact_root: Path
    runs_dir: Path
    manifests_dir: Path
    data_contract: Path
    cors_origins: tuple[str, ...]
    max_page_size: int
    eda_figures_dir: Path
    eda_metadata_dir: Path
    study_dashboard_path: Path
    environment: str

    @property
    def runs_root(self) -> Path:
        return self.runs_dir.resolve()


def _split_origins(raw: str) -> tuple[str, ...]:
    return tuple(o.strip() for o in raw.split(",") if o.strip())


@lru_cache(maxsize=1)
def get_settings() -> ApiSettings:
    artifact_root = Path(os.environ.get("PERP_LAB_ARTIFACT_ROOT", "artifacts")).resolve()
    runs_dir = Path(os.environ.get("PERP_LAB_RUNS_DIR", str(artifact_root / "runs"))).resolve()
    manifests_dir = Path(os.environ.get("PERP_LAB_MANIFESTS_DIR", "data/manifests")).resolve()
    data_contract = Path(
        os.environ.get("PERP_LAB_DATA_CONTRACT", "configs/data_contract.yaml")
    ).resolve()
    cors = os.environ.get("PERP_LAB_CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
    return ApiSettings(
        artifact_root=artifact_root,
        runs_dir=runs_dir,
        manifests_dir=manifests_dir,
        data_contract=data_contract,
        cors_origins=_split_origins(cors),
        max_page_size=int(os.environ.get("PERP_LAB_MAX_PAGE_SIZE", "500")),
        eda_figures_dir=Path(
            os.environ.get("PERP_LAB_EDA_FIGURES_DIR", "reports/figures/eda")
        ).resolve(),
        eda_metadata_dir=Path(
            os.environ.get("PERP_LAB_EDA_METADATA_DIR", "reports/metadata/eda")
        ).resolve(),
        study_dashboard_path=Path(
            os.environ.get(
                "PERP_LAB_STUDY_DASHBOARD",
                "reports/study_closure/study_dashboard.json",
            )
        ).resolve(),
        environment=os.environ.get("PERP_LAB_ENV", "development"),
    )
