"""Executable experiment pipelines (orchestration lives here, not in the CLI)."""

from perp_lab.experiments.pipeline import (
    DevPipelineResult,
    run_dev_pipeline,
    synthetic_klines,
)

__all__ = ["DevPipelineResult", "run_dev_pipeline", "synthetic_klines"]
