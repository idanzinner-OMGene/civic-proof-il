"""Unit tests for civic_archival.archiver.

These are pure unit tests — the Postgres connection and MinIO client are
monkeypatched. The live round-trip lives in
``tests/integration/test_phase2_ingestion.py``.
"""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from civic_archival import archive_payload
from civic_archival.archiver import extension_from_content_type
from civic_archival.fetcher import FetchResult


@pytest.fixture(autouse=True)
def _clear_settings():
    from civic_common.settings import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _make_fetch_result(content: bytes = b"hello") -> FetchResult:
    return FetchResult(
        url="https://example.com/odata",
        status_code=200,
        content=content,
        content_type="application/json",
        fetched_at=datetime(2026, 4, 21, 9, 0, tzinfo=timezone.utc),
    )


class _FakeCursor:
    def __init__(self, conn: "_FakeConn"):
        self._conn = conn
        self._last = None

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False

    def execute(self, query, params=None):
        q = str(query).upper()
        if "SELECT" in q and "INSERT" not in q:
            self._last = self._conn.select_fn(params)
        elif "INSERT" in q:
            self._conn.inserts.append(params)
            self._last = None

    def fetchone(self):
        return self._last


class _FakeConn:
    def __init__(self, select_fn):
        self.select_fn = select_fn
        self.inserts: list = []
        self.committed = 0

    def cursor(self, *, row_factory=None):
        return _FakeCursor(self)

    def commit(self):
        self.committed += 1

    def close(self):
        pass


def test_archive_payload_writes_once_on_fresh_content(monkeypatch):
    put_calls: list[tuple] = []

    def fake_put(uri, content, content_type):
        put_calls.append((uri, content, content_type))
        return "object"

    monkeypatch.setattr("civic_clients.minio_client.put_archive_object", fake_put)
    monkeypatch.setattr("civic_clients.minio_client.ensure_bucket", lambda: "civic-archive")

    conn = _FakeConn(select_fn=lambda _params: None)

    record = archive_payload(
        source_family="knesset",
        source_url="https://example.com/odata",
        fetch_result=_make_fetch_result(),
        ingest_run_id=1,
        source_tier=1,
        extension_hint="json",
        conn=conn,
    )

    assert record.created is True
    assert record.source_tier == 1
    assert record.archive_uri.startswith("s3://civic-archive/knesset/2026/04/21/")
    assert record.archive_uri.endswith(".json")
    assert len(put_calls) == 1
    assert len(conn.inserts) == 1


def test_archive_payload_is_idempotent_on_known_digest(monkeypatch):
    put_calls: list[tuple] = []

    def fake_put(*a, **kw):
        put_calls.append(a)
        return "object"

    monkeypatch.setattr("civic_clients.minio_client.put_archive_object", fake_put)
    monkeypatch.setattr("civic_clients.minio_client.ensure_bucket", lambda: "civic-archive")

    import uuid

    existing_object_id = uuid.uuid4()

    def fake_select(_params):
        return {
            "object_id": existing_object_id,
            "ingest_run_id": 42,
            "source_url": "https://example.com/first",
            "archive_uri": "s3://civic-archive/knesset/2026/04/01/" + "a" * 64 + ".json",
            "content_sha256": "a" * 64,
            "content_type": "application/json",
            "byte_size": 5,
            "source_tier": 1,
        }

    conn = _FakeConn(select_fn=fake_select)

    record = archive_payload(
        source_family="knesset",
        source_url="https://example.com/second",
        fetch_result=_make_fetch_result(),
        ingest_run_id=99,
        source_tier=1,
        extension_hint="json",
        conn=conn,
    )

    assert record.created is False
    assert record.object_id == existing_object_id
    assert record.ingest_run_id == 42  # original stays
    assert put_calls == []
    assert conn.inserts == []


def test_extension_from_content_type_known_and_unknown():
    assert extension_from_content_type("application/json") == "json"
    assert extension_from_content_type("text/html; charset=utf-8") == "html"
    assert extension_from_content_type("application/octet-stream") == "bin"


def test_archive_payload_rejects_bad_family(monkeypatch):
    conn = _FakeConn(select_fn=lambda _p: None)
    with pytest.raises(ValueError, match="source_family"):
        archive_payload(
            source_family="unknown",  # type: ignore[arg-type]
            source_url="https://example.com",
            fetch_result=_make_fetch_result(),
            ingest_run_id=1,
            source_tier=1,
            conn=conn,
        )
