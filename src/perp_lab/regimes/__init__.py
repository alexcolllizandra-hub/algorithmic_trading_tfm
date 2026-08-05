"""Market-regime models and fold-fit transforms (Chapter 5.3).

All parameter-learning objects here are fitted **only** on the training slice of
a walk-forward fold and applied unchanged to validation/test, so no future
information leaks into the past. Regime labels are causal (each prediction uses
only that row's causal features) and canonicalised so ``0`` is the lowest-
volatility regime.
"""

from perp_lab.regimes.models import (
    REGIME_COL,
    REGIME_NAME_COL,
    UNKNOWN_LABEL,
    GMMRegime,
    KMeansRegime,
    ThresholdRegime,
    regime_names,
)
from perp_lab.regimes.transforms import QuantileClipper, StandardScaler

__all__ = [
    "REGIME_COL",
    "REGIME_NAME_COL",
    "UNKNOWN_LABEL",
    "GMMRegime",
    "KMeansRegime",
    "QuantileClipper",
    "StandardScaler",
    "ThresholdRegime",
    "regime_names",
]
