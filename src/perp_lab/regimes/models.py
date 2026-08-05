"""Market-regime classifiers (fitted only on training data).

Three regime models share one contract so they are interchangeable as optional
strategy filters, as future meta-labeling inputs and as evaluation dimensions:

1. :class:`ThresholdRegime` -- an interpretable baseline that splits a single
   volatility proxy at training quantiles into ``low`` / ``medium`` / ``high``.
2. :class:`KMeansRegime` -- K-means over a small set of standardised regime
   inputs (volatility, trend strength, return dispersion, activity).
3. :class:`GMMRegime` -- a Gaussian Mixture Model over the same inputs.

Common contract:

* ``fit(train_df)`` learns parameters **only** from the training slice.
* ``predict(df)`` returns an integer label per row; rows with any missing input
  get :data:`UNKNOWN_LABEL` (``-1``) -- never a fabricated regime.
* Labels are **canonicalised** so ``0`` is always the lowest-volatility regime,
  making them comparable across models and folds.
* ``interpretation(df)`` summarises each regime's mean raw inputs (economics).
* ``params()`` returns a JSON-serialisable snapshot for run artifacts.

Because every input is a causal feature and each prediction uses only that row's
own features, regime labels never depend on future observations.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import polars as pl

from perp_lab.regimes.transforms import StandardScaler

UNKNOWN_LABEL = -1
REGIME_COL = "regime_id"
REGIME_NAME_COL = "regime"


def regime_names(n_regimes: int) -> list[str]:
    """Human-readable names: 3 regimes -> low/medium/high, else regime_{i}."""
    if n_regimes == 3:
        return ["low", "medium", "high"]
    return [f"regime_{i}" for i in range(n_regimes)]


def _order_map(order: np.ndarray) -> np.ndarray:
    """Map original cluster id -> volatility rank (0 = lowest ordering value)."""
    remap = np.empty(order.size, dtype=int)
    for rank, original in enumerate(order):
        remap[int(original)] = rank
    return remap


@dataclass
class ThresholdRegime:
    """Interpretable volatility-quantile regime baseline (train-fit thresholds)."""

    inputs: tuple[str, ...]
    n_regimes: int = 3
    seed: int = 42
    name: str = "threshold"
    thresholds_: list[float] = field(default_factory=list)
    fitted_: bool = False

    def __post_init__(self) -> None:
        if not self.inputs:
            raise ValueError("ThresholdRegime needs at least one input (a volatility proxy).")
        if self.n_regimes < 2:
            raise ValueError("n_regimes must be >= 2.")

    @property
    def ordering_col(self) -> str:
        return self.inputs[0]

    def fit(self, df: pl.DataFrame) -> ThresholdRegime:
        col = df[self.ordering_col].drop_nulls()
        if col.len() == 0:
            raise ValueError("ThresholdRegime.fit received no complete training rows.")
        qs = [(i + 1) / self.n_regimes for i in range(self.n_regimes - 1)]
        self.thresholds_ = [float(col.quantile(q)) for q in qs]  # type: ignore[arg-type]
        self.fitted_ = True
        return self

    def predict(self, df: pl.DataFrame) -> np.ndarray:
        if not self.fitted_:
            raise RuntimeError("ThresholdRegime must be fitted before predict.")
        vals = df[self.ordering_col].cast(pl.Float64).to_numpy().astype(float)
        labels = np.digitize(vals, self.thresholds_, right=False).astype(int)
        labels[~np.isfinite(vals)] = UNKNOWN_LABEL
        return labels

    def attach(self, df: pl.DataFrame) -> pl.DataFrame:
        return _attach_labels(df, self.predict(df), self.n_regimes)

    def interpretation(self, df: pl.DataFrame) -> dict[str, object]:
        return _interpretation(df, self.predict(df), self.inputs, self.n_regimes)

    def params(self) -> dict[str, object]:
        return {
            "model": self.name,
            "inputs": list(self.inputs),
            "ordering_col": self.ordering_col,
            "n_regimes": self.n_regimes,
            "thresholds": self.thresholds_,
            "seed": self.seed,
            "fitted": self.fitted_,
        }


@dataclass
class _ClusterRegime:
    """Shared machinery for K-means / GMM regimes over standardised inputs."""

    inputs: tuple[str, ...]
    n_regimes: int = 3
    seed: int = 42
    name: str = "cluster"
    scaler_: StandardScaler | None = None
    order_map_: np.ndarray | None = None
    fitted_: bool = False

    def __post_init__(self) -> None:
        if len(self.inputs) < 1:
            raise ValueError(f"{self.name} needs at least one regime input.")
        if self.n_regimes < 2:
            raise ValueError("n_regimes must be >= 2.")

    # -- subclass hooks ----------------------------------------------------- #
    def _fit_model(self, x: np.ndarray) -> None:  # pragma: no cover - abstract
        raise NotImplementedError

    def _predict_model(self, x: np.ndarray) -> np.ndarray:  # pragma: no cover - abstract
        raise NotImplementedError

    def _centers(self) -> np.ndarray:  # pragma: no cover - abstract
        raise NotImplementedError

    # -- contract ----------------------------------------------------------- #
    def fit(self, df: pl.DataFrame) -> _ClusterRegime:
        scaler = StandardScaler(self.inputs).fit(df)
        x = scaler.transform_matrix(df)
        complete = np.isfinite(x).all(axis=1)
        if complete.sum() < self.n_regimes:
            raise ValueError(f"{self.name}.fit needs >= n_regimes complete training rows.")
        self.scaler_ = scaler
        self._fit_model(x[complete])
        # Canonicalise: order clusters by their volatility (first-input) centre.
        centers = self._centers()
        order = np.argsort(centers[:, 0])
        self.order_map_ = _order_map(order)
        self.fitted_ = True
        return self

    def predict(self, df: pl.DataFrame) -> np.ndarray:
        if not self.fitted_ or self.scaler_ is None or self.order_map_ is None:
            raise RuntimeError(f"{self.name} must be fitted before predict.")
        x = self.scaler_.transform_matrix(df)
        complete = np.isfinite(x).all(axis=1)
        labels = np.full(df.height, UNKNOWN_LABEL, dtype=int)
        if complete.any():
            raw = self._predict_model(x[complete]).astype(int)
            labels[complete] = self.order_map_[raw]
        return labels

    def attach(self, df: pl.DataFrame) -> pl.DataFrame:
        return _attach_labels(df, self.predict(df), self.n_regimes)

    def interpretation(self, df: pl.DataFrame) -> dict[str, object]:
        return _interpretation(df, self.predict(df), self.inputs, self.n_regimes)

    def params(self) -> dict[str, object]:
        return {
            "model": self.name,
            "inputs": list(self.inputs),
            "n_regimes": self.n_regimes,
            "seed": self.seed,
            "scaler": self.scaler_.params() if self.scaler_ else None,
            "fitted": self.fitted_,
        }


@dataclass
class KMeansRegime(_ClusterRegime):
    """K-means regime classifier over standardised causal regime inputs."""

    name: str = "kmeans"
    _model: object = None

    def _fit_model(self, x: np.ndarray) -> None:
        from sklearn.cluster import KMeans

        model = KMeans(n_clusters=self.n_regimes, random_state=self.seed, n_init="auto")
        model.fit(x)
        self._model = model

    def _predict_model(self, x: np.ndarray) -> np.ndarray:
        assert self._model is not None
        return np.asarray(self._model.predict(x))  # type: ignore[attr-defined]

    def _centers(self) -> np.ndarray:
        assert self._model is not None
        return np.asarray(self._model.cluster_centers_)  # type: ignore[attr-defined]


@dataclass
class GMMRegime(_ClusterRegime):
    """Gaussian Mixture Model regime classifier over standardised inputs."""

    name: str = "gmm"
    _model: object = None

    def _fit_model(self, x: np.ndarray) -> None:
        from sklearn.mixture import GaussianMixture

        model = GaussianMixture(
            n_components=self.n_regimes, random_state=self.seed, covariance_type="full"
        )
        model.fit(x)
        self._model = model

    def _predict_model(self, x: np.ndarray) -> np.ndarray:
        assert self._model is not None
        return np.asarray(self._model.predict(x))  # type: ignore[attr-defined]

    def _centers(self) -> np.ndarray:
        assert self._model is not None
        return np.asarray(self._model.means_)  # type: ignore[attr-defined]


# --------------------------------------------------------------------------- #
# Shared helpers
# --------------------------------------------------------------------------- #
def _attach_labels(df: pl.DataFrame, labels: np.ndarray, n_regimes: int) -> pl.DataFrame:
    names = regime_names(n_regimes)
    name_series = [names[i] if i != UNKNOWN_LABEL and i < len(names) else None for i in labels]
    return df.with_columns(
        pl.Series(REGIME_COL, labels, dtype=pl.Int32),
        pl.Series(REGIME_NAME_COL, name_series, dtype=pl.String),
    )


def _interpretation(
    df: pl.DataFrame, labels: np.ndarray, inputs: tuple[str, ...], n_regimes: int
) -> dict[str, object]:
    names = regime_names(n_regimes)
    tagged = df.with_columns(pl.Series(REGIME_COL, labels, dtype=pl.Int32))
    summary: dict[str, object] = {}
    for rid in range(n_regimes):
        sub = tagged.filter(pl.col(REGIME_COL) == rid)
        means = {c: (float(sub[c].mean()) if sub.height else None) for c in inputs}  # type: ignore[arg-type]
        summary[str(rid)] = {
            "name": names[rid] if rid < len(names) else f"regime_{rid}",
            "n": int(sub.height),
            "share": round(sub.height / tagged.height, 4) if tagged.height else 0.0,
            "input_means": means,
        }
    return summary
