"""Tests for fold-fit transforms and market-regime classifiers."""

from __future__ import annotations

import numpy as np
import polars as pl
import pytest

from perp_lab.regimes import (
    REGIME_COL,
    UNKNOWN_LABEL,
    GMMRegime,
    KMeansRegime,
    QuantileClipper,
    StandardScaler,
    ThresholdRegime,
)


def _regime_frame(seed: int = 0) -> pl.DataFrame:
    rng = np.random.default_rng(seed)
    n = 600
    # Three volatility clusters, ascending.
    vol = np.concatenate(
        [
            np.abs(rng.normal(0.2, 0.05, 200)),
            np.abs(rng.normal(1.0, 0.1, 200)),
            np.abs(rng.normal(3.0, 0.3, 200)),
        ]
    )
    return pl.DataFrame(
        {
            "rvol": vol,
            "trend": rng.normal(0, 1, n),
            "dispersion": np.abs(rng.normal(0, 1, n)),
            "activity": rng.normal(0, 1, n),
        }
    )


_INPUTS = ("rvol", "trend", "dispersion", "activity")


# --------------------------------------------------------------------------- #
# Transforms fitted only on training data
# --------------------------------------------------------------------------- #
def test_standard_scaler_uses_only_training_statistics() -> None:
    train = pl.DataFrame({"x": [0.0, 2.0, 4.0]})  # mean 2, pop std ~1.633
    scaler = StandardScaler(("x",)).fit(train)
    assert scaler.means_["x"] == pytest.approx(2.0)
    # Applying to a different frame uses the TRAIN mean/std unchanged.
    other = pl.DataFrame({"x": [2.0, 100.0]})
    out = scaler.transform(other)
    assert out["x"].to_list()[0] == pytest.approx(0.0)  # (2 - 2)/std


def test_standard_scaler_constant_column_no_infinity() -> None:
    scaler = StandardScaler(("x",)).fit(pl.DataFrame({"x": [5.0, 5.0, 5.0]}))
    out = scaler.transform(pl.DataFrame({"x": [5.0, 7.0]}))
    assert np.isfinite(out["x"].to_numpy()).all()


def test_scaler_requires_fit_before_transform() -> None:
    with pytest.raises(RuntimeError, match="fitted"):
        StandardScaler(("x",)).transform(pl.DataFrame({"x": [1.0]}))


def test_quantile_clipper_bounds_values() -> None:
    train = pl.DataFrame({"x": list(range(100))})
    clip = QuantileClipper(("x",), lower_q=0.1, upper_q=0.9).fit(train)
    out = clip.transform(pl.DataFrame({"x": [-50.0, 500.0]}))
    lo, hi = clip.lower_["x"], clip.upper_["x"]
    assert out["x"].to_list()[0] == pytest.approx(lo)
    assert out["x"].to_list()[1] == pytest.approx(hi)


# --------------------------------------------------------------------------- #
# Regime models: fit / predict / canonical ordering / determinism
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("model_cls", [ThresholdRegime, KMeansRegime, GMMRegime])
def test_regime_labels_are_canonical_low_to_high(model_cls: type) -> None:
    df = _regime_frame()
    model = model_cls(inputs=_INPUTS).fit(df)
    labels = model.predict(df)
    tagged = df.with_columns(pl.Series(REGIME_COL, labels))
    mean_by_label = {
        rid: tagged.filter(pl.col(REGIME_COL) == rid)["rvol"].mean() for rid in (0, 1, 2)
    }
    # Canonicalised: regime 0 has the lowest mean volatility, 2 the highest.
    assert mean_by_label[0] < mean_by_label[1] < mean_by_label[2]  # type: ignore[operator]


def test_regime_unknown_label_for_missing_inputs() -> None:
    df = _regime_frame()
    model = KMeansRegime(inputs=_INPUTS).fit(df)
    with_null = df.with_columns(
        pl.when(pl.int_range(pl.len()) == 0).then(None).otherwise(pl.col("rvol")).alias("rvol")
    )
    labels = model.predict(with_null)
    assert labels[0] == UNKNOWN_LABEL


@pytest.mark.parametrize("model_cls", [KMeansRegime, GMMRegime])
def test_regime_models_are_reproducible(model_cls: type) -> None:
    df = _regime_frame()
    a = model_cls(inputs=_INPUTS, seed=7).fit(df).predict(df)
    b = model_cls(inputs=_INPUTS, seed=7).fit(df).predict(df)
    assert np.array_equal(a, b)


def test_threshold_regime_interpretation_reports_shares() -> None:
    df = _regime_frame()
    model = ThresholdRegime(inputs=_INPUTS).fit(df)
    interp = model.interpretation(df)
    assert set(interp.keys()) == {"0", "1", "2"}
    assert interp["0"]["name"] == "low"  # type: ignore[index]
    total = sum(interp[k]["n"] for k in interp)  # type: ignore[index]
    assert total == df.height


def test_regime_predict_before_fit_raises() -> None:
    with pytest.raises(RuntimeError, match="fitted"):
        KMeansRegime(inputs=_INPUTS).predict(_regime_frame())
