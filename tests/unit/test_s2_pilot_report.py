"""Gate S2-B pilot report: the partial-signal rule and the DEV-ONLY framing.

The report is allowed to make exactly one decision, so the tests concentrate on
it: a single lucky seed must not fire the criterion, a family that fires on a
majority of seeds must, and every performance number must stay descriptive.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import polars as pl
import pytest

from perp_lab.reporting.s1_pilot import ENGINES, PRIMARY_ENGINE
from perp_lab.reporting.s2_pilot import (
    MIN_SEEDS_FOR_PARTIAL_SIGNAL,
    S2PilotError,
    build_arm,
    build_s2_pilot_report,
    load_pilot_index,
    render_s2_pilot_markdown,
    write_s2_pilot_report,
)

START = datetime(2024, 1, 1, tzinfo=UTC)
FAMILIES = ("taker_flow_extreme", "illiquidity_reversion", "flow_price_divergence")
SEEDS = (42, 43, 44)
N_FOLDS = 3
BARS_PER_FOLD = 48


def _winner(fold: int, *, total_return: float, trades: float) -> dict[str, Any]:
    return {
        "fold": fold,
        "winner": f"cand-{fold}",
        "val_sharpe": 0.5,
        "params": {"holding_bars": 6},
        "selection_basis": "validation_only",
        "selection_fingerprint": f"fp{fold}",
        "frozen_before_test": True,
        "test_metrics": {
            "sharpe": 1.0 if total_return > 0 else -1.0,
            "total_return": total_return,
            "max_drawdown": -0.1,
            "n_trades": trades,
            "ann_return": total_return * 4,
        },
    }


def _write_run(
    root: Path,
    *,
    family: str,
    symbol: str,
    seed: int,
    mean_bar_return: float,
    positive_folds: int,
    trades: float = 40.0,
) -> Path:
    """One completed S2-B run directory, with `positive_folds` winning folds."""
    run_dir = root / f"search_{family}_{symbol}_{seed}"
    run_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)

    summary = {
        "run_kind": "search",
        "label": f"s2b_pilot_{family}_{symbol}_seed{seed}_DEV_ONLY_not_holdout",
        "family": family,
        "symbol": symbol,
        "timeframe": "1h",
        "seed": seed,
        "budget": 25,
        "n_folds": N_FOLDS,
        "budget_parity": {"equal_effective_budget": True},
        "methods": {
            engine: {
                "algorithm": engine,
                "n_unique_candidates": 75,
                "n_feasible": 30,
                "counters": {"evaluated": 75, "invalid": 0, "duplicate": 0, "cached": 0},
            }
            for engine in ENGINES
        },
    }
    (run_dir / "comparison_summary.json").write_text(json.dumps(summary), encoding="utf-8")
    (run_dir / "folds.json").write_text(
        json.dumps(
            {
                "folds": [
                    {
                        "index": k,
                        "val_start": (START + timedelta(hours=k * 200)).isoformat(),
                        "val_end": (START + timedelta(hours=k * 200 + 100)).isoformat(),
                    }
                    for k in range(N_FOLDS)
                ]
            }
        ),
        encoding="utf-8",
    )

    for engine in ENGINES:
        winners = [
            _winner(
                k,
                total_return=abs(mean_bar_return) * BARS_PER_FOLD
                if k < positive_folds
                else -abs(mean_bar_return) * BARS_PER_FOLD,
                trades=trades,
            )
            for k in range(N_FOLDS)
        ]
        (run_dir / f"{engine}_fold_winners.json").write_text(json.dumps(winners), encoding="utf-8")

        pl.DataFrame(
            {
                "fold_index": np.repeat(np.arange(N_FOLDS), 25),
                "status": ["EVALUATED"] * (N_FOLDS * 25),
                "mean_val_sharpe": rng.normal(0.0, 1.0, size=N_FOLDS * 25),
                "fitness": rng.normal(0.0, 1.0, size=N_FOLDS * 25),
            }
        ).write_parquet(run_dir / f"{engine}_candidates.parquet")

        for k in range(N_FOLDS):
            times = [START + timedelta(hours=k * BARS_PER_FOLD + i) for i in range(BARS_PER_FOLD)]
            sign = 1.0 if k < positive_folds else -1.0
            returns = sign * abs(mean_bar_return) + rng.normal(0.0, 1e-5, size=BARS_PER_FOLD)
            pl.DataFrame({"open_time": times, "net_return": returns}).write_parquet(
                run_dir / f"{engine}_fold{k}_test_equity.parquet"
            )
    return run_dir


def _batch(root: Path, winning: dict[tuple[str, int], int]) -> list[dict[str, Any]]:
    """Build every (family, asset, seed) arm; `winning` sets the positive folds."""
    arms: list[dict[str, Any]] = []
    for family in FAMILIES:
        for symbol in ("BTCUSDT", "ETHUSDT"):
            for seed in SEEDS:
                positive = winning.get((family, seed), 0) if symbol == "BTCUSDT" else 0
                run_dir = _write_run(
                    root / symbol,
                    family=family,
                    symbol=symbol,
                    seed=seed,
                    mean_bar_return=1e-4,
                    positive_folds=positive,
                )
                arms.append(
                    build_arm(
                        {
                            "family": family,
                            "symbol": symbol,
                            "seed": seed,
                            "run_dir": str(run_dir),
                        }
                    )
                )
    return arms


@pytest.fixture
def losing_batch(tmp_path: Path) -> list[dict[str, Any]]:
    return _batch(tmp_path, winning={})


# --------------------------------------------------------------------------- #
# The run index
# --------------------------------------------------------------------------- #


def test_the_run_index_is_read_in_a_stable_order(tmp_path: Path) -> None:
    payload = {
        "b": {"family": "illiquidity_reversion", "symbol": "BTCUSDT", "seed": 44, "run_dir": "x"},
        "a": {"family": "illiquidity_reversion", "symbol": "BTCUSDT", "seed": 42, "run_dir": "y"},
    }
    path = tmp_path / "index.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    assert [e["seed"] for e in load_pilot_index(path)] == [42, 44]


def test_an_empty_run_index_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "index.json"
    path.write_text("{}", encoding="utf-8")
    with pytest.raises(S2PilotError, match="lists no runs"):
        load_pilot_index(path)


# --------------------------------------------------------------------------- #
# The partial-signal criterion
# --------------------------------------------------------------------------- #


def test_a_batch_that_never_made_money_fires_nothing(losing_batch) -> None:
    signal = build_s2_pilot_report(losing_batch)["partial_signal"]
    assert signal["any_family_fires"] is False
    assert all(v["seeds_meeting_all_conditions"] == [] for v in signal["per_family_asset"])
    assert signal["engine"] == PRIMARY_ENGINE


def test_one_lucky_seed_does_not_fire_the_criterion(tmp_path: Path) -> None:
    arms = _batch(tmp_path, winning={("taker_flow_extreme", 43): N_FOLDS})
    signal = build_s2_pilot_report(arms)["partial_signal"]
    verdict = next(
        v
        for v in signal["per_family_asset"]
        if v["family"] == "taker_flow_extreme" and v["symbol"] == "BTCUSDT"
    )
    assert verdict["seeds_meeting_all_conditions"] == [43]
    assert verdict["seeds_required"] == MIN_SEEDS_FOR_PARTIAL_SIGNAL
    assert verdict["partial_signal"] is False
    assert signal["any_family_fires"] is False


def test_a_majority_of_seeds_fires_the_criterion(tmp_path: Path) -> None:
    arms = _batch(
        tmp_path,
        winning={("taker_flow_extreme", 42): N_FOLDS, ("taker_flow_extreme", 43): N_FOLDS},
    )
    signal = build_s2_pilot_report(arms)["partial_signal"]
    verdict = next(
        v
        for v in signal["per_family_asset"]
        if v["family"] == "taker_flow_extreme" and v["symbol"] == "BTCUSDT"
    )
    assert verdict["seeds_meeting_all_conditions"] == [42, 43]
    assert verdict["partial_signal"] is True
    assert signal["any_family_fires"] is True


def test_a_profit_confined_to_one_fold_does_not_count(tmp_path: Path) -> None:
    """P3: two seeds profitable, but each on a single fold, must not fire."""
    arms = _batch(
        tmp_path,
        winning={("taker_flow_extreme", 42): 1, ("taker_flow_extreme", 43): 1},
    )
    signal = build_s2_pilot_report(arms)["partial_signal"]
    verdict = next(
        v
        for v in signal["per_family_asset"]
        if v["family"] == "taker_flow_extreme" and v["symbol"] == "BTCUSDT"
    )
    assert verdict["seeds_meeting_all_conditions"] == []
    assert verdict["partial_signal"] is False


# --------------------------------------------------------------------------- #
# Report structure and framing
# --------------------------------------------------------------------------- #


def test_the_report_declares_the_holdout_untouched_and_its_place_in_the_ledger(
    losing_batch,
) -> None:
    report = build_s2_pilot_report(losing_batch)
    assert report["holdout_accessed"] is False
    assert report["development_partition_consultation"] == 4
    assert report["batch_attempt"] == 1
    assert "DEVELOPMENT-ONLY" in report["status"]
    assert sorted(report["families"]) == sorted(FAMILIES)
    assert report["seeds"] == list(SEEDS)


def test_every_family_asset_and_seed_is_reported_separately(losing_batch) -> None:
    report = build_s2_pilot_report(losing_batch)
    assert len(report["arms"]) == len(FAMILIES) * 2 * len(SEEDS)
    for arm in report["arms"]:
        assert set(arm["engines"]) == set(ENGINES)


def test_the_snooping_tests_are_reported_per_asset_and_seed(losing_batch) -> None:
    snooping = build_s2_pilot_report(losing_batch)["multiple_testing"]["family_level_snooping"]
    assert len(snooping) == 2 * len(SEEDS)
    for block in snooping:
        assert block["available"] is True
        assert block["families"] == sorted(FAMILIES)
        assert 0.0 <= block["hansen_spa"]["p_value"] <= 1.0
        assert 0.0 <= block["white_reality_check"]["p_value"] <= 1.0


def test_benjamini_hochberg_covers_every_family_on_every_asset(losing_batch) -> None:
    bh = build_s2_pilot_report(losing_batch)["multiple_testing"]["benjamini_hochberg"]
    assert sorted(bh) == ["BTCUSDT", "ETHUSDT"]
    for block in bh.values():
        assert block["available"] is True
        assert sorted(block["p_values"]) == sorted(FAMILIES)


def test_pbo_is_reported_when_supplied_and_flagged_when_not(losing_batch) -> None:
    absent = build_s2_pilot_report(losing_batch)["multiple_testing"][
        "probability_of_backtest_overfitting"
    ]
    assert absent["available"] is False

    row = {
        "family": "taker_flow_extreme",
        "symbol": "BTCUSDT",
        "n_candidates_evaluated": 120,
        "n_blocks": 8,
        "probability_of_backtest_overfitting": 0.42,
        "median_block_sharpe": -0.1,
        "development_bars": 1000,
        "scored_bars": 600,
        "regime": {
            "regime_model": "threshold",
            "regime_fit_start": "2020-01-01T00:00:00+00:00",
            "regime_fit_end": "2021-12-01T00:00:00+00:00",
            "scored_from": "2021-12-01T00:00:00+00:00",
        },
    }
    present = build_s2_pilot_report(losing_batch, pbo=[row])["multiple_testing"][
        "probability_of_backtest_overfitting"
    ]
    assert present["available"] is True
    assert present["results"] == [row]


def test_the_markdown_states_what_the_pbo_window_was(losing_batch) -> None:
    row = {
        "family": "taker_flow_extreme",
        "symbol": "BTCUSDT",
        "n_candidates_evaluated": 120,
        "n_blocks": 8,
        "probability_of_backtest_overfitting": 0.42,
        "median_block_sharpe": -0.1,
        "development_bars": 1000,
        "scored_bars": 600,
        "regime": {
            "regime_model": "threshold",
            "regime_fit_start": "2020-01-01T00:00:00+00:00",
            "regime_fit_end": "2021-12-01T00:00:00+00:00",
            "scored_from": "2021-12-01T00:00:00+00:00",
        },
    }
    markdown = render_s2_pilot_markdown(build_s2_pilot_report(losing_batch, pbo=[row]))
    assert "600 of 1000 development bars" in markdown
    assert "fitted only on the first walk-forward training window" in markdown


def test_the_markdown_says_plainly_that_nothing_is_promoted(losing_batch) -> None:
    markdown = render_s2_pilot_markdown(build_s2_pilot_report(losing_batch))
    assert "DEV-ONLY" in markdown
    assert "No family is promoted or rejected here" in markdown
    for family in FAMILIES:
        assert f"`{family}`" in markdown


def test_the_report_is_deterministic(losing_batch) -> None:
    assert build_s2_pilot_report(losing_batch) == build_s2_pilot_report(losing_batch)


def test_writing_the_report_produces_both_artifacts(losing_batch, tmp_path: Path) -> None:
    written = write_s2_pilot_report(build_s2_pilot_report(losing_batch), tmp_path / "out")
    assert written["json"].exists()
    assert written["markdown"].exists()
    payload = json.loads(written["json"].read_text(encoding="utf-8"))
    assert payload["report"] == "gate_s2b_development_pilot"


def test_an_empty_batch_is_refused() -> None:
    with pytest.raises(S2PilotError, match="at least one arm"):
        build_s2_pilot_report([])
