"""Idempotent archival: hash → MinIO put → raw_fetch_objects row.

Idempotency key is ``content_sha256`` (which has a UNIQUE constraint in
``raw_fetch_objects`` — see ``0002_phase1_domain_schema.py``). Two
archival calls for the same bytes return the same ``ArchiveRecord``;
the MinIO object is written at most once.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Literal

import psycopg
from psycopg import sql
from psycopg.rows import dict_row

from civic_clients import minio_client
from civic_clients.archive import SOURCE_FAMILIES, build_archive_uri, content_sha256

from .fetcher import FetchResult

__all__ = [
    "ArchiveRecord",
    "archive_payload",
    "extension_from_content_type",
]


SourceFamily = Literal["knesset", "gov_il", "elections"]


@dataclass(frozen=True, slots=True)
class ArchiveRecord:
    """The persisted state after a successful archival call."""

    object_id: uuid.UUID
    ingest_run_id: int
    archive_uri: str
    content_sha256: str
    byte_size: int
    source_url: str
    content_type: str
    source_tier: int
    created: bool


_CONTENT_TYPE_EXT = {
    "application/json": "json",
    "application/xml": "xml",
    "application/pdf": "pdf",
    "text/html": "html",
    "text/xml": "xml",
    "text/csv": "csv",
    "text/plain": "txt",
}


def extension_from_content_type(content_type: str) -> str:
    """Map a Content-Type header to a canonical archive extension.

    Falls back to ``"bin"`` for unknown types so the archive URI still
    parses; callers should pass an explicit ``extension_hint`` whenever
    they already know the format (the OData adapters do).
    """

    base = content_type.split(";", 1)[0].strip().lower()
    return _CONTENT_TYPE_EXT.get(base, "bin")


def archive_payload(
    *,
    source_family: SourceFamily,
    source_url: str,
    fetch_result: FetchResult,
    ingest_run_id: int,
    source_tier: int,
    extension_hint: str | None = None,
    conn: psycopg.Connection | None = None,
) -> ArchiveRecord:
    """Archive ``fetch_result.content`` idempotently.

    * Computes ``content_sha256`` once.
    * If a ``raw_fetch_objects`` row with this ``content_sha256`` already
      exists, returns its :class:`ArchiveRecord` with ``created=False``
      (neither MinIO nor Postgres is re-written).
    * Otherwise: writes to MinIO via
      :func:`civic_clients.minio_client.put_archive_object` and inserts
      a fresh row. ``created=True``.

    Caller may pass an open ``psycopg.Connection`` to participate in an
    outer transaction; if ``None`` a new connection is opened and
    committed here.
    """

    if source_family not in SOURCE_FAMILIES:
        raise ValueError(f"unknown source_family {source_family!r}")
    if source_tier not in (1, 2, 3):
        raise ValueError(f"source_tier must be 1, 2, or 3 (got {source_tier!r})")

    digest = content_sha256(fetch_result.content)
    extension = extension_hint or extension_from_content_type(fetch_result.content_type)

    owns_conn = conn is None
    if owns_conn:
        from civic_clients.postgres import make_connection

        conn = make_connection()

    try:
        existing = _find_existing(conn, digest)
        if existing is not None:
            return ArchiveRecord(
                object_id=existing["object_id"],
                ingest_run_id=existing["ingest_run_id"],
                archive_uri=existing["archive_uri"],
                content_sha256=existing["content_sha256"],
                byte_size=existing["byte_size"],
                source_url=existing["source_url"],
                content_type=existing["content_type"] or fetch_result.content_type,
                source_tier=existing["source_tier"],
                created=False,
            )

        archive_uri = build_archive_uri(
            source_family=source_family,
            captured_at=fetch_result.fetched_at,
            content=fetch_result.content,
            extension=extension,
        )

        minio_client.ensure_bucket()
        minio_client.put_archive_object(
            archive_uri,
            fetch_result.content,
            content_type=fetch_result.content_type,
        )

        object_id = uuid.uuid4()
        _insert_raw_fetch_object(
            conn,
            object_id=object_id,
            ingest_run_id=ingest_run_id,
            source_url=source_url,
            archive_uri=archive_uri,
            content_sha256=digest,
            content_type=fetch_result.content_type,
            byte_size=len(fetch_result.content),
            source_tier=source_tier,
        )
        if owns_conn:
            conn.commit()

        return ArchiveRecord(
            object_id=object_id,
            ingest_run_id=ingest_run_id,
            archive_uri=archive_uri,
            content_sha256=digest,
            byte_size=len(fetch_result.content),
            source_url=source_url,
            content_type=fetch_result.content_type,
            source_tier=source_tier,
            created=True,
        )
    finally:
        if owns_conn and conn is not None:
            conn.close()


def _find_existing(conn: psycopg.Connection, digest: str) -> dict | None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            sql.SQL(
                """
                SELECT object_id, ingest_run_id, source_url, archive_uri,
                       content_sha256, content_type, byte_size, source_tier
                  FROM raw_fetch_objects
                 WHERE content_sha256 = %s
                 LIMIT 1
                """
            ),
            (digest,),
        )
        return cur.fetchone()


def _insert_raw_fetch_object(
    conn: psycopg.Connection,
    *,
    object_id: uuid.UUID,
    ingest_run_id: int,
    source_url: str,
    archive_uri: str,
    content_sha256: str,
    content_type: str,
    byte_size: int,
    source_tier: int,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO raw_fetch_objects
              (object_id, ingest_run_id, source_url, archive_uri,
               content_sha256, content_type, byte_size, source_tier)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                str(object_id),
                ingest_run_id,
                source_url,
                archive_uri,
                content_sha256,
                content_type,
                byte_size,
                source_tier,
            ),
        )
