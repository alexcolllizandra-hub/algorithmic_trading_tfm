"""Reference baselines used to judge whether a search actually adds value.

A discovered strategy is only interesting relative to something trivial. These
baselines are deliberately **fixed**: their parameters are declared here (or come
from the experiment contract) and are never tuned by Random Search, the Genetic
Algorithm, or by looking at test data. They are evaluated on exactly the same
folds, costs, funding and backtester as searched candidates, so the comparison is
like-for-like.

Baselines provided:

* :class:`Flat` -- never trades; isolates the cost of doing nothing.
* :class:`AlwaysLong` -- persistent long exposure, the perpetual-futures analogue
  of buy-and-hold (it still pays funding and the initial entry cost).
* :class:`FixedCrossover` -- a textbook fast/slow moving-average crossover.
* :class:`FixedMomentum` -- long when trailing momentum is positive.
* :class:`FixedMeanReversion` -- fade a trailing price z-score.
* :class:`RandomEntry` -- deterministic pseudo-random positions with an exposure
  target, so a searched strategy must beat coin-flipping at similar turnover.

All of them emit a target position at each bar's close; the backtester applies
the next-bar fill, so none of them can act on information from their own bar.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import polars as pl

from perp_lab.strategies.base import SIDE_COL, apply_direction, validate_direction


def _side_frame(df: pl.DataFrame, side: pl.Expr) -> pl.DataFrame:
    """Standard output frame: timestamp plus an integer side in {-1, 0, +1}."""
    return df.select("open_time", side.fill_null(0).cast(pl.Int8).alias(SIDE_COL))


@dataclass(frozen=True)
class Flat:
    """Never holds a position. The zero-return, zero-cost reference."""

    name: str = "baseline_flat"

    def params(self) -> dict[str, object]:
        return {}

    def required_features(self) -> tuple[str, ...]:
        return ()

    def signals(self, features: pl.DataFrame) -> pl.DataFrame:
        return _side_frame(features, pl.lit(0))


@dataclass(frozen=True)
class AlwaysLong:
    """Persistent long exposure (buy-and-hold adapted to a perpetual contract).

    This is *not* spot buy-and-hold: the position pays funding for its whole life
    and pays the entry cost once, exactly as the backtester models any other
    position.
    """

    name: str = "baseline_always_long"

    def params(self) -> dict[str, object]:
        return {}

    def required_features(self) -> tuple[str, ...]:
        return ()

    def signals(self, features: pl.DataFrame) -> pl.DataFrame:
        return _side_frame(features, pl.lit(1))


@dataclass(frozen=True)
class FixedCrossover:
    """Fast/slow moving-average crossover with parameters fixed in advance."""

    fast: int = 24
    slow: int = 96
    direction: str = "both"
    name: str = "baseline_ma_crossover"

    def __post_init__(self) -> None:
        validate_direction(self.direction)
        if self.fast >= self.slow:
            raise ValueError(f"fast ({self.fast}) must be < slow ({self.slow}).")

    def params(self) -> dict[str, object]:
        return {"fast": self.fast, "slow": self.slow, "direction": self.direction}

    def required_features(self) -> tuple[str, ...]:
        return (f"sma_{self.fast}", f"sma_{self.slow}")

    def signals(self, features: pl.DataFrame) -> pl.DataFrame:
        fast, slow = pl.col(f"sma_{self.fast}"), pl.col(f"sma_{self.slow}")
        raw = pl.when(fast > slow).then(1).when(fast < slow).then(-1).otherwise(0)
        return _side_frame(features, apply_direction(raw, self.direction))


@dataclass(frozen=True)
class FixedMomentum:
    """Hold long while trailing cumulative return over ``window`` bars is positive."""

    window: int = 24
    direction: str = "both"
    name: str = "baseline_momentum"

    def __post_init__(self) -> None:
        validate_direction(self.direction)
        if self.window < 1:
            raise ValueError("window must be >= 1.")

    def params(self) -> dict[str, object]:
        return {"window": self.window, "direction": self.direction}

    def required_features(self) -> tuple[str, ...]:
        return (f"momentum_{self.window}",)

    def signals(self, features: pl.DataFrame) -> pl.DataFrame:
        mom = pl.col(f"momentum_{self.window}")
        raw = pl.when(mom > 0).then(1).when(mom < 0).then(-1).otherwise(0)
        return _side_frame(features, apply_direction(raw, self.direction))


@dataclass(frozen=True)
class FixedMeanReversion:
    """Fade a trailing price z-score: short when stretched up, long when down."""

    window: int = 48
    entry_z: float = 2.0
    direction: str = "both"
    name: str = "baseline_mean_reversion"

    def __post_init__(self) -> None:
        validate_direction(self.direction)
        if self.entry_z <= 0:
            raise ValueError("entry_z must be positive.")

    def params(self) -> dict[str, object]:
        return {"window": self.window, "entry_z": self.entry_z, "direction": self.direction}

    def required_features(self) -> tuple[str, ...]:
        return (f"zscore_{self.window}",)

    def signals(self, features: pl.DataFrame) -> pl.DataFrame:
        z = pl.col(f"zscore_{self.window}")
        raw = pl.when(z >= self.entry_z).then(-1).when(z <= -self.entry_z).then(1).otherwise(0)
        return _side_frame(features, apply_direction(raw, self.direction))


@dataclass(frozen=True)
class RandomEntry:
    """Deterministic pseudo-random positions at a target exposure.

    Seeded from ``seed`` and from the number of bars only, so the same fold always
    yields the same positions and the baseline is reproducible. ``exposure`` is the
    fraction of bars spent in a position; the sign is a fair coin flip. This is the
    "did the search beat luck at similar turnover?" control.
    """

    seed: int = 42
    exposure: float = 0.5
    name: str = "baseline_random_entry"

    def __post_init__(self) -> None:
        if not 0.0 <= self.exposure <= 1.0:
            raise ValueError("exposure must lie in [0, 1].")

    def params(self) -> dict[str, object]:
        return {"seed": self.seed, "exposure": self.exposure}

    def required_features(self) -> tuple[str, ...]:
        return ()

    def signals(self, features: pl.DataFrame) -> pl.DataFrame:
        rng = np.random.default_rng(self.seed)
        n = features.height
        active = rng.random(n) < self.exposure
        sign = np.where(rng.random(n) < 0.5, -1, 1)
        side = np.where(active, sign, 0).astype(np.int8)
        return features.select("open_time").with_columns(pl.Series(SIDE_COL, side, dtype=pl.Int8))


def default_baselines(seed: int = 42) -> dict[str, object]:
    """The baseline suite every development experiment must report against.

    Parameters are fixed here on purpose: a baseline tuned on validation (let
    alone on test) would stop being a baseline.
    """
    return {
        "flat": Flat(),
        "always_long": AlwaysLong(),
        "ma_crossover": FixedCrossover(fast=24, slow=96),
        "momentum": FixedMomentum(window=24),
        "mean_reversion": FixedMeanReversion(window=48, entry_z=2.0),
        "random_entry": RandomEntry(seed=seed, exposure=0.5),
    }


def baseline_feature_requirements(seed: int = 42) -> tuple[str, ...]:
    """Every feature column the default baseline suite reads."""
    cols: list[str] = []
    for strat in default_baselines(seed).values():
        for col in strat.required_features():  # type: ignore[attr-defined]
            if col not in cols:
                cols.append(col)
    return tuple(cols)
