"""EXPLORATORY regime-conditioned re-analysis of already-rejected families."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import polars as pl

from perp_lab.reporting.regime_conditioned import (
    MIN_CELL_BARS,
    RegimeCell,
    _unit_ledger_with_regime,
    best_conditional_candidate,
    causal_trend_labels,
    correct_within_block,
    family_regime_series,
    regime_cells,
)
from perp_lab.reporting.study_closure import StudyUnit

START = datetime(2024, 1, 1, tzinfo=UTC)


def _write_ledger(
    run_dir: Path, fold: int, returns: list[float], regimes: list[str], offset: int
) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    times = [START + timedelta(hours=offset + i) for i in range(len(returns))]
    pl.DataFrame(
        {
            "open_time": times,
            "net_return": returns,
            "regime": regimes,
            "regime_id": [0] * len(returns),
        }
    ).with_columns(pl.col("open_time").cast(pl.Datetime("ms", "UTC"))).write_parquet(
        run_dir / f"random_search_fold{fold}_test_equity.parquet"
    )


def _unit(
    run_dir: Path, family: str, seed: int, returns: list[float], regimes: list[str]
) -> StudyUnit:
    _write_ledger(run_dir, 0, returns, regimes, offset=0)
    return StudyUnit("R3", family, "BTCUSDT", seed, "random_search", run_dir)


def test_the_ledgers_regime_label_is_carried_through(tmp_path: Path) -> None:
    unit = _unit(tmp_path / "u", "breakout", 1, [0.01, -0.02], ["low", "high"])
    ledger = _unit_ledger_with_regime(unit.run_dir, "random_search")
    assert ledger["regime"].to_list() == ["low", "high"]


def test_a_ledger_without_regime_labels_is_skipped_not_guessed(tmp_path: Path) -> None:
    run_dir = tmp_path / "bare"
    run_dir.mkdir()
    pl.DataFrame(
        {"open_time": [START], "net_return": [0.01]},
    ).with_columns(pl.col("open_time").cast(pl.Datetime("ms", "UTC"))).write_parquet(
        run_dir / "random_search_fold0_test_equity.parquet"
    )
    assert _unit_ledger_with_regime(run_dir, "random_search").height == 0


def test_seeds_are_averaged_and_the_regime_label_survives(tmp_path: Path) -> None:
    units = [
        _unit(tmp_path / "a", "breakout", 1, [0.02, 0.04], ["low", "high"]),
        _unit(tmp_path / "b", "breakout", 2, [0.00, 0.00], ["low", "high"]),
    ]
    series = family_regime_series(units, symbol="BTCUSDT")
    frame = series["breakout"]
    assert frame["net_return"].to_list() == [0.01, 0.02]
    assert frame["regime"].to_list() == ["low", "high"]


def test_the_trend_label_never_uses_a_bar_that_had_not_happened_yet() -> None:
    # Truncation invariance: labels computed on a prefix must equal the labels the
    # full sample assigns to those same bars. A full-sample quantile would fail
    # this, which is precisely why the EDA tagger's volatility buckets are unused.
    rng = np.random.default_rng(7)
    n = 600
    prices = 100.0 * np.exp(np.cumsum(rng.normal(0.0, 0.01, size=n)))
    bars = pl.DataFrame(
        {
            "open_time": [START + timedelta(hours=i) for i in range(n)],
            "close": prices,
        }
    ).with_columns(pl.col("open_time").cast(pl.Datetime("ms", "UTC")))

    full = causal_trend_labels(bars)
    prefix = causal_trend_labels(bars.head(400))
    merged = prefix.join(full, on="open_time", how="inner", suffix="_full")
    assert merged.height == 400
    assert merged["trend_regime"].to_list() == merged["trend_regime_full"].to_list()


def test_both_state_dimensions_are_reported_when_trend_labels_are_supplied(
    tmp_path: Path,
) -> None:
    units = [_unit(tmp_path / "a", "breakout", 1, [0.01, -0.01], ["low", "high"])]
    series = family_regime_series(units, symbol="BTCUSDT")
    trend = pl.DataFrame(
        {"open_time": [START, START + timedelta(hours=1)], "trend_regime": ["up", "down"]}
    ).with_columns(pl.col("open_time").cast(pl.Datetime("ms", "UTC")))
    cells = regime_cells(series, {"breakout": "R3"}, trend=trend)
    assert {c.dimension for c in cells} == {"volatility", "trend"}
    assert {c.regime for c in cells} == {"low", "high", "up", "down"}


def test_only_the_volatility_dimension_appears_without_trend_labels(tmp_path: Path) -> None:
    units = [_unit(tmp_path / "a", "breakout", 1, [0.01, -0.01], ["low", "high"])]
    series = family_regime_series(units, symbol="BTCUSDT")
    cells = regime_cells(series, {"breakout": "R3"})
    assert {c.dimension for c in cells} == {"volatility"}


def _cell(name: str, p: float | None, sharpe: float = 1.0, bars: int = 1000) -> RegimeCell:
    return RegimeCell("fam", "R3", "volatility", name, bars, 0.5, 0.0, 0.0, sharpe, p)


def test_cells_too_small_to_support_a_claim_are_excluded_from_the_correction() -> None:
    cells = [_cell("low", 0.01), _cell("high", None, bars=MIN_CELL_BARS - 1)]
    correction = correct_within_block(cells)
    assert correction["n_cells"] == 2
    assert correction["n_testable_cells"] == 1
    assert correction["n_excluded_small_cells"] == 1


def test_conditioning_is_corrected_over_the_whole_block_not_cell_by_cell() -> None:
    # A p-value that would clear 0.05 on its own must not clear it once the other
    # slices that were also examined are counted.
    alone = correct_within_block([_cell("low", 0.02)])
    in_block = correct_within_block([_cell("low", 0.02)] + [_cell(f"r{i}", 0.6) for i in range(40)])
    assert alone["holm_bonferroni"]["n_rejected"] == 1
    assert in_block["holm_bonferroni"]["n_rejected"] == 0


def test_no_candidate_is_offered_when_nothing_survives() -> None:
    cells = [_cell("low", 0.4), _cell("high", 0.6)]
    assert best_conditional_candidate(cells, correct_within_block(cells)) is None


def test_the_strongest_surviving_cell_is_offered_as_a_hypothesis() -> None:
    cells = [_cell("low", 1e-6, sharpe=0.5), _cell("high", 1e-8, sharpe=2.0)]
    correction = correct_within_block(cells)
    candidate = best_conditional_candidate(cells, correction)
    assert candidate is not None
    assert candidate["label"] == "fam|volatility|high"
    assert candidate["adjusted_p_value"] <= 0.05
