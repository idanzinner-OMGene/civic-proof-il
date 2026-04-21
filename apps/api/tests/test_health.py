"""Tests for /healthz and /readyz endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.clients import (
    minio_client,
    neo4j_client,
    opensearch_client,
    postgres,
)
from api.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_healthz_returns_ok(client: TestClient) -> None:
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_readyz_all_healthy(client: TestClient) -> None:
    resp = client.get("/readyz")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ready"
    assert body["components"] == {
        "postgres": True,
        "neo4j": True,
        "opensearch": True,
        "minio": True,
    }


def test_readyz_returns_503_when_dependency_unhealthy(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(postgres, "ping_postgres", lambda: False)
    resp = client.get("/readyz")
    assert resp.status_code == 503
    body = resp.json()
    assert body["status"] == "not_ready"
    assert body["components"]["postgres"] is False


def test_readyz_components_contain_all_keys(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(postgres, "ping_postgres", lambda: True)
    monkeypatch.setattr(neo4j_client, "ping_neo4j", lambda: False)
    monkeypatch.setattr(opensearch_client, "ping_opensearch", lambda: True)
    monkeypatch.setattr(minio_client, "ping_minio", lambda: False)

    resp = client.get("/readyz")
    body = resp.json()
    assert set(body["components"].keys()) == {
        "postgres",
        "neo4j",
        "opensearch",
        "minio",
    }
    assert resp.status_code == 503
