"""Shared pytest fixtures for civic-common."""

from __future__ import annotations

import os

import pytest

_DEFAULT_ENV: dict[str, str] = {
    "POSTGRES_HOST": "localhost",
    "POSTGRES_PORT": "5432",
    "POSTGRES_USER": "civic",
    "POSTGRES_PASSWORD": "civic_dev_pw",
    "POSTGRES_DB": "civic",
    "NEO4J_URI": "bolt://localhost:7687",
    "NEO4J_USER": "neo4j",
    "NEO4J_PASSWORD": "civic_dev_pw",
    "OPENSEARCH_URL": "http://localhost:9200",
    "OPENSEARCH_USER": "admin",
    "OPENSEARCH_PASSWORD": "admin",
    "MINIO_ENDPOINT": "localhost:9000",
    "MINIO_ACCESS_KEY": "minioadmin",
    "MINIO_SECRET_KEY": "minioadmin",
    "MINIO_BUCKET_ARCHIVE": "civic-archive",
    "ENV": "test",
}
for _k, _v in _DEFAULT_ENV.items():
    os.environ.setdefault(_k, _v)


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> None:
    """Guarantee every test starts from a fresh Settings cache."""

    from civic_common.settings import get_settings

    get_settings.cache_clear()
