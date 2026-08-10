"""Tests for parameter perturbation around frozen fold winners."""

from __future__ import annotations

from perp_lab.config import load_experiment_config
from perp_lab.evaluation.parameter_perturbation import perturb_params
from perp_lab.search.registry import build_search_space


def test_perturb_params_produces_valid_neighbours_for_breakout() -> None:
    exp = load_experiment_config("configs/experiment.yaml")
    space = build_search_space(exp, "breakout", "BTCUSDT")
    base = {
        "channel_window": 96,
        "confirmation_bars": 2,
        "direction": "short",
        "use_regime_gate": True,
        "regime_gate": ("low", "medium"),
    }
    neighbours = perturb_params(space, base, pct=0.10)
    assert neighbours
    for values in neighbours:
        valid, _ = space.is_valid(values)
        assert valid
        assert values != base


def test_categorical_grid_moves_to_adjacent_values() -> None:
    exp = load_experiment_config("configs/experiment.yaml")
    space = build_search_space(exp, "breakout", "BTCUSDT")
    base = {
        "channel_window": 96,
        "confirmation_bars": 2,
        "direction": "long",
        "use_regime_gate": False,
        "regime_gate": ("low",),
    }
    neighbours = perturb_params(space, base, pct=0.20)
    assert neighbours
    windows = {values["channel_window"] for values in neighbours}
    assert any(w != 96 for w in windows)
