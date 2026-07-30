"""Smoke tests: every EDA function runs and returns the expected shape/type."""

from perp_lab.eda.correlation import rolling_correlation, static_correlation
from perp_lab.eda.dependence import autocorrelation, ljung_box_pvalue
from perp_lab.eda.regimes import tag_trend_volatility_regimes
from perp_lab.eda.returns import add_log_returns
from perp_lab.eda.seasonality import seasonality_by_hour, seasonality_by_weekday
from perp_lab.eda.volatility import annualized_volatility, realized_volatility, rolling_volatility


def test_volatility_columns(klines_5m):
    df = add_log_returns(klines_5m)
    df = rolling_volatility(df, window=20)
    df = realized_volatility(df, window=20)
    df = annualized_volatility(df, "5m", window=20)
    assert {"rolling_vol_20", "realized_vol_20", "ann_vol_20"} <= set(df.columns)


def test_autocorrelation_and_ljung_box(klines_5m):
    df = add_log_returns(klines_5m)
    acf_df = autocorrelation(df, max_lag=10)
    assert acf_df.height == 11  # lags 0..10
    assert acf_df["acf"][0] == 1.0
    p = ljung_box_pvalue(df, lags=5)
    assert 0.0 <= p <= 1.0


def test_autocorrelation_transforms(klines_5m):
    df = add_log_returns(klines_5m)
    for transform in ("identity", "abs", "square"):
        acf_df = autocorrelation(df, max_lag=5, transform=transform)
        assert acf_df.height == 6


def test_seasonality(klines_5m):
    by_hour = seasonality_by_hour(klines_5m, "volume")
    assert by_hour.height == 24
    by_wd = seasonality_by_weekday(klines_5m, "volume")
    assert by_wd.height >= 1


def test_correlation(make_klines):
    a = add_log_returns(make_klines(seed=1))
    b = add_log_returns(make_klines(seed=2))
    corr = static_correlation(a, b)
    assert -1.0 <= corr <= 1.0
    rc = rolling_correlation(a, b, window=20)
    assert "rolling_corr_20" in rc.columns


def test_regime_tagging(klines_5m):
    df = add_log_returns(klines_5m)
    tagged = tag_trend_volatility_regimes(df, trend_window=20, vol_window=20)
    assert {"trend_regime", "vol_regime", "regime"} <= set(tagged.columns)
    trends = set(tagged["trend_regime"].unique().to_list())
    assert trends <= {"up", "down", "flat"}
