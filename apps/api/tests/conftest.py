"""Shared pytest fixtures for the civic-api test suite."""

from __future__ import annotations

import os

import pytest

# NOTE: these defaults run at conftest-load time — before pytest imports any
# test module. ``apps/api/src/api/main.py`` instantiates ``Settings()`` at
# module level (``app = create_app()``), so env vars MUST be present before
# ``from api.main import app`` runs during collection. The per-test
# ``_env`` autouse fixture below additionally monkey-patches them for clean
# isolation and clears the ``get_settings`` lru_cache.
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
def _env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Populate all required env vars before Settings is instantiated."""

    monkeypatch.setenv("POSTGRES_HOST", "localhost")
    monkeypatch.setenv("POSTGRES_PORT", "5432")
    monkeypatch.setenv("POSTGRES_USER", "civic")
    monkeypatch.setenv("POSTGRES_PASSWORD", "civic_dev_pw")
    monkeypatch.setenv("POSTGRES_DB", "civic")
    monkeypatch.setenv("NEO4J_URI", "bolt://localhost:7687")
    monkeypatch.setenv("NEO4J_USER", "neo4j")
    monkeypatch.setenv("NEO4J_PASSWORD", "civic_dev_pw")
    monkeypatch.setenv("OPENSEARCH_URL", "http://localhost:9200")
    monkeypatch.setenv("OPENSEARCH_USER", "admin")
    monkeypatch.setenv("OPENSEARCH_PASSWORD", "admin")
    monkeypatch.setenv("MINIO_ENDPOINT", "localhost:9000")
    monkeypatch.setenv("MINIO_ACCESS_KEY", "minioadmin")
    monkeypatch.setenv("MINIO_SECRET_KEY", "minioadmin")
    monkeypatch.setenv("MINIO_BUCKET_ARCHIVE", "civic-archive")
    monkeypatch.setenv("ENV", "test")

    from api.settings import get_settings

    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def _stub_pings(monkeypatch: pytest.MonkeyPatch) -> None:
    """By default, patch all four ping_* helpers to report healthy."""

    from api.clients import (
        minio_client,
        neo4j_client,
        opensearch_client,
        postgres,
    )

    monkeypatch.setattr(postgres, "ping_postgres", lambda: True)
    monkeypatch.setattr(neo4j_client, "ping_neo4j", lambda: True)
    monkeypatch.setattr(opensearch_client, "ping_opensearch", lambda: True)
    monkeypatch.setattr(minio_client, "ping_minio", lambda: True)
