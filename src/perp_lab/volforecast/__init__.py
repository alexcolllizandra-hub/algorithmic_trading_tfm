"""Volatility-forecasting annex (frozen spec: docs/methodology/volforecast_spec.md).

Tests whether an LSTM improves next-24h realized-volatility forecasts over
the HAR-RV benchmark and a persistence baseline, under the study's expanding
walk-forward geometry. Produces no trading strategy and no promotion
evidence. Torch is an optional dependency (``dl`` extra): the naive and HAR
models run without it, and the LSTM raises a clear error if it is missing.
"""

from perp_lab.volforecast.data import build_vol_dataset
from perp_lab.volforecast.metrics import diebold_mariano, oos_metrics, qlike
from perp_lab.volforecast.models import fit_har, predict_har, predict_naive

__all__ = [
    "build_vol_dataset",
    "diebold_mariano",
    "fit_har",
    "oos_metrics",
    "predict_har",
    "predict_naive",
    "qlike",
]
