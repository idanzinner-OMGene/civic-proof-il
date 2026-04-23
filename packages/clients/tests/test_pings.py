"""Tests for the four ``ping`` helpers.

Each ping opens a client/connection and catches exceptions — we unit-test
that contract by monkey-patching the underlying factory to raise / succeed
and asserting the boolean return.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from civic_clients import minio_client, neo4j, opensearch, postgres


# ---------------------------------------------------------------------------
# Postgres
# ---------------------------------------------------------------------------


class _FakeCursor:
    def __enter__(self) -> "_FakeCursor":
        return self

    def __exit__(self, *_exc: object) -> None:
        return None

    def execute(self, *_args: object, **_kwargs: object) -> None:
        return None

    def fetchone(self) -> tuple[int]:
        return (1,)


class _FakeConn:
    def cursor(self) -> _FakeCursor:
        return _FakeCursor()

    def __enter__(self) -> "_FakeConn":
        return self

    def __exit__(self, *_exc: object) -> None:
        return None


def test_postgres_ping_true(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(postgres, "make_connection", lambda: _FakeConn())
    assert postgres.ping() is True


def test_postgres_ping_false_on_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    def _boom() -> _FakeConn:
        raise RuntimeError("nope")

    monkeypatch.setattr(postgres, "make_connection", _boom)
    assert postgres.ping() is False


# ---------------------------------------------------------------------------
# Neo4j
# ---------------------------------------------------------------------------


def test_neo4j_ping_true(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = SimpleNamespace(verify_connectivity=lambda: None)
    monkeypatch.setattr(neo4j, "make_driver", lambda: fake)
    assert neo4j.ping() is True


def test_neo4j_ping_false_on_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    def _boom() -> object:
        raise ConnectionError("unreachable")

    monkeypatch.setattr(neo4j, "make_driver", _boom)
    assert neo4j.ping() is False


# ---------------------------------------------------------------------------
# OpenSearch
# ---------------------------------------------------------------------------


def test_opensearch_ping_true(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = SimpleNamespace(ping=lambda: True)
    monkeypatch.setattr(opensearch, "make_client", lambda: fake)
    assert opensearch.ping() is True


def test_opensearch_ping_false_when_client_returns_false(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = SimpleNamespace(ping=lambda: False)
    monkeypatch.setattr(opensearch, "make_client", lambda: fake)
    assert opensearch.ping() is False


def test_opensearch_ping_false_on_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    def _boom() -> object:
        raise RuntimeError("cluster down")

    monkeypatch.setattr(opensearch, "make_client", _boom)
    assert opensearch.ping() is False


# ---------------------------------------------------------------------------
# MinIO
# ---------------------------------------------------------------------------


def test_minio_ping_true(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = SimpleNamespace(list_buckets=lambda: [])
    monkeypatch.setattr(minio_client, "make_client", lambda: fake)
    assert minio_client.ping() is True


def test_minio_ping_false_on_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    def _boom() -> object:
        raise RuntimeError("minio down")

    monkeypatch.setattr(minio_client, "make_client", _boom)
    assert minio_client.ping() is False
