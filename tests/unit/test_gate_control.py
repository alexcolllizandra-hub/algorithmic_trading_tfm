"""The gate positive control must inject exactly what it claims to inject."""

from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import polars as pl
import pytest

from perp_lab.evaluation import gate_control as gc
from perp_lab.evaluation.cost_decomposition import SCENARIOS, scenario_net


def _fake_run(root: Path, *, n_folds: int = 2, bars: int = 400, seed: int = 7) -> gc.ScaffoldRun:
    """A run directory with the persisted ledger layout and a few trades."""
    rng = np.random.default_rng(seed)
    run_dir = root / "search_fake_20260101T000000Z_abc123"
    run_dir.mkdir(parents=True)
    start = datetime(2024, 1, 1, tzinfo=UTC)
    for k in range(n_folds):
        times = [start + timedelta(hours=k * bars + i) for i in range(bars)]
        # Blocks of long / flat / short so trades and flat stretches both exist.
        position = np.zeros(bars)
        trade_id = np.full(bars, None, dtype=object)
        tid = 1
        i = 0
        while i < bars:
            length = int(rng.integers(5, 40))
            side = float(rng.choice([-1.0, 0.0, 1.0]))
            if side != 0.0:
                position[i : i + length] = side
                trade_id[i : i + length] = tid + k * 1000
                tid += 1
            i += length
        oo = rng.normal(0.0, 0.004, bars)
        turnover = np.abs(np.diff(position, prepend=0.0))
        fee = turnover * 4e-4
        slippage = turnover * 1e-4
        funding = np.where(position != 0, 1e-5, 0.0)
        gross = position * oo
        net = gross - fee - slippage - funding
        equity = np.cumprod(1.0 + net)
        ledger = pl.DataFrame(
            {
                "open_time": pl.Series(times).dt.replace_time_zone("UTC").dt.cast_time_unit("ms"),
                "asset": ["BTCUSDT"] * bars,
                "timeframe": ["1h"] * bars,
                "position": position,
                "execution_price": np.cumprod(1.0 + oo) * 100.0,
                "oo_return": oo,
                "gross_return": gross,
                "fee": fee,
                "slippage": slippage,
                "cost": fee + slippage,
                "funding_rate_in_bar": np.full(bars, 1e-5),
                "funding": funding,
                "net_return": net,
                "turnover": turnover,
                "equity": equity,
                "drawdown": equity / np.maximum.accumulate(equity) - 1.0,
                "trade_id": pl.Series(list(trade_id), dtype=pl.Int64),
                "regime": ["mid"] * bars,
            }
        )
        ledger.write_parquet(run_dir / f"random_search_fold{k}_test_equity.parquet")
        trades = (
            ledger.filter(pl.col("trade_id").is_not_null())
            .group_by("trade_id")
            .agg(
                pl.col("open_time").min().alias("entry_time"),
                pl.col("open_time").max().alias("exit_time"),
                pl.len().alias("n_bars"),
                pl.col("position").first(),
                ((pl.col("net_return") + 1.0).product() - 1.0).alias("net_return"),
                pl.col("funding").sum(),
                pl.col("cost").sum(),
            )
            .with_columns(pl.lit("signal_reverse").alias("exit_reason"))
            .sort("trade_id")
        )
        trades.write_parquet(run_dir / f"random_search_fold{k}_test_trades.parquet")
    return gc.ScaffoldRun(family="fake", symbol="BTCUSDT", seed=seed, run_dir=run_dir)


def test_calibration_hits_the_target_sharpe_in_expectation() -> None:
    sigma_p, f = 0.005, 0.4
    for target in (0.3, 0.5, 1.0, 2.0):
        mu = gc.calibrate_mu(target, sigma_p, f)
        assert gc.expected_sharpe(mu, sigma_p, f) == pytest.approx(target, abs=1e-6)
    assert gc.calibrate_mu(0.0, sigma_p, f) == 0.0
    assert gc.calibrate_mu(-0.5, sigma_p, f) < 0


def test_calibration_is_monotone_and_bounded() -> None:
    sigma_p, f = 0.004, 0.3
    mus = [gc.calibrate_mu(s, sigma_p, f) for s in (0.1, 0.5, 1.0, 3.0)]
    assert mus == sorted(mus)
    with pytest.raises(ValueError):
        gc.calibrate_mu(1e6, sigma_p, f)


def test_realised_sharpe_matches_target_on_average() -> None:
    # One 400k-bar series has an annualised-Sharpe standard error of about
    # sqrt(8760 / 400000) = 0.15, so ten independent series are averaged and
    # the tolerance is three standard errors of that mean.
    n, f, sigma_p, target = 400_000, 0.4, 0.005, 1.0
    realised = []
    for seed in range(10):
        rng = np.random.default_rng(seed)
        in_pos = rng.random(n) < f
        mu = gc.calibrate_mu(target, sigma_p, float(in_pos.mean()))
        r = np.zeros(n)
        r[in_pos] = mu + sigma_p * gc.scaled_student_t(rng, int(in_pos.sum()))
        realised.append(r.mean() / r.std(ddof=1) * math.sqrt(gc.BARS_PER_YEAR_1H))
    assert float(np.mean(realised)) == pytest.approx(target, abs=0.15)


def test_synthesize_keeps_scaffold_and_only_replaces_returns(tmp_path: Path) -> None:
    scaffold = _fake_run(tmp_path / "real")
    out = tmp_path / "synthetic"
    rng = np.random.default_rng(3)
    record = gc.synthesize_run(scaffold, out, target_sharpe=1.5, rng=rng)
    assert record["n_folds"] == 2 and record["n_bars"] == 800
    assert 0.0 < record["in_position_fraction"] < 1.0

    for k in range(2):
        real = pl.read_parquet(scaffold.run_dir / f"random_search_fold{k}_test_equity.parquet")
        syn = pl.read_parquet(out / f"random_search_fold{k}_test_equity.parquet")
        assert syn.columns == real.columns
        for col in (
            "open_time",
            "position",
            "oo_return",
            "fee",
            "slippage",
            "funding",
            "turnover",
            "trade_id",
        ):
            assert syn[col].equals(real[col]), col
        net = syn["net_return"].to_numpy()
        flat = syn["position"].to_numpy() == 0
        assert np.all(net[flat] == 0.0)
        gross_expected = (
            net + syn["fee"].to_numpy() + syn["slippage"].to_numpy() + syn["funding"].to_numpy()
        )
        np.testing.assert_allclose(syn["gross_return"].to_numpy(), gross_expected, atol=1e-15)
        np.testing.assert_allclose(syn["equity"].to_numpy(), np.cumprod(1.0 + net), rtol=1e-12)

        trades = pl.read_parquet(out / f"random_search_fold{k}_test_trades.parquet")
        real_trades = pl.read_parquet(
            scaffold.run_dir / f"random_search_fold{k}_test_trades.parquet"
        )
        assert trades.height == real_trades.height
        for tid, tr in zip(
            trades["trade_id"].to_list(), trades["net_return"].to_list(), strict=True
        ):
            bars = syn.filter(pl.col("trade_id") == tid)["net_return"].to_numpy()
            assert tr == pytest.approx(float(np.prod(1.0 + bars) - 1.0), rel=1e-12)


def test_synthesis_is_deterministic_for_a_given_seed_sequence(tmp_path: Path) -> None:
    scaffold = _fake_run(tmp_path / "real")
    a = gc.synthesize_run(
        scaffold, tmp_path / "a", target_sharpe=0.5, rng=np.random.default_rng(11)
    )
    b = gc.synthesize_run(
        scaffold, tmp_path / "b", target_sharpe=0.5, rng=np.random.default_rng(11)
    )
    assert a == b
    fa = pl.read_parquet(tmp_path / "a" / "random_search_fold0_test_equity.parquet")
    fb = pl.read_parquet(tmp_path / "b" / "random_search_fold0_test_equity.parquet")
    assert fa.equals(fb)


def test_control_task_runs_the_real_gate_code_end_to_end(tmp_path: Path) -> None:
    scaffold = _fake_run(tmp_path / "real", bars=300)
    task = {
        "family": "fake",
        "symbol": "BTCUSDT",
        "seed": 7,
        "run_dir": str(scaffold.run_dir),
        "scaffold_index": 0,
        "level_index": 0,
        "target_sharpe": 2.0,
        "rep": 0,
        "out_root": str(tmp_path / "work"),
        "master_seed": 1,
        "fee_bps": 4.0,
        "slippage_bps": 1.0,
    }
    result = gc.run_control_task(task)
    assert set(result["tests"]) >= set(gc.PROMOTION_TESTS)
    assert result["symbol"] == "BTCUSDT" and result["n_trades"] > 0
    assert not (tmp_path / "work").exists() or not any((tmp_path / "work").iterdir())
    verdicts = gc.gate_verdicts([result])
    assert verdicts[0]["verdict"] in {"PROMOTED", "REJECTED"}
    levels = gc.summarise_levels(verdicts)
    assert levels[0]["n_replications"] == 1 and 0.0 <= levels[0]["promotion_rate"] <= 1.0


def test_cost_scenarios_reprice_the_same_positions(tmp_path: Path) -> None:
    scaffold = _fake_run(tmp_path / "real")
    ledger = pl.read_parquet(scaffold.run_dir / "random_search_fold0_test_equity.parquet")
    taker = scenario_net(ledger, SCENARIOS["taker_4_1"])
    np.testing.assert_allclose(taker, ledger["net_return"].to_numpy(), atol=1e-15)
    gross = scenario_net(ledger, SCENARIOS["gross"])
    np.testing.assert_allclose(gross, ledger["gross_return"].to_numpy(), atol=1e-15)
    maker = scenario_net(ledger, SCENARIOS["maker_2_1"])
    expected = (
        ledger["gross_return"].to_numpy()
        - 0.5 * ledger["fee"].to_numpy()
        - ledger["slippage"].to_numpy()
        - ledger["funding"].to_numpy()
    )
    np.testing.assert_allclose(maker, expected, atol=1e-15)
    # Cheaper execution can never lower the net return of the same positions.
    assert np.all(scenario_net(ledger, SCENARIOS["no_fees"]) >= taker - 1e-15)
