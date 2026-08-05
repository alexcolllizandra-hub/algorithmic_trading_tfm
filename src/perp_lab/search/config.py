"""Strict Pydantic configuration for a search / comparison run.

Parameter *spaces*, costs, walk-forward geometry, objective weights and the
GA/RS budget parity all originate from the validated ``ExperimentConfig``; this
model only selects the algorithm, family, data source and run-level overrides
(chiefly the small geometry used for offline smoke runs). Unknown keys are
rejected (``extra="forbid"``).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator


class _Strict(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class GASettings(_Strict):
    population_size: int = Field(default=100, ge=2)
    generations: int = Field(default=20, ge=1)
    crossover_rate: float = Field(default=0.7, ge=0, le=1)
    mutation_rate: float = Field(default=0.2, ge=0, le=1)
    elitism: int = Field(default=1, ge=0)
    tournament_size: int = Field(default=3, ge=2)

    @model_validator(mode="after")
    def _elitism_below_population(self) -> GASettings:
        if self.elitism >= self.population_size:
            raise ValueError("ga.elitism must be smaller than ga.population_size.")
        return self

    @property
    def budget(self) -> int:
        return self.population_size * self.generations


class WalkForwardOverride(_Strict):
    """Small fold geometry for offline smoke runs (in days of the primary bar)."""

    initial_train_days: int = Field(ge=1)
    validation_days: int = Field(ge=1)
    test_days: int = Field(ge=1)
    step_days: int = Field(ge=1)
    min_folds: int = Field(default=1, ge=1)
    max_folds: int | None = Field(default=None, ge=1)


class ObjectiveOverride(_Strict):
    w_sharpe: float | None = None
    w_max_drawdown: float | None = None
    w_turnover: float | None = None
    w_fold_instability: float | None = None
    w_complexity: float | None = None
    min_trades_total: int | None = Field(default=None, ge=0)
    min_trades_per_fold: int | None = Field(default=None, ge=0)
    max_drawdown_limit: float | None = Field(default=None, gt=0)

    def as_overrides(self) -> dict[str, Any]:
        return {k: v for k, v in self.model_dump().items() if v is not None}


class SearchRunConfig(_Strict):
    """A full search-run contract (validated before any computation)."""

    experiment_config: Path = Path("configs/experiment.yaml")
    data_contract: Path = Path("configs/data_contract.yaml")
    family: Literal["momentum", "breakout", "mean_reversion"]
    algorithm: Literal["random_search", "genetic_algorithm", "comparison"] = "comparison"
    symbol: str = "BTCUSDT"
    timeframe: str = "1h"
    seed: int | None = None
    regime_model: Literal["threshold", "kmeans", "gmm"] = "threshold"
    require_funding: bool = False
    synthetic: bool = False
    synthetic_bars: int = Field(default=1500, ge=200)
    label: str = "research"
    max_folds: int | None = Field(default=None, ge=1)
    ga: GASettings = GASettings()
    walk_forward_override: WalkForwardOverride | None = None
    objective: ObjectiveOverride | None = None

    @model_validator(mode="after")
    def _synthetic_needs_geometry(self) -> SearchRunConfig:
        if self.synthetic and self.walk_forward_override is None:
            raise ValueError(
                "synthetic search runs require a walk_forward_override (the 730-day "
                "research geometry does not fit a short synthetic series)."
            )
        return self

    @model_validator(mode="after")
    def _synthetic_must_be_labelled_smoke(self) -> SearchRunConfig:
        """Research configs must reject synthetic fixtures.

        Synthetic data is allowed only for tests and explicitly labelled smoke
        configurations. The label must announce it (``smoke``/``synthetic``/
        ``test``) so a synthetic run can never be mistaken for a research result.
        """
        if self.synthetic:
            marker = self.label.lower()
            if not any(tag in marker for tag in ("smoke", "synthetic", "test")):
                raise ValueError(
                    "synthetic=true is only permitted for explicitly labelled smoke/test "
                    "configs; set label to include 'smoke', 'synthetic' or 'test'. "
                    "Research configurations must use real historical data (synthetic=false)."
                )
        return self

    @property
    def budget(self) -> int:
        return self.ga.budget


def load_search_config(path: str | Path) -> SearchRunConfig:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    return SearchRunConfig.model_validate(raw)
