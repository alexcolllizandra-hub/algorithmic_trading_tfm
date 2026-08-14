"""Tests for the object store: local round-trips, and Supabase refusing to guess.

No test here touches the network. The Supabase backend is exercised only for the
one behaviour that matters without credentials: failing loudly and naming what
is missing.
"""

from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest

from perp_lab.catalog.storage import (
    BACKEND_ENV,
    LOCAL_ROOT_ENV,
    SUPABASE_BUCKET_ENV,
    SUPABASE_KEY_ENV,
    SUPABASE_URL_ENV,
    LocalObjectStore,
    ObjectNotFoundError,
    ObjectStore,
    ObjectStoreCredentialsError,
    ObjectStoreError,
    SupabaseObjectStore,
    inspect_parquet,
    normalise_key,
    open_object_store,
)
from perp_lab.utils.hashing import sha256_bytes

SUPABASE_VARS = (SUPABASE_URL_ENV, SUPABASE_KEY_ENV, SUPABASE_BUCKET_ENV)


def _equity_parquet(tmp_path: Path, rows: int = 24) -> Path:
    path = tmp_path / "equity.parquet"
    pl.DataFrame(
        {"bar": list(range(rows)), "equity": [1.0 + 0.01 * i for i in range(rows)]}
    ).write_parquet(path)
    return path


def test_local_store_round_trips_bytes(tmp_path: Path) -> None:
    store = LocalObjectStore(tmp_path / "objects")
    payload = b"per-bar returns, but smaller"

    metadata = store.put("runs/r1/notes.txt", payload, media_type="text/plain")

    assert store.exists("runs/r1/notes.txt")
    assert store.get("runs/r1/notes.txt") == payload
    assert metadata.byte_size == len(payload)
    assert metadata.sha256 == sha256_bytes(payload)
    assert metadata.backend == "local"
    assert metadata.row_count is None


def test_local_store_reports_row_count_and_schema_for_parquet(tmp_path: Path) -> None:
    store = LocalObjectStore(tmp_path / "objects")
    source = _equity_parquet(tmp_path, rows=24)

    metadata = store.put_file("runs/r1/equity.parquet", source)

    assert metadata.row_count == 24
    assert metadata.arrow_schema is not None
    assert set(metadata.arrow_schema) == {"bar", "equity"}
    assert metadata.arrow_schema["equity"] == "double"
    assert metadata.sha256 == sha256_bytes(source.read_bytes())


def test_local_store_exposes_a_path_duckdb_can_read(tmp_path: Path) -> None:
    store = LocalObjectStore(tmp_path / "objects")
    store.put_file("runs/r1/equity.parquet", _equity_parquet(tmp_path))

    resolved = store.local_path("runs/r1/equity.parquet")

    assert resolved.is_file()
    assert pl.read_parquet(resolved).height == 24


def test_reading_a_missing_key_raises_rather_than_returning_empty(tmp_path: Path) -> None:
    store = LocalObjectStore(tmp_path / "objects")

    assert store.exists("nothing/here.parquet") is False
    with pytest.raises(ObjectNotFoundError):
        store.get("nothing/here.parquet")


def test_keys_that_escape_the_configured_root_are_rejected(tmp_path: Path) -> None:
    store = LocalObjectStore(tmp_path / "objects")

    with pytest.raises(ValueError):
        store.put("../outside.txt", b"nope")
    with pytest.raises(ValueError):
        normalise_key("   ")


def test_inspecting_a_non_parquet_payload_admits_it_knows_nothing() -> None:
    rows, schema = inspect_parquet(b'{"not": "parquet"}')

    assert rows is None
    assert schema is None


def test_the_default_backend_needs_no_credentials(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv(BACKEND_ENV, raising=False)
    monkeypatch.setenv(LOCAL_ROOT_ENV, str(tmp_path / "store"))

    store = open_object_store()

    assert isinstance(store, LocalObjectStore)
    assert isinstance(store, ObjectStore)
    assert store.root == tmp_path / "store"


def test_supabase_store_raises_a_named_error_when_its_variables_are_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for variable in SUPABASE_VARS:
        monkeypatch.delenv(variable, raising=False)

    with pytest.raises(ObjectStoreCredentialsError) as excinfo:
        SupabaseObjectStore.from_env()

    message = str(excinfo.value)
    for variable in SUPABASE_VARS:
        assert variable in message


def test_selecting_the_supabase_backend_without_credentials_fails_loudly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(BACKEND_ENV, "supabase")
    for variable in SUPABASE_VARS:
        monkeypatch.delenv(variable, raising=False)

    with pytest.raises(ObjectStoreCredentialsError):
        open_object_store()


def test_a_partially_configured_supabase_store_names_only_what_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(SUPABASE_URL_ENV, "https://example.invalid")
    monkeypatch.delenv(SUPABASE_KEY_ENV, raising=False)
    monkeypatch.delenv(SUPABASE_BUCKET_ENV, raising=False)

    with pytest.raises(ObjectStoreCredentialsError) as excinfo:
        SupabaseObjectStore.from_env()

    message = str(excinfo.value)
    assert SUPABASE_KEY_ENV in message
    assert SUPABASE_BUCKET_ENV in message
    assert SUPABASE_URL_ENV not in message


def test_an_unknown_backend_name_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(BACKEND_ENV, "s3")

    with pytest.raises(ObjectStoreError):
        open_object_store()
