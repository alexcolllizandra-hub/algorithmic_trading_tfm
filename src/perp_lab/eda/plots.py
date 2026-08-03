"""Matplotlib helpers producing thesis-ready figures.

Functions return a :class:`matplotlib.figure.Figure` so callers (notebooks or
the figure-generation skill) control saving and captioning. Use
:func:`save_figure` for a consistent export.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")  # headless-safe; notebooks can override with %matplotlib

import matplotlib.pyplot as plt
import numpy as np
import polars as pl
from matplotlib.figure import Figure
from scipy import stats


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


def plot_ecdf(df: pl.DataFrame, col: str = "log_return", title: str = "Empirical CDF") -> Figure:
    """Plot the empirical cumulative distribution of a column."""
    values = np.sort(df.select(pl.col(col)).drop_nulls().to_series().to_numpy())
    y = np.arange(1, values.size + 1) / values.size
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.step(values, y, where="post")
    ax.set_xlabel(col)
    ax.set_ylabel("Cumulative probability")
    ax.set_title(title)
    return fig


def plot_qq(df: pl.DataFrame, col: str = "log_return", title: str = "Normal Q-Q") -> Figure:
    """Q-Q plot of a return column against a standard-normal reference."""
    values = df.select(pl.col(col)).drop_nulls().to_series().to_numpy()
    fig, ax = plt.subplots(figsize=(5.5, 5.5))
    probplot_result: Any = stats.probplot(values, dist="norm")
    (osm, osr), (slope, intercept, _r) = probplot_result
    osm_arr = np.asarray(osm, dtype=float)
    ax.scatter(osm_arr, np.asarray(osr, dtype=float), s=4, alpha=0.4)
    ax.plot(osm_arr, float(slope) * osm_arr + float(intercept), color="black", lw=1.0)
    ax.set_xlabel("Theoretical quantiles (normal)")
    ax.set_ylabel("Sample quantiles")
    ax.set_title(title)
    return fig


def plot_drawdown(
    df: pl.DataFrame, dd_col: str = "drawdown", time_col: str = "open_time"
) -> Figure:
    """Filled underwater (drawdown) curve."""
    times = df[time_col].to_list()
    dd = df[dd_col].to_list()
    fig, ax = plt.subplots(figsize=(10, 3.5))
    ax.fill_between(times, dd, 0.0, color="#D55E00", alpha=0.5, step="pre")
    ax.set_xlabel("Time (UTC)")
    ax.set_ylabel("Drawdown")
    ax.set_title("Underwater curve")
    return fig


def plot_seasonality(
    df: pl.DataFrame, by: str, value_col: str = "mean", err_col: str | None = "stderr"
) -> Figure:
    """Bar plot of a seasonality table (``by`` in {'hour','weekday'}) with error bars."""
    x = df[by].to_list()
    y = df[value_col].to_list()
    yerr = df[err_col].to_list() if err_col and err_col in df.columns else None
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.bar(x, y, yerr=yerr, capsize=2, color="#0072B2", alpha=0.85)
    ax.axhline(0.0, color="black", lw=0.8)
    ax.set_xlabel(f"{by} (UTC)" if by == "hour" else by)
    ax.set_ylabel(value_col)
    ax.set_title(f"Seasonality by {by}")
    return fig
