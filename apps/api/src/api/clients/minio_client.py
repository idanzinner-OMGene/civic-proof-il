"""MinIO client helpers."""

from __future__ import annotations

from functools import lru_cache

from minio import Minio

from ..settings import get_settings


@lru_cache
def get_minio_client() -> Minio:
    """Return a cached MinIO client."""

    settings = get_settings()
    return Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=False,
    )


def ping_minio() -> bool:
    """Return True if we can list buckets on the MinIO endpoint."""

    try:
        get_minio_client().list_buckets()
        return True
    except Exception:
        return False
