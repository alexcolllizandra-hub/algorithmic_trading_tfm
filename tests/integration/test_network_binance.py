"""Opt-in network test hitting data.binance.vision.

Run explicitly with:  uv run pytest -m network
Skipped by default:    uv run pytest -m "not network"
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from perp_lab.data.providers.binance_vision import BinanceVisionBulkProvider

pytestmark = pytest.mark.network


def test_download_one_month_of_btc_5m():
    provider = BinanceVisionBulkProvider(verify_checksums=True)
    with provider:
        df = provider.fetch_klines(
            "BTCUSDT",
            "5m",
            datetime(2021, 1, 1, tzinfo=UTC),
            datetime(2021, 2, 1, tzinfo=UTC),
        )
    # January 2021 has 31 days => 31 * 288 five-minute bars.
    assert df.height == 31 * 288
    assert df["open_time"].min() == datetime(2021, 1, 1, tzinfo=UTC)
