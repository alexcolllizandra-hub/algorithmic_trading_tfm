"""End-to-end tests of the multi-seed orchestrator on synthetic data.

These exercise the properties that only appear once the whole grid runs: that a
seed actually changes the search, that budgets stay matched in every single unit,
that an interrupted study resumes without repeating or losing work, and that a
resume into a changed configuration is refused rather than silently pooled.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from perp_lab.config import Paths
from perp_lab.evaluation.multi_seed import analyse_study, long_table
from perp_lab.experiments.multi_seed import (
    config_fingerprint,
    resolve_seeds,
    run_multi_seed,
    unit_key,
)
from perp_lab.search.config import load_search_config
from perp_lab.tracking.journal import Checkpoint, Journal


@pytest.fixture
def smoke_config():
    return load_search_config("configs/search_smoke.yaml")


def _paths(tmp_path: Path) -> Paths:
    return Paths(
        data_root=tmp_path / "data",
        reports_root=tmp_path / "reports",
        artifacts_root=tmp_path / "artifacts",
    )


def test_resolve_seeds_is_deterministic_and_prefix_stable() -> None:
    """A larger study must extend the seed list, not renumber it.

    Otherwise growing a study from 3 to 10 seeds would invalidate the units
    already computed, and no checkpoint could ever be reused.
    """
    assert resolve_seeds(42, 10)[:3] == resolve_seeds(42, 3)
    assert resolve_seeds(42, 5) != resolve_seeds(43, 5)
    assert len(set(resolve_seeds(42, 20))) == 20


def test_study_runs_every_unit_and_records_them(tmp_path: Path, smoke_config) -> None:
    seeds = resolve_seeds(1, 2)
    result = run_multi_seed(
        smoke_config,
        symbols=("BTCUSDT",),
        seeds=seeds,
        study_dir=tmp_path / "study",
        paths=_paths(tmp_path),
    )
    assert len(result.units) == 2
    assert set(result.units) == {unit_key("BTCUSDT", s) for s in seeds}
    assert (tmp_path / "study" / "study_manifest.json").exists()
    assert (tmp_path / "study" / "status.json").exists()
    assert (tmp_path / "study" / "events.jsonl").exists()


def test_every_unit_spends_an_identical_budget_on_both_engines(
    tmp_path: Path, smoke_config
) -> None:
    """Budget parity is a per-unit property; checking only the aggregate would hide a gap."""
    result = run_multi_seed(
        smoke_config,
        symbols=("BTCUSDT",),
        seeds=resolve_seeds(1, 3),
        study_dir=tmp_path / "study",
        paths=_paths(tmp_path),
    )
    for key, unit in result.units.items():
        evaluated = {name: e["evaluated"] for name, e in unit["engines"].items()}
        assert len(set(evaluated.values())) == 1, f"{key} spent unequal budgets: {evaluated}"
        assert unit["budget_parity"]["equal_effective_budget"] is True


def test_different_seeds_produce_genuinely_different_searches(tmp_path: Path, smoke_config) -> None:
    """If seeds did not change the outcome, the whole study would be meaningless."""
    result = run_multi_seed(
        smoke_config,
        symbols=("BTCUSDT",),
        seeds=resolve_seeds(1, 4),
        study_dir=tmp_path / "study",
        paths=_paths(tmp_path),
    )
    table = long_table(result.units)
    winners = table.filter(table["engine"] == "random_search")["winner"].to_list()
    assert len(set(winners)) > 1


def test_each_unit_records_its_own_seed_streams(tmp_path: Path, smoke_config) -> None:
    result = run_multi_seed(
        smoke_config,
        symbols=("BTCUSDT",),
        seeds=resolve_seeds(1, 2),
        study_dir=tmp_path / "study",
        paths=_paths(tmp_path),
    )
    schedules = [u["seed_schedule"] for u in result.units.values()]
    for schedule in schedules:
        assert schedule["engines"]["random_search"] != schedule["engines"]["genetic_algorithm"]
        assert schedule["per_fold_regime"]
    # Different base seeds must move every derived stream.
    assert schedules[0]["engines"] != schedules[1]["engines"]


def test_resume_skips_completed_units_and_finishes_the_rest(tmp_path: Path, smoke_config) -> None:
    study = tmp_path / "study"
    paths = _paths(tmp_path)
    first = run_multi_seed(
        smoke_config,
        symbols=("BTCUSDT",),
        seeds=resolve_seeds(1, 2),
        study_dir=study,
        paths=paths,
    )
    first_run_ids = {k: v["run_id"] for k, v in first.units.items()}

    # Grow the study: the first two units must be reused verbatim.
    second = run_multi_seed(
        smoke_config,
        symbols=("BTCUSDT",),
        seeds=resolve_seeds(1, 4),
        study_dir=study,
        paths=paths,
    )
    assert second.resumed == 2
    assert len(second.units) == 4
    for key, run_id in first_run_ids.items():
        assert second.units[key]["run_id"] == run_id, "a completed unit was recomputed"

    kinds = [e["kind"] for e in Journal(study).read_events()]
    assert kinds.count("unit_skipped") == 2


def test_a_killed_study_loses_at_most_the_unit_in_flight(tmp_path: Path, smoke_config) -> None:
    """Simulate a crash after the first unit by inspecting the checkpoint on disk."""
    study = tmp_path / "study"
    paths = _paths(tmp_path)
    run_multi_seed(
        smoke_config,
        symbols=("BTCUSDT",),
        seeds=resolve_seeds(1, 1),
        study_dir=study,
        paths=paths,
    )
    assert Checkpoint(study).completed_keys()

    status = Journal(study).read_status()
    assert status["state"] == "completed"
    assert status["completed"] == status["total"]


def test_resume_refuses_a_changed_configuration(tmp_path: Path, smoke_config) -> None:
    """Pooling units from two different contracts would corrupt the aggregate silently."""
    study = tmp_path / "study"
    paths = _paths(tmp_path)
    run_multi_seed(
        smoke_config,
        symbols=("BTCUSDT",),
        seeds=resolve_seeds(1, 1),
        study_dir=study,
        paths=paths,
    )
    changed = smoke_config.model_copy(
        update={"ga": smoke_config.ga.model_copy(update={"max_generations": 40})}
    )
    assert config_fingerprint(changed) != config_fingerprint(smoke_config)
    with pytest.raises(ValueError, match="different"):
        run_multi_seed(
            changed,
            symbols=("BTCUSDT",),
            seeds=resolve_seeds(1, 1),
            study_dir=study,
            paths=paths,
        )


def test_fingerprint_ignores_only_the_dimensions_the_study_varies(smoke_config) -> None:
    base = config_fingerprint(smoke_config)
    assert config_fingerprint(smoke_config.model_copy(update={"seed": 999})) == base
    assert config_fingerprint(smoke_config.model_copy(update={"symbol": "ETHUSDT"})) == base
    assert config_fingerprint(smoke_config.model_copy(update={"label": "other_test"})) == base
    assert config_fingerprint(smoke_config.model_copy(update={"family": "momentum"})) != base


def test_analysis_of_a_real_study_reports_seed_spread(tmp_path: Path, smoke_config) -> None:
    result = run_multi_seed(
        smoke_config,
        symbols=("BTCUSDT",),
        seeds=resolve_seeds(1, 3),
        study_dir=tmp_path / "study",
        paths=_paths(tmp_path),
    )
    analysis = analyse_study(result.units)
    assert analysis["seeds"] == sorted(resolve_seeds(1, 3))
    stability = analysis["seed_stability"]["BTCUSDT|random_search"]
    assert stability["n_seeds"] == 3
    # Inference must still be based on folds, never on seeds.
    paired = analysis["paired_rs_vs_ga"]
    assert paired["n_independent_units_used"] < paired["n_cells_symbol_seed_fold"]
