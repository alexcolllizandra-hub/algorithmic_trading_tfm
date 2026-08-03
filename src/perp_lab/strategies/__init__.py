"""Interpretable baseline strategies (Chapter 5.4).

Strategies consume a causal feature frame and emit a target position ``side``
(-1 short, 0 flat, +1 long) decided at the **close** of each bar. The execution
delay to the next bar's open is applied by the backtester, so a strategy never
looks ahead. This initial slice ships one momentum (moving-average crossover)
baseline; breakout and mean-reversion families follow the same interface.
"""

from perp_lab.strategies.base import SIDE_COL, Strategy
from perp_lab.strategies.momentum import MomentumCrossover

__all__ = ["SIDE_COL", "MomentumCrossover", "Strategy"]
