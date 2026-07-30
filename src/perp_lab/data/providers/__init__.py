"""Market-data providers.

- :class:`BinanceVisionBulkProvider` -- bulk historical download from
  ``data.binance.vision`` (the workhorse for the thesis dataset).
- :class:`CcxtIncrementalProvider` -- appends only the most recent candles
  beyond the last archived month, via CCXT public endpoints.
"""

from perp_lab.data.providers.base import (
    FUNDING_SCHEMA,
    KLINE_SCHEMA,
    ExchangeDataProvider,
)
from perp_lab.data.providers.binance_vision import BinanceVisionBulkProvider
from perp_lab.data.providers.ccxt_incremental import CcxtIncrementalProvider

__all__ = [
    "FUNDING_SCHEMA",
    "KLINE_SCHEMA",
    "BinanceVisionBulkProvider",
    "CcxtIncrementalProvider",
    "ExchangeDataProvider",
]
