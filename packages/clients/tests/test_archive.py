"""Tests for :mod:`civic_clients.archive`."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from civic_clients.archive import (
    ArchiveCoord,
    build_archive_uri,
    content_sha256,
    parse_archive_uri,
)

HELLO_SHA = "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"


def test_content_sha256_golden() -> None:
    assert content_sha256(b"hello") == HELLO_SHA


def test_build_archive_uri_canonical(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MINIO_BUCKET_ARCHIVE", "civic-archive")
    from civic_common.settings import get_settings

    get_settings.cache_clear()

    captured_at = datetime(2024, 1, 15, 9, 0, 0, tzinfo=timezone.utc)
    uri = build_archive_uri("knesset", captured_at, b"hello", "html")

    assert uri == f"s3://civic-archive/knesset/2024/01/15/{HELLO_SHA}.html"


def test_build_archive_uri_uses_current_bucket(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MINIO_BUCKET_ARCHIVE", "my-custom-bucket")
    from civic_common.settings import get_settings

    get_settings.cache_clear()

    captured_at = datetime(2024, 1, 15, 9, 0, 0, tzinfo=timezone.utc)
    uri = build_archive_uri("gov_il", captured_at, b"hello", "pdf")

    assert uri.startswith("s3://my-custom-bucket/gov_il/2024/01/15/")
    assert uri.endswith(".pdf")


def test_build_archive_uri_normalizes_extension(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MINIO_BUCKET_ARCHIVE", "civic-archive")
    from civic_common.settings import get_settings

    get_settings.cache_clear()

    captured_at = datetime(2024, 1, 15, tzinfo=timezone.utc)
    uri = build_archive_uri("knesset", captured_at, b"hello", ".PDF")
    assert uri.endswith(".pdf")


def test_build_archive_uri_rejects_unknown_source_family() -> None:
    captured_at = datetime(2024, 1, 15, tzinfo=timezone.utc)
    with pytest.raises(ValueError, match="source_family"):
        build_archive_uri("foo", captured_at, b"hello", "html")


def test_build_archive_uri_rejects_naive_datetime() -> None:
    naive = datetime(2024, 1, 15, 9, 0, 0)
    with pytest.raises(ValueError, match="timezone-aware"):
        build_archive_uri("knesset", naive, b"hello", "html")


def test_build_archive_uri_rejects_empty_extension() -> None:
    captured_at = datetime(2024, 1, 15, tzinfo=timezone.utc)
    with pytest.raises(ValueError, match="non-empty"):
        build_archive_uri("knesset", captured_at, b"hello", ".")


def test_parse_archive_uri_roundtrip(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MINIO_BUCKET_ARCHIVE", "civic-archive")
    from civic_common.settings import get_settings

    get_settings.cache_clear()

    captured_at = datetime(2024, 1, 15, 9, 0, 0, tzinfo=timezone.utc)
    uri = build_archive_uri("elections", captured_at, b"hello", "json")
    coord = parse_archive_uri(uri)

    assert isinstance(coord, ArchiveCoord)
    assert coord.bucket == "civic-archive"
    assert coord.source_family == "elections"
    assert coord.year == 2024
    assert coord.month == 1
    assert coord.day == 15
    assert coord.sha256 == HELLO_SHA
    assert coord.extension == "json"


def test_parse_archive_uri_rejects_malformed() -> None:
    with pytest.raises(ValueError, match="canonical archive URI"):
        parse_archive_uri("s3://bad")
    with pytest.raises(ValueError, match="canonical archive URI"):
        parse_archive_uri("http://example/knesset/2024/01/15/abc.pdf")


def test_parse_archive_uri_rejects_unknown_family() -> None:
    uri = f"s3://civic-archive/weird/2024/01/15/{HELLO_SHA}.html"
    with pytest.raises(ValueError, match="source_family"):
        parse_archive_uri(uri)


def test_parse_archive_uri_rejects_invalid_date() -> None:
    uri = f"s3://civic-archive/knesset/2024/02/30/{HELLO_SHA}.html"
    with pytest.raises(ValueError, match="invalid calendar date"):
        parse_archive_uri(uri)
