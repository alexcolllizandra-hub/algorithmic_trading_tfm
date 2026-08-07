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
    # Fair budget: both capped at the same number of unique evaluations.
    for outcome in res.outcomes.values():
        assert outcome.counters.evaluated <= cfg.budget
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


def test_both_methods_spend_exactly_the_same_evaluation_budget(tmp_path) -> None:
    """RS must not silently receive more evaluations than the GA can perform.

    The GA's reachable count is population + (generations-1)*(population-elitism);
    the shared budget is defined as that number, so both must land on it exactly.
    """
    cfg = _smoke_cfg()
    res = run_search(cfg, write_artifacts=False)
    evaluated = {name: o.counters.evaluated for name, o in res.outcomes.items()}
    assert evaluated["random_search"] == evaluated["genetic_algorithm"]
    assert evaluated["random_search"] <= cfg.budget
    parity = res.summary["budget_parity"]
    assert parity["equal_effective_budget"] is True
    assert parity["evaluated_per_method"] == evaluated


def test_out_of_sample_artifacts_are_written_for_every_method(tmp_path) -> None:
    """Both methods persist per-fold OOS test series, not only the winning one.

    Without this the concatenated walk-forward OOS evidence can be rebuilt for a
    single method and the RS-vs-GA comparison stops being auditable.
    """
    cfg = _smoke_cfg()
    paths = Paths(artifacts_root=tmp_path / "artifacts")
    res = run_search(cfg, paths=paths, write_artifacts=True)
    assert res.run_dir is not None
    for method in ("random_search", "genetic_algorithm"):
        scored = [w for w in res.fold_winners[method] if w.get("winner") is not None]
        equities = sorted(res.run_dir.glob(f"{method}_fold*_test_equity.parquet"))
        assert len(equities) == len(scored), f"{method} is missing per-fold OOS equity"


def test_summary_records_walk_forward_coverage(tmp_path) -> None:
    """The summary must state the OOS span, so one window cannot look complete."""
    cfg = _smoke_cfg()
    res = run_search(cfg, write_artifacts=False)
    cov = res.summary["walk_forward_coverage"]
    assert cov["n_folds"] == res.summary["n_folds"]
    assert cov["oos_test_days"] == cov["n_folds"] * cov["test_days"]
    assert cov["max_folds_cap"] == 2
    assert cov["oos_test_start"] < cov["oos_test_end"]


def test_run_search_is_reproducible(tmp_path) -> None:
    cfg = _smoke_cfg()
    r1 = run_search(cfg, write_artifacts=False)
    r2 = run_search(cfg, write_artifacts=False)
    for name in r1.outcomes:
        o1, o2 = r1.outcomes[name], r2.outcomes[name]
        assert [c.candidate_id for c in o1.candidates] == [c.candidate_id for c in o2.candidates]
        assert o1.convergence == o2.convergence
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
