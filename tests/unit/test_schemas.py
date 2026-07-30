import polars as pl
import pytest
from pandera.errors import SchemaError, SchemaErrors

from perp_lab.validation.schemas import validate_klines


def test_valid_klines_pass(klines_5m):
    out = validate_klines(klines_5m)
    assert out.height == klines_5m.height


def test_negative_volume_fails(klines_5m):
    bad = klines_5m.with_columns(
        pl.when(pl.int_range(pl.len()) == 0).then(-1.0).otherwise(pl.col("volume")).alias("volume")
    )
    with pytest.raises((SchemaError, SchemaErrors)):
        validate_klines(bad)


def test_extra_column_rejected_by_strict_schema(klines_5m):
    bad = klines_5m.with_columns(pl.lit(1).alias("unexpected"))
    with pytest.raises((SchemaError, SchemaErrors)):
        validate_klines(bad)
