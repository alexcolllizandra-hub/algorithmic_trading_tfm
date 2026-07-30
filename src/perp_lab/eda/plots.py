"""Matplotlib helpers producing thesis-ready figures.

Functions return a :class:`matplotlib.figure.Figure` so callers (notebooks or
the figure-generation skill) control saving and captioning. Use
:func:`save_figure` for a consistent export.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless-safe; notebooks can override with %matplotlib

import matplotlib.pyplot as plt
import polars as pl
from matplotlib.figure import Figure


def save_figure(fig: Figure, path: str | Path, dpi: int = 150) -> Path:
    """Save a figure to ``path`` (creating parent dirs) and return the path."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=dpi, bbox_inches="tight")
    return path


def plot_price(df: pl.DataFrame, price_col: str = "close", time_col: str = "open_time") -> Figure:
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(df[time_col].to_list(), df[price_col].to_list(), lw=0.7)
    ax.set_xlabel("Time (UTC)")
    ax.set_ylabel("Price")
    ax.set_title("Price evolution")
    return fig


def plot_return_distribution(df: pl.DataFrame, col: str = "log_return", bins: int = 200) -> Figure:
    values = df.select(pl.col(col)).drop_nulls().to_series().to_numpy()
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.hist(values, bins=bins, density=True, alpha=0.8)
    ax.set_xlabel(col)
    ax.set_ylabel("Density")
    ax.set_title("Return distribution")
    return fig


def plot_acf(acf_df: pl.DataFrame) -> Figure:
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(acf_df["lag"].to_list(), acf_df["acf"].to_list(), width=0.8)
    ax.axhline(0.0, color="black", lw=0.8)
    ax.set_xlabel("Lag")
    ax.set_ylabel("ACF")
    ax.set_title("Autocorrelation")
    return fig


def plot_rolling_volatility(df: pl.DataFrame, vol_col: str, time_col: str = "open_time") -> Figure:
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(df[time_col].to_list(), df[vol_col].to_list(), lw=0.7)
    ax.set_xlabel("Time (UTC)")
    ax.set_ylabel(vol_col)
    ax.set_title("Rolling volatility")
    return fig
