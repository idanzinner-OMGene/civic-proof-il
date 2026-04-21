"""Shared fixtures for Phase 0 smoke tests.

The ``_HOST`` env-var variants let smoke tests running on the host hit
published docker-compose ports while still honoring the in-container
hostnames in ``.env``. If unset, defaults point at ``localhost``.
"""

from __future__ import annotations

import os
import time

import httpx
import pytest

API_URL = os.environ.get("API_URL", "http://localhost:8000")

POSTGRES = {
    "host": os.environ.get("POSTGRES_HOST_HOST", "localhost"),
    "port": int(os.environ.get("POSTGRES_PORT", "5432")),
    "user": os.environ.get("POSTGRES_USER", "civic"),
    "password": os.environ.get("POSTGRES_PASSWORD", "civic_dev_pw"),
    "dbname": os.environ.get("POSTGRES_DB", "civic"),
}

NEO4J = {
    "uri": os.environ.get("NEO4J_URI_HOST", "bolt://localhost:7687"),
    "auth": (
        os.environ.get("NEO4J_USER", "neo4j"),
        os.environ.get("NEO4J_PASSWORD", "civic_dev_pw"),
    ),
}

OPENSEARCH_URL = os.environ.get("OPENSEARCH_URL_HOST", "http://localhost:9200")

MINIO = {
    "endpoint": os.environ.get("MINIO_ENDPOINT_HOST", "localhost:9000"),
    "access_key": os.environ.get("MINIO_ACCESS_KEY", "minioadmin"),
    "secret_key": os.environ.get("MINIO_SECRET_KEY", "minioadmin"),
}


@pytest.fixture(scope="session")
def api_url() -> str:
    return API_URL


@pytest.fixture(scope="session")
def wait_for_api() -> None:
    deadline = time.time() + 120
    while time.time() < deadline:
        try:
            r = httpx.get(f"{API_URL}/healthz", timeout=2)
            if r.status_code == 200:
                return
        except Exception:
            pass
        time.sleep(2)
    pytest.skip("API did not come up within 120s")
