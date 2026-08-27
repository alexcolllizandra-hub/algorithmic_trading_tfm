"""Predictive and economic scorecards for a meta-label decision.

Two scorecards, kept apart because they answer different questions and because
conflating them is the standard way a machine-learning layer is talked into a
strategy it does not deserve.

**Predictive** (:func:`predictive_metrics`) asks whether the probabilities are
informative and well calibrated. The headline is PR-AUC, not ROC-AUC: meta-labels are
imbalanced (after costs, most signals are not worth taking) and ROC-AUC is
dominated by the majority class, so it stays high while precision on the
minority class collapses. ROC-AUC is reported as a secondary, comparable number.
Brier score and log loss measure whether a probability of 0.7 means 0.7, which
is what makes a decision threshold meaningful; the calibration table
(:func:`calibration_table`) shows where that breaks.

**Economic** (:func:`economic_metrics`) asks whether acting on those
probabilities made money after costs. It is computed from a backtest ledger, so
it uses the same execution and cost model as every other result in this project
rather than a bespoke PnL sum.

A model may only be preferred on the economic scorecard. The predictive one
explains and audits it. Nothing here selects a model; selection lives in
:mod:`perp_lab.meta_labeling.study`, and every number in this module is computed
on whichever block the caller passes in.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import polars as pl
from sklearn.metrics import average_precision_score, brier_score_loss, log_loss, roc_auc_score

from perp_lab.backtesting.engine import BacktestResult
from perp_lab.backtesting.metrics import trade_metrics

_EPSILON = 1e-15


@dataclass(frozen=True)
class PredictiveMetrics:
    """Discrimination and calibration of the predicted probabilities.

    ``pr_auc_lift`` is PR-AUC divided by the base rate: the factor by which the
    model beats "accept everything". It is the scale-free version of PR-AUC and
    the only one comparable between blocks with different base rates. A value of
    1.0 means the model is worth nothing, whatever its ROC-AUC says.
    """

    n: int
    base_rate: float
    pr_auc: float
    roc_auc: float
    brier_score: float
    log_loss: float
    expected_calibration_error: float

    @property
    def pr_auc_lift(self) -> float:
        return self.pr_auc / self.base_rate if self.base_rate > 0 else float("nan")

    def to_dict(self) -> dict[str, float | int]:
        return {
            "n": self.n,
            "base_rate": self.base_rate,
            "pr_auc": self.pr_auc,
            "pr_auc_lift": self.pr_auc_lift,
            "roc_auc": self.roc_auc,
            "brier_score": self.brier_score,
            "log_loss": self.log_loss,
            "expected_calibration_error": self.expected_calibration_error,
        }


def _validated(y_true: np.ndarray, probabilities: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    truth = np.asarray(y_true).astype(int).ravel()
    probs = np.asarray(probabilities, dtype=float).ravel()
    if truth.size != probs.size:
        raise ValueError("y_true and probabilities must have the same length.")
    if truth.size == 0:
        raise ValueError("Scoring an empty block is not meaningful.")
    if np.any((probs < 0.0) | (probs > 1.0)):
        raise ValueError("probabilities must lie in [0, 1].")
    if not np.all(np.isin(truth, (0, 1))):
        raise ValueError("y_true must be binary (0/1) meta-labels.")
    return truth, probs


def calibration_table(
    y_true: np.ndarray, probabilities: np.ndarray, *, n_bins: int = 10
) -> pl.DataFrame:
    """Predicted versus realised frequency, in equal-width probability bins.

    Equal-width rather than equal-count bins: the question is "when the model
    says 0.8, does it happen 80% of the time", which is a statement about
    probability levels, not about sample quantiles. Empty bins are dropped
    because a bin the model never predicted carries no evidence either way.
    """
    truth, probs = _validated(y_true, probabilities)
    if n_bins < 2:
        raise ValueError("n_bins must be at least 2.")

    edges = np.linspace(0.0, 1.0, n_bins + 1)
    index = np.clip(np.digitize(probs, edges[1:-1], right=False), 0, n_bins - 1)
    rows = []
    for b in range(n_bins):
        mask = index == b
        count = int(mask.sum())
        if count == 0:
            continue
        rows.append(
            {
                "bin_lower": float(edges[b]),
                "bin_upper": float(edges[b + 1]),
                "n": count,
                "mean_predicted": float(probs[mask].mean()),
                "observed_rate": float(truth[mask].mean()),
            }
        )
    return pl.DataFrame(
        rows,
        schema={
            "bin_lower": pl.Float64,
            "bin_upper": pl.Float64,
            "n": pl.Int64,
            "mean_predicted": pl.Float64,
            "observed_rate": pl.Float64,
        },
    )


def expected_calibration_error(
    y_true: np.ndarray, probabilities: np.ndarray, *, n_bins: int = 10
) -> float:
    """Sample-weighted mean gap between predicted and realised frequency."""
    table = calibration_table(y_true, probabilities, n_bins=n_bins)
    if table.height == 0:
        return float("nan")
    gap = (table["mean_predicted"] - table["observed_rate"]).abs().to_numpy()
    weight = table["n"].to_numpy().astype(float)
    return float(np.sum(gap * weight) / weight.sum())


def predictive_metrics(
    y_true: np.ndarray, probabilities: np.ndarray, *, n_bins: int = 10
) -> PredictiveMetrics:
    """Score predicted probabilities against realised meta-labels.

    ROC-AUC is undefined on a single-class block; it is reported as ``nan``
    rather than as a neutral 0.5, which would read as "no skill" when in fact
    nothing was measured. PR-AUC degenerates to the base rate in that case,
    which is the correct answer.
    """
    truth, probs = _validated(y_true, probabilities)
    both_classes = np.unique(truth).size == 2
    clipped = np.clip(probs, _EPSILON, 1.0 - _EPSILON)
    return PredictiveMetrics(
        n=int(truth.size),
        base_rate=float(truth.mean()),
        pr_auc=float(average_precision_score(truth, probs))
        if both_classes
        else float(truth.mean()),
        roc_auc=float(roc_auc_score(truth, probs)) if both_classes else float("nan"),
        brier_score=float(brier_score_loss(truth, probs)),
        log_loss=float(log_loss(truth, clipped, labels=[0, 1])),
        expected_calibration_error=expected_calibration_error(truth, probs, n_bins=n_bins),
    )


@dataclass(frozen=True)
class EconomicMetrics:
    """Net-of-cost economics of one arm over one evaluation block."""

    net_return: float
    sharpe: float
    sortino: float
    max_drawdown: float
    turnover: float
    total_cost: float
    total_funding: float
    n_trades: int
    profit_factor: float
    trade_hit_rate: float
    exposure: float

    def to_dict(self) -> dict[str, float | int]:
        return {
            "net_return": self.net_return,
            "sharpe": self.sharpe,
            "sortino": self.sortino,
            "max_drawdown": self.max_drawdown,
            "turnover": self.turnover,
            "total_cost": self.total_cost,
            "total_funding": self.total_funding,
            "n_trades": self.n_trades,
            "profit_factor": self.profit_factor,
            "trade_hit_rate": self.trade_hit_rate,
            "exposure": self.exposure,
        }


def economic_metrics(result: BacktestResult) -> EconomicMetrics:
    """Summarise a backtest ledger into the arm-comparison scorecard.

    Everything is read from the ledger the engine produced, so costs, funding
    and next-bar execution are those of the backtester and not a reconstruction.
    An arm that never trades is a legitimate outcome — it is exactly what a
    meta-label should do on a market with no edge — and reports zeros with an
    undefined (``nan``) profit factor rather than failing.
    """
    ledger = result.ledger
    if ledger.height == 0:
        return EconomicMetrics(
            net_return=0.0,
            sharpe=0.0,
            sortino=0.0,
            max_drawdown=0.0,
            turnover=0.0,
            total_cost=0.0,
            total_funding=0.0,
            n_trades=0,
            profit_factor=float("nan"),
            trade_hit_rate=float("nan"),
            exposure=0.0,
        )

    trades = result.trades()
    per_trade = (
        trades["net_return"].to_numpy().astype(float)
        if trades.height > 0
        else np.zeros(0, dtype=float)
    )
    trade_stats = trade_metrics(per_trade) if per_trade.size else {}
    metrics = result.metrics
    return EconomicMetrics(
        net_return=float(metrics.get("total_return", 0.0)),
        sharpe=float(metrics.get("sharpe", 0.0)),
        sortino=float(metrics.get("sortino", 0.0)),
        max_drawdown=float(metrics.get("max_drawdown", 0.0)),
        turnover=float(ledger["turnover"].sum()),
        total_cost=float(ledger["cost"].sum()),
        total_funding=float(ledger["funding"].sum()),
        n_trades=int(trades.height),
        profit_factor=float(trade_stats.get("profit_factor", float("nan"))),
        trade_hit_rate=float(trade_stats.get("trade_hit_rate", float("nan"))),
        exposure=float(
            metrics.get("exposure", float((ledger["position"].to_numpy() != 0.0).mean()))
        ),
    )
