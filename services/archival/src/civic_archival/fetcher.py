"""Polite httpx wrapper used by every Phase-2 ingestion adapter.

Exactly one shared client so a single VCR monkeypatch (see
``docs/conventions/cassette-recording.md``) covers every adapter's
outbound call. Fetcher deliberately refuses to return non-2xx responses
without an explicit ``allow_error`` flag — quiet archival of an HTML
error page is a common bug class.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timezone

import httpx

__all__ = ["FetchResult", "Fetcher", "fetch"]


DEFAULT_USER_AGENT = "civic-proof-il/0.2 (+https://github.com/idanpa/civic-proof-il)"
DEFAULT_TIMEOUT = 30.0
DEFAULT_HEADERS = {
    "User-Agent": DEFAULT_USER_AGENT,
    "Accept-Language": "he,en;q=0.8",
    "Accept": "application/json, text/html;q=0.9, */*;q=0.1",
}


@dataclass(frozen=True, slots=True)
class FetchResult:
    """Result of a single HTTP fetch.

    ``fetched_at`` is always timezone-aware UTC so it feeds
    :func:`civic_clients.archive.build_archive_uri` without drift.
    """

    url: str
    status_code: int
    content: bytes
    content_type: str
    fetched_at: datetime


class Fetcher:
    """Thin wrapper around :class:`httpx.Client` with polite defaults.

    Instantiate once per process (or per worker) and reuse — httpx
    pools connections internally.
    """

    def __init__(
        self,
        *,
        timeout: float = DEFAULT_TIMEOUT,
        headers: dict[str, str] | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        merged_headers = {**DEFAULT_HEADERS, **(headers or {})}
        self._client = client or httpx.Client(
            timeout=timeout,
            headers=merged_headers,
            follow_redirects=True,
        )

    def fetch(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        allow_error: bool = False,
    ) -> FetchResult:
        """Perform one GET and return a :class:`FetchResult`.

        Honors a server-sent ``Retry-After`` header exactly once
        (single retry, then gives up). Raises on non-2xx unless
        ``allow_error`` is set.
        """

        response = self._client.get(url, headers=headers)
        if response.status_code == 429 and "retry-after" in response.headers:
            try:
                wait_s = float(response.headers["retry-after"])
            except ValueError:
                wait_s = 1.0
            time.sleep(min(wait_s, 30.0))
            response = self._client.get(url, headers=headers)

        if not allow_error and response.status_code >= 400:
            raise httpx.HTTPStatusError(
                f"{url} returned {response.status_code}",
                request=response.request,
                response=response,
            )

        return FetchResult(
            url=url,
            status_code=response.status_code,
            content=response.content,
            content_type=response.headers.get("content-type", "application/octet-stream"),
            fetched_at=datetime.now(tz=timezone.utc),
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "Fetcher":
        return self

    def __exit__(self, *_exc) -> None:
        self.close()


_default_fetcher: Fetcher | None = None


def fetch(url: str, *, allow_error: bool = False) -> FetchResult:
    """Module-level convenience that reuses a single process-wide Fetcher."""

    global _default_fetcher
    if _default_fetcher is None:
        _default_fetcher = Fetcher()
    return _default_fetcher.fetch(url, allow_error=allow_error)
