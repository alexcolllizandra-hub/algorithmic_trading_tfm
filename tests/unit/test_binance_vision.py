import io
import zipfile
from datetime import UTC, datetime

from perp_lab.data.providers.binance_vision import (
    BinanceVisionBulkProvider,
    _month_iter,
    monthly_funding_relpath,
    monthly_kline_relpath,
    monthly_mark_relpath,
)

_RAW_CSV = (
    "1609459200000,29000.0,29100.0,28900.0,29050.0,10.5,"
    "1609459499999,304500.0,42,5.2,150000.0,0\n"
    "1609459500000,29050.0,29200.0,29000.0,29180.0,8.0,"
    "1609459799999,232000.0,30,4.0,116000.0,0\n"
)


def test_month_iter_spans_year_boundary():
    months = _month_iter(datetime(2020, 11, 1, tzinfo=UTC), datetime(2021, 2, 1, tzinfo=UTC))
    assert months == [(2020, 11), (2020, 12), (2021, 1), (2021, 2)]


def test_monthly_kline_relpath():
    path = monthly_kline_relpath("um", "BTCUSDT", "5m", 2021, 1)
    assert path == "data/futures/um/monthly/klines/BTCUSDT/5m/BTCUSDT-5m-2021-01.zip"


def test_monthly_mark_relpath():
    # Mark-price archives reuse the klines file naming; only the directory differs.
    path = monthly_mark_relpath("um", "ETHUSDT", "5m", 2020, 12)
    assert path == "data/futures/um/monthly/markPriceKlines/ETHUSDT/5m/ETHUSDT-5m-2020-12.zip"


def test_monthly_funding_relpath():
    path = monthly_funding_relpath("um", "BTCUSDT", 2021, 3)
    assert path == "data/futures/um/monthly/fundingRate/BTCUSDT/BTCUSDT-fundingRate-2021-03.zip"


def test_parse_klines_from_csv_bytes():
    provider = BinanceVisionBulkProvider(verify_checksums=False)
    df = provider._parse_klines(_RAW_CSV.encode())
    assert df.columns[:5] == ["open_time", "open", "high", "low", "close"]
    assert df.height == 2
    assert df["trade_count"].to_list() == [42, 30]
    assert df["open_time"][0] == datetime(2021, 1, 1, 0, 0, tzinfo=UTC)


def test_read_inner_csv():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("BTCUSDT-5m-2021-01.csv", _RAW_CSV)
    csv_bytes = BinanceVisionBulkProvider._read_inner_csv(buf.getvalue())
    assert csv_bytes.decode().startswith("1609459200000")


def test_has_header_detection():
    assert BinanceVisionBulkProvider._has_header(b"open_time,open,high\n1,2,3")
    assert not BinanceVisionBulkProvider._has_header(_RAW_CSV.encode())
