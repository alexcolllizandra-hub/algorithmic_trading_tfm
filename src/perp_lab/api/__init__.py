"""Read-only quantitative API for the perp-lab research platform.

FastAPI application that adapts existing run artifacts (written by
``perp_lab.search``) and validated market manifests into versioned JSON. It is
the *authoritative* adapter: the frontend never reads artifacts or re-implements
backtesting/search logic. All heavy interpretation reuses
``perp_lab.dashboard.loader`` and ``perp_lab.data`` — never a second engine.
"""

API_VERSION = "v1"

__all__ = ["API_VERSION"]
