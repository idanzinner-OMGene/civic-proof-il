"""Shared Postgres / Neo4j / OpenSearch / MinIO clients.

All services import from here rather than constructing drivers/clients
themselves, so the env-var contract and connection conventions live in
exactly one place.
"""

from __future__ import annotations

from . import minio_client, neo4j, opensearch, postgres
from .archive import (
    SOURCE_FAMILIES,
    ArchiveCoord,
    build_archive_uri,
    content_sha256,
    parse_archive_uri,
)

__all__ = [
    "ArchiveCoord",
    "SOURCE_FAMILIES",
    "build_archive_uri",
    "content_sha256",
    "minio_client",
    "neo4j",
    "opensearch",
    "parse_archive_uri",
    "postgres",
]
