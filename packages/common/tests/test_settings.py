"""Unit tests for :mod:`civic_common.settings`."""

from __future__ import annotations

import pytest

from civic_common.settings import Settings, get_settings


def test_settings_reads_env_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("POSTGRES_HOST", "db.example")
    monkeypatch.setenv("POSTGRES_PORT", "6543")
    monkeypatch.setenv("POSTGRES_USER", "alice")
    monkeypatch.setenv("POSTGRES_PASSWORD", "s3cret")
    monkeypatch.setenv("POSTGRES_DB", "civic_test")
    monkeypatch.setenv("NEO4J_URI", "bolt://neo.example:7687")
    monkeypatch.setenv("NEO4J_USER", "neo4j")
    monkeypatch.setenv("NEO4J_PASSWORD", "neo_pw")
    monkeypatch.setenv("OPENSEARCH_URL", "http://os.example:9200")
    monkeypatch.setenv("MINIO_ENDPOINT", "minio.example:9000")
    monkeypatch.setenv("MINIO_ACCESS_KEY", "AK")
    monkeypatch.setenv("MINIO_SECRET_KEY", "SK")
    monkeypatch.setenv("MINIO_BUCKET_ARCHIVE", "civic-archive-test")

    s = Settings()
    assert s.postgres_host == "db.example"
    assert s.postgres_port == 6543
    assert s.postgres_user == "alice"
    assert s.postgres_db == "civic_test"
    assert s.neo4j_uri == "bolt://neo.example:7687"
    assert s.opensearch_url == "http://os.example:9200"
    assert s.minio_endpoint == "minio.example:9000"
    assert s.minio_bucket_archive == "civic-archive-test"


def test_get_settings_is_cached(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MINIO_BUCKET_ARCHIVE", "bucket-one")
    first = get_settings()

    monkeypatch.setenv("MINIO_BUCKET_ARCHIVE", "bucket-two")
    second = get_settings()
    assert first is second
    assert second.minio_bucket_archive == "bucket-one"

    get_settings.cache_clear()
    third = get_settings()
    assert third is not first
    assert third.minio_bucket_archive == "bucket-two"


def test_settings_defaults_optional_opensearch_creds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OPENSEARCH_USER", raising=False)
    monkeypatch.delenv("OPENSEARCH_PASSWORD", raising=False)

    s = Settings()
    assert s.opensearch_user is None
    assert s.opensearch_password is None
