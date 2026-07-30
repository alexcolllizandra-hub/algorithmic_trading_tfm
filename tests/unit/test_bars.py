import pytest

from perp_lab.data.bars import resample_klines


def test_resample_5m_to_15m_shape(klines_5m):
    bars = resample_klines(klines_5m, "5m", "15m")
    # 288 five-minute bars -> 96 fifteen-minute bars.
    assert bars.height == 96
    assert bars.columns == klines_5m.columns


def test_resample_ohlc_aggregation(klines_5m):
    bars = resample_klines(klines_5m, "5m", "15m")
    first_group = klines_5m.head(3)
    first_bar = bars.head(1)
    assert first_bar["open"].item() == pytest.approx(first_group["open"].item(0))
    assert first_bar["high"].item() == pytest.approx(first_group["high"].max())
    assert first_bar["low"].item() == pytest.approx(first_group["low"].min())
    assert first_bar["close"].item() == pytest.approx(first_group["close"].tail(1).item())
    assert first_bar["volume"].item() == pytest.approx(first_group["volume"].sum())


def test_resample_to_1h(klines_5m):
    bars = resample_klines(klines_5m, "5m", "1h")
    assert bars.height == 24


def test_drop_incomplete_removes_partial_bar(make_klines):
    # 4 five-minute bars: one full 15m bar (3 bars) + 1 partial.
    df = make_klines(n=4)
    kept = resample_klines(df, "5m", "15m", drop_incomplete=True)
    assert kept.height == 1
    kept_all = resample_klines(df, "5m", "15m", drop_incomplete=False)
    assert kept_all.height == 2


def test_resample_rejects_finer_target(klines_5m):
    with pytest.raises(ValueError):
        resample_klines(klines_5m, "15m", "5m")


def test_resample_rejects_unknown_timeframe(klines_5m):
    with pytest.raises(ValueError):
        resample_klines(klines_5m, "5m", "7m")


def test_resample_empty_preserves_schema():
    from perp_lab.data.providers.base import empty_klines

    out = resample_klines(empty_klines(), "5m", "15m")
    assert out.height == 0
    assert out.columns == list(empty_klines().columns)
