"""MinIO client — thin re-export from :mod:`civic_clients.minio_client`."""

from __future__ import annotations

from civic_clients.minio_client import ensure_bucket, make_client, ping, put_archive_object

get_minio_client = make_client
ping_minio = ping

__all__ = [
    "ensure_bucket",
    "get_minio_client",
    "make_client",
    "ping",
    "ping_minio",
    "put_archive_object",
]
