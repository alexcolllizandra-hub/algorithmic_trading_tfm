"""Gate S1-B pilot report: viability gating, artifact reading and DEV-ONLY framing."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import polars as pl
import pytest

from perp_lab.reporting.s1_pilot import (
    ENGINES,
    PRIMARY_ENGINE,
    S1PilotError,
    build_s1_pilot_report,
    load_engine_pilot,
    render_s1_pilot_markdown,
    write_s1_pilot_report,
)

START = datetime(2024, 1, 1, tzinfo=UTC)
N_FOLDS = 3
BARS_PER_FOLD = 48


def _winner(fold: int, *, total_return: float, sharpe: float, trades: float) -> dict[str, object]:
    return {
        "fold": fold,
        "winner": f"cand-{fold}",
        "val_sharpe": 0.5,
        "params": {"lookback": 24},
        "selection_basis": "validation_only",
        "selection_fingerprint": f"fp{fold}",
        "frozen_before_test": True,
        "test_metrics": {
            "sharpe": sharpe,
            "total_return": total_return,
            "max_drawdown": -0.1,
            "n_trades": trades,
            "ann_return": total_return * 4,
        },
    }


def _write_run(
    root: Path,
    family: str,
    *,
    mean_bar_return: float,
    trades: float = 40.0,
    n_feasible: int = 30,
    seed: int = 0,
    winners_override: dict[str, list[dict[str, object]]] | None = None,
) -> Path:
    run_dir = root / f"search_{family}_20260101T000000Z_aaaaaa"
    run_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)

    summary = {
        "run_kind": "search",
        "label": f"s1b_pilot_{family}_DEV_ONLY_not_holdout",
        "family": family,
        "symbol": "BTCUSDT",
        "timeframe": "1h",
        "seed": 42,
        "budget": 25,
        "n_folds": N_FOLDS,
        "budget_parity": {"equal_effective_budget": True},
        "methods": {
            engine: {
                "algorithm": engine,
                "n_unique_candidates": 75,
                "n_feasible": n_feasible,
                "counters": {"evaluated": 75, "invalid": 0, "duplicate": 0, "cached": 0},
            }
            for engine in ENGINES
        },
    }
    (run_dir / "comparison_summary.json").write_text(json.dumps(summary), encoding="utf-8")

    folds = {
        "folds": [
            {
                "index": k,
                "val_start": (START + timedelta(hours=k * 200)).isoformat(),
                "val_end": (START + timedelta(hours=k * 200 + 100)).isoformat(),
            }
            for k in range(N_FOLDS)
        ]
    }
    (run_dir / "folds.json").write_text(json.dumps(folds), encoding="utf-8")

    for engine in ENGINES:
        winners = (winners_override or {}).get(engine) or [
            _winner(k, total_return=mean_bar_return * BARS_PER_FOLD, sharpe=1.0, trades=trades)
            for k in range(N_FOLDS)
        ]
        (run_dir / f"{engine}_fold_winners.json").write_text(json.dumps(winners), encoding="utf-8")

        ledger = pl.DataFrame(
            {
                "fold_index": np.repeat(np.arange(N_FOLDS), 25),
                "status": ["EVALUATED"] * (N_FOLDS * 25),
                "mean_val_sharpe": rng.normal(0.0, 1.0, size=N_FOLDS * 25),
                "fitness": rng.normal(0.0, 1.0, size=N_FOLDS * 25),
            }
        )
        ledger.write_parquet(run_dir / f"{engine}_candidates.parquet")

        for k in range(N_FOLDS):
            times = [START + timedelta(hours=k * BARS_PER_FOLD + i) for i in range(BARS_PER_FOLD)]
            returns = mean_bar_return + rng.normal(0.0, 1e-4, size=BARS_PER_FOLD)
            pl.DataFrame({"open_time": times, "net_return": returns}).write_parquet(
                run_dir / f"{engine}_fold{k}_test_equity.parquet"
            )
    return run_dir


@pytest.fixture
def four_families(tmp_path: Path) -> dict[str, Path]:
    return {
        family: _write_run(tmp_path, family, mean_bar_return=value, seed=i)
        for i, (family, value) in enumerate(
            {
                "mtf_trend_consensus": -1e-4,
                "funding_reversal": 5e-5,
                "intraday_seasonality": -2e-4,
                "xasset_spread_reversion": -3e-4,
            }.items()
        )
    }


def test_a_healthy_run_is_mechanically_viable(tmp_path: Path) -> None:
    run_dir = _write_run(tmp_path, "funding_reversal", mean_bar_return=1e-5)
    pilot = load_engine_pilot(run_dir, PRIMARY_ENGINE)
    assert pilot.mechanically_viable
    assert pilot.viability_failures == ()
    assert pilot.n_folds == N_FOLDS
    assert pilot.total_test_trades == 120.0
    assert pilot.oos_bars == N_FOLDS * BARS_PER_FOLD
    assert pilot.median_test_sharpe == pytest.approx(1.0)


def test_a_family_that_cannot_trade_is_flagged(tmp_path: Path) -> None:
    run_dir = _write_run(tmp_path, "intraday_seasonality", mean_bar_return=0.0, trades=1.0)
    pilot = load_engine_pilot(run_dir, PRIMARY_ENGINE)
    assert not pilot.mechanically_viable
    assert any("out-of-sample trades" in reason for reason in pilot.viability_failures)


def test_a_family_with_no_feasible_candidate_is_flagged(tmp_path: Path) -> None:
    run_dir = _write_run(tmp_path, "mtf_trend_consensus", mean_bar_return=0.0, n_feasible=0)
    pilot = load_engine_pilot(run_dir, PRIMARY_ENGINE)
    assert not pilot.mechanically_viable
    assert "no feasible candidate in any fold" in pilot.viability_failures


def test_a_winner_not_frozen_before_its_test_slice_is_a_failed_invariant(tmp_path: Path) -> None:
    broken = _winner(0, total_return=0.01, sharpe=1.0, trades=40.0)
    broken["frozen_before_test"] = False
    override = {engine: [broken] for engine in ENGINES}
    run_dir = _write_run(
        tmp_path, "funding_reversal", mean_bar_return=1e-5, winners_override=override
    )
    pilot = load_engine_pilot(run_dir, PRIMARY_ENGINE)
    assert not pilot.mechanically_viable
    assert "a fold winner was not frozen before its test slice" in pilot.viability_failures


def test_a_fold_without_a_winner_is_recorded_not_dropped(tmp_path: Path) -> None:
    winners = [_winner(0, total_return=0.01, sharpe=1.0, trades=40.0)]
    winners.append(
        {
            "fold": 1,
            "winner": None,
            "reason": "no feasible candidate",
            "selection_basis": "validation_only",
        }
    )
    override = dict.fromkeys(ENGINES, winners)
    run_dir = _write_run(
        tmp_path, "funding_reversal", mean_bar_return=1e-5, winners_override=override
    )
    pilot = load_engine_pilot(run_dir, PRIMARY_ENGINE)
    assert pilot.folds_without_winner == 1
    assert pilot.mechanically_viable, "an infeasible fold is an outcome, not an invariant breach"


def test_missing_artifacts_fail_loudly(tmp_path: Path) -> None:
    run_dir = _write_run(tmp_path, "funding_reversal", mean_bar_return=1e-5)
    (run_dir / "folds.json").unlink()
    with pytest.raises(S1PilotError, match="missing required artifact"):
        load_engine_pilot(run_dir, PRIMARY_ENGINE)


def test_an_unknown_engine_is_refused(tmp_path: Path) -> None:
    run_dir = _write_run(tmp_path, "funding_reversal", mean_bar_return=1e-5)
    with pytest.raises(S1PilotError, match="no results for engine"):
        load_engine_pilot(run_dir, "grid_search")


def test_overlapping_out_of_sample_folds_are_refused(tmp_path: Path) -> None:
    run_dir = _write_run(tmp_path, "funding_reversal", mean_bar_return=1e-5)
    duplicate = pl.read_parquet(run_dir / f"{PRIMARY_ENGINE}_fold0_test_equity.parquet")
    duplicate.write_parquet(run_dir / f"{PRIMARY_ENGINE}_fold1_test_equity.parquet")
    with pytest.raises(S1PilotError, match="overlap in time"):
        load_engine_pilot(run_dir, PRIMARY_ENGINE)


# --------------------------------------------------------------------------- #
# Batch report
# --------------------------------------------------------------------------- #


def test_the_report_declares_the_holdout_untouched_and_its_gating_rule(
    four_families: dict[str, Path],
) -> None:
    report = build_s1_pilot_report(four_families)
    assert report["holdout_accessed"] is False
    assert report["primary_engine"] == "random_search"
    assert "never for weak performance" in report["gating_rule"]
    assert "DEVELOPMENT-ONLY" in report["status"]
    assert sorted(report["families"]) == sorted(four_families)


def test_every_healthy_family_passes_the_viability_screen(
    four_families: dict[str, Path],
) -> None:
    report = build_s1_pilot_report(four_families)
    assert sorted(report["mechanically_viable_families"]) == sorted(four_families)


def test_a_mislabelled_run_directory_is_refused(four_families: dict[str, Path]) -> None:
    swapped = dict(four_families)
    swapped["funding_reversal"] = four_families["mtf_trend_consensus"]
    with pytest.raises(S1PilotError, match="records family"):
        build_s1_pilot_report(swapped)


def test_pbo_is_reported_as_unavailable_with_its_reason(
    four_families: dict[str, Path],
) -> None:
    report = build_s1_pilot_report(four_families)
    pbo = report["multiple_testing"]["probability_of_backtest_overfitting"]
    assert pbo["available"] is False
    assert "independent per outer fold" in pbo["reason"]


def test_the_family_level_snooping_tests_cover_only_between_family_selection(
    four_families: dict[str, Path],
) -> None:
    report = build_s1_pilot_report(four_families)
    snoop = report["multiple_testing"]["family_level_snooping"]
    assert snoop["available"] is True
    assert snoop["engine"] == PRIMARY_ENGINE
    assert 0.0 <= snoop["hansen_spa"]["p_value"] <= 1.0
    assert 0.0 <= snoop["white_reality_check"]["p_value"] <= 1.0
    assert "inside each family" in snoop["does_not_cover"]


def test_benjamini_hochberg_covers_every_family(four_families: dict[str, Path]) -> None:
    report = build_s1_pilot_report(four_families)
    bh = report["multiple_testing"]["benjamini_hochberg"]
    assert bh["available"] is True
    assert sorted(bh["p_values"]) == sorted(four_families)
    assert sorted(bh["rejected"]) == sorted(four_families)


def test_the_report_is_deterministic(four_families: dict[str, Path]) -> None:
    assert build_s1_pilot_report(four_families) == build_s1_pilot_report(four_families)


def test_the_markdown_says_plainly_that_nothing_is_promoted(
    four_families: dict[str, Path],
) -> None:
    markdown = render_s1_pilot_markdown(build_s1_pilot_report(four_families))
    assert "DEV-ONLY" in markdown
    assert "No family is promoted or rejected here." in markdown
    assert "PBO (CSCV) not computed" in markdown
    for family in four_families:
        assert f"`{family}`" in markdown


def test_writing_the_report_produces_both_artifacts(
    four_families: dict[str, Path], tmp_path: Path
) -> None:
    written = write_s1_pilot_report(four_families, tmp_path / "out")
    assert written["json"].exists()
    assert written["markdown"].exists()
    payload = json.loads(written["json"].read_text(encoding="utf-8"))
    assert payload["report"] == "gate_s1b_development_pilot"


def test_an_empty_batch_is_refused() -> None:
    with pytest.raises(S1PilotError, match="at least one family"):
        build_s1_pilot_report({})
