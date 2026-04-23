"""MinIO (S3-compatible) client factory + archive write helper."""

from __future__ import annotations

import io
from functools import lru_cache

from minio import Minio

from civic_common.settings import get_settings

from .archive import parse_archive_uri

__all__ = [
    "ensure_bucket",
    "make_client",
    "ping",
    "put_archive_object",
]


@lru_cache(maxsize=1)
def make_client() -> Minio:
    """Return the process-wide cached MinIO client.

    TLS is off in dev (our compose stack exposes MinIO on plain HTTP).
    Production overrides should pass an HTTPS endpoint and pass
    ``secure=True`` via a future settings flag.
    """

    s = get_settings()
    return Minio(
        s.minio_endpoint,
        access_key=s.minio_access_key,
        secret_key=s.minio_secret_key,
        secure=False,
    )


def ping() -> bool:
    """Return ``True`` if we can enumerate buckets on the endpoint."""

    try:
        make_client().list_buckets()
        return True
    except Exception:
        return False


def ensure_bucket(name: str | None = None) -> str:
    """Create the archive bucket if it doesn't already exist.

    Defaults to ``Settings.minio_bucket_archive``. Returns the bucket name
    actually used so callers can log / assert on it.
    """

    client = make_client()
    bucket = name or get_settings().minio_bucket_archive
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)
    return bucket


def put_archive_object(uri: str, content: bytes, content_type: str) -> str:
    """Write ``content`` to the object referenced by ``uri``.

    The URI is parsed via :func:`civic_clients.archive.parse_archive_uri`
    so the bucket/source-family/date/hash/extension layout is validated
    before we touch the store. The bucket in the URI must match the
    configured ``MINIO_BUCKET_ARCHIVE`` — cross-bucket writes are a bug.

    Returns the ``object_name`` (i.e. the URI minus ``s3://<bucket>/``)
    on success.
    """

    coord = parse_archive_uri(uri)
    configured = get_settings().minio_bucket_archive
    if coord.bucket != configured:
        raise ValueError(
            f"uri bucket {coord.bucket!r} does not match MINIO_BUCKET_ARCHIVE "
            f"{configured!r}"
        )

    object_name = (
        f"{coord.source_family}/{coord.year:04d}/{coord.month:02d}/"
        f"{coord.day:02d}/{coord.sha256}.{coord.extension}"
    )

    client = make_client()
    client.put_object(
        bucket_name=coord.bucket,
        object_name=object_name,
        data=io.BytesIO(content),
        length=len(content),
        content_type=content_type,
    )
    return object_name
