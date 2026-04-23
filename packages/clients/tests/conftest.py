"""Shared pytest fixtures for the civic-clients test suite."""

from __future__ import annotations

import os

import pytest

# Populate env at conftest import time so that any module-level
# ``get_settings()`` call during collection sees a valid environment.
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
def _reset_settings_cache() -> None:
    """Ensure ``get_settings`` always reflects the current env."""

    from civic_common.settings import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
