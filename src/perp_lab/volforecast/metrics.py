"""Frozen evaluation metrics: MSE on log RV, QLIKE, R2_oos and Diebold-Mariano."""

from __future__ import annotations

import numpy as np
from scipy import stats

_EPS = 1e-12


def qlike(pred_log_rv: np.ndarray, true_log_rv: np.ndarray) -> float:
    """QLIKE on variance levels: mean(sigma2/h - log(sigma2/h) - 1).

    Robust to the heavy right tail of RV and the standard loss for volatility
    forecast comparison. Lower is better; a perfect forecast scores 0.
    """
    sigma2 = np.exp(2.0 * true_log_rv)
    h = np.exp(2.0 * pred_log_rv) + _EPS
    ratio = sigma2 / h
    return float(np.mean(ratio - np.log(ratio) - 1.0))


def oos_metrics(
    pred_log_rv: np.ndarray, true_log_rv: np.ndarray, naive_log_rv: np.ndarray
) -> dict[str, float]:
    """MSE (log RV), QLIKE and out-of-sample R2 against the naive baseline."""
    err = pred_log_rv - true_log_rv
    naive_err = naive_log_rv - true_log_rv
    mse = float(np.mean(err**2))
    mse_naive = float(np.mean(naive_err**2))
    return {
        "mse_log_rv": mse,
        "qlike": qlike(pred_log_rv, true_log_rv),
        "r2_oos_vs_naive": 1.0 - mse / mse_naive if mse_naive > 0 else np.nan,
        "n": float(err.size),
    }


def diebold_mariano(
    pred_a: np.ndarray,
    pred_b: np.ndarray,
    true: np.ndarray,
    *,
    lag: int = 24,
) -> dict[str, float]:
    """Diebold-Mariano test on squared-error loss with a Newey-West variance.

    d_t = e_a^2 - e_b^2; negative mean favours model A. The long-run variance
    uses Bartlett weights up to ``lag`` (the forecast horizon), which accounts
    for the overlap-induced serial correlation of the loss differential.
    """
    d = (pred_a - true) ** 2 - (pred_b - true) ** 2
    n = d.size
    d_bar = float(np.mean(d))
    centered = d - d_bar
    gamma0 = float(np.mean(centered**2))
    variance = gamma0
    for k in range(1, min(lag, n - 1) + 1):
        gamma_k = float(np.mean(centered[k:] * centered[:-k]))
        variance += 2.0 * (1.0 - k / (lag + 1)) * gamma_k
    se = np.sqrt(max(variance, _EPS) / n)
    statistic = d_bar / se
    p_value = 2.0 * (1.0 - stats.norm.cdf(abs(statistic)))
    return {"dm_stat": float(statistic), "p_value": float(p_value), "mean_loss_diff": d_bar}
