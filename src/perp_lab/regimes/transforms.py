"""Fold-fit / apply transforms (parameters learned only on training data).

Any transform that *learns* parameters from data -- scaling statistics, clipping
thresholds, imputation values -- must be fitted on the **training** slice of a
walk-forward fold and then applied *unchanged* to validation and test. Fitting on
the whole series (or per-slice) would leak future information into the past.

These objects follow a minimal ``fit`` / ``transform`` contract:

* ``fit(train_df)`` learns and stores parameters, returning ``self``.
* ``transform(df)`` applies the stored parameters to any frame.
* ``params()`` returns a JSON-serialisable snapshot for run artifacts.

They are deliberately lightweight (NumPy + Polars only) and deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import polars as pl

FloatArray = np.ndarray


@dataclass
class StandardScaler:
    """Standardise columns using training means / population std deviations.

    A zero training std maps to 1.0 so a constant column becomes all-zeros rather
    than producing infinities. ``transform_matrix`` preserves nulls as ``nan`` so
    downstream models can mask incomplete rows.
    """

    columns: tuple[str, ...]
    means_: dict[str, float] = field(default_factory=dict)
    stds_: dict[str, float] = field(default_factory=dict)
    fitted_: bool = False

    @property
    def is_fitted(self) -> bool:
        return self.fitted_

    def fit(self, df: pl.DataFrame) -> StandardScaler:
        sub = df.select(self.columns).drop_nulls()
        if sub.height == 0:
            raise ValueError("StandardScaler.fit received no complete training rows.")
        self.means_ = {c: float(sub[c].mean()) for c in self.columns}  # type: ignore[arg-type]
        stds: dict[str, float] = {}
        for c in self.columns:
            s = float(sub[c].std(ddof=0))  # type: ignore[arg-type]
            stds[c] = s if s > 0 else 1.0
        self.stds_ = stds
        self.fitted_ = True
        return self

    def _check(self) -> None:
        if not self.fitted_:
            raise RuntimeError("StandardScaler must be fitted on training data before transform.")

    def transform_matrix(self, df: pl.DataFrame) -> FloatArray:
        """Return the scaled ``(n_rows, n_columns)`` matrix (nulls become nan)."""
        self._check()
        cols: list[FloatArray] = []
        for c in self.columns:
            arr = df[c].cast(pl.Float64).to_numpy().astype(float)
            cols.append((arr - self.means_[c]) / self.stds_[c])
        return np.column_stack(cols) if cols else np.empty((df.height, 0))

    def transform(self, df: pl.DataFrame) -> pl.DataFrame:
        """Return ``df`` with each column replaced by its standardised values."""
        self._check()
        exprs = [
            ((pl.col(c).cast(pl.Float64) - self.means_[c]) / self.stds_[c]).alias(c)
            for c in self.columns
        ]
        return df.with_columns(exprs)

    def params(self) -> dict[str, object]:
        return {
            "transform": "standard_scaler",
            "columns": list(self.columns),
            "means": self.means_,
            "stds": self.stds_,
            "fitted": self.fitted_,
        }


@dataclass
class QuantileClipper:
    """Winsorise columns at training lower/upper quantiles (no future info)."""

    columns: tuple[str, ...]
    lower_q: float = 0.01
    upper_q: float = 0.99
    lower_: dict[str, float] = field(default_factory=dict)
    upper_: dict[str, float] = field(default_factory=dict)
    fitted_: bool = False

    def __post_init__(self) -> None:
        if not (0.0 <= self.lower_q < self.upper_q <= 1.0):
            raise ValueError("QuantileClipper needs 0 <= lower_q < upper_q <= 1.")

    @property
    def is_fitted(self) -> bool:
        return self.fitted_

    def fit(self, df: pl.DataFrame) -> QuantileClipper:
        sub = df.select(self.columns).drop_nulls()
        if sub.height == 0:
            raise ValueError("QuantileClipper.fit received no complete training rows.")
        self.lower_ = {c: float(sub[c].quantile(self.lower_q)) for c in self.columns}  # type: ignore[arg-type]
        self.upper_ = {c: float(sub[c].quantile(self.upper_q)) for c in self.columns}  # type: ignore[arg-type]
        self.fitted_ = True
        return self

    def transform(self, df: pl.DataFrame) -> pl.DataFrame:
        if not self.fitted_:
            raise RuntimeError("QuantileClipper must be fitted before transform.")
        exprs = [pl.col(c).clip(self.lower_[c], self.upper_[c]).alias(c) for c in self.columns]
        return df.with_columns(exprs)

    def params(self) -> dict[str, object]:
        return {
            "transform": "quantile_clipper",
            "columns": list(self.columns),
            "lower_q": self.lower_q,
            "upper_q": self.upper_q,
            "lower": self.lower_,
            "upper": self.upper_,
            "fitted": self.fitted_,
        }
