"""Tests for the regime comparison statistics (Kruskal-Wallis, Dunn, effect size)."""

from __future__ import annotations

import numpy as np
import polars as pl

from perp_lab.eda.regime_tests import (
    dunn_posthoc,
    kruskal_regime,
    regime_comparison,
    regime_medians_ci,
)


def _regime_frame(seed: int = 0, *, separated: bool) -> pl.DataFrame:
    rng = np.random.default_rng(seed)
    n = 300
    if separated:
        low = rng.normal(0.0, 1.0, n)
        medium = rng.normal(3.0, 1.0, n)
        high = rng.normal(6.0, 1.0, n)
    else:
        low = rng.normal(0.0, 1.0, n)
        medium = rng.normal(0.0, 1.0, n)
        high = rng.normal(0.0, 1.0, n)
    value = np.concatenate([low, medium, high])
    regime = ["low"] * n + ["medium"] * n + ["high"] * n
    return pl.DataFrame({"value": value, "vol_regime": regime})


def test_kruskal_detects_separated_groups() -> None:
    df = _regime_frame(1, separated=True)
    res = kruskal_regime(df, "value")
    assert res["pvalue"] < 1e-6
    assert res["n_groups"] == 3.0
    assert res["n"] == 900.0
    assert 0.0 < res["epsilon_squared"] <= 1.0


def test_kruskal_no_difference_gives_large_pvalue() -> None:
    df = _regime_frame(2, separated=False)
    res = kruskal_regime(df, "value")
    assert res["pvalue"] > 0.05


def test_kruskal_empty_with_single_group() -> None:
    df = pl.DataFrame({"value": [1.0, 2.0, 3.0], "vol_regime": ["low", "low", "low"]})
    assert kruskal_regime(df, "value") == {}


def test_dunn_posthoc_shape_and_adjustment() -> None:
    df = _regime_frame(3, separated=True)
    post = dunn_posthoc(df, "value")
    assert post.height == 3  # low-medium, low-high, medium-high
    assert set(post.columns) == {
        "group_a",
        "group_b",
        "n_a",
        "n_b",
        "z",
        "p_raw",
        "p_adj",
        "reject",
    }
    # BH-adjusted p-values are never smaller than the raw ones.
    assert (post["p_adj"] >= post["p_raw"] - 1e-12).all()
    # Strongly separated groups are all rejected.
    assert bool(post["reject"].all())


def test_regime_medians_ci_brackets_median() -> None:
    df = _regime_frame(4, separated=True)
    table = regime_medians_ci(df, "value", block=12, n_boot=200)
    assert table.height == 3
    for row in table.iter_rows(named=True):
        assert row["ci_low"] <= row["median"] <= row["ci_high"]


def test_regime_comparison_one_row_per_variable() -> None:
    df = _regime_frame(5, separated=True).with_columns((pl.col("value") * 2.0).alias("value2"))
    table = regime_comparison(df, ["value", "value2"])
    assert table.height == 2
    assert set(table["variable"].to_list()) == {"value", "value2"}
