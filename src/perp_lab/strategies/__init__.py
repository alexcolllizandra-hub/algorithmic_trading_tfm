"""Interpretable baseline strategies (Chapter 5.4).

Strategies consume a causal feature frame and emit a target position ``side``
(-1 short, 0 flat, +1 long) decided at the **close** of each bar. The execution
delay to the next bar's open is applied by the backtester, so a strategy never
looks ahead. Three interpretable families share one interface: momentum
(moving-average crossover), breakout (Donchian channel) and mean-reversion
(price z-score). Optional causal filters (trend / regime gates) can restrict
when a position is held.
"""

from perp_lab.strategies.base import SIDE_COL, Strategy, evolve_positions
from perp_lab.strategies.breakout import Breakout
from perp_lab.strategies.filters import (
    apply_regime_gate,
    apply_trend_gate,
    regime_mask,
    trend_masks,
)
from perp_lab.strategies.mean_reversion import MeanReversion
from perp_lab.strategies.momentum import MomentumCrossover

__all__ = [
    "SIDE_COL",
    "Breakout",
    "MeanReversion",
    "MomentumCrossover",
    "Strategy",
    "apply_regime_gate",
    "apply_trend_gate",
    "evolve_positions",
    "regime_mask",
    "trend_masks",
]
