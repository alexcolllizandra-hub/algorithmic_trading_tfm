"""Figure-generation smoke tests: helpers return Matplotlib figures."""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

from matplotlib.figure import Figure

from perp_lab.eda.drawdown import add_drawdown
from perp_lab.eda.plots import (
    plot_drawdown,
    plot_ecdf,
    plot_price,
    plot_qq,
    plot_seasonality,
)
from perp_lab.eda.returns import add_log_returns
from perp_lab.eda.seasonality import seasonality_stats


def test_price_and_distribution_figures(klines_5m):
    assert isinstance(plot_price(klines_5m), Figure)
    df = add_log_returns(klines_5m)
    assert isinstance(plot_ecdf(df), Figure)
    assert isinstance(plot_qq(df), Figure)


def test_drawdown_and_seasonality_figures(klines_5m):
    dd = add_drawdown(klines_5m)
    assert isinstance(plot_drawdown(dd), Figure)
    table = seasonality_stats(klines_5m, "volume", by="hour")
    assert isinstance(plot_seasonality(table, by="hour"), Figure)
