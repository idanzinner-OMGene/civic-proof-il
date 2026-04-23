"""Helpers for Knesset OData JSON feeds.

Every Knesset ingestion adapter pulls from the
``https://knesset.gov.il/Odata/ParliamentInfo.svc/`` tree (OData v3
with JSON format). The real responses are shaped::

    {
      "odata.metadata": "...",          # v3 form
      "value": [ { ... }, ... ],
      "odata.nextLink": "...optional..."
    }

OData v4 endpoints use ``@odata.context`` / ``@odata.nextLink`` /
``@odata.count``. We accept both key styles so the parser works
whether upstream flips format.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Iterator

__all__ = ["ODataPage", "iter_odata_pages", "parse_odata_page"]


@dataclass(frozen=True, slots=True)
class ODataPage:
    value: list[dict[str, Any]]
    next_link: str | None
    total_count: int | None


def parse_odata_page(payload: bytes | str) -> ODataPage:
    """Parse one OData JSON response; raise ``ValueError`` on malformed input."""

    if isinstance(payload, bytes):
        payload = payload.decode("utf-8")
    data = json.loads(payload)
    if not isinstance(data, dict) or "value" not in data:
        raise ValueError("OData response missing 'value' array")
    value = data.get("value") or []
    if not isinstance(value, list):
        raise ValueError("OData 'value' is not a list")
    return ODataPage(
        value=value,
        next_link=data.get("@odata.nextLink") or data.get("odata.nextLink"),
        total_count=data.get("@odata.count") or data.get("odata.count"),
    )


def iter_odata_pages(
    start_url: str,
    *,
    fetch,
    max_pages: int | None = None,
) -> Iterator[tuple[str, bytes, ODataPage]]:
    """Iterate ``(url, raw_bytes, page)`` tuples following ``@odata.nextLink``.

    ``fetch`` is any callable ``(url) -> FetchResult``-ish object that
    returns ``.content`` and ``.url``. In production this is
    :class:`civic_archival.fetcher.Fetcher.fetch`; in tests it's a stub.
    Raises if a page is malformed.
    """

    url: str | None = start_url
    pages = 0
    while url is not None:
        result = fetch(url)
        page = parse_odata_page(result.content)
        yield url, result.content, page
        pages += 1
        if max_pages is not None and pages >= max_pages:
            return
        url = page.next_link
