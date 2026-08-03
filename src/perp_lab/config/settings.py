"""Settings loading: YAML files for data + operational env overrides."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from perp_lab.config.experiment import ExperimentConfig
from perp_lab.config.models import DataContract, EdaConfig, Paths

CONFIGS_DIR = Path("configs")
DEFAULT_DATA_CONTRACT = CONFIGS_DIR / "data_contract.yaml"
DEFAULT_EDA_CONFIG = CONFIGS_DIR / "eda.yaml"
DEFAULT_EXPERIMENT_CONFIG = CONFIGS_DIR / "experiment.yaml"


class AppSettings(BaseSettings):
    """Operational settings (paths, seed) with environment overrides.

    Environment variables use the ``PERP_LAB__`` prefix and ``__`` as the
    nested delimiter, e.g. ``PERP_LAB__PATHS__DATA_ROOT=/mnt/data``.
    """

    model_config = SettingsConfigDict(
        env_prefix="PERP_LAB__",
        env_nested_delimiter="__",
        env_file=".env",
        extra="ignore",
    )

    seed: int = 42
    env_name: str = "local"
    paths: Paths = Field(default_factory=Paths)


def _read_yaml(path: str | Path) -> dict[str, Any]:
    text = Path(path).read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValueError(f"Expected a mapping at the top of {path}, got {type(data)}.")
    return data


def load_data_contract(path: str | Path = DEFAULT_DATA_CONTRACT) -> DataContract:
    """Load and validate the data contract from a YAML file."""
    return DataContract.model_validate(_read_yaml(path))


def load_eda_config(path: str | Path = DEFAULT_EDA_CONFIG) -> EdaConfig:
    """Load and validate the EDA configuration from a YAML file."""
    if not Path(path).exists():
        return EdaConfig()
    return EdaConfig.model_validate(_read_yaml(path))


def load_experiment_config(path: str | Path = DEFAULT_EXPERIMENT_CONFIG) -> ExperimentConfig:
    """Load and validate the Chapter 5 experiment contract from a YAML file."""
    return ExperimentConfig.model_validate(_read_yaml(path))


def load_settings() -> AppSettings:
    """Load operational settings from environment / .env with defaults."""
    return AppSettings()
