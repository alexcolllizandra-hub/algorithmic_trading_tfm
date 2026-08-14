"""Object storage for the bulk evidence, with a local backend as the default.

Equity curves, per-bar returns, trade blotters and Monte Carlo trajectories are
matrices with millions of cells. They belong in Parquet, addressed by key, not
inlined into a database column. This module is the seam: one small protocol, a
local filesystem implementation that needs no account, and a Supabase Storage
implementation that is used only when its credentials are present in the
environment.

Every ``put`` returns an :class:`ObjectMetadata` carrying exactly what an
``artifacts`` row needs — byte size, SHA-256, row count and Arrow schema for
Parquet payloads — so registering a file in the catalogue cannot drift from
writing it.

No credential is ever constructed, defaulted or guessed here. The Supabase
backend reads ``SUPABASE_URL``, ``SUPABASE_SERVICE_ROLE_KEY`` and
``SUPABASE_STORAGE_BUCKET`` and refuses to be built without them, naming the
variables that are missing.
"""

from __future__ import annotations

import io
import os
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Protocol, runtime_checkable

import httpx
import pyarrow.parquet as pq

from perp_lab.utils.hashing import sha256_bytes

BACKEND_ENV = "PERP_LAB_OBJECT_STORE_BACKEND"
LOCAL_ROOT_ENV = "PERP_LAB_OBJECT_STORE_ROOT"
SUPABASE_URL_ENV = "SUPABASE_URL"
SUPABASE_KEY_ENV = "SUPABASE_SERVICE_ROLE_KEY"
SUPABASE_BUCKET_ENV = "SUPABASE_STORAGE_BUCKET"

DEFAULT_LOCAL_ROOT = Path("data/object_store")
DEFAULT_TIMEOUT_SECONDS = 30.0

LOCAL_BACKEND = "local"
SUPABASE_BACKEND = "supabase"


class ObjectStoreError(RuntimeError):
    """Base class for every object-store failure."""


class ObjectStoreCredentialsError(ObjectStoreError):
    """Raised when a backend is requested without the environment it requires."""


class ObjectNotFoundError(ObjectStoreError):
    """Raised when a key does not exist in the store."""


@dataclass(frozen=True)
class ObjectMetadata:
    """Everything the catalogue must record about a stored object."""

    key: str
    uri: str
    backend: str
    bucket: str
    byte_size: int
    sha256: str
    row_count: int | None = None
    arrow_schema: dict[str, str] | None = None
    media_type: str | None = None


@runtime_checkable
class ObjectStore(Protocol):
    """The four operations the catalogue needs from a blob store."""

    backend: str
    bucket: str

    def put(self, key: str, data: bytes, *, media_type: str | None = None) -> ObjectMetadata: ...

    def get(self, key: str) -> bytes: ...

    def exists(self, key: str) -> bool: ...

    def url(self, key: str) -> str: ...


def normalise_key(key: str) -> str:
    """Validate an object key: POSIX-relative, no traversal, no empty segments.

    Keys become paths on the local backend and URL segments on Supabase, so a
    key containing ``..`` would let a caller write outside the configured root.
    """
    cleaned = key.strip().replace("\\", "/").lstrip("/")
    if not cleaned:
        raise ValueError("Object key must not be empty.")
    parts = PurePosixPath(cleaned).parts
    if any(part in {"..", "."} for part in parts):
        raise ValueError(f"Object key must not contain relative segments: {key!r}")
    return "/".join(parts)


def describe_existing_file(path: str | Path, *, media_type: str | None = None) -> ObjectMetadata:
    """Index a file where it already lives. Does not copy or move it.

    The scientific evidence stays in ``artifacts/`` and ``reports/``. The
    catalogue records where those bytes are, how large they are and what they
    hash to, so re-ingesting the same tree updates the index and never produces
    a second copy that could drift from the original.
    """
    from perp_lab.utils.hashing import sha256_file

    resolved = Path(path).resolve()
    if not resolved.is_file():
        raise ObjectNotFoundError(f"No file to index at {resolved}.")
    row_count, schema = (None, None)
    if resolved.suffix == ".parquet":
        try:
            parquet_file = pq.ParquetFile(resolved)
            row_count = int(parquet_file.metadata.num_rows)
            arrow = parquet_file.schema_arrow
            schema = {
                name: str(dtype) for name, dtype in zip(arrow.names, arrow.types, strict=True)
            }
        except Exception:
            row_count, schema = None, None
    return ObjectMetadata(
        key=resolved.as_posix(),
        uri=resolved.as_uri(),
        backend=LOCAL_BACKEND,
        bucket="",
        byte_size=resolved.stat().st_size,
        sha256=sha256_file(resolved),
        row_count=row_count,
        arrow_schema=schema,
        media_type=media_type,
    )


def inspect_parquet(data: bytes) -> tuple[int | None, dict[str, str] | None]:
    """Row count and column types of a Parquet payload, from its footer.

    Returns ``(None, None)`` for anything that is not readable Parquet; a JSON
    report has no row count, and inventing one would be worse than admitting it.
    """
    try:
        parquet_file = pq.ParquetFile(io.BytesIO(data))
    except Exception:
        return None, None
    schema = parquet_file.schema_arrow
    return int(parquet_file.metadata.num_rows), {
        name: str(dtype) for name, dtype in zip(schema.names, schema.types, strict=True)
    }


def _describe(
    *, key: str, uri: str, backend: str, bucket: str, data: bytes, media_type: str | None
) -> ObjectMetadata:
    row_count, schema = inspect_parquet(data) if key.endswith(".parquet") else (None, None)
    return ObjectMetadata(
        key=key,
        uri=uri,
        backend=backend,
        bucket=bucket,
        byte_size=len(data),
        sha256=sha256_bytes(data),
        row_count=row_count,
        arrow_schema=schema,
        media_type=media_type,
    )


class LocalObjectStore:
    """Filesystem-backed store under a configurable root. The offline default.

    The root is a plain directory, so the artifacts a run already writes can be
    registered in place without being copied anywhere.
    """

    backend = LOCAL_BACKEND

    def __init__(self, root: str | Path | None = None, *, bucket: str = "") -> None:
        configured = root if root is not None else os.environ.get(LOCAL_ROOT_ENV) or None
        self.root = Path(configured) if configured is not None else DEFAULT_LOCAL_ROOT
        self.bucket = bucket

    def _path(self, key: str) -> Path:
        return self.root / normalise_key(key)

    def put(self, key: str, data: bytes, *, media_type: str | None = None) -> ObjectMetadata:
        normalised = normalise_key(key)
        path = self.root / normalised
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return _describe(
            key=normalised,
            uri=self.url(normalised),
            backend=self.backend,
            bucket=self.bucket,
            data=data,
            media_type=media_type,
        )

    def put_file(
        self, key: str, source: str | Path, *, media_type: str | None = None
    ) -> ObjectMetadata:
        """Copy a file already on disk into the store, under ``key``."""
        return self.put(key, Path(source).read_bytes(), media_type=media_type)

    def get(self, key: str) -> bytes:
        path = self._path(key)
        if not path.is_file():
            raise ObjectNotFoundError(f"No object at key {key!r} under {self.root}.")
        return path.read_bytes()

    def exists(self, key: str) -> bool:
        return self._path(key).is_file()

    def url(self, key: str) -> str:
        return self._path(key).resolve().as_uri()

    def local_path(self, key: str) -> Path:
        """The on-disk path of a key, so DuckDB can read it without a download."""
        return self._path(key)


class SupabaseObjectStore:
    """Supabase Storage over its REST API.

    Constructed only from explicit values or from :meth:`from_env`; there is no
    default URL, no default key and no default bucket, because a wrong guess
    would either fail confusingly or write somewhere unintended.
    """

    backend = SUPABASE_BACKEND

    def __init__(
        self,
        *,
        base_url: str,
        service_role_key: str,
        bucket: str,
        client: httpx.Client | None = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        missing = [
            name
            for name, value in (
                (SUPABASE_URL_ENV, base_url),
                (SUPABASE_KEY_ENV, service_role_key),
                (SUPABASE_BUCKET_ENV, bucket),
            )
            if not value
        ]
        if missing:
            raise ObjectStoreCredentialsError(_missing_message(missing))
        self.base_url = base_url.rstrip("/")
        self._key = service_role_key
        self.bucket = bucket
        self._client = client
        self._timeout = timeout

    @classmethod
    def from_env(cls, *, client: httpx.Client | None = None) -> SupabaseObjectStore:
        """Build from the environment, naming every variable that is absent."""
        base_url = os.environ.get(SUPABASE_URL_ENV, "").strip()
        service_role_key = os.environ.get(SUPABASE_KEY_ENV, "").strip()
        bucket = os.environ.get(SUPABASE_BUCKET_ENV, "").strip()
        missing = [
            name
            for name, value in (
                (SUPABASE_URL_ENV, base_url),
                (SUPABASE_KEY_ENV, service_role_key),
                (SUPABASE_BUCKET_ENV, bucket),
            )
            if not value
        ]
        if missing:
            raise ObjectStoreCredentialsError(_missing_message(missing))
        return cls(
            base_url=base_url, service_role_key=service_role_key, bucket=bucket, client=client
        )

    # -- HTTP plumbing ----------------------------------------------------- #

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._key}", "apikey": self._key}

    def _object_endpoint(self, key: str) -> str:
        return f"{self.base_url}/storage/v1/object/{self.bucket}/{normalise_key(key)}"

    def _request(
        self,
        method: str,
        url: str,
        *,
        content: bytes | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        headers = {**self._headers(), **(extra_headers or {})}
        if self._client is not None:
            return self._client.request(method, url, headers=headers, content=content)
        with httpx.Client(timeout=self._timeout) as client:
            return client.request(method, url, headers=headers, content=content)

    # -- ObjectStore ------------------------------------------------------- #

    def put(self, key: str, data: bytes, *, media_type: str | None = None) -> ObjectMetadata:
        normalised = normalise_key(key)
        response = self._request(
            "POST",
            self._object_endpoint(normalised),
            content=data,
            extra_headers={
                "content-type": media_type or "application/octet-stream",
                "x-upsert": "true",
            },
        )
        if response.status_code >= 400:
            raise ObjectStoreError(
                f"Supabase Storage rejected the upload of {normalised!r}: "
                f"{response.status_code} {response.text}"
            )
        return _describe(
            key=normalised,
            uri=self.url(normalised),
            backend=self.backend,
            bucket=self.bucket,
            data=data,
            media_type=media_type,
        )

    def get(self, key: str) -> bytes:
        response = self._request("GET", self._object_endpoint(key))
        if response.status_code == 404:
            raise ObjectNotFoundError(f"No object at key {key!r} in bucket {self.bucket!r}.")
        if response.status_code >= 400:
            raise ObjectStoreError(
                f"Supabase Storage rejected the download of {key!r}: "
                f"{response.status_code} {response.text}"
            )
        return response.content

    def exists(self, key: str) -> bool:
        response = self._request("HEAD", self._object_endpoint(key))
        return response.status_code < 400

    def url(self, key: str) -> str:
        return f"supabase://{self.bucket}/{normalise_key(key)}"


def _missing_message(missing: list[str]) -> str:
    return (
        "The Supabase object store needs credentials that are not set: "
        + ", ".join(missing)
        + ". Set them in the environment, or leave "
        + f"{BACKEND_ENV} unset to use the local object store, which needs none."
    )


def open_object_store(backend: str | None = None) -> ObjectStore:
    """Return the configured store; local unless Supabase is explicitly selected."""
    selected = (backend or os.environ.get(BACKEND_ENV) or LOCAL_BACKEND).strip().lower()
    if selected == LOCAL_BACKEND:
        return LocalObjectStore()
    if selected == SUPABASE_BACKEND:
        return SupabaseObjectStore.from_env()
    raise ObjectStoreError(
        f"Unknown object-store backend {selected!r}; expected "
        f"{LOCAL_BACKEND!r} or {SUPABASE_BACKEND!r}."
    )


__all__ = [
    "BACKEND_ENV",
    "LOCAL_BACKEND",
    "LOCAL_ROOT_ENV",
    "SUPABASE_BACKEND",
    "SUPABASE_BUCKET_ENV",
    "SUPABASE_KEY_ENV",
    "SUPABASE_URL_ENV",
    "LocalObjectStore",
    "ObjectMetadata",
    "ObjectNotFoundError",
    "ObjectStore",
    "ObjectStoreCredentialsError",
    "ObjectStoreError",
    "SupabaseObjectStore",
    "describe_existing_file",
    "inspect_parquet",
    "normalise_key",
    "open_object_store",
]
