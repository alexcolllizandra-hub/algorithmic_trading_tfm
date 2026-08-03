"""Coherent academic figure style shared by every EDA notebook.

The palette is colour-blind-friendly (Okabe-Ito derived) and fixes a single
colour per asset and per timeframe so figures are visually consistent across
the whole thesis. Import :func:`apply_house_style` once at the top of a
notebook (after importing matplotlib) to configure global rcParams.
"""

from __future__ import annotations

import matplotlib as mpl

# Stable, colour-blind-friendly asset colours (Okabe-Ito).
ASSET_COLORS: dict[str, str] = {
    "BTCUSDT": "#E69F00",  # orange
    "ETHUSDT": "#0072B2",  # blue
}

# Distinct colours for the three timeframes.
TIMEFRAME_COLORS: dict[str, str] = {
    "5m": "#009E73",  # green
    "15m": "#CC79A7",  # magenta
    "1h": "#D55E00",  # vermillion
}

# Volatility-regime traffic-light palette (low = calm, high = stressed).
REGIME_COLORS: dict[str, str] = {
    "low": "#2CA02C",  # green
    "medium": "#E6A817",  # amber
    "high": "#D62728",  # red
}

_NEUTRAL = "#4D4D4D"


def asset_color(symbol: str, default: str = _NEUTRAL) -> str:
    """Return the fixed house colour for an asset symbol."""
    return ASSET_COLORS.get(symbol.upper(), default)


def timeframe_color(timeframe: str, default: str = _NEUTRAL) -> str:
    """Return the fixed house colour for a timeframe token."""
    return TIMEFRAME_COLORS.get(timeframe, default)


def regime_color(regime: str, default: str = _NEUTRAL) -> str:
    """Return the traffic-light colour for a low/medium/high volatility regime."""
    return REGIME_COLORS.get(regime, default)


def apply_house_style() -> None:
    """Configure global matplotlib rcParams for thesis-quality figures.

    Idempotent: safe to call at the start of every notebook. Uses 300 DPI for
    both on-screen rendering and raster export and avoids unnecessary chart
    decoration.
    """
    mpl.rcParams.update(
        {
            "figure.figsize": (9.0, 4.5),
            "figure.dpi": 120,
            "savefig.dpi": 300,
            "savefig.bbox": "tight",
            "font.size": 11,
            "font.family": "DejaVu Sans",
            "axes.titlesize": 12,
            "axes.titleweight": "bold",
            "axes.labelsize": 11,
            "axes.grid": True,
            "axes.axisbelow": True,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "grid.color": "#DDDDDD",
            "grid.linewidth": 0.6,
            "legend.frameon": False,
            "legend.fontsize": 10,
            "lines.linewidth": 1.2,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
        }
    )
