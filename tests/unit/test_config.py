from datetime import date

import pytest
from pydantic import ValidationError

from perp_lab.config import load_data_contract
from perp_lab.config.models import ContractSpec, DataContract, HoldoutSpec

CONFIG_PATH = "configs/data_contract.yaml"


def test_load_repo_data_contract():
    contract = load_data_contract(CONFIG_PATH)
    assert contract.exchange == "binance"
    assert contract.market_type == "um"
    assert contract.base_timeframe == "5m"
    assert set(contract.symbol_names()) == {"BTCUSDT", "ETHUSDT"}
    assert contract.derived_timeframes == ("15m", "1h")


def test_holdout_before_cutoff():
    contract = load_data_contract(CONFIG_PATH)
    start = contract.holdout.start_date(contract.cutoff_date)
    assert start < contract.cutoff_date


def _base_kwargs():
    return {
        "symbols": (ContractSpec(symbol="BTCUSDT", listing_date=date(2019, 9, 8)),),
        "cutoff_date": date(2026, 7, 1),
        "holdout": HoldoutSpec(months=6),
    }


def test_reject_derived_finer_than_base():
    with pytest.raises(ValidationError):
        DataContract(base_timeframe="1h", derived_timeframes=("5m",), **_base_kwargs())


def test_reject_cutoff_before_listing():
    with pytest.raises(ValidationError):
        DataContract(
            symbols=(ContractSpec(symbol="BTCUSDT", listing_date=date(2027, 1, 1)),),
            cutoff_date=date(2026, 7, 1),
            holdout=HoldoutSpec(months=6),
        )


def test_symbol_is_uppercased():
    spec = ContractSpec(symbol="btcusdt", listing_date=date(2019, 9, 8))
    assert spec.symbol == "BTCUSDT"


def test_get_unknown_symbol_raises():
    contract = load_data_contract(CONFIG_PATH)
    with pytest.raises(KeyError):
        contract.get("DOGEUSDT")
