"""Unit tests for civic_archival.fetcher."""

from __future__ import annotations

import httpx
import pytest

from civic_archival.fetcher import DEFAULT_USER_AGENT, FetchResult, Fetcher


def _stub_client(handler):
    transport = httpx.MockTransport(handler)
    return httpx.Client(transport=transport, headers={"User-Agent": DEFAULT_USER_AGENT})


def test_fetch_returns_fetch_result_with_utc_timestamp():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["User-Agent"] == DEFAULT_USER_AGENT
        return httpx.Response(
            200,
            content=b'{"ok": true}',
            headers={"content-type": "application/json"},
        )

    with Fetcher(client=_stub_client(handler)) as f:
        result = f.fetch("https://example.com/odata")

    assert isinstance(result, FetchResult)
    assert result.status_code == 200
    assert result.content == b'{"ok": true}'
    assert result.content_type == "application/json"
    assert result.fetched_at.tzinfo is not None


def test_fetch_raises_on_4xx_without_allow_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, content=b"not found")

    with Fetcher(client=_stub_client(handler)) as f:
        with pytest.raises(httpx.HTTPStatusError):
            f.fetch("https://example.com/missing")


def test_fetch_allows_error_on_opt_in():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, content=b"not found")

    with Fetcher(client=_stub_client(handler)) as f:
        result = f.fetch("https://example.com/missing", allow_error=True)

    assert result.status_code == 404


def test_fetch_retries_once_on_429(monkeypatch):
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(429, headers={"retry-after": "0"})
        return httpx.Response(200, content=b"ok")

    monkeypatch.setattr("civic_archival.fetcher.time.sleep", lambda _s: None)

    with Fetcher(client=_stub_client(handler)) as f:
        result = f.fetch("https://example.com/rate")

    assert calls["n"] == 2
    assert result.status_code == 200
