"""DataLake loading and holdout-exclusion guarantees."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import polars as pl
import pytest

from perp_lab.config.models import ContractSpec, DataContract, HoldoutSpec, Paths
from perp_lab.eda.datasets import DataLake, HoldoutLeakageError, assert_no_holdout


def _contract() -> DataContract:
    return DataContract(
        symbols=(ContractSpec(symbol="BTCUSDT", listing_date=date(2020, 12, 30)),),
        cutoff_date=date(2021, 1, 4),
        holdout=HoldoutSpec(start=date(2021, 1, 3)),
    )


def _write_5m(paths: Paths) -> datetime:
    start = datetime(2021, 1, 1, tzinfo=UTC)
    n = 288 * 3  # three days of 5-minute bars, crossing the holdout boundary
    times = [start + timedelta(minutes=5 * i) for i in range(n)]
    df = pl.DataFrame(
        {
            "open_time": times,
            "open": [100.0] * n,
            "high": [101.0] * n,
            "low": [99.0] * n,
            "close": [100.0] * n,
            "volume": [1.0] * n,
            "quote_volume": [100.0] * n,
            "trade_count": [1] * n,
            "taker_buy_base": [0.5] * n,
            "taker_buy_quote": [50.0] * n,
        }
    ).with_columns(
        pl.col("open_time").cast(pl.Datetime("ms", "UTC")),
        pl.col("trade_count").cast(pl.Int64),
    )
    path = paths.validated_dir / "BTCUSDT" / "5m.parquet"
    path.parent.mkdir(parents=True, exist_ok=True)
    df.write_parquet(path)
    return start


def test_development_load_excludes_holdout(tmp_path):
    paths = Paths(data_root=tmp_path / "data", reports_root=tmp_path / "reports")
    _write_5m(paths)
    lake = DataLake(_contract(), paths)
    boundary = datetime(2021, 1, 3, tzinfo=UTC)

    dev = lake.load_klines("BTCUSDT", "5m", partition="development")
    assert dev.holdout_excluded is True
    assert dev.period_end is not None and dev.period_end < boundary
    assert dev.n_rows == 288 * 2  # first two days only

    hold = lake.load_klines("BTCUSDT", "5m", partition="holdout")
    assert hold.period_start is not None and hold.period_start >= boundary


def test_assert_no_holdout_raises_on_leak():
    start = datetime(2021, 1, 2, 20, 0, tzinfo=UTC)
    times = [start + timedelta(hours=i) for i in range(10)]  # crosses 2021-01-03
    df = pl.DataFrame({"open_time": times}).with_columns(
        pl.col("open_time").cast(pl.Datetime("ms", "UTC"))
    )
    with pytest.raises(HoldoutLeakageError):
        assert_no_holdout(df, datetime(2021, 1, 3, tzinfo=UTC))


def test_available_reports_missing_files(tmp_path):
    paths = Paths(data_root=tmp_path / "data", reports_root=tmp_path / "reports")
    lake = DataLake(_contract(), paths)
    status = lake.available()
    assert status["BTCUSDT:5m"] is False
