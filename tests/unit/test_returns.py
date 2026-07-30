import math

from perp_lab.eda.returns import add_log_returns, annualization_factor, return_stats


def test_add_log_returns_first_is_null(klines_5m):
    out = add_log_returns(klines_5m)
    assert out["log_return"].null_count() == 1
    assert out.height == klines_5m.height


def test_annualization_factor_5m():
    # sqrt(bars per year) with 365-day year: 365*24*12 = 105_120 bars.
    assert annualization_factor("5m") == math.sqrt(105_120)


def test_annualization_factor_1h():
    assert annualization_factor("1h") == math.sqrt(365 * 24)


def test_return_stats_keys(klines_5m):
    out = add_log_returns(klines_5m)
    stats = return_stats(out)
    for key in ("mean", "std", "skew", "excess_kurtosis", "jarque_bera_pvalue"):
        assert key in stats
    assert stats["n"] == klines_5m.height - 1
