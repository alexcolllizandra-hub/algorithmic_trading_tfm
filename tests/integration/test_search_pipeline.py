"""End-to-end integration tests for the search framework.

Exercises the full path: synthetic bars -> features -> regimes -> strategy ->
walk-forward search -> backtester -> candidate ranking -> fold winner -> test
evaluation -> artifacts, plus a fair-budget RS/GA comparison and the CLI.
"""

from __future__ import annotations

import json

import pytest

from perp_lab import cli
from perp_lab.config import load_settings
from perp_lab.config.models import Paths
from perp_lab.search.config import (
    GASettings,
    ObjectiveOverride,
    SearchRunConfig,
    WalkForwardOverride,
)
from perp_lab.search.runner import run_search


def _smoke_cfg(**over: object) -> SearchRunConfig:
    base: dict[str, object] = {
        "family": "mean_reversion",
        "algorithm": "comparison",
        "symbol": "BTCUSDT",
        "timeframe": "1h",
        "seed": 7,
        "regime_model": "threshold",
        "require_funding": True,
        "synthetic": True,
        "synthetic_bars": 1000,
        "label": "test_smoke",
        "ga": GASettings(population_size=5, generations=2, elitism=1, tournament_size=3),
        "walk_forward_override": WalkForwardOverride(
            initial_train_days=25, validation_days=7, test_days=7, step_days=7, max_folds=2
        ),
        "objective": ObjectiveOverride(
            min_trades_total=1, min_trades_per_fold=0, max_drawdown_limit=0.99
        ),
    }
    base.update(over)
    return SearchRunConfig(**base)  # type: ignore[arg-type]


def test_run_search_comparison_end_to_end(tmp_path) -> None:
    cfg = _smoke_cfg()
    paths = Paths(artifacts_root=tmp_path / "artifacts")
    res = run_search(cfg, paths=paths, write_artifacts=True)

    assert set(res.outcomes) == {"random_search", "genetic_algorithm"}
    summary = res.summary
    total_budget = summary["total_budget_per_method"]
    # Fair budget: each outer fold gets the same evaluation cap.
    for outcome in res.outcomes.values():
        assert outcome.counters.evaluated <= total_budget
    assert summary["search_protocol"] == "independent_per_outer_fold"
    # Artifacts exist and reload.
    assert res.run_dir is not None
    summary = json.loads((res.run_dir / "comparison_summary.json").read_text())
    assert summary["comparison_metric"].startswith("aggregate out-of-sample")
    assert "EXPLORATORY" in summary["warning"]
    # Feature manifest + search space + objective all written.
    for name in ("feature_manifest.json", "search_space.json", "objective.json", "folds.json"):
        assert (res.run_dir / name).exists()
    # Fold winners were scored on test.
    fw = json.loads((res.run_dir / "genetic_algorithm_fold_winners.json").read_text())
    assert isinstance(fw, list) and len(fw) == summary["n_folds"]


def test_run_search_is_reproducible(tmp_path) -> None:
    cfg = _smoke_cfg()
    r1 = run_search(cfg, write_artifacts=False)
    r2 = run_search(cfg, write_artifacts=False)
    for name in r1.outcomes:
        w1 = r1.fold_winners[name]
        w2 = r2.fold_winners[name]
        assert [w.get("winner") for w in w1] == [w.get("winner") for w in w2]
        for fold_outcome_a, fold_outcome_b in zip(
            r1.fold_outcomes[name], r2.fold_outcomes[name], strict=True
        ):
            assert [c.candidate_id for c in fold_outcome_a.candidates] == [
                c.candidate_id for c in fold_outcome_b.candidates
            ]
            assert fold_outcome_a.convergence == fold_outcome_b.convergence
    assert r1.summary["methods"].keys() == r2.summary["methods"].keys()


def test_require_funding_uses_labelled_synthetic_fixture(tmp_path) -> None:
    cfg = _smoke_cfg(require_funding=True)
    res = run_search(cfg, write_artifacts=False)
    # With funding required and applied, at least one feasible candidate exists.
    ga = res.outcomes["genetic_algorithm"]
    assert any(c.status.value == "evaluated" for c in ga.candidates)


def test_synthetic_without_geometry_is_rejected() -> None:
    with pytest.raises(ValueError):
        SearchRunConfig(family="momentum", synthetic=True)


def test_research_config_rejects_synthetic_fixture() -> None:
    # Research label + synthetic must be rejected (guards against passing off a
    # synthetic fixture as a research result).
    with pytest.raises(ValueError, match="explicitly labelled smoke"):
        SearchRunConfig(
            family="momentum",
            synthetic=True,
            label="research",
            walk_forward_override=WalkForwardOverride(
                initial_train_days=25, validation_days=7, test_days=7, step_days=7
            ),
        )


def test_cli_search_and_summary(tmp_path, monkeypatch) -> None:
    settings = load_settings()
    redirected = settings.model_copy(update={"paths": Paths(artifacts_root=tmp_path / "art")})
    monkeypatch.setattr(cli, "load_settings", lambda: redirected)

    cfg_path = tmp_path / "smoke.yaml"
    cfg_path.write_text(
        "\n".join(
            [
                "family: mean_reversion",
                "algorithm: comparison",
                "seed: 3",
                "require_funding: true",
                "synthetic: true",
                "synthetic_bars: 900",
                "label: cli_smoke",
                "ga:",
                "  population_size: 4",
                "  generations: 2",
                "  elitism: 1",
                "  tournament_size: 3",
                "walk_forward_override:",
                "  initial_train_days: 20",
                "  validation_days: 7",
                "  test_days: 7",
                "  step_days: 7",
                "  max_folds: 2",
                "objective:",
                "  min_trades_total: 1",
                "  min_trades_per_fold: 0",
                "  max_drawdown_limit: 0.99",
            ]
        ),
        encoding="utf-8",
    )
    rc = cli.main(["search", "--config", str(cfg_path), "--log-dir", str(tmp_path / "logs")])
    assert rc == 0

    runs = list((tmp_path / "art" / "runs").iterdir())
    assert runs, "search run directory was not created"
    rc2 = cli.main(["search-summary", str(runs[0]), "--log-dir", str(tmp_path / "logs")])
    assert rc2 == 0
