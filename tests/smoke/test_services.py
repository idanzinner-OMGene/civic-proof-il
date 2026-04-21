"""Direct connectivity smoke tests for each backing store.

Client libraries are imported lazily via ``pytest.importorskip`` so that
collecting these tests does not require them to be installed.
"""

from __future__ import annotations

import pytest


def test_postgres_connectivity():
    psycopg = pytest.importorskip("psycopg")
    from .conftest import POSTGRES

    with psycopg.connect(**POSTGRES, connect_timeout=5) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            assert cur.fetchone()[0] == 1


def test_neo4j_connectivity():
    neo4j = pytest.importorskip("neo4j")
    from .conftest import NEO4J

    driver = neo4j.GraphDatabase.driver(NEO4J["uri"], auth=NEO4J["auth"])
    try:
        driver.verify_connectivity()
    finally:
        driver.close()


def test_opensearch_connectivity():
    httpx = pytest.importorskip("httpx")
    from .conftest import OPENSEARCH_URL

    r = httpx.get(f"{OPENSEARCH_URL}/_cluster/health", timeout=5)
    assert r.status_code == 200
    assert r.json()["status"] in ("green", "yellow")


def test_minio_connectivity():
    minio_mod = pytest.importorskip("minio")
    from .conftest import MINIO

    client = minio_mod.Minio(
        MINIO["endpoint"],
        access_key=MINIO["access_key"],
        secret_key=MINIO["secret_key"],
        secure=False,
    )
    client.list_buckets()
