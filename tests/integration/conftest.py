"""Env setup for hermetic Phase-3+4 integration tests.

``apps/api/src/api/main.py`` instantiates :class:`civic_common.Settings`
at import time, which requires all backing-store env vars to be set.
These defaults make the FastAPI route importable during test
collection without a live docker stack — tests that actually reach the
services are marked ``@pytest.mark.integration`` and skipped by
default.
"""

from __future__ import annotations

import os

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
