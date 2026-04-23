"""Shared Phase-2 adapter runner.

Every Knesset adapter runs the same skeleton:

1. Fetch pages (OData ``@odata.nextLink`` pagination).
2. Archive each raw page to MinIO + ``raw_fetch_objects``.
3. Parse + normalize rows from each page.
4. Upsert the normalized rows to Neo4j.

Only the parse/normalize/upsert callbacks differ between adapters.
``run_adapter`` is a thin orchestrator that wires the pieces together.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Iterable

from .odata import ODataPage, parse_odata_page
from .orchestrator import IngestRun

__all__ = ["AdapterResult", "run_adapter"]


Normalized = dict[str, Any]


@dataclass(slots=True)
class AdapterResult:
    pages: int = 0
    rows_parsed: int = 0
    rows_upserted: int = 0
    archive_uris: list[str] = field(default_factory=list)


def run_adapter(
    *,
    ingest_run: IngestRun,
    source_url: str,
    fetch: Callable,
    archive: Callable | None,
    parse: Callable[[ODataPage], Iterable[dict[str, Any]]],
    normalize: Callable[[dict[str, Any]], Iterable[Normalized]],
    upsert: Callable[[Normalized], Any],
    max_pages: int | None = None,
    page_parser: Callable[[bytes], ODataPage] = parse_odata_page,
) -> AdapterResult:
    """Run one adapter end-to-end.

    * ``fetch(url) -> FetchResult`` — wraps the httpx call.
    * ``archive(fetch_result) -> ArchiveRecord | None`` — optional
      (pass ``None`` to disable archival, e.g. in unit tests).
    * ``parse(page) -> iterable of row dicts``.
    * ``normalize(row) -> iterable of normalized dicts`` (often 1:N
      because one row expands to multiple Neo4j nodes/rels).
    * ``upsert(normalized_record) -> anything``.
    * ``page_parser(raw_bytes) -> ODataPage`` defaults to the OData
      JSON parser. CSV-backed adapters inject
      ``civic_ingest.parse_csv_page`` instead.

    Follows ``@odata.nextLink`` until exhausted or ``max_pages`` reached.
    """

    result = AdapterResult()
    url: str | None = source_url
    pages = 0
    while url is not None:
        fetch_result = fetch(url)
        page = page_parser(fetch_result.content)

        if archive is not None:
            archive_record = archive(fetch_result)
            if archive_record is not None:
                uri = getattr(archive_record, "archive_uri", None)
                if uri:
                    result.archive_uris.append(uri)

        for row in parse(page):
            result.rows_parsed += 1
            for normalized in normalize(row):
                upsert(normalized)
                result.rows_upserted += 1

        result.pages += 1
        pages += 1
        if max_pages is not None and pages >= max_pages:
            break
        url = page.next_link

    ingest_run.add_stats(
        {
            "pages": result.pages,
            "rows_parsed": result.rows_parsed,
            "rows_upserted": result.rows_upserted,
            "archive_uri_count": len(result.archive_uris),
        }
    )
    return result
