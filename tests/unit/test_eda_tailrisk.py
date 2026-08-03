"""Historical VaR / Expected Shortfall tests with manual expected values."""

from __future__ import annotations

import numpy as np
import polars as pl
import pytest

from perp_lab.eda.tailrisk import historical_var_es, tail_asymmetry, tail_risk_table

# Ten evenly spaced returns from -0.10 to +0.08.
_VALUES = [-0.10, -0.08, -0.06, -0.04, -0.02, 0.0, 0.02, 0.04, 0.06, 0.08]


def test_var_es_order_statistic_level_20pct():
    out = historical_var_es(np.array(_VALUES), level=0.2)
    # k = floor(0.2 * 10) = 2 worst = [-0.10, -0.08].
    assert out["k"] == 2.0
    assert out["var"] == pytest.approx(-0.08)  # 2nd smallest = tail threshold
    assert out["es"] == pytest.approx(-0.09)  # mean(-0.10, -0.08)


def test_var_es_level_10pct_single_observation():
    out = historical_var_es(np.array(_VALUES), level=0.1)
    assert out["k"] == 1.0
    assert out["var"] == pytest.approx(-0.10)
    assert out["es"] == pytest.approx(-0.10)


def test_tail_risk_table_multiple_levels():
    df = pl.DataFrame({"log_return": _VALUES})
    table = tail_risk_table(df, "log_return", levels=(0.1, 0.2))
    assert table.height == 2
    assert set(table.columns) == {"level", "n", "k", "var", "es"}


def test_tail_asymmetry_symmetric_returns():
    out = tail_asymmetry(pl.DataFrame({"log_return": _VALUES}), level=0.2)
    # Lower tail mean(-0.10,-0.08) = -0.09; upper mean(0.08,0.06) = 0.07.
    assert out["lower_es"] == pytest.approx(-0.09)
    assert out["upper_mean"] == pytest.approx(0.07)
    assert out["abs_ratio"] == pytest.approx(0.09 / 0.07)


def test_var_es_rejects_bad_level():
    assert historical_var_es(np.array(_VALUES), level=0.0) == {}
    assert historical_var_es(np.array([]), level=0.05) == {}
