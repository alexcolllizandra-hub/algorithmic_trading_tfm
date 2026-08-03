"""Pydantic models describing the data contract and analysis configuration."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from perp_lab.utils.timeutils import TIMEFRAME_TO_MS


class ContractSpec(BaseModel):
    """A single perpetual contract and the earliest date its data exists."""

    model_config = ConfigDict(frozen=True)

    symbol: str
    listing_date: date
    description: str = ""

    @field_validator("symbol")
    @classmethod
    def _upper(cls, v: str) -> str:
        return v.strip().upper()


class HoldoutSpec(BaseModel):
    """Definition of the frozen final holdout period.

    Either an explicit ``start`` date or a number of ``months`` counted back
    from the data-contract cutoff. The holdout is never used for EDA-driven
    decisions or parameter selection.
    """

    model_config = ConfigDict(frozen=True)

    months: int = Field(default=6, ge=1, le=48)
    start: date | None = None

    def start_date(self, cutoff: date) -> date:
        """Resolve the holdout start given the contract ``cutoff`` date."""
        if self.start is not None:
            return self.start
        # Approximate months as 30-day steps; the exact boundary is snapped to a
        # bar during dataset construction. Documented in docs/data_contract.md.
        return cutoff - timedelta(days=30 * self.months)


class Paths(BaseModel):
    """Filesystem layout for the data lake and generated reports."""

    data_root: Path = Path("data")
    reports_root: Path = Path("reports")

    @property
    def raw_dir(self) -> Path:
        return self.data_root / "raw"

    @property
    def validated_dir(self) -> Path:
        return self.data_root / "validated"

    @property
    def processed_dir(self) -> Path:
        return self.data_root / "processed"

    @property
    def manifests_dir(self) -> Path:
        return self.data_root / "manifests"

    @property
    def figures_dir(self) -> Path:
        return self.reports_root / "figures"

    @property
    def tables_dir(self) -> Path:
        return self.reports_root / "tables"

    def ensure(self) -> None:
        """Create every data/report directory if missing."""
        for directory in (
            self.raw_dir,
            self.validated_dir,
            self.processed_dir,
            self.manifests_dir,
            self.figures_dir,
            self.tables_dir,
        ):
            directory.mkdir(parents=True, exist_ok=True)


class DataContract(BaseModel):
    """The formal, versioned description of the market data used in the thesis.

    See ``docs/data_contract.md`` for the human-readable rationale.
    """

    model_config = ConfigDict(frozen=True)

    version: str = "0.1.0"
    exchange: str = "binance"
    market_type: str = "um"  # Binance USDT-M (linear) futures
    base_timeframe: str = "5m"
    derived_timeframes: tuple[str, ...] = ("15m", "1h")
    aux_streams: tuple[str, ...] = ("fundingRate", "markPriceKlines")
    symbols: tuple[ContractSpec, ...]
    cutoff_date: date
    holdout: HoldoutSpec = HoldoutSpec()

    @field_validator("base_timeframe")
    @classmethod
    def _known_base(cls, v: str) -> str:
        if v not in TIMEFRAME_TO_MS:
            raise ValueError(f"Unknown base timeframe {v!r}")
        return v

    @field_validator("derived_timeframes")
    @classmethod
    def _known_derived(cls, v: tuple[str, ...]) -> tuple[str, ...]:
        for tf in v:
            if tf not in TIMEFRAME_TO_MS:
                raise ValueError(f"Unknown derived timeframe {tf!r}")
        return v

    @model_validator(mode="after")
    def _check_consistency(self) -> DataContract:
        if not self.symbols:
            raise ValueError("At least one contract must be specified.")
        base_ms = TIMEFRAME_TO_MS[self.base_timeframe]
        for tf in self.derived_timeframes:
            derived_ms = TIMEFRAME_TO_MS[tf]
            if derived_ms <= base_ms:
                raise ValueError(
                    f"Derived timeframe {tf} must be coarser than the base "
                    f"timeframe {self.base_timeframe}."
                )
            if derived_ms % base_ms != 0:
                raise ValueError(
                    f"Derived timeframe {tf} must be an integer multiple of "
                    f"the base timeframe {self.base_timeframe}."
                )
        for contract in self.symbols:
            if contract.listing_date >= self.cutoff_date:
                raise ValueError(
                    f"cutoff_date {self.cutoff_date} must be after the listing "
                    f"date of {contract.symbol} ({contract.listing_date})."
                )
        holdout_start = self.holdout.start_date(self.cutoff_date)
        if holdout_start >= self.cutoff_date:
            raise ValueError("Holdout start must precede the cutoff date.")
        return self

    def symbol_names(self) -> tuple[str, ...]:
        return tuple(c.symbol for c in self.symbols)

    def get(self, symbol: str) -> ContractSpec:
        symbol = symbol.strip().upper()
        for contract in self.symbols:
            if contract.symbol == symbol:
                return contract
        raise KeyError(f"{symbol} is not part of the data contract.")

    def all_timeframes(self) -> tuple[str, ...]:
        return (self.base_timeframe, *self.derived_timeframes)


class EdaConfig(BaseModel):
    """Parameters for the reusable EDA library (windows, thresholds, etc.)."""

    model_config = ConfigDict(frozen=True)

    return_kind: str = "log"  # "log" or "simple"
    rolling_vol_windows: tuple[int, ...] = (24, 96, 672)
    acf_max_lag: int = 100
    # Bars-per-year for 24/7 annualization, keyed by timeframe.
    trading_days_per_year: int = 365
    # Threshold (in rolling-sigma units) above which a return is *flagged* as
    # extreme. Flagged, never dropped.
    extreme_return_sigma: float = 10.0
    # Window (in calendar days) for rolling distribution moments (vol/skew/kurt)
    # reported on the 1h series. Economically interpretable default of 30 days.
    rolling_moment_window_days: int = 30

    @field_validator("return_kind")
    @classmethod
    def _valid_kind(cls, v: str) -> str:
        if v not in {"log", "simple"}:
            raise ValueError("return_kind must be 'log' or 'simple'")
        return v
